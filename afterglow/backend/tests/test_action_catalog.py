"""Sanity tests for the in-process action catalog.

The catalog is a small constant table; we mostly want to make sure the
shape and key contract stay stable so the template_validator and the wizard
can rely on it.
"""
from __future__ import annotations

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
