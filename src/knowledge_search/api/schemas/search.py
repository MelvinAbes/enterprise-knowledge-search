from uuid import UUID

from pydantic import BaseModel

from knowledge_search.application import SearchExecution
from knowledge_search.retrieval import SearchResult


class CitationResponse(BaseModel):
    document_id: UUID
    chunk_id: UUID
    original_filename: str
    excerpt: str
    section_path: list[str]
    page_number: int | None


class SearchResultResponse(BaseModel):
    score: float
    keyword_rank: int | None
    vector_rank: int | None
    media_type: str
    citation: CitationResponse

    @classmethod
    def from_domain(cls, result: SearchResult) -> "SearchResultResponse":
        return cls(
            score=result.score,
            keyword_rank=result.keyword_rank,
            vector_rank=result.vector_rank,
            media_type=result.media_type.value,
            citation=CitationResponse(
                document_id=result.citation.document_id,
                chunk_id=result.citation.chunk_id,
                original_filename=result.citation.original_filename,
                excerpt=result.citation.excerpt,
                section_path=list(result.citation.section_path),
                page_number=result.citation.page_number,
            ),
        )


class SearchResponse(BaseModel):
    query: str
    mode: str
    items: list[SearchResultResponse]

    @classmethod
    def from_domain(cls, execution: SearchExecution) -> "SearchResponse":
        return cls(
            query=execution.query,
            mode=execution.mode.value,
            items=[SearchResultResponse.from_domain(result) for result in execution.results],
        )
