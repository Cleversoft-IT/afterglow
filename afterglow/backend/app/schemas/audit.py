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
