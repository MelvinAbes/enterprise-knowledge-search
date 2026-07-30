from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Query, Request, UploadFile, status

from knowledge_search.api.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    DocumentSubmissionResponse,
    IngestionJobResponse,
)
from knowledge_search.api.services import DocumentApiServices

router = APIRouter(tags=["documents"])


def _services(request: Request) -> DocumentApiServices:
    services: DocumentApiServices = request.app.state.document_services
    return services


@router.post(
    "/documents",
    response_model=DocumentSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_document(
    request: Request,
    document: Annotated[
        UploadFile,
        File(description="PDF, Markdown, or UTF-8 text document"),
    ],
) -> DocumentSubmissionResponse:
    submission = _services(request).submissions.submit(
        filename=document.filename or "",
        content_type=document.content_type,
        source=document.file,
    )
    return DocumentSubmissionResponse(
        document=DocumentResponse.from_domain(submission.document),
        ingestion_job=IngestionJobResponse.from_domain(submission.job),
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> DocumentListResponse:
    documents = _services(request).queries.list_documents(offset=offset, limit=limit)
    return DocumentListResponse(
        items=[DocumentResponse.from_domain(document) for document in documents],
        offset=offset,
        limit=limit,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(request: Request, document_id: UUID) -> DocumentResponse:
    document = _services(request).queries.get_document(document_id)
    return DocumentResponse.from_domain(document)


@router.get("/ingestion-jobs/{job_id}", response_model=IngestionJobResponse)
def get_ingestion_job(request: Request, job_id: UUID) -> IngestionJobResponse:
    job = _services(request).queries.get_job(job_id)
    return IngestionJobResponse.from_domain(job)
