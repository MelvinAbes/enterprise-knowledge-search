from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from knowledge_search.api.schemas.problems import ProblemDetails
from knowledge_search.application.errors import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    IngestionJobNotFoundError,
)
from knowledge_search.ingestion.errors import (
    EmbeddingError,
    IngestionError,
    IngestionErrorCode,
    QueueDispatchError,
    VectorIndexError,
)
from knowledge_search.retrieval.errors import SearchQueryError


def register_error_handlers(application: FastAPI) -> None:
    application.add_exception_handler(IngestionError, _ingestion_error)
    application.add_exception_handler(DuplicateDocumentError, _duplicate_document)
    application.add_exception_handler(DocumentNotFoundError, _document_not_found)
    application.add_exception_handler(IngestionJobNotFoundError, _job_not_found)
    application.add_exception_handler(QueueDispatchError, _queue_unavailable)
    application.add_exception_handler(EmbeddingError, _retrieval_unavailable)
    application.add_exception_handler(VectorIndexError, _retrieval_unavailable)
    application.add_exception_handler(SearchQueryError, _search_query_error)
    application.add_exception_handler(RequestValidationError, _validation_error)


async def _ingestion_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, IngestionError)
    status_code = {
        IngestionErrorCode.FILE_TOO_LARGE: status.HTTP_413_CONTENT_TOO_LARGE,
        IngestionErrorCode.UNSUPPORTED_MEDIA_TYPE: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        IngestionErrorCode.MEDIA_TYPE_MISMATCH: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    }.get(error.code, status.HTTP_400_BAD_REQUEST)
    return _problem_response(
        request=request,
        status_code=status_code,
        title="Document rejected",
        detail=error.message,
        code=error.code.value,
    )


async def _duplicate_document(
    request: Request,
    error: Exception,
) -> JSONResponse:
    assert isinstance(error, DuplicateDocumentError)
    return _problem_response(
        request=request,
        status_code=status.HTTP_409_CONFLICT,
        title="Duplicate document",
        detail=str(error),
        code="duplicate_document",
        extensions={"existing_document_id": str(error.existing_document_id)},
    )


async def _document_not_found(
    request: Request,
    error: Exception,
) -> JSONResponse:
    assert isinstance(error, DocumentNotFoundError)
    return _problem_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        title="Document not found",
        detail=str(error),
        code="document_not_found",
    )


async def _job_not_found(
    request: Request,
    error: Exception,
) -> JSONResponse:
    assert isinstance(error, IngestionJobNotFoundError)
    return _problem_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        title="Ingestion job not found",
        detail=str(error),
        code="ingestion_job_not_found",
    )


async def _queue_unavailable(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, QueueDispatchError)
    extensions = {
        key: str(value)
        for key, value in {
            "document_id": error.document_id,
            "ingestion_job_id": error.job_id,
        }.items()
        if value is not None
    }
    return _problem_response(
        request=request,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        title="Ingestion queue unavailable",
        detail="The document was stored but could not be scheduled for processing.",
        code="queue_unavailable",
        extensions=extensions or None,
        headers={"Retry-After": "5"},
    )


async def _validation_error(
    request: Request,
    error: Exception,
) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    issues = [
        {
            "location": [str(part) for part in issue["loc"]],
            "message": issue["msg"],
            "type": issue["type"],
        }
        for issue in error.errors()
    ]
    return _problem_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        title="Request validation failed",
        detail="One or more request values are invalid.",
        code="request_validation_failed",
        extensions={"issues": issues},
    )


async def _retrieval_unavailable(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, (EmbeddingError, VectorIndexError))
    return _problem_response(
        request=request,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        title="Retrieval dependency unavailable",
        detail="Semantic retrieval is temporarily unavailable.",
        code="retrieval_unavailable",
        headers={"Retry-After": "5"},
    )


async def _search_query_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, SearchQueryError)
    return _problem_response(
        request=request,
        status_code=status.HTTP_400_BAD_REQUEST,
        title="Search query rejected",
        detail=str(error),
        code="invalid_search_query",
    )


def _problem_response(
    *,
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    code: str,
    extensions: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    problem = ProblemDetails(
        type=f"urn:enterprise-knowledge-search:problem:{code}",
        title=title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
        code=code,
        extensions=extensions,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(mode="json", exclude_none=True),
        media_type="application/problem+json",
        headers=headers,
    )
