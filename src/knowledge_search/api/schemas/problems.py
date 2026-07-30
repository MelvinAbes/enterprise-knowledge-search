from typing import Any

from pydantic import BaseModel


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    extensions: dict[str, Any] | None = None
