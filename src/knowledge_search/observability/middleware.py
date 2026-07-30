from time import perf_counter
from uuid import UUID, uuid4

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from knowledge_search.observability.metrics import RequestMetrics

REQUEST_ID_HEADER = "X-Request-ID"
logger = structlog.get_logger()


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, metrics: RequestMetrics) -> None:
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _request_id(request.headers.get(REQUEST_ID_HEADER))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = perf_counter() - started
            route = _route_name(request)
            self._metrics.observe(
                method=request.method,
                route=route,
                status_code=500,
                duration_seconds=duration,
            )
            logger.exception(
                "http_request_failed",
                method=request.method,
                route=route,
                status_code=500,
                duration_ms=round(duration * 1_000, 3),
            )
            raise
        else:
            duration = perf_counter() - started
            route = _route_name(request)
            self._metrics.observe(
                method=request.method,
                route=route,
                status_code=response.status_code,
                duration_seconds=duration,
            )
            response.headers[REQUEST_ID_HEADER] = request_id
            logger.info(
                "http_request_completed",
                method=request.method,
                route=route,
                status_code=response.status_code,
                duration_ms=round(duration * 1_000, 3),
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()


def _request_id(value: str | None) -> str:
    if value is not None:
        try:
            return str(UUID(value))
        except ValueError:
            pass
    return str(uuid4())


def _route_name(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path is not None else "unmatched"
