import uuid
from datetime import datetime, timezone
from typing import Any


def send_email_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": f"EM-{uuid.uuid4().hex[:10]}",
        "channel": "email",
        "to": payload.get("to"),
        "subject": payload.get("subject", "(no subject)"),
        "delivered_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def send_quote_email_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": f"QT-{uuid.uuid4().hex[:10]}",
        "channel": "email",
        "to": payload.get("to"),
        "subject": payload.get("subject", "Your quote"),
        "quote_amount": payload.get("quote_amount"),
        "delivered_at": datetime.now(tz=timezone.utc).isoformat(),
    }
