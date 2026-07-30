from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from knowledge_search.api.app import create_app
from knowledge_search.api.services import (
    DocumentApiServices,
    ReadinessService,
)
from knowledge_search.application import (
    AnswerService,
    DocumentDeletionService,
    DocumentQueries,
    DocumentSubmissionService,
    SearchService,
)
from knowledge_search.application.ingestion import IngestionJobProcessor
from knowledge_search.config import Settings
from knowledge_search.domain import Chunk, Document, DocumentStatus, IngestionJobStatus
from knowledge_search.generation import DisabledAnswerGenerator
from knowledge_search.ingestion import (
    DocumentContentPreparer,
    DocumentExtractorRegistry,
    MarkdownExtractor,
    PdfExtractor,
    SectionAwareChunker,
    TextExtractor,
)
from knowledge_search.ingestion.errors import EmbeddingError, QueueDispatchError
from knowledge_search.persistence import (
    PostgresSearchRepository,
    PostgresSessionFactory,
    SqlAlchemyChunkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionJobRepository,
)
from knowledge_search.persistence.models import CorpusRevisionRecord, IngestionJobRecord
from knowledge_search.providers import LocalDocumentStore
from knowledge_search.retrieval import RetrievalCandidate, SearchFilters

pytestmark = pytest.mark.integration


class RecordingQueue:
    def __init__(self) -> None:
        self.job_ids: list[UUID] = []

    def enqueue(self, job_id: UUID) -> None:
        self.job_ids.append(job_id)

    def is_ready(self) -> bool:
        return True


class UnavailableQueue:
    def enqueue(self, job_id: UUID) -> None:
        raise QueueDispatchError(f"queue rejected {job_id}")

    def is_ready(self) -> bool:
        return False


class DeterministicEmbeddings:
    model_name = "deterministic-test-embeddings"
    dimensions = 3

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [
            [
                float(len(text)),
                float(text.count("backup")),
                float(text.count("recovery")),
            ]
            for text in texts
        ]


class FailingEmbeddings:
    model_name = "failing-test-embeddings"
    dimensions = 3

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingError(f"embedding failed for {len(texts)} chunks")


