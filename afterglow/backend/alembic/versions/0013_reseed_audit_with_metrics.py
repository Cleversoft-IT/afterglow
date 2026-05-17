"""Reseed audit_log so the new seed shape (duration + token + payload) lands.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-17

`_emit_seeded_call_audit` now populates `duration_ms`, `input_tokens`,
`output_tokens` and `payload` with realistic values for each pipeline step,
so the Audit log surfaces meaningful numbers even when no live pipeline has
run after a reset. seed.py short-circuits when templates already exist, so
existing installations would never see the new audit rows unless we wipe
the seedable tables and let entrypoint re-run the seed.

DB content is disposable (see `.claude/memory/feedback_db_disposable.md`);
we TRUNCATE the same set of tables as migration 0011.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    pass
