import uuid
from datetime import datetime, timezone
from typing import Any


def send_whatsapp_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": f"WA-{uuid.uuid4().hex[:10]}",
        "channel": "whatsapp",
        "to": payload.get("to") or payload.get("phone_e164"),
        "body": payload.get("body") or "[generated confirmation]",
        "delivered_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def request_photos_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": f"WA-{uuid.uuid4().hex[:10]}",
        "channel": "whatsapp",
        "to": payload.get("to") or payload.get("phone_e164"),
        "body": payload.get("body") or "Please share photos of the damage.",
        "delivered_at": datetime.now(tz=timezone.utc).isoformat(),
    }
