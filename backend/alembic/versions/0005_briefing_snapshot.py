"""briefing_snapshot column on extracted_fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-16

Captures the next_call_briefing produced by Gemini at the moment of *this*
call. Without it, the only briefing per call would be Customer.memory_summary,
which is overwritten on every subsequent call — so historical lookups
("show me what the briefing was 3 calls ago") lose information.

Additive, non-breaking: column is nullable, existing rows stay valid.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "extracted_fields",
        sa.Column("briefing_snapshot", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("extracted_fields", "briefing_snapshot")
