from datetime import datetime, timezone
from typing import Any


def update_customer_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "customer_id": payload.get("customer_id"),
        "updated_fields": list(payload.get("fields", {}).keys()),
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
