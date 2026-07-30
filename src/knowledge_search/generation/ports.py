from typing import Protocol

from knowledge_search.domain import Citation


class AnswerGenerator(Protocol):
    @property
    def enabled(self) -> bool: ...

    def generate(self, *, question: str, citations: list[Citation]) -> str | None: ...
