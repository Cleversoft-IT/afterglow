"""customers.profile_facts JSONB — store internal-real action facts.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-16

`customer.update_profile` is upgraded from mock_external to internal_real:
the executor writes the latest known facts (allergies, seating preferences,
free-form notes) directly onto the customer row, and snapshots the previous
state so an undo can flip them back. The blob lives in a JSONB column to
keep template-driven keys (`allergies`, `seating_preference`, `occasion`...)
soft-typed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "profile_facts",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("customers", "profile_facts")
