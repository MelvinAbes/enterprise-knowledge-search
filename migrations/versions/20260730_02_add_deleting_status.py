"""Add recoverable document deletion state.

Revision ID: 20260730_02
Revises: 20260730_01
Create Date: 2026-07-30 21:15:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260730_02"
down_revision: str | None = "20260730_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORIGINAL_STATUSES = "'uploaded', 'queued', 'processing', 'ready', 'failed'"
DELETION_STATUSES = f"{ORIGINAL_STATUSES}, 'deleting'"


def upgrade() -> None:
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_status",
        "documents",
        f"status IN ({DELETION_STATUSES})",
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE documents
        SET status = 'failed', failure_code = 'deletion_interrupted'
        WHERE status = 'deleting'
        """
    )
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_status",
        "documents",
        f"status IN ({ORIGINAL_STATUSES})",
    )
