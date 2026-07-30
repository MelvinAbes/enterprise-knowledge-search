from knowledge_search.domain import Citation


class DisabledAnswerGenerator:
    @property
    def enabled(self) -> bool:
        return False

    def generate(self, *, question: str, citations: list[Citation]) -> None:
        return None
