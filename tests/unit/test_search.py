from uuid import UUID

import pytest

from knowledge_search.application import SearchService
from knowledge_search.domain import DocumentMediaType, SourceLocator
from knowledge_search.retrieval import (
    RetrievalCandidate,
    SearchableChunk,
    SearchFilters,
    SearchMode,
    reciprocal_rank_fusion,
)

CHUNK_A = UUID("00000000-0000-0000-0000-00000000000a")
CHUNK_B = UUID("00000000-0000-0000-0000-00000000000b")
CHUNK_C = UUID("00000000-0000-0000-0000-00000000000c")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")


class SearchRepositoryStub:
    def __init__(
        self,
        *,
        keyword: list[RetrievalCandidate],
        chunks: dict[UUID, SearchableChunk],
    ) -> None:
        self.keyword = keyword
        self.chunks = chunks
        self.queries: list[str] = []

    def keyword_candidates(
        self,
        *,
        query: str,
        limit: int,
        filters: SearchFilters,
    ) -> list[RetrievalCandidate]:
        self.queries.append(query)
        return self.keyword[:limit]

    def load_chunks(self, chunk_ids: list[UUID]) -> dict[UUID, SearchableChunk]:
        return {
            chunk_id: self.chunks[chunk_id] for chunk_id in chunk_ids if chunk_id in self.chunks
        }


class EmbeddingStub:
    model_name = "test"
    dimensions = 2

    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.texts.extend(texts)
        return [[0.4, 0.6] for _ in texts]


class VectorIndexStub:
    def __init__(self, candidates: list[RetrievalCandidate]) -> None:
        self.candidates = candidates
        self.filters: list[SearchFilters] = []

    def search(
        self,
        *,
        vector: list[float],
        limit: int,
        filters: SearchFilters,
    ) -> list[RetrievalCandidate]:
        self.filters.append(filters)
        assert vector == [0.4, 0.6]
        return self.candidates[:limit]


def _chunk(chunk_id: UUID, text: str) -> SearchableChunk:
    return SearchableChunk(
        id=chunk_id,
        document_id=DOCUMENT_ID,
        text=text,
        original_filename="operations.md",
        media_type=DocumentMediaType.MARKDOWN,
        locator=SourceLocator(section_path=("Operations",)),
    )


def test_reciprocal_rank_fusion_combines_overlap_and_breaks_ties_by_id() -> None:
    ranked = reciprocal_rank_fusion(
        keyword=[
            RetrievalCandidate(chunk_id=CHUNK_A, rank=1, score=0.9),
            RetrievalCandidate(chunk_id=CHUNK_B, rank=2, score=0.8),
        ],
        vector=[
            RetrievalCandidate(chunk_id=CHUNK_B, rank=1, score=0.95),
            RetrievalCandidate(chunk_id=CHUNK_C, rank=2, score=0.75),
        ],
        rrf_k=60,
    )

    assert [candidate.chunk_id for candidate in ranked] == [
        CHUNK_B,
        CHUNK_A,
        CHUNK_C,
    ]
    assert ranked[0].keyword_rank == 2
    assert ranked[0].vector_rank == 1
    assert ranked[0].score == pytest.approx((1 / 62) + (1 / 61))


def test_hybrid_search_normalizes_query_and_assembles_citations() -> None:
    repository = SearchRepositoryStub(
        keyword=[
            RetrievalCandidate(chunk_id=CHUNK_A, rank=1, score=0.9),
            RetrievalCandidate(chunk_id=CHUNK_B, rank=2, score=0.8),
        ],
        chunks={
            CHUNK_A: _chunk(CHUNK_A, "Backups are retained for thirty days."),
            CHUNK_B: _chunk(CHUNK_B, "Recovery exercises run monthly."),
        },
    )
    embeddings = EmbeddingStub()
    vector_index = VectorIndexStub([RetrievalCandidate(chunk_id=CHUNK_B, rank=1, score=0.95)])
    filters = SearchFilters(media_types=(DocumentMediaType.MARKDOWN,))
    service = SearchService(
        repository=repository,
        embeddings=embeddings,
        vector_index=vector_index,
        candidate_multiplier=3,
        rrf_k=60,
    )

    execution = service.search(
        query="  monthly   recovery ",
        mode=SearchMode.HYBRID,
        limit=2,
        filters=filters,
    )

    assert execution.query == "monthly recovery"
    assert execution.mode is SearchMode.HYBRID
    assert repository.queries == ["monthly recovery"]
    assert embeddings.texts == ["monthly recovery"]
    assert vector_index.filters == [filters]
    assert [result.citation.chunk_id for result in execution.results] == [
        CHUNK_B,
        CHUNK_A,
    ]
    assert execution.results[0].citation.section_path == ("Operations",)


def test_keyword_search_does_not_generate_query_embedding() -> None:
    repository = SearchRepositoryStub(
        keyword=[RetrievalCandidate(chunk_id=CHUNK_A, rank=1, score=0.9)],
        chunks={CHUNK_A: _chunk(CHUNK_A, "Backup policy")},
    )
    embeddings = EmbeddingStub()
    service = SearchService(
        repository=repository,
        embeddings=embeddings,
        vector_index=VectorIndexStub([]),
        candidate_multiplier=2,
        rrf_k=60,
    )

    execution = service.search(
        query="backup",
        mode=SearchMode.KEYWORD,
        limit=1,
        filters=SearchFilters(),
    )

    assert len(execution.results) == 1
    assert execution.results[0].keyword_rank == 1
    assert execution.results[0].vector_rank is None
    assert embeddings.texts == []
