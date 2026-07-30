from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from knowledge_search.api.schemas.search import SearchResponse
from knowledge_search.api.services import DocumentApiServices
from knowledge_search.domain import DocumentMediaType
from knowledge_search.retrieval import SearchFilters, SearchMode

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search_documents(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=500)],
    mode: Annotated[SearchMode, Query()] = SearchMode.HYBRID,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    document_id: Annotated[list[UUID] | None, Query()] = None,
    media_type: Annotated[list[DocumentMediaType] | None, Query()] = None,
) -> SearchResponse:
    services: DocumentApiServices = request.app.state.document_services
    if services.search is None:
        raise RuntimeError("search service is not configured")
    execution = services.search.search(
        query=q,
        mode=mode,
        limit=limit,
        filters=SearchFilters(
            document_ids=tuple(document_id or ()),
            media_types=tuple(media_type or ()),
        ),
    )
    return SearchResponse.from_domain(execution)
