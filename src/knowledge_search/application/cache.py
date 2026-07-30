import hashlib
import json
from typing import Protocol

from knowledge_search.application.search import SearchExecution
from knowledge_search.retrieval import SearchFilters, SearchMode


class SearchExecutor(Protocol):
    def search(
        self,
        *,
        query: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> SearchExecution: ...


class SearchResultCache(Protocol):
    def get(self, key: str) -> SearchExecution | None: ...

    def set(self, key: str, execution: SearchExecution, *, ttl_seconds: int) -> None: ...


class CorpusRevisionProvider(Protocol):
    def current(self) -> int: ...


class CachedSearchService:
    def __init__(
        self,
        *,
        search: SearchExecutor,
        cache: SearchResultCache,
        corpus_revision: CorpusRevisionProvider,
        ttl_seconds: int,
    ) -> None:
        self._search = search
        self._cache = cache
        self._corpus_revision = corpus_revision
        self._ttl_seconds = ttl_seconds

    def search(
        self,
        *,
        query: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> SearchExecution:
        if self._ttl_seconds == 0:
            return self._search.search(
                query=query,
                mode=mode,
                limit=limit,
                filters=filters,
            )
        key = _cache_key(
            query=query,
            mode=mode,
            limit=limit,
            filters=filters,
            corpus_revision=self._corpus_revision.current(),
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        execution = self._search.search(
            query=query,
            mode=mode,
            limit=limit,
            filters=filters,
        )
        self._cache.set(key, execution, ttl_seconds=self._ttl_seconds)
        return execution


def _cache_key(
    *,
    query: str,
    mode: SearchMode,
    limit: int,
    filters: SearchFilters,
    corpus_revision: int,
) -> str:
    canonical = json.dumps(
        {
            "query": " ".join(query.split()),
            "mode": mode.value,
            "limit": limit,
            "document_ids": sorted(str(value) for value in filters.document_ids),
            "media_types": sorted(value.value for value in filters.media_types),
            "corpus_revision": corpus_revision,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
