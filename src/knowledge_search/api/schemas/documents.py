from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from knowledge_search.domain import Document, IngestionJob


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    status: str
    failure_code: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentResponse":
        return cls(
            id=document.id,
            original_filename=document.original_filename,
            media_type=document.media_type.value,
            size_bytes=document.size_bytes,
            status=document.status.value,
            failure_code=document.failure_code,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class IngestionJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: str
    attempt_count: int
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_domain(cls, job: IngestionJob) -> "IngestionJobResponse":
        return cls(
            id=job.id,
            document_id=job.document_id,
            status=job.status.value,
            attempt_count=job.attempt_count,
            failure_code=job.failure_code,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )


class DocumentSubmissionResponse(BaseModel):
    document: DocumentResponse
    ingestion_job: IngestionJobResponse


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    offset: int
    limit: int
