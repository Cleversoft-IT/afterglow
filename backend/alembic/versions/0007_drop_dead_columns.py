"""drop dead columns: template_versions table, calls.audio_duration_sec

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-16

`template_versions` was introduced in 0001 as a placeholder for a "versioned
template" feature that never landed. The only code that touched it was the
two earlier migrations (0001 created it, 0002 / 0006 TRUNCATEd it for FK
ordering); no application code reads or writes it. Templates carry a `version`
column on the main row, auto-bumped per (name, session_id) by the wizard's
POST handler — that is the live versioning path.

`calls.audio_duration_sec` was wired into the schema but the post-call pipeline
never computes or persists a duration, and no API surface reads it. Dead column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("template_versions")
    op.drop_column("calls", "audio_duration_sec")


def downgrade() -> None:
    op.add_column(
        "calls",
        sa.Column("audio_duration_sec", sa.Integer(), nullable=True),
    )
    op.create_table(
        "template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("template_id", "version", name="uq_template_version"),
    )
