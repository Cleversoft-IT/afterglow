import uuid
from datetime import datetime, timezone
from typing import Any


def request_review_feedback_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_request_id": f"REV-{uuid.uuid4().hex[:10].upper()}",
        "status": "sent",
        "channel": payload.get("channel"),
        "platform": payload.get("platform", "google"),
        "sent_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def publish_review_response_mock(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "response_id": f"RSP-{uuid.uuid4().hex[:10].upper()}",
        "status": "published",
        "review_id": payload.get("review_id"),
        "published_at": datetime.now(tz=timezone.utc).isoformat(),
    }
