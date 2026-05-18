"""Contract tests for the three seed templates (restaurant / dentist /
bodyshop). The BookingBadge in the UI relies on
`payload.booking_date` + `payload.booking_time` being present on every
`booking.create` action emitted by a seed call — this only happens if the
template schema requires those fields. These tests pin the contract at the
schema level so the bug can't sneak back in via a partial rename."""
from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.db.seed import (
    BODYSHOP_TEMPLATE,
    DENTIST_TEMPLATE,
    RESTAURANT_TEMPLATE,
    SEED_CUSTOMERS,
    _AI_BOOKING_BLUEPRINTS,
    _CUSTOMER_PHONES_BY_NAME,
    _ensure_seed_customers,
    _make_ai_booking_spec,
)


SEED_TEMPLATES = {
    "restaurant": RESTAURANT_TEMPLATE,
    "dentist": DENTIST_TEMPLATE,
    "bodyshop": BODYSHOP_TEMPLATE,
}


SIX_CUSTOMERS = {
    "Mark Ross",
    "Julia White",
    "Laura Bennett",
    "Andrew Green",
    "Sophie Walker",
    "Tom Hughes",
}


def test_booking_create_preconditions_require_slot_fields():
    """Every `booking.create` in a seed template must list `booking_date`
    and `booking_time` in its preconditions, so the planner refuses to
    emit the action until both are extracted."""
    for name, template in SEED_TEMPLATES.items():
        action = next(
            (a for a in template["action_types"] if a["key"] == "booking.create"),
            None,
        )
        assert action is not None, f"{name}: booking.create missing from template"
        preconditions = set(action.get("preconditions", []))
        missing = {"booking_date", "booking_time"} - preconditions
        assert missing == set(), (
            f"{name}: booking.create preconditions missing slot fields {missing}"
        )


def test_booking_create_payload_required_includes_slot_fields():
    """Every `booking.create` payload schema must have booking_date and
    booking_time in `required`. Without this the validator + planner can
    still emit a booking without a slot, and BookingBadge renders empty."""
    for name, template in SEED_TEMPLATES.items():
        action = next(
            (a for a in template["action_types"] if a["key"] == "booking.create"),
            None,
        )
        assert action is not None, f"{name}: booking.create missing"
        schema = action.get("payload_schema") or {}
        required = set(schema.get("required", []))
        missing = {"booking_date", "booking_time"} - required
        assert missing == set(), (
            f"{name}: booking.create payload_schema.required missing {missing}"
        )


def test_no_appointment_namespace_in_seed_templates():
    """Round 8 unification — no `appointment.*` action keys should survive
    in any seed template. If a regression reintroduces `appointment.create`
    the wizard / planner would fall back to the unknown-action path and
    the action would be dropped by the validator."""
    for name, template in SEED_TEMPLATES.items():
        for action in template["action_types"]:
            assert not action["key"].startswith("appointment."), (
                f"{name}: forbidden appointment.* key {action['key']}"
            )


def test_no_legacy_appointment_field_keys():
    """The dentist preset used to call the slot fields `preferred_date` /
    `preferred_time_window`. Round 8 renamed them to `booking_date` /
    `booking_time` so BookingBadge can render. A regression that brings
    those keys back would split the consumer contract again."""
    for name, template in SEED_TEMPLATES.items():
        field_keys = {f["key"] for f in template.get("fields_schema", [])}
        forbidden = {"preferred_date", "preferred_time_window", "appointment_date", "appointment_time"}
        clash = field_keys & forbidden
        assert clash == set(), (
            f"{name}: forbidden legacy field keys {clash}"
        )


def test_ai_booking_blueprints_cover_six_customers():
    """Round 9 — the busy-week generator emits `ai_booking` rows for six
    customers (Mark / Julia / Laura / Andrew / Sophie / Tom). The blueprint
    dict must carry exactly that roster, otherwise `_make_ai_booking_spec`
    KeyErrors and the seed boot fails."""
    assert set(_AI_BOOKING_BLUEPRINTS.keys()) == SIX_CUSTOMERS, (
        f"blueprint roster {set(_AI_BOOKING_BLUEPRINTS.keys())} != {SIX_CUSTOMERS}"
    )


