"""add Call.is_anchor_day flag for day_offset=0 seed reposition

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-19

The lifespan refresh task uses this flag to identify the day_offset=0
seed Call rows (Sophie Walker booking + a mock) and reposition them just
before `now` on every boot. Without the flag, identifying anchor-day
rows by `date(created_at) = today` is unstable: after the first
reposition the new `created_at` can fall into the previous UTC day, so
the next boot would miss them.

Pre-existing rows get `is_anchor_day = FALSE` via the server default;
since migration 0017 already wiped every seed Call, on a deployed DB
the next seed run re-materializes the day_offset=0 slots with the flag
set to TRUE explicitly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "calls",
        sa.Column(
            "is_anchor_day",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("calls", "is_anchor_day")
