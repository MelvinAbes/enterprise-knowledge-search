from uuid import UUID

import pytest

from knowledge_search.application import SearchExecution
from knowledge_search.domain import Citation, DocumentMediaType
from knowledge_search.providers import RedisSearchResultCache
from knowledge_search.retrieval import SearchMode, SearchResult

pytestmark = pytest.mark.integration


def test_redis_cache_round_trips_search_results(redis_url: str) -> None:
    execution = SearchExecution(
        query="backup retention",
        mode=SearchMode.HYBRID,
        results=[
            SearchResult(
                score=0.031,
                keyword_rank=1,
                vector_rank=2,
                media_type=DocumentMediaType.MARKDOWN,
                citation=Citation(
                    document_id=UUID("1692cdf5-fba5-4532-bb2d-c243c09675c5"),
                    chunk_id=UUID("4411ec31-11aa-4303-9388-c13b365a5276"),
                    original_filename="operations.md",
                    excerpt="Backups are retained for thirty days.",
                    section_path=("Operations", "Backups"),
                ),
            )
        ],
    )
    cache = RedisSearchResultCache(
        redis_url=redis_url,
        key_prefix="eks:test-search",
    )

    assert cache.get("missing") is None

    cache.set("result", execution, ttl_seconds=60)

    assert cache.get("result") == execution
