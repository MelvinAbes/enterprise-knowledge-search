from dataclasses import dataclass
from typing import Protocol

from knowledge_search.application.search import SearchExecution
from knowledge_search.generation.models import AnswerStatus
from knowledge_search.generation.ports import AnswerGenerator
from knowledge_search.retrieval import SearchFilters, SearchMode


@dataclass(frozen=True, slots=True)
class AnswerExecution:
    question: str
    answer: str | None
    status: AnswerStatus
    search: SearchExecution


class SearchExecutor(Protocol):
    def search(
        self,
        *,
        query: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> SearchExecution: ...


class AnswerService:
    def __init__(
        self,
        *,
        search: SearchExecutor,
        generator: AnswerGenerator,
    ) -> None:
        self._search = search
        self._generator = generator

    def answer(
        self,
        *,
        question: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> AnswerExecution:
        search = self._search.search(
            query=question,
            mode=mode,
            limit=limit,
            filters=filters,
        )
        citations = [result.citation for result in search.results]
        if not self._generator.enabled:
            return AnswerExecution(
                question=search.query,
                answer=None,
                status=AnswerStatus.DISABLED,
                search=search,
            )
        if not citations:
            return AnswerExecution(
                question=search.query,
                answer=None,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                search=search,
            )
        return AnswerExecution(
            question=search.query,
            answer=self._generator.generate(
                question=search.query,
                citations=citations,
            ),
            status=AnswerStatus.GENERATED,
            search=search,
        )
