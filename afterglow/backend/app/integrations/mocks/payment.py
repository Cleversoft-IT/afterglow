import uuid
from datetime import datetime, timezone
from typing import Any


def create_payment_link_mock(payload: dict[str, Any]) -> dict[str, Any]:
    link_id = f"PAY-{uuid.uuid4().hex[:10].upper()}"
    return {
        "payment_id": link_id,
        "status": "pending",
        "payment_url": f"https://pay.example/{link_id}",
        "amount": payload.get("amount"),
        "currency": payload.get("currency", "EUR"),
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def request_deposit_mock(payload: dict[str, Any]) -> dict[str, Any]:
    link_id = f"DEP-{uuid.uuid4().hex[:10].upper()}"
    return {
        "deposit_id": link_id,
        "status": "requested",
        "payment_url": f"https://pay.example/deposit/{link_id}",
        "amount": payload.get("amount"),
        "currency": payload.get("currency", "EUR"),
        "booking_reference": payload.get("booking_reference"),
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def send_invoice_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "invoice_id": f"INV-{uuid.uuid4().hex[:10].upper()}",
        "status": "sent",
        "to": payload.get("to"),
        "amount": payload.get("amount"),
        "currency": payload.get("currency", "EUR"),
        "sent_at": datetime.now(tz=timezone.utc).isoformat(),
    }
