"""templates v2: structured prompt_hints, per-session uniqueness, wipe data

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-16

Reshapes `Template` to support the v2 schema (FieldDefinition + ActionDefinition
extended with confidence/PII/preconditions/payload_schema metadata, and
`prompt_hints` as a JSONB array of `{when, then}` rules instead of a free-text
string). Also fixes the unique-constraint trap on `(name, version)` so two demo
sessions can save the same template name without colliding.

Destructive: every row in `templates` and the tables that cascade from it is
deleted before the schema change. This is intentional — demo records are
disposable and there is no production tenant whose data must be preserved
(see `.claude/memory/feedback_db_disposable.md`). The seed re-runs from
`seed.py` on the next backend boot.

Why split the unique into two partial indexes:
  Postgres treats NULL as distinct in a unique constraint. A naive
  `UNIQUE (name, version, session_id)` would allow multiple prod rows with
  `session_id IS NULL` to share the same name/version. The fix is two partial
  indexes — one for prod (`session_id IS NULL`), one for demo sessions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Wipe all rows whose shape may not match v2. Cascade order matters
    # because `calls.template_id` is RESTRICT and there are FKs from
    # executed_actions/extracted_fields/audit_log/customer_memory_chunks to
    # `calls` and `customers`. Demo_sessions FK to templates.
    op.execute(
        "TRUNCATE TABLE executed_actions, extracted_fields, "
        "customer_memory_chunks, audit_log, calls, demo_sessions, "
        "customers, template_versions, templates "
        "RESTART IDENTITY CASCADE"
    )

    # 2. Drop the legacy global unique on (name, version). Replaced below.
    op.drop_constraint(
        "uq_template_name_version", "templates", type_="unique"
    )

    # 3. Reshape prompt_hints: Text -> JSONB. Drop & re-add is cleanest now
    # that the table is empty — avoids the fragility of ALTER COLUMN … USING.
    op.drop_column("templates", "prompt_hints")
    op.add_column(
        "templates",
        sa.Column("prompt_hints", postgresql.JSONB(), nullable=True),
    )

    # 4. Two partial unique indexes for (name, version) scoped by session_id.
    # Prod rows (session_id IS NULL) get a globally unique (name, version).
    # Demo rows get unique (name, version) per session_id.
    op.create_index(
        "uq_template_name_version_prod",
        "templates",
        ["name", "version"],
        unique=True,
        postgresql_where=sa.text("session_id IS NULL"),
    )
    op.create_index(
        "uq_template_name_version_session",
        "templates",
        ["name", "version", "session_id"],
        unique=True,
        postgresql_where=sa.text("session_id IS NOT NULL"),
    )


def downgrade() -> None:
    # Best-effort rollback: rebuild legacy unique + Text column. Data wipe
    # cannot be undone (and is intentional).
    op.drop_index(
        "uq_template_name_version_session", table_name="templates"
    )
    op.drop_index(
        "uq_template_name_version_prod", table_name="templates"
    )

    op.drop_column("templates", "prompt_hints")
    op.add_column(
        "templates",
        sa.Column("prompt_hints", sa.Text(), nullable=True),
    )

    op.create_unique_constraint(
        "uq_template_name_version", "templates", ["name", "version"]
    )
