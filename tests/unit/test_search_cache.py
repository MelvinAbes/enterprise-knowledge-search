from dataclasses import dataclass

from knowledge_search.application import SearchExecution
from knowledge_search.application.cache import CachedSearchService
from knowledge_search.retrieval import SearchFilters, SearchMode


class SearchStub:
    def __init__(self) -> None:
        self.calls = 0

    def search(
        self,
        *,
        query: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> SearchExecution:
        self.calls += 1
        return SearchExecution(
            query=" ".join(query.split()),
            mode=mode,
            results=[],
        )


class CacheStub:
    def __init__(self) -> None:
        self.values: dict[str, SearchExecution] = {}

    def get(self, key: str) -> SearchExecution | None:
        return self.values.get(key)

    def set(
        self,
        key: str,
        execution: SearchExecution,
        *,
        ttl_seconds: int,
    ) -> None:
        assert ttl_seconds == 300
        self.values[key] = execution


@dataclass
class RevisionStub:
    revision: int = 0

    def current(self) -> int:
        return self.revision


def test_cache_key_uses_normalized_query_and_corpus_revision() -> None:
    search = SearchStub()
    cache = CacheStub()
    revision = RevisionStub()
    service = CachedSearchService(
        search=search,
        cache=cache,
        corpus_revision=revision,
        ttl_seconds=300,
    )

    first = service.search(
        query="monthly   recovery",
        mode=SearchMode.HYBRID,
        limit=5,
        filters=SearchFilters(),
    )
    repeated = service.search(
        query=" monthly recovery ",
        mode=SearchMode.HYBRID,
        limit=5,
        filters=SearchFilters(),
    )
    revision.revision = 1
    after_ingestion = service.search(
        query="monthly recovery",
        mode=SearchMode.HYBRID,
        limit=5,
        filters=SearchFilters(),
    )

    assert repeated is first
    assert after_ingestion is not first
    assert search.calls == 2
    assert len(cache.values) == 2
