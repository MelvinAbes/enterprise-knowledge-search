from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from knowledge_search.domain import (
    Chunk,
    Document,
    DocumentMediaType,
    DocumentStatus,
    IngestionJob,
    IngestionJobStatus,
    InvalidStateTransitionError,
    SourceLocator,
)
from knowledge_search.domain.documents import DomainValidationError

DOCUMENT_ID = UUID("0a5300ea-8c50-43ed-b783-bbeab7a53076")
JOB_ID = UUID("b4de1814-5f54-4a73-8524-1a88b22db093")
CREATED_AT = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
SHA256 = "a" * 64


def create_document() -> Document:
    return Document.create(
        document_id=DOCUMENT_ID,
        original_filename="operations-guide.md",
        storage_key="documents/0a5300ea/source.md",
        media_type=DocumentMediaType.MARKDOWN,
        sha256=SHA256,
        size_bytes=1_024,
        now=CREATED_AT,
    )


def test_document_follows_supported_lifecycle() -> None:
    queued_at = CREATED_AT + timedelta(seconds=1)
    processing_at = CREATED_AT + timedelta(seconds=2)
    ready_at = CREATED_AT + timedelta(seconds=3)

    document = (
        create_document()
        .queue(now=queued_at)
        .start_processing(now=processing_at)
        .mark_ready(now=ready_at)
    )

    assert document.status is DocumentStatus.READY
    assert document.updated_at == ready_at
    assert document.failure_code is None


def test_ready_document_cannot_return_to_processing() -> None:
    document = create_document().queue().start_processing().mark_ready()

    with pytest.raises(InvalidStateTransitionError):
        document.start_processing()


def test_failed_document_can_be_requeued_without_failure_code() -> None:
    document = create_document().queue().mark_failed("unsupported_encoding")

    retried = document.queue()

    assert retried.status is DocumentStatus.QUEUED
    assert retried.failure_code is None


def test_document_requires_lowercase_sha256() -> None:
    with pytest.raises(DomainValidationError):
        Document.create(
            document_id=DOCUMENT_ID,
            original_filename="source.txt",
            storage_key="documents/source.txt",
            media_type=DocumentMediaType.TEXT,
            sha256="A" * 64,
            size_bytes=12,
            now=CREATED_AT,
        )


def test_ingestion_retry_preserves_attempt_count() -> None:
    first_start = CREATED_AT + timedelta(seconds=1)
    first_finish = CREATED_AT + timedelta(seconds=2)
    requeued_at = CREATED_AT + timedelta(seconds=2, milliseconds=500)
    second_start = CREATED_AT + timedelta(seconds=3)
    job = IngestionJob.create(document_id=DOCUMENT_ID, job_id=JOB_ID, now=CREATED_AT)

    retried = (
        job.start(now=first_start)
        .fail("embedding_unavailable", now=first_finish)
        .requeue(now=requeued_at)
        .start(now=second_start)
    )

    assert retried.status is IngestionJobStatus.RUNNING
    assert retried.attempt_count == 2
    assert retried.started_at == second_start
    assert retried.finished_at is None
    assert retried.failure_code is None


def test_succeeded_job_retains_start_and_finish_times() -> None:
    started_at = CREATED_AT + timedelta(seconds=1)
    finished_at = CREATED_AT + timedelta(seconds=5)
    job = IngestionJob.create(document_id=DOCUMENT_ID, job_id=JOB_ID, now=CREATED_AT)

    succeeded = job.start(now=started_at).succeed(now=finished_at)

    assert succeeded.status is IngestionJobStatus.SUCCEEDED
    assert succeeded.started_at == started_at
    assert succeeded.finished_at == finished_at


def test_chunk_identifier_is_deterministic() -> None:
    locator = SourceLocator(
        section_path=("Operations", "Backups"),
        page_number=3,
        char_start=120,
        char_end=220,
    )

    first = Chunk.create(
        document_id=DOCUMENT_ID,
        ordinal=2,
        text="Backups are retained for thirty days.",
        token_count=8,
        content_hash=SHA256,
        locator=locator,
    )
    second = Chunk.create(
        document_id=DOCUMENT_ID,
        ordinal=2,
        text="Backups are retained for thirty days.",
        token_count=8,
        content_hash=SHA256,
        locator=locator,
    )

    assert first.id == second.id


def test_source_locator_rejects_invalid_offsets() -> None:
    with pytest.raises(DomainValidationError):
        SourceLocator(char_start=20, char_end=10)
