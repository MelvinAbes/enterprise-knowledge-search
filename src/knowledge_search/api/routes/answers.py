from fastapi import APIRouter, Request

from knowledge_search.api.schemas.answers import AnswerRequest, AnswerResponse
from knowledge_search.api.services import DocumentApiServices
from knowledge_search.retrieval import SearchFilters

router = APIRouter(tags=["answers"])


@router.post("/answers", response_model=AnswerResponse)
def answer_question(request: Request, payload: AnswerRequest) -> AnswerResponse:
    services: DocumentApiServices = request.app.state.document_services
    if services.answers is None:
        raise RuntimeError("answer service is not configured")
    execution = services.answers.answer(
        question=payload.question,
        mode=payload.mode,
        limit=payload.limit,
        filters=SearchFilters(
            document_ids=tuple(payload.document_ids),
            media_types=tuple(payload.media_types),
        ),
    )
    return AnswerResponse.from_domain(execution)
