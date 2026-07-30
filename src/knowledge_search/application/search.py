from dataclasses import dataclass

from knowledge_search.domain import Citation
from knowledge_search.ingestion.ports import EmbeddingProvider
from knowledge_search.retrieval.errors import SearchQueryError
from knowledge_search.retrieval.models import (
    FusedCandidate,
    RetrievalCandidate,
    SearchFilters,
    SearchMode,
    SearchResult,
)
from knowledge_search.retrieval.ports import SearchRepository, VectorSearchIndex
from knowledge_search.retrieval.ranking import reciprocal_rank_fusion


@dataclass(frozen=True, slots=True)
class SearchExecution:
    query: str
    mode: SearchMode
    results: list[SearchResult]


class SearchService:
    def __init__(
        self,
        *,
        repository: SearchRepository,
        embeddings: EmbeddingProvider,
        vector_index: VectorSearchIndex,
        candidate_multiplier: int,
        rrf_k: int,
    ) -> None:
        if candidate_multiplier < 1:
            raise ValueError("candidate multiplier must be greater than zero")
        if rrf_k < 1:
            raise ValueError("rrf_k must be greater than zero")
        self._repository = repository
        self._embeddings = embeddings
        self._vector_index = vector_index
        self._candidate_multiplier = candidate_multiplier
        self._rrf_k = rrf_k

    def search(
        self,
        *,
        query: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> SearchExecution:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise SearchQueryError("Search query must not be blank.")
        if limit < 1:
            raise SearchQueryError("Search limit must be greater than zero.")

        candidate_limit = limit * self._candidate_multiplier
        keyword = (
            self._repository.keyword_candidates(
                query=normalized_query,
                limit=candidate_limit,
                filters=filters,
            )
            if mode in {SearchMode.KEYWORD, SearchMode.HYBRID}
            else []
        )
        vector = (
            self._vector_candidates(
                query=normalized_query,
                limit=candidate_limit,
                filters=filters,
            )
            if mode in {SearchMode.VECTOR, SearchMode.HYBRID}
            else []
        )
        ranked = self._rank(mode=mode, keyword=keyword, vector=vector)
        chunks = self._repository.load_chunks([candidate.chunk_id for candidate in ranked])

        results: list[SearchResult] = []
        for candidate in ranked:
            chunk = chunks.get(candidate.chunk_id)
            if chunk is None:
                continue
            results.append(
                SearchResult(
                    score=candidate.score,
                    keyword_rank=candidate.keyword_rank,
                    vector_rank=candidate.vector_rank,
                    media_type=chunk.media_type,
                    citation=Citation(
                        document_id=chunk.document_id,
                        chunk_id=chunk.id,
                        original_filename=chunk.original_filename,
                        excerpt=chunk.text,
                        section_path=chunk.locator.section_path,
                        page_number=chunk.locator.page_number,
                    ),
                )
            )
            if len(results) == limit:
                break
        return SearchExecution(
            query=normalized_query,
            mode=mode,
            results=results,
        )

    def _vector_candidates(
        self,
        *,
        query: str,
        limit: int,
        filters: SearchFilters,
    ) -> list[RetrievalCandidate]:
        vector = self._embeddings.embed_documents([query])[0]
        return self._vector_index.search(
            vector=vector,
            limit=limit,
            filters=filters,
        )

    def _rank(
        self,
        *,
        mode: SearchMode,
        keyword: list[RetrievalCandidate],
        vector: list[RetrievalCandidate],
    ) -> list[FusedCandidate]:
        if mode is SearchMode.HYBRID:
            return reciprocal_rank_fusion(
                keyword=keyword,
                vector=vector,
                rrf_k=self._rrf_k,
            )
        source = keyword if mode is SearchMode.KEYWORD else vector
        return [
            FusedCandidate(
                chunk_id=candidate.chunk_id,
                score=candidate.score,
                keyword_rank=candidate.rank if mode is SearchMode.KEYWORD else None,
                vector_rank=candidate.rank if mode is SearchMode.VECTOR else None,
            )
            for candidate in source
        ]
