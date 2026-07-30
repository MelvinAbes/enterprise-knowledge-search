from contextlib import suppress
from uuid import UUID

from knowledge_search.application.errors import (
    DocumentNotFoundError,
    IngestionJobNotFoundError,
)
from knowledge_search.domain import DocumentStatus, IngestionJobStatus
from knowledge_search.ingestion.errors import (
    EmbeddingError,
    IngestionError,
    VectorIndexError,
)
from knowledge_search.ingestion.pipeline import DocumentContentPreparer
from knowledge_search.ingestion.ports import DocumentStore, EmbeddingProvider, VectorIndex
from knowledge_search.persistence import (
    PostgresSessionFactory,
    SqlAlchemyChunkRepository,
    SqlAlchemyCorpusRevisionRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionJobRepository,
)


class IngestionJobProcessor:
    def __init__(
        self,
        *,
        sessions: PostgresSessionFactory,
        store: DocumentStore,
        content_preparer: DocumentContentPreparer,
        embeddings: EmbeddingProvider,
        vector_index: VectorIndex,
    ) -> None:
        self._sessions = sessions
        self._store = store
        self._content_preparer = content_preparer
        self._embeddings = embeddings
        self._vector_index = vector_index

    def process(self, job_id: UUID) -> None:
        document_id = self._start_job(job_id)
        if document_id is None:
            return
        try:
            with self._sessions.transaction() as session:
                document = SqlAlchemyDocumentRepository(session).get(document_id)
            if document is None:
                raise DocumentNotFoundError(document_id)

            with self._store.open(document.storage_key) as source:
                chunks = self._content_preparer.prepare(document, source)
            vectors = self._embeddings.embed_documents([chunk.text for chunk in chunks])
            self._vector_index.ensure_collection(dimensions=self._embeddings.dimensions)
            self._vector_index.upsert(
                document=document,
                chunks=chunks,
                vectors=vectors,
            )

            with self._sessions.transaction() as session:
                document_repository = SqlAlchemyDocumentRepository(session)
                job_repository = SqlAlchemyIngestionJobRepository(session)
                stored_document = document_repository.get(document_id)
                stored_job = job_repository.get(job_id)
                if stored_document is None:
                    raise DocumentNotFoundError(document_id)
                if stored_job is None:
                    raise IngestionJobNotFoundError(job_id)

                chunk_repository = SqlAlchemyChunkRepository(session)
                chunk_repository.delete_for_document(document_id)
                chunk_repository.add_many(chunks)
                document_repository.save(stored_document.mark_ready())
                job_repository.save(stored_job.succeed())
                SqlAlchemyCorpusRevisionRepository(session).increment()
        except Exception as error:
            self._mark_failed(
                document_id=document_id,
                job_id=job_id,
                failure_code=_failure_code(error),
            )
            with suppress(VectorIndexError):
                self._vector_index.delete_document(document_id)
            raise

    def _start_job(self, job_id: UUID) -> UUID | None:
        with self._sessions.transaction() as session:
            document_repository = SqlAlchemyDocumentRepository(session)
            job_repository = SqlAlchemyIngestionJobRepository(session)
            job = job_repository.get(job_id)
            if job is None:
                raise IngestionJobNotFoundError(job_id)
            document = document_repository.get(job.document_id)
            if document is None:
                raise DocumentNotFoundError(job.document_id)

            if (
                job.status is IngestionJobStatus.SUCCEEDED
                and document.status is DocumentStatus.READY
            ):
                return None
            if job.status is IngestionJobStatus.FAILED and document.status is DocumentStatus.FAILED:
                job = job.requeue()
                document = document.queue()
            if (
                job.status is not IngestionJobStatus.QUEUED
                or document.status is not DocumentStatus.QUEUED
            ):
                raise RuntimeError("document and ingestion job states are inconsistent")

            document_repository.save(document.start_processing())
            job_repository.save(job.start())
            return document.id

    def _mark_failed(self, *, document_id: UUID, job_id: UUID, failure_code: str) -> None:
        with self._sessions.transaction() as session:
            document_repository = SqlAlchemyDocumentRepository(session)
            job_repository = SqlAlchemyIngestionJobRepository(session)
            document = document_repository.get(document_id)
            job = job_repository.get(job_id)
            if document is not None and document.status is DocumentStatus.PROCESSING:
                document_repository.save(document.mark_failed(failure_code))
            if job is not None and job.status is IngestionJobStatus.RUNNING:
                job_repository.save(job.fail(failure_code))


def _failure_code(error: Exception) -> str:
    if isinstance(error, IngestionError):
        return error.code.value
    if isinstance(error, EmbeddingError):
        return "embedding_failed"
    if isinstance(error, VectorIndexError):
        return "vector_index_failed"
    return "ingestion_failed"
