import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


def _ts() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def _ts_updated() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = (
        # Uniqueness of (name, version) is enforced by two partial indexes —
        # one for prod tenant rows (session_id IS NULL) and one for demo
        # session rows. A plain UniqueConstraint that includes session_id
        # would let multiple prod rows share the same name/version because
        # Postgres treats NULL as distinct.
        Index(
            "uq_template_name_version_prod",
            "name",
            "version",
            unique=True,
            postgresql_where=text("session_id IS NULL"),
        ),
        Index(
            "uq_template_name_version_session",
            "name",
            "version",
            "session_id",
            unique=True,
            postgresql_where=text("session_id IS NOT NULL"),
        ),
        Index(
            "uq_template_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active IS TRUE AND session_id IS NULL"),
        ),
        Index("idx_templates_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain_hint: Mapped[str] = mapped_column(
        String(32), nullable=False, default="generic"
    )
    fields_schema: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    action_types: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    # JSONB array of {when, then} rules. See schemas.templates.PromptHintRule.
    prompt_hints: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Per-template demo recording config (caller name + phone + TTS script +
    # audio file location). Null for seed templates that ship the bundled
    # MP3s under app/assets/audio/. See migration 0010.
    simulation_config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = _ts_updated()


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("idx_customers_phone", "phone_e164"),
        Index(
            "uq_customer_phone_seed",
            "phone_e164",
            unique=True,
            postgresql_where=text("session_id IS NULL"),
        ),
        Index(
            "uq_customer_phone_session",
            "phone_e164",
            "session_id",
            unique=True,
            postgresql_where=text("session_id IS NOT NULL"),
        ),
        Index("idx_customers_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    phone_e164: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    preferred_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    # Free-form bag of facts learned across calls (allergies, seating
    # preferences, occasion, etc.). `customer.update_profile` is the only
    # writer; the orchestrator reads it on the next call's caller card.
    profile_facts: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    memory_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    last_call_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = _ts_updated()


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (
        Index("idx_calls_status", "status"),
        Index("idx_calls_customer", "customer_id", "created_at"),
        Index("idx_calls_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id", ondelete="RESTRICT")
    )
    phone_e164: Mapped[str] = mapped_column(String(32), nullable=False)
    audio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    raw_transcript: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = _ts()


class ExtractedFields(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[uuid.UUID] = _uuid_pk()
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE")
    )
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    confidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Per-call snapshot of next_call_briefing — Customer.memory_summary holds
    # only the latest; this preserves history for structured_history lookups.
    briefing_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _ts()


class ExecutedAction(Base):
    __tablename__ = "executed_actions"
    __table_args__ = (
        Index("idx_actions_call", "call_id"),
        Index("idx_actions_status", "status", "created_at"),
        Index("idx_actions_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE")
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    evidence: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(20), default="auto")
    status: Mapped[str] = mapped_column(String(30), default="executed")
    reverted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reverted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = _ts()


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_call", "call_id", "created_at"),
        Index("idx_audit_agent", "agent_name", "created_at"),
        Index("idx_audit_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    call_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True
    )
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    step_type: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = _ts()


class CustomerMemoryChunk(Base):
    __tablename__ = "customer_memory_chunks"
    __table_args__ = (
        UniqueConstraint("vultr_collection_id", "vultr_item_id", name="uq_memory_chunk"),
        Index("idx_memory_customer", "customer_id", "created_at"),
        Index("idx_memory_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE")
    )
    call_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True
    )
    vultr_collection_id: Mapped[str] = mapped_column(String(200), nullable=False)
    vultr_item_id: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = _ts()


class DemoSession(Base):
    """Anonymous sandbox for a single demo iframe visitor.

    A row materializes the first time the backend sees a request with a
    new `X-Demo-Session` header from the iframe origin. The session scopes
    every write the visitor makes (template wizard outputs, calls, customers,
    audit, executed actions) so concurrent judges do not stomp on each other.

    `active_template_id` replaces `Template.is_active` for demo callers: in
    demo mode `GET /templates/active` reads from here, `PUT /templates/active`
    updates here. Production single-tenant (no header) keeps using `is_active`.
    """

    __tablename__ = "demo_sessions"
    __table_args__ = (Index("idx_demo_sessions_last_seen", "last_seen_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    active_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = _ts()
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
