"""Sanity tests for the in-process action catalog.

The catalog is a small constant table; we mostly want to make sure the
shape and key contract stay stable so the template_validator and the wizard
can rely on it.
"""
from __future__ import annotations

import jsonschema

from app.integrations import action_catalog
from app.integrations.mocks import MOCK_REGISTRY


def test_every_mock_registry_key_is_in_catalog():
    """Templates that pick a key from MOCK_REGISTRY must resolve in the
    catalog — otherwise the validator would flag them and the executor would
    refuse them. New mocks added to MOCK_REGISTRY MUST get a catalog entry."""
    missing = sorted(set(MOCK_REGISTRY.keys()) - set(action_catalog.CATALOG.keys()))
    assert missing == [], f"mock keys without catalog entry: {missing}"


def test_internal_real_entries_declare_a_handler():
    for entry in action_catalog.CATALOG.values():
        if entry.integration_kind == "internal_real":
            assert entry.internal_handler, (
                f"internal_real entry {entry.key} must set internal_handler"
            )


def test_mock_external_entries_declare_a_mock_target():
    for entry in action_catalog.CATALOG.values():
        if entry.integration_kind == "mock_external":
            assert entry.mock_target, (
                f"mock_external entry {entry.key} must set mock_target"
            )


def test_can_undo_is_false_for_send_messages():
    # Sent messages cannot be unsent — this is the rule the UI relies on.
    for key in (
        "whatsapp.send_confirmation",
        "whatsapp.request_photos",
        "sms.send_reminder",
        "email.send",
    ):
        assert action_catalog.can_undo(key) is False, (
            f"{key} must not advertise undo support"
        )


def test_is_simulated_matches_integration_kind():
    assert action_catalog.is_simulated("booking.create") is True
    assert action_catalog.is_simulated("customer.update_profile") is False


def test_is_simulated_unknown_key_defaults_true():
    # An unknown action key must default to "simulated" so the UI keeps the
    # honest signal even when a template ships a stale action key.
    assert action_catalog.is_simulated("rocket.launch") is True
    assert action_catalog.can_undo("rocket.launch") is False


def test_appointment_namespace_removed():
    """Round 8 unification — appointment.* was merged into booking.* so the
    Bookings tab and BookingBadge only ever consume one shape. Any
    regression that reintroduces appointment.create or
    appointment.create_inspection breaks the seed contract."""
    assert "appointment.create" not in action_catalog.CATALOG
    assert "appointment.create_inspection" not in action_catalog.CATALOG
    assert "appointment.cancel" not in action_catalog.CATALOG


def test_domain_payload_schema_for_hotel_booking_create():
    """Hotel templates must get the hotel-shaped booking schema instead of
    the restaurant default (`booking_date`+`booking_time` required) which
    rejected every Hotel call until 2026-05-19.

    Required surface: guest_name + booking_date (= check-in date,
    canonical for the Bookings UI) + check_out_date. `booking_time` is
    OPTIONAL — check-in times are institutional, the agent should not
    have to invent a value when the transcript doesn't mention one.
    """
    entry = action_catalog.CATALOG["booking.create"]
    assert entry.domain_payload_schemas is not None
    hotel = entry.domain_payload_schemas.get("hotel")
    assert hotel is not None, "booking.create needs a hotel-specific schema"
    required = set(hotel.get("required") or [])
    assert required == {"guest_name", "booking_date", "check_out_date"}, required
    assert "booking_time" not in required
    assert "booking_time" in hotel.get("properties") or {}


def test_all_default_and_domain_payload_schemas_are_valid_jsonschema():
    """Every schema we hand to jsonschema at validation time must itself be
    a valid Draft-7 JSONSchema, else the agent's first call_tool blows up
    with a schema-meta error instead of a payload error."""
    for key, entry in action_catalog.CATALOG.items():
        if entry.default_payload_schema is not None:
            jsonschema.Draft7Validator.check_schema(entry.default_payload_schema)
        for domain, schema in (entry.domain_payload_schemas or {}).items():
            jsonschema.Draft7Validator.check_schema(schema), f"{key}@{domain}"


def test_to_dict_does_not_leak_domain_payload_schemas():
    """`/api/v1/actions/catalog` must expose only the canonical schema
    surface so the operator UI keeps a single shape per action. The
    per-domain variants are an internal persistence concern."""
    entry = action_catalog.CATALOG["booking.create"]
    payload = entry.to_dict()
    assert "default_payload_schema" in payload
    assert "domain_payload_schemas" not in payload


def test_booking_create_rejects_natural_language_date():
    """The strict ISO `booking_date` / `booking_time` pattern in the
    catalog schemas is what stops the call_agent from emitting
    "next Tuesday" — that string would crash the web Bookings tab via
    formatBookingSlot. We validate with the SAME validator the executor
    uses (`jsonschema.validate(payload, schema)`, no FormatChecker), not
    `Draft7Validator.check_schema`, so the regex `pattern` enforcement is
    actually exercised."""
    import pytest
    schema = action_catalog.CATALOG["booking.create"].default_payload_schema
    # Natural-language date — the actual demo regression we're guarding.
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {"booking_date": "next Tuesday", "booking_time": "20:00"}, schema
        )
    # 24h-out-of-range time. The regex only allows 00-23, so "25:00"
    # short-circuits before the call_agent could write a bogus row.
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {"booking_date": "2026-05-23", "booking_time": "25:00"}, schema
        )
    # NB: regex pattern checks shape only — `2026-13-01` passes here
    # because `\d{2}` matches "13". Calendar validity is out of scope;
    # the model is steered toward today-relative resolution by the
    # call_agent system prompt instead.
    # Valid payload passes.
    jsonschema.validate(
        {"booking_date": "2026-05-23", "booking_time": "20:00"}, schema
    )


def test_booking_create_hotel_variant_rejects_natural_language_date():
    """Hotel variant uses a separate schema (with check_out_date), same
    strict pattern enforcement."""
    import pytest
    entry = action_catalog.CATALOG["booking.create"]
    schema = entry.payload_schema_for_domain("hotel")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {
                "guest_name": "Mark Ross",
                "booking_date": "next Tuesday",
                "check_out_date": "2026-05-25",
            },
            schema,
        )
    jsonschema.validate(
        {
            "guest_name": "Mark Ross",
            "booking_date": "2026-05-23",
            "check_out_date": "2026-05-25",
        },
        schema,
    )


def test_booking_compatible_domains_cover_demo_verticals():
    """booking.create must work for restaurant + dentist + bodyshop (the
    three seed templates) plus the wizard-suggested verticals. Loss of any
    of these breaks the wizard's domain → catalog matching."""
    expected = {
        "restaurant", "hotel", "salon", "gym", "events",
        "dentist", "bodyshop", "clinic", "*",
    }
    entry = action_catalog.CATALOG["booking.create"]
    missing = expected - set(entry.compatible_domains)
    assert missing == set(), f"booking.create lost domains: {missing}"
    cancel = action_catalog.CATALOG["booking.cancel"]
    missing_cancel = expected - set(cancel.compatible_domains)
    assert missing_cancel == set(), (
        f"booking.cancel lost domains: {missing_cancel}"
    )
