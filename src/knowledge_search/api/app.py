from fastapi import FastAPI

from knowledge_search.api.routes.health import router as health_router
from knowledge_search.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    application_settings = settings or get_settings()
    application = FastAPI(
        title=application_settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    application.state.settings = application_settings
    application.include_router(health_router)
    return application
