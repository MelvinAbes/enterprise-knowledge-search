from uuid import UUID

from pydantic import BaseModel, Field

from knowledge_search.api.schemas.search import SearchResultResponse
from knowledge_search.application import AnswerExecution
from knowledge_search.domain import DocumentMediaType
from knowledge_search.retrieval import SearchMode


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000)
    mode: SearchMode = SearchMode.HYBRID
    limit: int = Field(default=5, ge=1, le=20)
    document_ids: list[UUID] = Field(default_factory=list, max_length=50)
    media_types: list[DocumentMediaType] = Field(default_factory=list)


class AnswerResponse(BaseModel):
    question: str
    answer: str | None
    generation_status: str
    mode: str
    sources: list[SearchResultResponse]

    @classmethod
    def from_domain(cls, execution: AnswerExecution) -> "AnswerResponse":
        return cls(
            question=execution.question,
            answer=execution.answer,
            generation_status=execution.status.value,
            mode=execution.search.mode.value,
            sources=[
                SearchResultResponse.from_domain(result) for result in execution.search.results
            ],
        )