def test_each_blueprint_emits_booking_create_with_slots():
    """For every blueprint, `_make_ai_booking_spec` must yield an action
    of type `booking.create` whose payload carries `booking_date` (YYYY-MM-
    DD) and `booking_time` (HH:MM). BookingBadge in the Home renders both;
    if either is missing the chip stays blank."""
    fake_uuid = uuid.UUID("00000000-0000-4000-8000-000000000000")
    created = datetime(2026, 5, 15, 19, 0, tzinfo=timezone.utc)
    for name in SIX_CUSTOMERS:
        spec = _make_ai_booking_spec(
            fixture_uuid=fake_uuid,
            customer_id=fake_uuid,
            template_id=fake_uuid,
            phone="+15550000000",
            created_at=created,
            customer_name=name,
        )
        actions = spec["actions"]
        assert actions and actions[0]["action_type"] == "booking.create", (
            f"{name}: expected booking.create, got {actions}"
        )
        payload = actions[0]["payload"]
        date_str = payload.get("booking_date")
        time_str = payload.get("booking_time")
        assert isinstance(date_str, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str), (
            f"{name}: bad booking_date {date_str!r}"
        )
        assert isinstance(time_str, str) and re.fullmatch(r"\d{2}:\d{2}", time_str), (
            f"{name}: bad booking_time {time_str!r}"
        )


def test_customer_phones_by_name_matches_blueprints():
    """The phone lookup table must cover exactly the blueprint roster:
    `_ensure_personal_calls` resolves `customer_id` via this dict, and a
    missing entry would silently degrade the ai_booking call into a plain
    completed row."""
    assert set(_CUSTOMER_PHONES_BY_NAME.keys()) == set(
        _AI_BOOKING_BLUEPRINTS.keys()
    ), (
        f"phones {set(_CUSTOMER_PHONES_BY_NAME.keys())} != "
        f"blueprints {set(_AI_BOOKING_BLUEPRINTS.keys())}"
    )


def test_seed_customers_constant_matches_blueprints():
    """SEED_CUSTOMERS is the single source of truth for the customer roster
    that both the main seed path and `_ensure_seed_customers` consume. If
    its names drift from the blueprint dict, the busy-week generator can't
    resolve customer_id and the AI booking degrades silently."""
    seed_names = {row[0] for row in SEED_CUSTOMERS}
    assert seed_names == set(_AI_BOOKING_BLUEPRINTS.keys()), (
        f"SEED_CUSTOMERS {seed_names} != blueprints "
        f"{set(_AI_BOOKING_BLUEPRINTS.keys())}"
    )


def _make_mock_session(existing_phones: list[str]):
    """Build a stand-in async session that:
      - `execute(...)` returns a result whose `.scalars().all()` yields the
        provided phone list (matching the shape `_ensure_seed_customers`
        reads when querying Customer.phone_e164);
      - `add(...)` is a MagicMock so we can count Customer inserts;
      - `flush()` is an AsyncMock no-op.
    """
    session = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = list(existing_phones)
    result = MagicMock()
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


def test_ensure_seed_customers_idempotent():
    """`_ensure_seed_customers` must upsert only missing rows. With 4
    existing phones (Mark/Julia/Laura/Andrew) → 2 inserts (Sophie/Tom);
    with all 6 phones present → zero inserts."""
    existing4 = [c[1] for c in SEED_CUSTOMERS if c[0] in {
        "Mark Ross", "Julia White", "Laura Bennett", "Andrew Green",
    }]
    session = _make_mock_session(existing4)
    asyncio.run(_ensure_seed_customers(session))
    assert session.add.call_count == 2, (
        f"expected 2 inserts (Sophie/Tom), got {session.add.call_count}"
    )

    existing6 = [c[1] for c in SEED_CUSTOMERS]
    session2 = _make_mock_session(existing6)
    asyncio.run(_ensure_seed_customers(session2))
    assert session2.add.call_count == 0, (
        f"expected 0 inserts (idempotent), got {session2.add.call_count}"
    )
