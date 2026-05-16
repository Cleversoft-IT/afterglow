"""Unit tests for app.agents.pii_sanitizer.

The sanitizer is invoked between `call_analyzer` and persist; it must:
- redact PII tokens (health/financial/identity/contact) from the briefing
- not touch the raw `fields` list (operator UI + executor still need it)
- scrub matching tokens from each planned_action's evidence
- emit one audit record per affected field
- leave non-PII fields alone
"""
from __future__ import annotations

from app.agents.call_analyzer import CallAnalysis, FieldExtraction, PlannedAction
from app.agents.pii_sanitizer import sanitize_analysis


def _restaurant_schema():
    """Reusable subset of the restaurant template's fields_schema."""
    return [
        {"key": "party_size", "type": "integer", "label": "Guests"},
        {"key": "customer_name", "type": "string", "label": "Name", "pii_class": "contact"},
        {
            "key": "allergies",
            "type": "string_list",
            "label": "Allergies",
            "sensitive": True,
            "pii_class": "health",
            "confidence_threshold": 0.90,
        },
        {"key": "booking_time", "type": "time", "label": "Time"},
    ]


def _make_analysis(briefing: str, evidence: list[str] | None = None):
    return CallAnalysis(
        intent="booking_new",
        sentiment="positive",
        language="it",
        urgency="low",
        fields=[
            FieldExtraction(key="party_size", value="4", confidence=0.95, evidence="siamo in quattro"),
            FieldExtraction(key="customer_name", value="Marco Rossi", confidence=0.91, evidence="Mi chiamo Marco Rossi"),
            FieldExtraction(key="allergies", value='["glutine"]', confidence=0.95, evidence="sono intollerante al glutine"),
            FieldExtraction(key="booking_time", value="20:30", confidence=0.93, evidence="verso le otto e mezza"),
        ],
        planned_actions=[
            PlannedAction(
                action_type="booking.create",
                title="Create booking",
                summary="Book a table",
                payload={"party_size": 4, "customer_name": "Marco Rossi"},
                confidence=0.9,
                evidence=evidence or ["Mi chiamo Marco Rossi, siamo in quattro"],
            ),
        ],
        next_call_briefing=briefing,
    )


def test_sanitize_redacts_contact_and_health_in_briefing():
    schema = _restaurant_schema()
    analysis = _make_analysis(
        briefing="Marco Rossi prenota per 4 persone alle 20:30; allergico al glutine."
    )

    out = sanitize_analysis(schema, analysis)
    briefing = out.analysis.next_call_briefing

    assert "Marco Rossi" not in briefing
    assert "[redacted: contact]" in briefing
    assert "glutine" not in briefing
    assert "[redacted: health]" in briefing
    # Non-PII tokens stay intact
    assert "20:30" in briefing
    assert "4 persone" in briefing


def test_sanitize_preserves_raw_fields():
    schema = _restaurant_schema()
    analysis = _make_analysis(briefing="...")

    out = sanitize_analysis(schema, analysis)

    by_key = {f.key: f.value for f in out.analysis.fields}
    assert by_key["customer_name"] == "Marco Rossi"
    assert by_key["allergies"] == '["glutine"]'


def test_sanitize_scrubs_evidence_on_planned_actions():
    schema = _restaurant_schema()
    analysis = _make_analysis(
        briefing="...",
        evidence=["Mi chiamo Marco Rossi, sono allergico al glutine."],
    )

    out = sanitize_analysis(schema, analysis)
    evidence_after = out.analysis.planned_actions[0].evidence[0]

    assert "Marco Rossi" not in evidence_after
    assert "glutine" not in evidence_after


def test_sanitize_audit_record_per_pii_field():
    schema = _restaurant_schema()
    analysis = _make_analysis(briefing="Marco Rossi, glutine.")

    out = sanitize_analysis(schema, analysis)

    by_field = {r.field: r for r in out.audit_pii_actions}
    assert "customer_name" in by_field
    assert "allergies" in by_field
    # party_size and booking_time are pii_class="none" → no record
    assert "party_size" not in by_field
    assert "booking_time" not in by_field

    assert by_field["customer_name"].pii_class == "contact"
    assert by_field["customer_name"].action == "redact"
    assert by_field["allergies"].pii_class == "health"
    assert by_field["allergies"].action == "redact"


def test_sanitize_flags_when_confidence_below_threshold():
    schema = _restaurant_schema()
    # Mention "glutine" in briefing but the extracted allergies confidence is
    # below the health threshold (0.90) — should be flagged.
    analysis = CallAnalysis(
        intent="booking_new",
        sentiment="neutral",
        language="it",
        urgency="low",
        fields=[
            FieldExtraction(key="allergies", value='["glutine"]', confidence=0.70, evidence="forse glutine"),
        ],
        planned_actions=[],
        next_call_briefing="Possibili allergie: glutine (da verificare).",
    )

    out = sanitize_analysis(schema, analysis)
    record = out.audit_pii_actions[0]
    assert record.field == "allergies"
    assert record.action == "flag"
    # Briefing should STILL be redacted — flagged values must not leak either.
    assert "glutine" not in out.analysis.next_call_briefing
    assert "[redacted: health]" in out.analysis.next_call_briefing


def test_sanitize_no_op_when_no_pii_fields():
    schema = [
        {"key": "party_size", "type": "integer", "label": "Guests"},
        {"key": "booking_time", "type": "time", "label": "Time"},
    ]
    analysis = CallAnalysis(
        intent="booking_new",
        sentiment="neutral",
        language="it",
        urgency="low",
        fields=[
            FieldExtraction(key="party_size", value="4", confidence=0.95, evidence="siamo in 4"),
        ],
        planned_actions=[],
        next_call_briefing="Prenotazione per 4 alle 20:30.",
    )
    out = sanitize_analysis(schema, analysis)
    assert out.audit_pii_actions == []
    assert out.analysis.next_call_briefing == "Prenotazione per 4 alle 20:30."
