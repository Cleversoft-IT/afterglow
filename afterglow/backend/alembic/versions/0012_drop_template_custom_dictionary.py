"""Drop templates.custom_dictionary column.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-17

Templates no longer carry an ASR custom dictionary. Speechmatics now runs
without `additional_vocab` — the column is dead. See ticket
`simplify-template-fuzzy-forest` and `.claude/memory/project_template_simplified_2026_05_17.md`.

Existing seed rows were already TRUNCATEd by migration 0011 and will be
re-seeded by entrypoint.sh against the new shape, so the column drop has no
data to mourn.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY


revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("templates", "custom_dictionary")


def downgrade() -> None:
    op.add_column(
        "templates",
        sa.Column(
            "custom_dictionary",
            ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