class RecordingVectorIndex:
    def __init__(self) -> None:
        self.dimensions: int | None = None
        self.points: dict[UUID, tuple[Document, Chunk, list[float]]] = {}
        self.deleted_document_ids: list[UUID] = []

    def ensure_collection(self, *, dimensions: int) -> None:
        self.dimensions = dimensions

    def upsert(
        self,
        *,
        document: Document,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> None:
        self.points.update(
            {
                chunk.id: (document, chunk, vector)
                for chunk, vector in zip(chunks, vectors, strict=True)
            }
        )

    def delete_document(self, document_id: UUID) -> None:
        self.deleted_document_ids.append(document_id)
        self.points = {
            chunk_id: value
            for chunk_id, value in self.points.items()
            if value[1].document_id != document_id
        }

    def search(
        self,
        *,
        vector: list[float],
        limit: int,
        filters: SearchFilters,
    ) -> list[RetrievalCandidate]:
        matching = [
            (chunk_id, sum(left * right for left, right in zip(point, vector, strict=True)))
            for chunk_id, (document, _, point) in self.points.items()
            if (not filters.document_ids or document.id in filters.document_ids)
            and (not filters.media_types or document.media_type in filters.media_types)
        ]
        matching.sort(key=lambda item: (-item[1], str(item[0])))
        return [
            RetrievalCandidate(chunk_id=chunk_id, rank=rank, score=score)
            for rank, (chunk_id, score) in enumerate(matching[:limit], start=1)
        ]

    def is_ready(self) -> bool:
        return True


def _content_preparer() -> DocumentContentPreparer:
    return DocumentContentPreparer(
        extractors=DocumentExtractorRegistry(
            text=TextExtractor(),
            markdown=MarkdownExtractor(),
            pdf=PdfExtractor(max_pages=10),
        ),
        chunker=SectionAwareChunker(size=30, overlap=5),
    )


@contextmanager
def _api_client(
    *,
    database_url: str,
    storage_path: Path,
    queue: RecordingQueue | UnavailableQueue,
    search_vector_index: RecordingVectorIndex | None = None,
) -> Iterator[tuple[TestClient, PostgresSessionFactory]]:
    sessions = PostgresSessionFactory(SecretStr(database_url))
    search_service = (
        SearchService(
            repository=PostgresSearchRepository(sessions),
            embeddings=DeterministicEmbeddings(),
            vector_index=search_vector_index,
            candidate_multiplier=4,
            rrf_k=60,
        )
        if search_vector_index is not None
        else None
    )
    store = LocalDocumentStore(storage_path)
    submissions = DocumentSubmissionService(
        sessions=sessions,
        store=store,
        queue=queue,
        max_upload_bytes=4_096,
    )
    deletion_vector_index = search_vector_index or RecordingVectorIndex()
    services = DocumentApiServices(
        submissions=submissions,
        queries=DocumentQueries(sessions),
        readiness=ReadinessService(
            database=sessions,
            queue=queue,
            vector_index=RecordingVectorIndex(),
        ),
        shutdown=sessions.dispose,
        search=search_service,
        answers=(
            AnswerService(
                search=search_service,
                generator=DisabledAnswerGenerator(),
            )
            if search_service is not None
            else None
        ),
        deletions=DocumentDeletionService(
            sessions=sessions,
            store=store,
            vector_index=deletion_vector_index,
        ),
    )
    settings = Settings(
        environment="test",
        database_url=SecretStr(database_url),
        redis_url=SecretStr("redis://127.0.0.1:6379/0"),
        document_storage_path=storage_path,
        max_upload_bytes=4_096,
    )
    with TestClient(create_app(settings, document_services=services)) as client:
        yield client, sessions
    sessions.dispose()


def test_upload_worker_and_status_endpoints_complete_document_ingestion(
    migrated_database_url: str,
    tmp_path: Path,
) -> None:
    queue = RecordingQueue()
    vector_index = RecordingVectorIndex()

    with _api_client(
        database_url=migrated_database_url,
        storage_path=tmp_path,
        queue=queue,
        search_vector_index=vector_index,
    ) as (client, sessions):
        response = client.post(
            "/api/v1/documents",
            files={
                "document": (
                    "operations.md",
                    (
                        b"# Operations\n\nDatabase backups are retained for thirty days.\n\n"
                        b"## Recovery\n\nRecovery exercises are completed every month.\n"
                    ),
                    "text/markdown",
                )
            },
        )

        assert response.status_code == 202
        payload = response.json()
        document_id = UUID(payload["document"]["id"])
        job_id = UUID(payload["ingestion_job"]["id"])
        assert payload["document"]["status"] == "queued"
        assert payload["ingestion_job"]["status"] == "queued"
        assert queue.job_ids == [job_id]

        processor = IngestionJobProcessor(
            sessions=sessions,
            store=LocalDocumentStore(tmp_path),
            content_preparer=_content_preparer(),
            embeddings=DeterministicEmbeddings(),
            vector_index=vector_index,
        )
        processor.process(job_id)
        processor.process(job_id)

        document_response = client.get(f"/api/v1/documents/{document_id}")
        job_response = client.get(f"/api/v1/ingestion-jobs/{job_id}")
        assert document_response.status_code == 200
        assert document_response.json()["status"] == "ready"
        assert job_response.status_code == 200
        assert job_response.json()["status"] == "succeeded"
        assert job_response.json()["attempt_count"] == 1

        with sessions.transaction() as session:
            chunks = SqlAlchemyChunkRepository(session).list_for_document(document_id)
            revision = session.get(CorpusRevisionRecord, 1)

        assert len(chunks) == 2
        assert chunks[0].locator.section_path == ("Operations",)
        assert chunks[1].locator.section_path == ("Operations", "Recovery")
        assert set(vector_index.points) == {chunk.id for chunk in chunks}
        assert vector_index.dimensions == 3
        assert revision is not None
        assert revision.revision == 1

        keyword_response = client.get(
            "/api/v1/search",
            params={"q": "monthly recovery", "mode": "keyword"},
        )
        vector_response = client.get(
            "/api/v1/search",
            params={"q": "monthly recovery", "mode": "vector"},
        )
        hybrid_response = client.get(
            "/api/v1/search",
            params={"q": "monthly recovery", "mode": "hybrid"},
        )

        assert keyword_response.status_code == 200
        assert vector_response.status_code == 200
        assert hybrid_response.status_code == 200
        keyword_item = keyword_response.json()["items"][0]
        assert keyword_item["citation"]["document_id"] == str(document_id)
        assert keyword_item["citation"]["section_path"] == ["Operations", "Recovery"]
        assert keyword_item["keyword_rank"] == 1
        assert keyword_item["vector_rank"] is None
        assert vector_response.json()["items"][0]["vector_rank"] == 1
        assert hybrid_response.json()["items"][0]["citation"]["original_filename"] == (
            "operations.md"
        )
        filtered_response = client.get(
            "/api/v1/search",
            params={
                "q": "monthly recovery",
                "mode": "hybrid",
                "media_type": "application/pdf",
            },
        )
        blank_response = client.get("/api/v1/search", params={"q": " "})
        assert filtered_response.status_code == 200
        assert filtered_response.json()["items"] == []
        assert blank_response.status_code == 400
        assert blank_response.json()["code"] == "invalid_search_query"

        answer_response = client.post(
            "/api/v1/answers",
            json={
                "question": "How often are recovery exercises completed?",
                "mode": "hybrid",
                "limit": 2,
            },
        )
        assert answer_response.status_code == 200
        assert answer_response.json()["answer"] is None
        assert answer_response.json()["generation_status"] == "disabled"
        assert answer_response.json()["sources"]

        delete_response = client.delete(f"/api/v1/documents/{document_id}")
        assert delete_response.status_code == 204
        assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
        assert (
            client.get(
                "/api/v1/search",
                params={"q": "monthly recovery", "mode": "keyword"},
            ).json()["items"]
            == []
        )
        assert vector_index.points == {}
        assert list(tmp_path.glob("*/source.md")) == []
        with sessions.transaction() as session:
            deletion_revision = session.get(CorpusRevisionRecord, 1)
        assert deletion_revision is not None
        assert deletion_revision.revision == 2


def test_queued_document_cannot_be_deleted(
    migrated_database_url: str,
    tmp_path: Path,
) -> None:
    queue = RecordingQueue()

    with _api_client(
        database_url=migrated_database_url,
        storage_path=tmp_path,
        queue=queue,
    ) as (client, _):
        upload = client.post(
            "/api/v1/documents",
            files={"document": ("policy.txt", b"Retain backups.", "text/plain")},
        )
        document_id = upload.json()["document"]["id"]

        response = client.delete(f"/api/v1/documents/{document_id}")

        assert response.status_code == 409
        assert response.json()["code"] == "document_deletion_conflict"
        assert response.json()["extensions"]["document_status"] == "queued"


def test_duplicate_upload_returns_existing_document_reference(
    migrated_database_url: str,
    tmp_path: Path,
) -> None:
    queue = RecordingQueue()

    with _api_client(
        database_url=migrated_database_url,
        storage_path=tmp_path,
        queue=queue,
    ) as (client, _):
        first = client.post(
            "/api/v1/documents",
            files={"document": ("policy.txt", b"Retain backups.", "text/plain")},
        )
        duplicate = client.post(
            "/api/v1/documents",
            files={"document": ("policy-copy.txt", b"Retain backups.", "text/plain")},
        )

        assert first.status_code == 202
        assert duplicate.status_code == 409
        assert duplicate.headers["content-type"].startswith("application/problem+json")
        assert (
            duplicate.json()["extensions"]["existing_document_id"] == first.json()["document"]["id"]
        )
        assert queue.job_ids == [UUID(first.json()["ingestion_job"]["id"])]
        assert len(list(tmp_path.glob("*/source.txt"))) == 1


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "expected_status", "expected_code"),
    [
        (
            "policy.exe",
            "text/plain",
            b"Retain backups.",
            415,
            "media_type_mismatch",
        ),
        (
            "policy.txt",
            "application/octet-stream",
            b"Retain backups.",
            415,
            "unsupported_media_type",
        ),
        (
            "policy.txt",
            "text/plain",
            b"x" * 4_097,
            413,
            "file_too_large",
        ),
    ],
)
def test_upload_validation_returns_problem_details(
    migrated_database_url: str,
    tmp_path: Path,
    filename: str,
    content_type: str,
    content: bytes,
    expected_status: int,
    expected_code: str,
) -> None:
    queue = RecordingQueue()

    with _api_client(
        database_url=migrated_database_url,
        storage_path=tmp_path,
        queue=queue,
    ) as (client, _):
        response = client.post(
            "/api/v1/documents",
            files={"document": (filename, content, content_type)},
        )

        assert response.status_code == expected_status
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["code"] == expected_code
        assert queue.job_ids == []
        assert list(tmp_path.glob("*/source.*")) == []


