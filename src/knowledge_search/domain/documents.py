import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4, uuid5

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CHUNK_NAMESPACE = UUID("30a8a70d-4e6a-48cd-981e-02faf07d1b10")


class DomainValidationError(ValueError):
    """Raised when a domain value violates a required invariant."""


class InvalidStateTransitionError(DomainValidationError):
    """Raised when an aggregate receives an invalid lifecycle transition."""


class DocumentMediaType(StrEnum):
    PDF = "application/pdf"
    MARKDOWN = "text/markdown"
    TEXT = "text/plain"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class IngestionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


DOCUMENT_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.UPLOADED: frozenset({DocumentStatus.QUEUED}),
    DocumentStatus.QUEUED: frozenset({DocumentStatus.PROCESSING, DocumentStatus.FAILED}),
    DocumentStatus.PROCESSING: frozenset({DocumentStatus.READY, DocumentStatus.FAILED}),
    DocumentStatus.READY: frozenset(),
    DocumentStatus.FAILED: frozenset({DocumentStatus.QUEUED}),
}

JOB_TRANSITIONS: dict[IngestionJobStatus, frozenset[IngestionJobStatus]] = {
    IngestionJobStatus.QUEUED: frozenset({IngestionJobStatus.RUNNING, IngestionJobStatus.FAILED}),
    IngestionJobStatus.RUNNING: frozenset(
        {IngestionJobStatus.SUCCEEDED, IngestionJobStatus.FAILED}
    ),
    IngestionJobStatus.SUCCEEDED: frozenset(),
    IngestionJobStatus.FAILED: frozenset({IngestionJobStatus.QUEUED}),
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_sha256(value: str) -> None:
    if SHA256_PATTERN.fullmatch(value) is None:
        raise DomainValidationError("sha256 must contain 64 lowercase hexadecimal characters")


def _validate_timestamp(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class SourceLocator:
    section_path: tuple[str, ...] = ()
    page_number: int | None = None
    char_start: int = 0
    char_end: int = 0

    def __post_init__(self) -> None:
        if any(not section.strip() for section in self.section_path):
            raise DomainValidationError("section path entries must not be blank")
        if self.page_number is not None and self.page_number < 1:
            raise DomainValidationError("page number must be greater than zero")
        if self.char_start < 0:
            raise DomainValidationError("character start must not be negative")
        if self.char_end < self.char_start:
            raise DomainValidationError("character end must not precede character start")


@dataclass(frozen=True, slots=True)
class Document:
    id: UUID
    original_filename: str
    storage_key: str
    media_type: DocumentMediaType
    sha256: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    failure_code: str | None = None

    def __post_init__(self) -> None:
        if not self.original_filename.strip():
            raise DomainValidationError("original filename must not be blank")
        if not self.storage_key.strip():
            raise DomainValidationError("storage key must not be blank")
        _validate_sha256(self.sha256)
        if self.size_bytes < 0:
            raise DomainValidationError("size must not be negative")
        _validate_timestamp(self.created_at, "created_at")
        _validate_timestamp(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise DomainValidationError("updated_at must not precede created_at")
        if self.status is DocumentStatus.FAILED and not self.failure_code:
            raise DomainValidationError("failed documents require a failure code")
        if self.status is not DocumentStatus.FAILED and self.failure_code is not None:
            raise DomainValidationError("only failed documents may contain a failure code")

    @classmethod
    def create(
        cls,
        *,
        original_filename: str,
        storage_key: str,
        media_type: DocumentMediaType,
        sha256: str,
        size_bytes: int,
        document_id: UUID | None = None,
        now: datetime | None = None,
    ) -> "Document":
        timestamp = now or _utc_now()
        return cls(
            id=document_id or uuid4(),
            original_filename=original_filename,
            storage_key=storage_key,
            media_type=media_type,
            sha256=sha256,
            size_bytes=size_bytes,
            status=DocumentStatus.UPLOADED,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def queue(self, *, now: datetime | None = None) -> "Document":
        return self._transition(DocumentStatus.QUEUED, now=now)

    def start_processing(self, *, now: datetime | None = None) -> "Document":
        return self._transition(DocumentStatus.PROCESSING, now=now)

    def mark_ready(self, *, now: datetime | None = None) -> "Document":
        return self._transition(DocumentStatus.READY, now=now)

    def mark_failed(self, failure_code: str, *, now: datetime | None = None) -> "Document":
        if not failure_code.strip():
            raise DomainValidationError("failure code must not be blank")
        return self._transition(DocumentStatus.FAILED, now=now, failure_code=failure_code)

    def _transition(
        self,
        target: DocumentStatus,
        *,
        now: datetime | None,
        failure_code: str | None = None,
    ) -> "Document":
        if target not in DOCUMENT_TRANSITIONS[self.status]:
            raise InvalidStateTransitionError(
                f"document cannot transition from {self.status} to {target}"
            )
        timestamp = now or _utc_now()
        if timestamp < self.updated_at:
            raise DomainValidationError("document transition time must not move backwards")
        return replace(
            self,
            status=target,
            updated_at=timestamp,
            failure_code=failure_code,
        )


@dataclass(frozen=True, slots=True)
class IngestionJob:
    id: UUID
    document_id: UUID
    status: IngestionJobStatus
    attempt_count: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        if self.attempt_count < 0:
            raise DomainValidationError("attempt count must not be negative")
        _validate_timestamp(self.created_at, "created_at")
        _validate_timestamp(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise DomainValidationError("updated_at must not precede created_at")
        if self.started_at is not None:
            _validate_timestamp(self.started_at, "started_at")
        if self.finished_at is not None:
            _validate_timestamp(self.finished_at, "finished_at")
        if self.started_at is not None and self.started_at < self.created_at:
            raise DomainValidationError("started_at must not precede created_at")
        if self.finished_at is not None and self.finished_at < self.created_at:
            raise DomainValidationError("finished_at must not precede created_at")
        if (
            self.started_at is not None
            and self.finished_at is not None
            and self.finished_at < self.started_at
        ):
            raise DomainValidationError("finished_at must not precede started_at")
        if self.status is IngestionJobStatus.RUNNING and self.started_at is None:
            raise DomainValidationError("running jobs require a start time")
        if (
            self.status in {IngestionJobStatus.SUCCEEDED, IngestionJobStatus.FAILED}
            and self.finished_at is None
        ):
            raise DomainValidationError("finished jobs require a finish time")
        if self.status is IngestionJobStatus.FAILED and not self.failure_code:
            raise DomainValidationError("failed jobs require a failure code")
        if self.status is not IngestionJobStatus.FAILED and self.failure_code is not None:
            raise DomainValidationError("only failed jobs may contain a failure code")

    @classmethod
    def create(
        cls,
        *,
        document_id: UUID,
        job_id: UUID | None = None,
        now: datetime | None = None,
    ) -> "IngestionJob":
        timestamp = now or _utc_now()
        return cls(
            id=job_id or uuid4(),
            document_id=document_id,
            status=IngestionJobStatus.QUEUED,
            attempt_count=0,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def start(self, *, now: datetime | None = None) -> "IngestionJob":
        timestamp = now or _utc_now()
        return self._transition(
            IngestionJobStatus.RUNNING,
            now=timestamp,
            attempt_count=self.attempt_count + 1,
            started_at=timestamp,
        )

    def succeed(self, *, now: datetime | None = None) -> "IngestionJob":
        timestamp = now or _utc_now()
        return self._transition(
            IngestionJobStatus.SUCCEEDED,
            now=timestamp,
            started_at=self.started_at,
            finished_at=timestamp,
        )

    def fail(self, failure_code: str, *, now: datetime | None = None) -> "IngestionJob":
        if not failure_code.strip():
            raise DomainValidationError("failure code must not be blank")
        timestamp = now or _utc_now()
        return self._transition(
            IngestionJobStatus.FAILED,
            now=timestamp,
            started_at=self.started_at,
            finished_at=timestamp,
            failure_code=failure_code,
        )

    def requeue(self, *, now: datetime | None = None) -> "IngestionJob":
        return self._transition(
            IngestionJobStatus.QUEUED,
            now=now or _utc_now(),
            started_at=None,
            finished_at=None,
            failure_code=None,
        )

    def _transition(
        self,
        target: IngestionJobStatus,
        *,
        now: datetime,
        attempt_count: int | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        failure_code: str | None = None,
    ) -> "IngestionJob":
        if target not in JOB_TRANSITIONS[self.status]:
            raise InvalidStateTransitionError(
                f"ingestion job cannot transition from {self.status} to {target}"
            )
        if now < self.updated_at:
            raise DomainValidationError("ingestion transition time must not move backwards")
        return replace(
            self,
            status=target,
            attempt_count=self.attempt_count if attempt_count is None else attempt_count,
            updated_at=now,
            started_at=started_at,
            finished_at=finished_at,
            failure_code=failure_code,
        )


@dataclass(frozen=True, slots=True)
class Chunk:
    id: UUID
    document_id: UUID
    ordinal: int
    text: str
    token_count: int
    content_hash: str
    locator: SourceLocator

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise DomainValidationError("chunk ordinal must not be negative")
        if not self.text.strip():
            raise DomainValidationError("chunk text must not be blank")
        if self.token_count < 1:
            raise DomainValidationError("chunk token count must be greater than zero")
        _validate_sha256(self.content_hash)

    @classmethod
    def create(
        cls,
        *,
        document_id: UUID,
        ordinal: int,
        text: str,
        token_count: int,
        content_hash: str,
        locator: SourceLocator,
    ) -> "Chunk":
        stable_key = f"{document_id}:{ordinal}:{content_hash}"
        return cls(
            id=uuid5(CHUNK_NAMESPACE, stable_key),
            document_id=document_id,
            ordinal=ordinal,
            text=text,
            token_count=token_count,
            content_hash=content_hash,
            locator=locator,
        )


@dataclass(frozen=True, slots=True)
class Citation:
    document_id: UUID
    chunk_id: UUID
    original_filename: str
    excerpt: str
    section_path: tuple[str, ...] = ()
    page_number: int | None = None

    def __post_init__(self) -> None:
        if not self.original_filename.strip():
            raise DomainValidationError("citation filename must not be blank")
        if not self.excerpt.strip():
            raise DomainValidationError("citation excerpt must not be blank")
        if self.page_number is not None and self.page_number < 1:
            raise DomainValidationError("citation page number must be greater than zero")
