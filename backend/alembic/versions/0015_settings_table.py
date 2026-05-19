"""runtime settings table (round-9: seed anchor + relative-date dataset)

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-18

Round-9 ships a relative-date seed dataset: every `created_at` lands as
`anchor + day_offset`, where `anchor` is persisted in this new `settings`
table under the `seed_anchor_date` key. A startup task in `main.py:lifespan`
calls `refresh_seed_dates_if_needed(today)` which BULK-UPDATEs all seed
timestamps by `today - anchor` so the demo never shows stale "2 weeks ago"
calls.

The table is intentionally generic key/value so future runtime flags can
share it without another schema bump.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("settings")
