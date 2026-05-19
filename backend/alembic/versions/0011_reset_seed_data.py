"""Reset all seed/demo data so the new seed shape lands on next entrypoint.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-16

Migrations 0008-0010 extended the schema (is_seed, profile_facts,
simulation_config) and seed.py was updated to populate seed call history +
bundled simulation_config + internal_real action wiring. But seed.py
short-circuits when templates already exist, so an installation that was
seeded before this round of changes never sees the new content.

DB content is disposable (see `.claude/memory/feedback_db_disposable.md`),
so the safe move is to TRUNCATE every table that the seed touches and let
the entrypoint re-run seed.py against the new schema. Demo sessions are
included so the iframe sandbox starts clean too.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Order matters only for human-readability; CASCADE drops referencing rows
# transparently.
_TABLES = (
    "audit_log",
    "customer_memory_chunks",
    "executed_actions",
    "extracted_fields",
    "calls",
    "demo_sessions",
    "templates",
    "customers",
)


def upgrade() -> None:
    op.execute(
        "TRUNCATE TABLE "
        + ", ".join(_TABLES)
        + " RESTART IDENTITY CASCADE"
    )


def downgrade() -> None:
    # No-op: the data we wiped was seed/demo only — there is nothing to
    # restore on a downgrade.
    pass
