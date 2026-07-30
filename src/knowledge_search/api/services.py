from collections.abc import Callable
from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from knowledge_search.application import (
    DocumentQueries,
    DocumentSubmission,
    DocumentSubmissionService,
)
from knowledge_search.config import Settings
from knowledge_search.domain import Document, IngestionJob
from knowledge_search.ingestion.ports import IngestionQueue, VectorIndex
from knowledge_search.persistence import PostgresSessionFactory
from knowledge_search.providers import (
    LocalDocumentStore,
    QdrantVectorIndex,
    RedisIngestionQueue,
)


class DocumentSubmissionHandler(Protocol):
    def submit(
        self,
        *,
        filename: str,
        content_type: str | None,
        source: BinaryIO,
    ) -> DocumentSubmission: ...


class DocumentQueryHandler(Protocol):
    def get_document(self, document_id: UUID) -> Document: ...

    def list_documents(self, *, offset: int, limit: int) -> list[Document]: ...

    def get_job(self, job_id: UUID) -> IngestionJob: ...


class ReadinessProbe(Protocol):
    def is_ready(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    database: bool
    queue: bool
    vector_index: bool

    @property
    def ready(self) -> bool:
        return self.database and self.queue and self.vector_index

    def checks(self) -> dict[str, bool]:
        return {
            "database": self.database,
            "queue": self.queue,
            "vector_index": self.vector_index,
        }


class ReadinessService:
    def __init__(
        self,
        *,
        database: ReadinessProbe,
        queue: ReadinessProbe,
        vector_index: ReadinessProbe,
    ) -> None:
        self._database = database
        self._queue = queue
        self._vector_index = vector_index

    def check(self) -> ReadinessReport:
        return ReadinessReport(
            database=self._database.is_ready(),
            queue=self._queue.is_ready(),
            vector_index=self._vector_index.is_ready(),
        )


@dataclass(frozen=True, slots=True)
class DocumentApiServices:
    submissions: DocumentSubmissionHandler
    queries: DocumentQueryHandler
    readiness: ReadinessService
    shutdown: Callable[[], None]


def create_document_api_services(settings: Settings) -> DocumentApiServices:
    sessions = PostgresSessionFactory(settings.database_url)
    store = LocalDocumentStore(settings.document_storage_path)
    queue: IngestionQueue = RedisIngestionQueue(
        redis_url=settings.redis_url,
        queue_name=settings.ingestion_queue_name,
    )
    vector_index: VectorIndex = QdrantVectorIndex(
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
    )
    return DocumentApiServices(
        submissions=DocumentSubmissionService(
            sessions=sessions,
            store=store,
            queue=queue,
            max_upload_bytes=settings.max_upload_bytes,
        ),
        queries=DocumentQueries(sessions),
        readiness=ReadinessService(
            database=sessions,
            queue=queue,
            vector_index=vector_index,
        ),
        shutdown=sessions.dispose,
    )
