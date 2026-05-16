"""Unit tests for app.agents.pii_sanitizer (observe-only revision, 2026-05-16).

The sanitizer is invoked between `call_analyzer` and persist; it must:
- LEAVE the briefing and planned_action evidence untouched (no redaction)
- LEAVE the raw `fields` list intact
- Emit one audit record per non-`none` pii_class field, labelling it as
  `observed` (confidence >= class threshold) or `observed_low_confidence`.
- Skip `pii_class=none` fields entirely.
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
        language="en",
        urgency="low",
        fields=[
            FieldExtraction(key="party_size", value="4", confidence=0.95, evidence="four of us"),
            FieldExtraction(key="customer_name", value="Mark Ross", confidence=0.91, evidence="My name is Mark Ross"),
            FieldExtraction(key="allergies", value='["gluten"]', confidence=0.95, evidence="I am gluten intolerant"),
            FieldExtraction(key="booking_time", value="20:30", confidence=0.93, evidence="around eight thirty"),
        ],
        planned_actions=[
            PlannedAction(
                action_type="booking.create",
                title="Create booking",
                summary="Book a table",
                payload={"party_size": 4, "customer_name": "Mark Ross"},
                confidence=0.9,
                evidence=evidence or ["My name is Mark Ross, four of us"],
            ),
        ],
        next_call_briefing=briefing,
    )


def test_sanitize_does_not_redact_briefing():
    schema = _restaurant_schema()
    briefing = "Mark Ross prefers a quiet table; he is gluten-intolerant."
    analysis = _make_analysis(briefing=briefing)

    out = sanitize_analysis(schema, analysis)

    # Briefing is untouched — operators MUST see allergies and names.
    assert out.analysis.next_call_briefing == briefing
    assert "Mark Ross" in out.analysis.next_call_briefing
    assert "gluten" in out.analysis.next_call_briefing


def test_sanitize_does_not_scrub_evidence_on_planned_actions():
    schema = _restaurant_schema()
    evidence_in = ["My name is Mark Ross, I am gluten intolerant."]
    analysis = _make_analysis(briefing="...", evidence=evidence_in)

    out = sanitize_analysis(schema, analysis)

    assert out.analysis.planned_actions[0].evidence == evidence_in


def test_sanitize_preserves_raw_fields():
    schema = _restaurant_schema()
    analysis = _make_analysis(briefing="...")

    out = sanitize_analysis(schema, analysis)

    by_key = {f.key: f.value for f in out.analysis.fields}
    assert by_key["customer_name"] == "Mark Ross"
    assert by_key["allergies"] == '["gluten"]'


def test_sanitize_emits_observed_records_for_pii_fields():
    schema = _restaurant_schema()
    analysis = _make_analysis(briefing="Mark Ross, gluten.")

    out = sanitize_analysis(schema, analysis)

    by_field = {r.field: r for r in out.audit_pii_actions}
    assert "customer_name" in by_field
    assert "allergies" in by_field
    # party_size and booking_time are pii_class="none" → no record
    assert "party_size" not in by_field
    assert "booking_time" not in by_field

    assert by_field["customer_name"].pii_class == "contact"
    assert by_field["customer_name"].action == "observed"
    assert by_field["allergies"].pii_class == "health"
    assert by_field["allergies"].action == "observed"


def test_sanitize_marks_low_confidence_records():
    schema = _restaurant_schema()
    # Mention "gluten" in briefing but the extracted allergies confidence is
    # below the health threshold (0.90) — record should be `observed_low_confidence`,
    # while the briefing stays verbatim.
    briefing = "Possible allergies: gluten (to verify)."
    analysis = CallAnalysis(
        intent="booking_new",
        sentiment="neutral",
        language="en",
        urgency="low",
        fields=[
            FieldExtraction(key="allergies", value='["gluten"]', confidence=0.70, evidence="maybe gluten"),
        ],
        planned_actions=[],
        next_call_briefing=briefing,
    )

    out = sanitize_analysis(schema, analysis)
    record = out.audit_pii_actions[0]
    assert record.field == "allergies"
    assert record.action == "observed_low_confidence"
    assert out.analysis.next_call_briefing == briefing
    assert "gluten" in out.analysis.next_call_briefing


def test_sanitize_no_op_when_no_pii_fields():
    schema = [
        {"key": "party_size", "type": "integer", "label": "Guests"},
        {"key": "booking_time", "type": "time", "label": "Time"},
    ]
    briefing = "Booking for 4 at 20:30."
    analysis = CallAnalysis(
        intent="booking_new",
        sentiment="neutral",
        language="en",
        urgency="low",
        fields=[
            FieldExtraction(key="party_size", value="4", confidence=0.95, evidence="four of us"),
        ],
        planned_actions=[],
        next_call_briefing=briefing,
    )
    out = sanitize_analysis(schema, analysis)
    assert out.audit_pii_actions == []
    assert out.analysis.next_call_briefing == briefing
