"""Schema-level tests for the CallListItem response, focused on the
`customer_tags` field added in round 7. A full HTTP/integration test would
require a Postgres ephemeral instance (Customer.tags is ARRAY(String), no
SQLite parity), so these assertions stay at the Pydantic boundary — they
catch typos, missing defaults, and serialization regressions without
spinning up a DB."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas import CallListItem


def _base_kwargs(**overrides):
    base = dict(
        id=uuid.uuid4(),
        phone_e164="+15551234567",
        template_id=uuid.uuid4(),
        status="completed",
        created_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return base


def test_customer_tags_defaults_to_empty_list():
    item = CallListItem(**_base_kwargs())
    assert item.customer_tags == []


def test_customer_tags_accepts_string_list():
    item = CallListItem(
        **_base_kwargs(customer_tags=["repeat", "gluten_free"])
    )
    assert item.customer_tags == ["repeat", "gluten_free"]


def test_customer_tags_roundtrip_json():
    item = CallListItem(
        **_base_kwargs(
            customer_id=uuid.uuid4(),
            customer_display_name="Mark Ross",
            customer_tags=["repeat"],
        )
    )
    payload = item.model_dump()
    assert payload["customer_tags"] == ["repeat"]
    rebuilt = CallListItem.model_validate(payload)
    assert rebuilt.customer_tags == ["repeat"]


def test_customer_tags_missing_in_payload_becomes_empty():
    # Mimics the LEFT JOIN miss: API code passes `list(tags or [])` so the
    # caller never sees None — but make sure the schema itself stays
    # defensive if a payload omits the key entirely.
    payload = _base_kwargs()
    item = CallListItem.model_validate(payload)
    assert item.customer_tags == []
