from collections.abc import Callable
from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from knowledge_search.application import (
    AnswerExecution,
    AnswerService,
    DocumentDeletionService,
    DocumentQueries,
    DocumentSubmission,
    DocumentSubmissionService,
    SearchExecution,
    SearchService,
)
from knowledge_search.application.cache import CachedSearchService
from knowledge_search.config import Settings
from knowledge_search.domain import Document, IngestionJob
from knowledge_search.generation import (
    ChatCompletionsAnswerGenerator,
    DisabledAnswerGenerator,
)
from knowledge_search.generation.ports import AnswerGenerator
from knowledge_search.ingestion.ports import IngestionQueue
from knowledge_search.persistence import (
    PostgresCorpusRevisionProvider,
    PostgresSearchRepository,
    PostgresSessionFactory,
)
from knowledge_search.providers import (
    FastEmbedProvider,
    LocalDocumentStore,
    QdrantVectorIndex,
    RedisIngestionQueue,
    RedisSearchResultCache,
)
from knowledge_search.retrieval import SearchFilters, SearchMode


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


class DocumentDeletionHandler(Protocol):
    def delete(self, document_id: UUID) -> None: ...


class ReadinessProbe(Protocol):
    def is_ready(self) -> bool: ...


class SearchHandler(Protocol):
    def search(
        self,
        *,
        query: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> SearchExecution: ...


class AnswerHandler(Protocol):
    def answer(
        self,
        *,
        question: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> AnswerExecution: ...


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
    search: SearchHandler | None = None
    answers: AnswerHandler | None = None
    deletions: DocumentDeletionHandler | None = None


def create_document_api_services(settings: Settings) -> DocumentApiServices:
    sessions = PostgresSessionFactory(settings.database_url)
    store = LocalDocumentStore(settings.document_storage_path)
    queue: IngestionQueue = RedisIngestionQueue(
        redis_url=settings.redis_url,
        queue_name=settings.ingestion_queue_name,
    )
    vector_index = QdrantVectorIndex(
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
    )
    embeddings = FastEmbedProvider(
        model_name=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        cache_path=settings.model_cache_path,
    )
    uncached_search = SearchService(
        repository=PostgresSearchRepository(sessions),
        embeddings=embeddings,
        vector_index=vector_index,
        candidate_multiplier=settings.retrieval_candidate_multiplier,
        rrf_k=settings.hybrid_rrf_k,
    )
    search = CachedSearchService(
        search=uncached_search,
        cache=RedisSearchResultCache(redis_url=settings.redis_url),
        corpus_revision=PostgresCorpusRevisionProvider(sessions),
        ttl_seconds=settings.search_cache_ttl_seconds,
    )
    generator: AnswerGenerator
    if settings.answer_provider == "disabled":
        generator = DisabledAnswerGenerator()
    else:
        token = (
            settings.answer_api_token.get_secret_value()
            if settings.answer_api_token is not None
            else None
        )
        generator = ChatCompletionsAnswerGenerator(
            base_url=str(settings.answer_base_url),
            model=settings.answer_model,
            api_token=token or None,
            timeout_seconds=settings.answer_timeout_seconds,
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
        search=search,
        answers=AnswerService(search=search, generator=generator),
        deletions=DocumentDeletionService(
            sessions=sessions,
            store=store,
            vector_index=vector_index,
        ),
    )
