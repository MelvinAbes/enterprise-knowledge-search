from uuid import UUID

from pydantic import BaseModel, SecretStr, ValidationError
from redis import Redis
from redis.exceptions import RedisError

from knowledge_search.application.search import SearchExecution
from knowledge_search.domain import Citation, DocumentMediaType
from knowledge_search.retrieval import SearchMode, SearchResult


class _CachedCitation(BaseModel):
    document_id: UUID
    chunk_id: UUID
    original_filename: str
    excerpt: str
    section_path: list[str]
    page_number: int | None


class _CachedResult(BaseModel):
    score: float
    keyword_rank: int | None
    vector_rank: int | None
    media_type: DocumentMediaType
    citation: _CachedCitation


class _CachedExecution(BaseModel):
    query: str
    mode: SearchMode
    results: list[_CachedResult]


class RedisSearchResultCache:
    def __init__(
        self,
        *,
        redis_url: SecretStr | str,
        key_prefix: str = "eks:search",
    ) -> None:
        raw_url = redis_url.get_secret_value() if isinstance(redis_url, SecretStr) else redis_url
        self._redis: Redis = Redis.from_url(
            raw_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        self._key_prefix = key_prefix

    def get(self, key: str) -> SearchExecution | None:
        try:
            value = self._redis.get(f"{self._key_prefix}:{key}")
            if not isinstance(value, str):
                return None
            return _deserialize(_CachedExecution.model_validate_json(value))
        except (RedisError, ValidationError):
            return None

    def set(
        self,
        key: str,
        execution: SearchExecution,
        *,
        ttl_seconds: int,
    ) -> None:
        try:
            self._redis.set(
                f"{self._key_prefix}:{key}",
                _serialize(execution).model_dump_json(),
                ex=ttl_seconds,
            )
        except RedisError:
            return


def _serialize(execution: SearchExecution) -> _CachedExecution:
    return _CachedExecution(
        query=execution.query,
        mode=execution.mode,
        results=[
            _CachedResult(
                score=result.score,
                keyword_rank=result.keyword_rank,
                vector_rank=result.vector_rank,
                media_type=result.media_type,
                citation=_CachedCitation(
                    document_id=result.citation.document_id,
                    chunk_id=result.citation.chunk_id,
                    original_filename=result.citation.original_filename,
                    excerpt=result.citation.excerpt,
                    section_path=list(result.citation.section_path),
                    page_number=result.citation.page_number,
                ),
            )
            for result in execution.results
        ],
    )


def _deserialize(payload: _CachedExecution) -> SearchExecution:
    return SearchExecution(
        query=payload.query,
        mode=payload.mode,
        results=[
            SearchResult(
                score=item.score,
                keyword_rank=item.keyword_rank,
                vector_rank=item.vector_rank,
                media_type=item.media_type,
                citation=Citation(
                    document_id=item.citation.document_id,
                    chunk_id=item.citation.chunk_id,
                    original_filename=item.citation.original_filename,
                    excerpt=item.citation.excerpt,
                    section_path=tuple(item.citation.section_path),
                    page_number=item.citation.page_number,
                ),
            )
            for item in payload.results
        ],
    )
