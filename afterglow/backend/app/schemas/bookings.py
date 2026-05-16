"""Bookings list — executed reservation actions across calls."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class BookingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_id: uuid.UUID
    customer_id: Optional[uuid.UUID] = None
    action_type: str
    title: str
    summary: Optional[str] = None
    payload: dict[str, Any] = {}
    status: str
    created_at: datetime
    customer_display_name: Optional[str] = None
    customer_phone_e164: Optional[str] = None
    is_simulated: bool = False
    can_undo: bool = False
