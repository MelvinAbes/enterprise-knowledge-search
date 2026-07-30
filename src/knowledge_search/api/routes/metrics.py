from fastapi import APIRouter, Request, Response

from knowledge_search.observability import RequestMetrics

router = APIRouter(tags=["operations"])


@router.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    request_metrics: RequestMetrics = request.app.state.request_metrics
    content, content_type = request_metrics.render()
    return Response(content=content, headers={"Content-Type": content_type})
