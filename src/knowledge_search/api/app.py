from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from knowledge_search.api.errors import register_error_handlers
from knowledge_search.api.routes.answers import router as answers_router
from knowledge_search.api.routes.documents import router as documents_router
from knowledge_search.api.routes.health import router as health_router
from knowledge_search.api.routes.metrics import router as metrics_router
from knowledge_search.api.routes.search import router as search_router
from knowledge_search.api.services import (
    DocumentApiServices,
    ReadinessService,
    create_document_api_services,
)
from knowledge_search.config import Settings, get_settings
from knowledge_search.observability import (
    RequestMetrics,
    RequestObservabilityMiddleware,
    configure_logging,
)


def create_app(
    settings: Settings | None = None,
    *,
    document_services: DocumentApiServices | None = None,
    readiness_service: ReadinessService | None = None,
) -> FastAPI:
    application_settings = settings or get_settings()
    configure_logging(application_settings.log_level)
    owns_services = document_services is None
    services = document_services or create_document_api_services(application_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_services:
            services.shutdown()

    application = FastAPI(
        title=application_settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = application_settings
    application.state.document_services = services
    application.state.readiness_service = readiness_service or services.readiness
    request_metrics = RequestMetrics()
    application.state.request_metrics = request_metrics
    application.add_middleware(
        RequestObservabilityMiddleware,
        metrics=request_metrics,
    )
    register_error_handlers(application)
    application.include_router(health_router)
    application.include_router(metrics_router)
    application.include_router(documents_router, prefix=application_settings.api_prefix)
    application.include_router(search_router, prefix=application_settings.api_prefix)
    application.include_router(answers_router, prefix=application_settings.api_prefix)
    return application
