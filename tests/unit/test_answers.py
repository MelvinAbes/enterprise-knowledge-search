import json
from uuid import UUID

import httpx
import pytest

from knowledge_search.application import (
    AnswerService,
    SearchExecution,
)
from knowledge_search.domain import Citation, DocumentMediaType
from knowledge_search.generation import (
    AnswerStatus,
    ChatCompletionsAnswerGenerator,
    DisabledAnswerGenerator,
    GenerationError,
)
from knowledge_search.retrieval import SearchFilters, SearchMode, SearchResult

DOCUMENT_ID = UUID("9fa95893-07d9-4385-98f8-b22250fa10a0")
CHUNK_ID = UUID("aff59840-f6cc-40c9-ad07-afb3cfdf25ac")


class SearchStub:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results

    def search(
        self,
        *,
        query: str,
        mode: SearchMode,
        limit: int,
        filters: SearchFilters,
    ) -> SearchExecution:
        return SearchExecution(query=query.strip(), mode=mode, results=self.results[:limit])


def _search_result() -> SearchResult:
    return SearchResult(
        score=0.5,
        keyword_rank=1,
        vector_rank=1,
        media_type=DocumentMediaType.MARKDOWN,
        citation=Citation(
            document_id=DOCUMENT_ID,
            chunk_id=CHUNK_ID,
            original_filename="operations.md",
            excerpt="Backups are retained for thirty days.",
            section_path=("Operations", "Backups"),
        ),
    )


def test_disabled_generation_returns_retrieval_sources_without_answer() -> None:
    service = AnswerService(
        search=SearchStub([_search_result()]),
        generator=DisabledAnswerGenerator(),
    )

    execution = service.answer(
        question="How long are backups retained?",
        mode=SearchMode.HYBRID,
        limit=5,
        filters=SearchFilters(),
    )

    assert execution.status is AnswerStatus.DISABLED
    assert execution.answer is None
    assert len(execution.search.results) == 1


def test_http_generator_sends_bounded_evidence_and_parses_answer() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer local-token"
        assert payload["model"] == "local-model"
        assert payload["temperature"] == 0
        assert "operations.md" in payload["messages"][1]["content"]
        assert "Backups are retained for thirty days." in payload["messages"][1]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Backups are retained for thirty days [1]."}}]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        generator = ChatCompletionsAnswerGenerator(
            base_url="http://model.test/v1",
            model="local-model",
            api_token="local-token",
            timeout_seconds=5,
            client=client,
        )
        answer = generator.generate(
            question="How long are backups retained?",
            citations=[_search_result().citation],
        )

    assert answer == "Backups are retained for thirty days [1]."


def test_http_generator_translates_invalid_provider_response() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": []}))
    with httpx.Client(transport=transport) as client:
        generator = ChatCompletionsAnswerGenerator(
            base_url="http://model.test/v1",
            model="local-model",
            api_token=None,
            timeout_seconds=5,
            client=client,
        )

        with pytest.raises(GenerationError):
            generator.generate(
                question="How long are backups retained?",
                citations=[_search_result().citation],
            )
