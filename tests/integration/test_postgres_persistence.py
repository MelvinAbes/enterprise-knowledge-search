from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import inspect, select

from knowledge_search.domain import (
    Chunk,
    Document,
    DocumentMediaType,
    DocumentStatus,
    IngestionJob,
    IngestionJobStatus,
    SourceLocator,
)
from knowledge_search.persistence import (
    PostgresSessionFactory,
    SqlAlchemyChunkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionJobRepository,
)
from knowledge_search.persistence.models import ChunkRecord, CorpusRevisionRecord

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_TABLES = {"chunks", "corpus_revision", "documents", "ingestion_jobs"}
DOCUMENT_ID = UUID("83bb36a0-937d-4a39-a734-593e6830ab09")
JOB_ID = UUID("8c243fc4-214d-48ce-b92a-e86dc72b8819")
CREATED_AT = datetime(2026, 7, 30, 15, 0, tzinfo=UTC)
DOCUMENT_HASH = "b" * 64
CHUNK_HASH = "c" * 64


def create_document() -> Document:
    return Document.create(
        document_id=DOCUMENT_ID,
        original_filename="backup-policy.md",
        storage_key=f"documents/{DOCUMENT_ID}/source.md",
        media_type=DocumentMediaType.MARKDOWN,
        sha256=DOCUMENT_HASH,
        size_bytes=2_048,
        now=CREATED_AT,
    )


def test_migration_matches_declared_metadata(migrated_database_url: str) -> None:
    session_factory = PostgresSessionFactory(SecretStr(migrated_database_url))
    try:
        inspector = inspect(session_factory.engine)
        assert DOMAIN_TABLES.issubset(set(inspector.get_table_names()))
        chunk_indexes = {index["name"]: index for index in inspector.get_indexes("chunks")}
        assert (
            chunk_indexes["ix_chunks_search_vector"]["dialect_options"]["postgresql_using"] == "gin"
        )

        alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
        alembic_config.set_main_option(
            "sqlalchemy.url",
            migrated_database_url.replace("%", "%%"),
        )
        command.check(alembic_config)
    finally:
        session_factory.dispose()


def test_repositories_round_trip_document_chunks_and_job(
    migrated_database_url: str,
) -> None:
    session_factory = PostgresSessionFactory(SecretStr(migrated_database_url))
    document = create_document()
    job = IngestionJob.create(document_id=document.id, job_id=JOB_ID, now=CREATED_AT)
    chunk = Chunk.create(
        document_id=document.id,
        ordinal=0,
        text="Database backups are retained for thirty days.",
        token_count=8,
        content_hash=CHUNK_HASH,
        locator=SourceLocator(
            section_path=("Operations", "Backups"),
            page_number=2,
            char_start=40,
            char_end=88,
        ),
    )

    try:
        with session_factory.transaction() as session:
            SqlAlchemyDocumentRepository(session).add(document)
            SqlAlchemyIngestionJobRepository(session).add(job)
            SqlAlchemyChunkRepository(session).add_many([chunk])

        with session_factory.transaction() as session:
            stored_document = SqlAlchemyDocumentRepository(session).get(document.id)
            stored_job = SqlAlchemyIngestionJobRepository(session).get(job.id)
            stored_chunks = SqlAlchemyChunkRepository(session).list_for_document(document.id)
            search_vector = session.scalar(
                select(ChunkRecord.search_vector).where(ChunkRecord.id == chunk.id)
            )
            revision = session.get(CorpusRevisionRecord, 1)

        assert stored_document == document
        assert stored_job == job
        assert stored_chunks == [chunk]
        assert "backup" in str(search_vector)
        assert revision is not None
        assert revision.revision == 0
    finally:
        session_factory.dispose()


def test_repositories_persist_lifecycle_changes(migrated_database_url: str) -> None:
    session_factory = PostgresSessionFactory(SecretStr(migrated_database_url))
    processing_at = CREATED_AT + timedelta(minutes=1)
    finished_at = CREATED_AT + timedelta(minutes=2)
    original_document = create_document()
    original_job = IngestionJob.create(
        document_id=original_document.id,
        job_id=JOB_ID,
        now=CREATED_AT,
    )

    try:
        with session_factory.transaction() as session:
            SqlAlchemyDocumentRepository(session).add(original_document)
            SqlAlchemyIngestionJobRepository(session).add(original_job)

        with session_factory.transaction() as session:
            document_repository = SqlAlchemyDocumentRepository(session)
            job_repository = SqlAlchemyIngestionJobRepository(session)
            document = document_repository.get(DOCUMENT_ID)
            job = job_repository.get(JOB_ID)
            assert document is not None
            assert job is not None

            processing_document = document.queue(now=processing_at).start_processing(
                now=processing_at
            )
            running_job = job.start(now=processing_at)
            document_repository.save(processing_document)
            job_repository.save(running_job)

        with session_factory.transaction() as session:
            document_repository = SqlAlchemyDocumentRepository(session)
            job_repository = SqlAlchemyIngestionJobRepository(session)
            document = document_repository.get(DOCUMENT_ID)
            job = job_repository.get(JOB_ID)
            assert document is not None
            assert job is not None

            document_repository.save(document.mark_ready(now=finished_at))
            job_repository.save(job.succeed(now=finished_at))

        with session_factory.transaction() as session:
            stored_document = SqlAlchemyDocumentRepository(session).get(DOCUMENT_ID)
            stored_job = SqlAlchemyIngestionJobRepository(session).get(JOB_ID)

        assert stored_document is not None
        assert stored_document.status is DocumentStatus.READY
        assert stored_job is not None
        assert stored_job.status is IngestionJobStatus.SUCCEEDED
        assert stored_job.attempt_count == 1
    finally:
        session_factory.dispose()
