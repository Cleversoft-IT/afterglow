import uuid
from datetime import datetime, timezone
from typing import Any


def update_customer_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "customer_id": payload.get("customer_id"),
        "updated_fields": list(payload.get("fields", {}).keys()),
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def create_lead_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "lead_id": f"LD-{uuid.uuid4().hex[:10].upper()}",
        "status": "new",
        "source": payload.get("source", "phone_call"),
        "name": payload.get("name"),
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def create_ticket_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticket_id": f"TKT-{uuid.uuid4().hex[:10].upper()}",
        "status": "open",
        "priority": payload.get("priority", "normal"),
        "subject": payload.get("subject"),
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
