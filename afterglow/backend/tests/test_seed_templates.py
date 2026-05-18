"""Contract tests for the three seed templates (restaurant / dentist /
bodyshop). The BookingBadge in the UI relies on
`payload.booking_date` + `payload.booking_time` being present on every
`booking.create` action emitted by a seed call — this only happens if the
template schema requires those fields. These tests pin the contract at the
schema level so the bug can't sneak back in via a partial rename."""
from __future__ import annotations

from app.db.seed import (
    BODYSHOP_TEMPLATE,
    DENTIST_TEMPLATE,
    RESTAURANT_TEMPLATE,
)


SEED_TEMPLATES = {
    "restaurant": RESTAURANT_TEMPLATE,
    "dentist": DENTIST_TEMPLATE,
    "bodyshop": BODYSHOP_TEMPLATE,
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
