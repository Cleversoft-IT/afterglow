"""demo iframe sandbox: per-session scoping

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-15

Adds an optional `session_id` to every table that the public demo iframe
mutates so concurrent visitors do not stomp on each other. The production
single-tenant path keeps writing rows with `session_id IS NULL` and is
unchanged semantically.

The new `demo_sessions` table tracks the visitor's identity (`X-Demo-Session`
header) plus its picked active template. The partial unique index on
`templates.is_active` is rescoped to only enforce uniqueness for the seed
templates (`session_id IS NULL`), so wizard-generated templates inside a
session can freely coexist.

`customers.phone_e164` loses its global unique constraint; we split it into
two partial unique indexes — one for seed customers, one for session clones.

`extracted_fields` is intentionally NOT scoped: it cascades from `calls`, and
cleanup deletes the parent first.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SESSIONED_TABLES = (
    "calls",
    "audit_log",
    "executed_actions",
    "customer_memory_chunks",
    "templates",
    "customers",
)


def upgrade() -> None:
    # 1. demo_sessions table.
    op.create_table(
        "demo_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "active_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_demo_sessions_last_seen", "demo_sessions", ["last_seen_at"]
    )

    # 2. session_id column on every demo-writable table + index.
    for table in SESSIONED_TABLES:
        op.add_column(
            table,
            sa.Column(
                "session_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_index(f"idx_{table}_session", table, ["session_id"])

    # 3. templates: rescope the "single active" partial unique to seed only.
    op.drop_index("uq_template_active", table_name="templates")
    op.create_index(
        "uq_template_active",
        "templates",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE AND session_id IS NULL"),
    )

    # 4. customers: drop the global unique on phone_e164, split into two
    # partial uniques (seed vs per-session).
    op.drop_constraint("uq_customer_phone", "customers", type_="unique")
    op.create_index(
        "uq_customer_phone_seed",
        "customers",
        ["phone_e164"],
        unique=True,
        postgresql_where=sa.text("session_id IS NULL"),
    )
    op.create_index(
        "uq_customer_phone_session",
        "customers",
        ["phone_e164", "session_id"],
        unique=True,
        postgresql_where=sa.text("session_id IS NOT NULL"),
    )


def downgrade() -> None:
    # customers: rebuild the global unique.
    op.drop_index("uq_customer_phone_session", table_name="customers")
    op.drop_index("uq_customer_phone_seed", table_name="customers")
    op.create_unique_constraint(
        "uq_customer_phone", "customers", ["phone_e164"]
    )

    # templates: rebuild the original partial unique.
    op.drop_index("uq_template_active", table_name="templates")
    op.create_index(
        "uq_template_active",
        "templates",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )

    for table in SESSIONED_TABLES:
        op.drop_index(f"idx_{table}_session", table_name=table)
        op.drop_column(table, "session_id")

    op.drop_index("idx_demo_sessions_last_seen", table_name="demo_sessions")
    op.drop_table("demo_sessions")