def test_queue_failure_marks_persisted_document_and_job_failed(
    migrated_database_url: str,
    tmp_path: Path,
) -> None:
    with _api_client(
        database_url=migrated_database_url,
        storage_path=tmp_path,
        queue=UnavailableQueue(),
    ) as (client, sessions):
        response = client.post(
            "/api/v1/documents",
            files={"document": ("policy.txt", b"Retain backups.", "text/plain")},
        )

        assert response.status_code == 503
        assert response.json()["code"] == "queue_unavailable"
        document_id = UUID(response.json()["extensions"]["document_id"])
        job_id = UUID(response.json()["extensions"]["ingestion_job_id"])
        documents = client.get("/api/v1/documents").json()["items"]
        assert len(documents) == 1
        assert UUID(documents[0]["id"]) == document_id
        assert client.get(f"/api/v1/ingestion-jobs/{job_id}").json()["status"] == "failed"

        with sessions.transaction() as session:
            document = SqlAlchemyDocumentRepository(session).get(document_id)
            job = session.scalar(
                select(IngestionJobRecord).where(IngestionJobRecord.document_id == document_id)
            )

        assert document is not None
        assert document.status is DocumentStatus.FAILED
        assert document.failure_code == "queue_unavailable"
        assert job is not None
        assert job.status == IngestionJobStatus.FAILED.value
        assert job.failure_code == "queue_unavailable"


