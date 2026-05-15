"""purge legacy rows + introduce explicit is_seed flag

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-15

Migration 0003 made `session_id IS NULL` mean both "seed, visible to
everyone" AND "production single-tenant row". That conflation breaks two
things:

  1. Demo writes made BEFORE 0003 (calls, audit, executed_actions,
     memory_chunks) landed with `session_id IS NULL` and now leak into
     every brand-new demo session.
  2. If production single-tenant ever writes its own data (via bypass
     mode or with no header), those rows would also be `session_id IS
     NULL` and would leak into the demo sandbox the same way.

The clean separation:
  - `templates` and `customers` have a real `is_seed BOOLEAN` column.
    The three preset templates and the two known callers are
    `is_seed = TRUE`. Demo visitors see seeds + their own clones;
    production tenant sees seeds + its own writes.
  - `calls`, `audit_log`, `executed_actions`, `customer_memory_chunks`
    do not have a notion of "seed" — they are pure activity logs. Demo
    sessions see strictly their own rows; production tenant sees only
    its own (session_id IS NULL).

This migration:
  1. Deletes every demo-noise row that has `session_id IS NULL` on the
     activity-log tables (calls, audit, executed_actions, memory_chunks).
  2. Adds `is_seed BOOLEAN NOT NULL DEFAULT FALSE` to templates and
     customers.
  3. Flips `is_seed = TRUE` for the three seed template names and the
     two seed phone numbers.
  4. Deletes any non-seed template/customer that has `session_id IS
     NULL` (i.e. demo writes from before 0003 against unknown phones).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_CUSTOMER_PHONES = ("+393331112233", "+393334445566")
SEED_TEMPLATE_NAMES = (
    "Standard booking",
    "Appointment intake",
    "Damage quote intake",
)


def upgrade() -> None:
    # 1. Wipe legacy demo activity (session_id IS NULL on activity tables).
    op.execute("DELETE FROM customer_memory_chunks WHERE session_id IS NULL")
    op.execute("DELETE FROM executed_actions WHERE session_id IS NULL")
    op.execute("DELETE FROM audit_log WHERE session_id IS NULL")
    # `calls` cascades to extracted_fields.
    op.execute("DELETE FROM calls WHERE session_id IS NULL")

    # 2. Add is_seed columns.
    op.add_column(
        "templates",
        sa.Column(
            "is_seed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "is_seed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # 3. Flip the seeds.
    seed_names_sql = ", ".join(f"'{n}'" for n in SEED_TEMPLATE_NAMES)
    seed_phones_sql = ", ".join(f"'{p}'" for p in SEED_CUSTOMER_PHONES)
    op.execute(
        f"UPDATE templates SET is_seed = TRUE "
        f"WHERE session_id IS NULL AND name IN ({seed_names_sql})"
    )
    op.execute(
        f"UPDATE customers SET is_seed = TRUE "
        f"WHERE session_id IS NULL AND phone_e164 IN ({seed_phones_sql})"
    )

    # 4. Purge orphan templates/customers (legacy demo noise with
    # session_id IS NULL but not flagged as seed).
    op.execute(
        "DELETE FROM templates WHERE session_id IS NULL AND is_seed IS FALSE"
    )
    op.execute(
        "DELETE FROM customers WHERE session_id IS NULL AND is_seed IS FALSE"
    )


def downgrade() -> None:
    op.drop_column("customers", "is_seed")
    op.drop_column("templates", "is_seed")
    # Deleted rows are not restored — they were orphan demo noise.
