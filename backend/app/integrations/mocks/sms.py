import uuid
from datetime import datetime, timezone
from typing import Any


def send_sms_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": f"SMS-{uuid.uuid4().hex[:10].upper()}",
        "status": "delivered",
        "delivered_at": datetime.now(tz=timezone.utc).isoformat(),
        "to": payload.get("phone_e164"),
    }
