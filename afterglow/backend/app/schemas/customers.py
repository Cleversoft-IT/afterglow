"""Pydantic schemas for customers."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCard(BaseModel):
    id: UUID
    phone_e164: str
    display_name: Optional[str] = None
    preferred_language: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    memory_summary: Optional[str] = None
    total_calls: int = 0
    last_call_at: Optional[datetime] = None


class CustomerProfileView(CustomerCard):
    created_at: datetime
