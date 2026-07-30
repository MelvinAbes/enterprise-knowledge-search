"""Create document ingestion and lexical-search schema.

Revision ID: 20260730_01
Revises:
Create Date: 2026-07-30 20:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("media_type", sa.String(length=64), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status = 'failed' AND failure_code IS NOT NULL) "
            "OR (status <> 'failed' AND failure_code IS NULL)",
            name="ck_documents_failure_state",
        ),
        sa.CheckConstraint(
            "media_type IN ('application/pdf', 'text/markdown', 'text/plain')",
            name="ck_documents_media_type",
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_documents_sha256",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_documents_size_bytes"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'queued', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_documents_created_at", "documents", ["created_at"], unique=False)
    op.create_index("ix_documents_status", "documents", ["status"], unique=False)

    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "section_path",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english'::regconfig, text)",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.CheckConstraint("char_end >= char_start", name="ck_chunks_char_range"),
        sa.CheckConstraint("char_start >= 0", name="ck_chunks_char_start"),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_chunks_content_hash",
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_chunks_ordinal"),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_chunks_page_number",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(section_path) = 'array'",
            name="ck_chunks_section_path",
        ),
        sa.CheckConstraint("char_length(text) > 0", name="ck_chunks_text"),
        sa.CheckConstraint("token_count > 0", name="ck_chunks_token_count"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "ordinal", name="uq_chunks_document_ordinal"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"], unique=False)
    op.create_index(
        "ix_chunks_search_vector",
        "chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_ingestion_jobs_attempt_count",
        ),
        sa.CheckConstraint(
            "(status = 'failed' AND failure_code IS NOT NULL) "
            "OR (status <> 'failed' AND failure_code IS NULL)",
            name="ck_ingestion_jobs_failure_state",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_ingestion_jobs_status",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_jobs_document_id",
        "ingestion_jobs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_jobs_status",
        "ingestion_jobs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "corpus_revision",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("revision >= 0", name="ck_corpus_revision_non_negative"),
        sa.CheckConstraint("id = 1", name="ck_corpus_revision_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    corpus_revision = sa.table(
        "corpus_revision",
        sa.column("id", sa.SmallInteger()),
        sa.column("revision", sa.BigInteger()),
    )
    op.bulk_insert(corpus_revision, [{"id": 1, "revision": 0}])


def downgrade() -> None:
    op.drop_table("corpus_revision")
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_document_id", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_chunks_search_vector", table_name="chunks", postgresql_using="gin")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_table("documents")
