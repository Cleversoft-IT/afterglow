"""Pydantic schemas for the calls API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CallSubmittedResponse(BaseModel):
    call_id: UUID
    status: str = "pending"


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


class CallExtractedView(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None


class CallDetailView(BaseModel):
    id: UUID
    customer_id: Optional[UUID] = None
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
    template_id: UUID
    status: str
    detected_language: Optional[str] = None
    created_at: datetime
