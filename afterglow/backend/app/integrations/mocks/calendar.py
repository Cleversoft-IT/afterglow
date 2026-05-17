import uuid
from datetime import datetime, timezone
from typing import Any


def add_calendar_event_mock(payload: dict[str, Any]) -> dict[str, Any]:
    event_id = f"EVT-{uuid.uuid4().hex[:10].upper()}"
    return {
        "event_id": event_id,
        "status": "scheduled",
        "ical_url": f"https://cal.example/{event_id}.ics",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "echo": payload,
    }


def send_calendar_invite_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "invite_id": f"INV-{uuid.uuid4().hex[:10].upper()}",
        "status": "sent",
        "to": payload.get("to"),
        "sent_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def block_calendar_slot_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "block_id": f"BLK-{uuid.uuid4().hex[:10].upper()}",
        "status": "blocked",
        "start": payload.get("start"),
        "end": payload.get("end"),
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
