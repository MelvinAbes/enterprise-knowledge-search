from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from knowledge_search.api.services import ReadinessService

router = APIRouter(tags=["health"])


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, bool]


@router.get("/health/live", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def readiness(request: Request, response: Response) -> ReadinessResponse:
    readiness_service: ReadinessService = request.app.state.readiness_service
    report = readiness_service.check()
    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="not_ready", checks=report.checks())
    return ReadinessResponse(status="ready", checks=report.checks())
