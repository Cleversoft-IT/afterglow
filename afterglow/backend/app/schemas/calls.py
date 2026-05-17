"""Pydantic schemas for the calls API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.customers import CustomerCard


class CallSubmittedResponse(BaseModel):
    call_id: UUID
    status: str = "pending"


class FieldDefinitionLite(BaseModel):
    """Subset of the template's FieldDefinition used to label extracted fields
    in the call detail UI. The full definition lives on the Template; we only
    ship what the renderer needs."""

    key: str
    label: str
    type: str = "string"


class CallActionView(BaseModel):
    id: UUID
    action_type: str
    title: str
    summary: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    confidence: Optional[float] = None
    evidence: Optional[list[str]] = None
    execution_mode: str = "auto"
    status: str
    reverted_at: Optional[datetime] = None
    created_at: datetime
    # Server-computed visibility hints. `is_simulated` drives the
    # "Simulated" badge in the UI (true for mock_external + unknown keys);
    # `can_undo` controls whether the Undo button is shown at all.
    is_simulated: bool = True
    can_undo: bool = False


class CallExtractedView(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    # Per-key metadata so the UI can show a human label next to the machine
    # key. Only fields actually present in `fields` get an entry here.
    field_definitions: list[FieldDefinitionLite] = Field(default_factory=list)


class CallDetailView(BaseModel):
    id: UUID
    customer_id: Optional[UUID] = None
    customer: Optional[CustomerCard] = None
    template_id: UUID
    phone_e164: str
    detected_language: Optional[str] = None
    raw_transcript: Optional[dict[str, Any]] = None
    status: str
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    extracted: Optional[CallExtractedView] = None
    executed_actions: list[CallActionView] = Field(default_factory=list)


class CallListItem(BaseModel):
    id: UUID
    phone_e164: str
    customer_id: Optional[UUID] = None
    customer_display_name: Optional[str] = None
    template_id: UUID
    status: str
    detected_language: Optional[str] = None
    created_at: datetime
