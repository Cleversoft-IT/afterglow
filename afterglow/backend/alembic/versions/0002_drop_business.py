"""drop businesses table, single-tenant schema

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All pre-migration rows belong to the legacy multi-business demo and have
    # no meaning under the new single-tenant model. Wipe them so the new seed
    # can repopulate cleanly (and so the partial unique index below doesn't
    # trip on three rows all marked is_active=TRUE).
    op.execute("DELETE FROM customer_memory_chunks")
    op.execute("DELETE FROM audit_log")
    op.execute("DELETE FROM executed_actions")
    op.execute("DELETE FROM extracted_fields")
    op.execute("DELETE FROM calls")
    op.execute("DELETE FROM template_versions")
    op.execute("DELETE FROM customers")
    op.execute("DELETE FROM templates")

    # Drop composite indexes that include business_id.
    op.drop_index("idx_templates_business", table_name="templates")
    op.drop_index("idx_customers_phone", table_name="customers")
    op.drop_index("idx_calls_business_status", table_name="calls")

    # Drop business-scoped unique constraints (will be recreated globally).
    op.drop_constraint("uq_template_name_version", "templates", type_="unique")
    op.drop_constraint("uq_customer_phone", "customers", type_="unique")

    # Drop foreign keys to businesses (auto-generated names from 0001).
    op.drop_constraint("templates_business_id_fkey", "templates", type_="foreignkey")
    op.drop_constraint("customers_business_id_fkey", "customers", type_="foreignkey")
    op.drop_constraint("calls_business_id_fkey", "calls", type_="foreignkey")

    # Drop business_id columns explicitly.
    op.drop_column("templates", "business_id")
    op.drop_column("customers", "business_id")
    op.drop_column("calls", "business_id")

    # Drop businesses table.
    op.drop_table("businesses")

    # Add domain_hint to templates. Default "generic" lets existing rows survive;
    # seed will populate restaurant/dentist/bodyshop explicitly.
    op.add_column(
        "templates",
        sa.Column(
            "domain_hint",
            sa.String(32),
            nullable=False,
            server_default="generic",
        ),
    )

    # Recreate uniques without business scope.
    op.create_unique_constraint(
        "uq_template_name_version", "templates", ["name", "version"]
    )
    op.create_unique_constraint(
        "uq_customer_phone", "customers", ["phone_e164"]
    )

    # Partial unique index: at most one active template at a time.
    # Zero-active is allowed at the DB level and handled by the API (409).
    op.create_index(
        "uq_template_active",
        "templates",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )

    # Recreate non-composite indexes.
    op.create_index("idx_calls_status", "calls", ["status"])
    op.create_index("idx_customers_phone", "customers", ["phone_e164"])


def downgrade() -> None:
    op.drop_index("idx_customers_phone", table_name="customers")
    op.drop_index("idx_calls_status", table_name="calls")
    op.drop_index("uq_template_active", table_name="templates")
    op.drop_constraint("uq_customer_phone", "customers", type_="unique")
    op.drop_constraint("uq_template_name_version", "templates", type_="unique")

    op.drop_column("templates", "domain_hint")

    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("default_language", sa.String(10), server_default="it"),
        sa.Column("timezone", sa.String(50), server_default="Europe/Rome"),
        sa.Column("settings", postgresql.JSONB, server_default="{}"),
        sa.Column("vultr_collection_id", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.add_column(
        "templates",
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "calls",
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_foreign_key(
        "templates_business_id_fkey",
        "templates",
        "businesses",
        ["business_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "customers_business_id_fkey",
        "customers",
        "businesses",
        ["business_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "calls_business_id_fkey",
        "calls",
        "businesses",
        ["business_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_unique_constraint(
        "uq_template_name_version",
        "templates",
        ["business_id", "name", "version"],
    )
    op.create_unique_constraint(
        "uq_customer_phone",
        "customers",
        ["business_id", "phone_e164"],
    )

    op.create_index(
        "idx_templates_business", "templates", ["business_id", "is_active"]
    )
    op.create_index(
        "idx_customers_phone", "customers", ["business_id", "phone_e164"]
    )
    op.create_index(
        "idx_calls_business_status", "calls", ["business_id", "status"]
    )
