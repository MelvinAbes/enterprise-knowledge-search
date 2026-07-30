from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DOCUMENT_STATUS_VALUES: Final = "'uploaded', 'queued', 'processing', 'ready', 'failed', 'deleting'"
JOB_STATUS_VALUES: Final = "'queued', 'running', 'succeeded', 'failed'"


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({DOCUMENT_STATUS_VALUES})",
            name="ck_documents_status",
        ),
        CheckConstraint(
            "media_type IN ('application/pdf', 'text/markdown', 'text/plain')",
            name="ck_documents_media_type",
        ),
        CheckConstraint("size_bytes >= 0", name="ck_documents_size_bytes"),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_documents_sha256",
        ),
        CheckConstraint(
            "(status = 'failed' AND failure_code IS NOT NULL) "
            "OR (status <> 'failed' AND failure_code IS NULL)",
            name="ck_documents_failure_state",
        ),
        Index("ix_documents_status", "status"),
        Index("ix_documents_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(POSTGRES_UUID(as_uuid=True), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    media_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunks: Mapped[list["ChunkRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    ingestion_jobs: Mapped[list["IngestionJobRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChunkRecord(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_chunks_document_ordinal"),
        CheckConstraint("ordinal >= 0", name="ck_chunks_ordinal"),
        CheckConstraint("token_count > 0", name="ck_chunks_token_count"),
        CheckConstraint("char_start >= 0", name="ck_chunks_char_start"),
        CheckConstraint("char_end >= char_start", name="ck_chunks_char_range"),
        CheckConstraint("char_length(text) > 0", name="ck_chunks_text"),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_chunks_page_number",
        ),
        CheckConstraint(
            "jsonb_typeof(section_path) = 'array'",
            name="ck_chunks_section_path",
        ),
        CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_chunks_content_hash",
        ),
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[UUID] = mapped_column(POSTGRES_UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        POSTGRES_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    section_path: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    page_number: Mapped[int | None] = mapped_column(Integer)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english'::regconfig, text)", persisted=True),
        nullable=False,
    )

    document: Mapped[DocumentRecord] = relationship(back_populates="chunks")


class IngestionJobRecord(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({JOB_STATUS_VALUES})",
            name="ck_ingestion_jobs_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_ingestion_jobs_attempt_count"),
        CheckConstraint(
            "(status = 'failed' AND failure_code IS NOT NULL) "
            "OR (status <> 'failed' AND failure_code IS NULL)",
            name="ck_ingestion_jobs_failure_state",
        ),
        Index("ix_ingestion_jobs_document_id", "document_id"),
        Index("ix_ingestion_jobs_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(POSTGRES_UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        POSTGRES_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[DocumentRecord] = relationship(back_populates="ingestion_jobs")


class CorpusRevisionRecord(Base):
    __tablename__ = "corpus_revision"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_corpus_revision_singleton"),
        CheckConstraint("revision >= 0", name="ck_corpus_revision_non_negative"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
