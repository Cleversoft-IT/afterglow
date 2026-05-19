"""Pydantic schemas for audit log views."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    id: UUID
    call_id: Optional[UUID]
    agent_name: str
    step_type: str
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    duration_ms: Optional[int] = None
    payload: Optional[dict[str, Any]] = None
    status: str
    error: Optional[str] = None
    created_at: datetime
    # Pre-joined call metadata (populated by the list_audit endpoint via a
    # LEFT JOIN on Call + Customer) so the overview UI can group + label
    # rows without an N+1 lookup per call_id. All optional because audit
    # rows can have call_id IS NULL (lifespan events) or a Call without a
    # resolved Customer (cold-call pipeline failure).
    call_phone_e164: Optional[str] = None
    call_display_name: Optional[str] = None
    call_status: Optional[str] = None
