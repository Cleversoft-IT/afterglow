"""add is_seed flag to calls + executed_actions

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-16

The seed script needs to insert demo Call rows (Mark Ross / Julia White) so
the fresh-install dashboard shows realistic history alongside the seeded
customers. We flag those rows with `is_seed=True` for parity with the
existing `customers.is_seed` and `templates.is_seed` columns, so future
cleanup scripts can target seed-only rows. Same flag on `executed_actions`
because the seed plants matching action history (booking.create +
whatsapp.send_confirmation + customer.update_profile).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "calls",
        sa.Column(
            "is_seed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "executed_actions",
        sa.Column(
            "is_seed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("executed_actions", "is_seed")
    op.drop_column("calls", "is_seed")
