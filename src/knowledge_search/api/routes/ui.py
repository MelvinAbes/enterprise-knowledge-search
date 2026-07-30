from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


def create_ui_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter(tags=["interface"])

    @router.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "api_prefix": request.app.state.settings.api_prefix,
            },
        )

    return router