def test_worker_failure_is_recorded_and_vector_cleanup_is_attempted(
    migrated_database_url: str,
    tmp_path: Path,
) -> None:
    queue = RecordingQueue()
    vector_index = RecordingVectorIndex()

    with _api_client(
        database_url=migrated_database_url,
        storage_path=tmp_path,
        queue=queue,
    ) as (client, sessions):
        response = client.post(
            "/api/v1/documents",
            files={"document": ("policy.txt", b"Retain backups.", "text/plain")},
        )
        document_id = UUID(response.json()["document"]["id"])
        job_id = UUID(response.json()["ingestion_job"]["id"])
        processor = IngestionJobProcessor(
            sessions=sessions,
            store=LocalDocumentStore(tmp_path),
            content_preparer=_content_preparer(),
            embeddings=FailingEmbeddings(),
            vector_index=vector_index,
        )

        with pytest.raises(EmbeddingError):
            processor.process(job_id)

        with sessions.transaction() as session:
            document = SqlAlchemyDocumentRepository(session).get(document_id)
            job = SqlAlchemyIngestionJobRepository(session).get(job_id)

        assert document is not None
        assert document.status is DocumentStatus.FAILED
        assert document.failure_code == "embedding_failed"
        assert job is not None
        assert job.status is IngestionJobStatus.FAILED
        assert job.failure_code == "embedding_failed"
        assert vector_index.deleted_document_ids == [document_id]
