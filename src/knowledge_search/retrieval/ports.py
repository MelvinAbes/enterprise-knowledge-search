from typing import Protocol
from uuid import UUID

from knowledge_search.retrieval.models import (
    RetrievalCandidate,
    SearchableChunk,
    SearchFilters,
)


class SearchRepository(Protocol):
    def keyword_candidates(
        self,
        *,
        query: str,
        limit: int,
        filters: SearchFilters,
    ) -> list[RetrievalCandidate]: ...

    def load_chunks(
        self,
        chunk_ids: list[UUID],
    ) -> dict[UUID, SearchableChunk]: ...


class VectorSearchIndex(Protocol):
    def search(
        self,
        *,
        vector: list[float],
        limit: int,
        filters: SearchFilters,
    ) -> list[RetrievalCandidate]: ...
