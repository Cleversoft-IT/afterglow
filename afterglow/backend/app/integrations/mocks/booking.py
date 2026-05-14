import uuid
from datetime import datetime, timezone
from typing import Any


def create_booking_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "booking_id": f"BK-{uuid.uuid4().hex[:8].upper()}",
        "status": "confirmed",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "echo": payload,
    }


def cancel_booking_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "booking_id": payload.get("booking_id", "unknown"),
        "status": "cancelled",
        "cancelled_at": datetime.now(tz=timezone.utc).isoformat(),
    }
