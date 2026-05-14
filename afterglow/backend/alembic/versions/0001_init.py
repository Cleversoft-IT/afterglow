"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("default_language", sa.String(10), server_default="it"),
        sa.Column("timezone", sa.String(50), server_default="Europe/Rome"),
        sa.Column("settings", postgresql.JSONB, server_default="{}"),
        sa.Column("vultr_collection_id", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("fields_schema", postgresql.JSONB, server_default="[]"),
        sa.Column("action_types", postgresql.JSONB, server_default="[]"),
        sa.Column("custom_dictionary", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("prompt_hints", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("business_id", "name", "version", name="uq_template_name_version"),
    )
    op.create_index("idx_templates_business", "templates", ["business_id", "is_active"])

    op.create_table(
        "template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("snapshot", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("template_id", "version", name="uq_template_version"),
    )

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_e164", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("preferred_language", sa.String(10), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("memory_summary", sa.Text, nullable=True),
        sa.Column("total_calls", sa.Integer, server_default="0"),
        sa.Column("last_call_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("business_id", "phone_e164", name="uq_customer_phone"),
    )
    op.create_index("idx_customers_phone", "customers", ["business_id", "phone_e164"])

    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("phone_e164", sa.String(32), nullable=False),
        sa.Column("audio_url", sa.Text, nullable=True),
        sa.Column("audio_duration_sec", sa.Integer, nullable=True),
        sa.Column("detected_language", sa.String(10), nullable=True),
        sa.Column("raw_transcript", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_calls_business_status", "calls", ["business_id", "status"])
    op.create_index("idx_calls_customer", "calls", ["customer_id", "created_at"])

    op.create_table(
        "extracted_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fields", postgresql.JSONB, server_default="{}"),
        sa.Column("confidence", postgresql.JSONB, server_default="{}"),
        sa.Column("evidence", postgresql.JSONB, server_default="{}"),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("urgency", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "executed_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("payload", postgresql.JSONB, server_default="{}"),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.Column("execution_mode", sa.String(20), server_default="auto"),
        sa.Column("status", sa.String(30), server_default="executed"),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_actions_call", "executed_actions", ["call_id"])
    op.create_index("idx_actions_status", "executed_actions", ["status", "created_at"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_name", sa.String(80), nullable=False),
        sa.Column("step_type", sa.String(40), nullable=False),
        sa.Column("model", sa.String(80), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), server_default="success"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_audit_call", "audit_log", ["call_id", "created_at"])
    op.create_index("idx_audit_agent", "audit_log", ["agent_name", "created_at"])

    op.create_table(
        "customer_memory_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vultr_collection_id", sa.String(200), nullable=False),
        sa.Column("vultr_item_id", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("chunk_metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("vultr_collection_id", "vultr_item_id", name="uq_memory_chunk"),
    )
    op.create_index("idx_memory_customer", "customer_memory_chunks", ["customer_id", "created_at"])


def downgrade() -> None:
    op.drop_table("customer_memory_chunks")
    op.drop_table("audit_log")
    op.drop_table("executed_actions")
    op.drop_table("extracted_fields")
    op.drop_table("calls")
    op.drop_table("customers")
    op.drop_table("template_versions")
    op.drop_table("templates")
    op.drop_table("businesses")
