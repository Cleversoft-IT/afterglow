"""Tests for `_enrich_action_types_with_catalog_schemas` — the chokepoint
that merges per-domain JSONSchemas from `action_catalog` onto an
action_type at template persistence time.

These tests are pure-function (no DB / FastAPI app spin-up): they exercise
the helper directly and the wiring contract from
`CreateTemplateRequest.template.domain_hint` to that helper. The endpoint
itself is exercised indirectly through the production smoke step listed
in the plan.
"""
from __future__ import annotations

from app.api.templates import _enrich_action_types_with_catalog_schemas
from app.schemas.templates import (
    ActionDefinitionDraft,
    CreateTemplateRequest,
    FieldDefinition,
    TemplateWizardResponse,
)


def test_enrich_uses_domain_specific_schema_when_available():
    """Hotel templates should pick up `domain_payload_schemas["hotel"]`
    for `booking.create`, which requires `check_out_date` and treats
    `booking_time` as optional."""
    enriched = _enrich_action_types_with_catalog_schemas(
        [{"key": "booking.create"}],
        template_domain_hint="hotel",
    )
    schema = enriched[0]["payload_schema"]
    required = set(schema["required"])
    assert "check_out_date" in required
    assert "booking_time" not in required


def test_enrich_falls_back_to_default_for_unknown_domain():
    """Unknown / generic domain → restaurant-shaped default. Confirms
    the helper degrades gracefully instead of failing or returning the
    last-seen override."""
    enriched = _enrich_action_types_with_catalog_schemas(
        [{"key": "booking.create"}],
        template_domain_hint="bowling",
    )
    schema = enriched[0]["payload_schema"]
    assert set(schema["required"]) == {"booking_date", "booking_time"}


def test_enrich_preserves_explicit_payload_schema():
    """When an action_type ships an explicit `payload_schema`, the
    enricher must NOT overwrite it — operator overrides win regardless
    of `template_domain_hint`."""
    custom = {"type": "object", "properties": {"x": {"type": "string"}}}
    enriched = _enrich_action_types_with_catalog_schemas(
        [{"key": "booking.create", "payload_schema": custom}],
        template_domain_hint="hotel",
    )
    assert enriched[0]["payload_schema"] is custom


def test_enrich_none_domain_uses_default_schema():
    """Both `None` and the empty-string sentinel must behave like
    "domain unknown → default schema"."""
    for hint in (None, ""):
        enriched = _enrich_action_types_with_catalog_schemas(
            [{"key": "booking.create"}],
            template_domain_hint=hint,
        )
        assert set(enriched[0]["payload_schema"]["required"]) == {
            "booking_date",
            "booking_time",
        }


def test_create_template_callsite_resolves_tpl_domain_hint_not_payload():
    """Regression guard for the audit blocker: `CreateTemplateRequest`
    nests the template, so the call-site in `templates.py:create_template`
    MUST read `tpl.domain_hint` (where `tpl = payload.template`), NOT
    `payload.domain_hint` (which does not exist on
    `CreateTemplateRequest`).

    We verify the contract by:
      1. Parsing a realistic Hotel `CreateTemplateRequest` payload.
      2. Replaying the same `(tpl.domain_hint, tpl.action_types)`
         resolution the endpoint does.
      3. Asserting the helper returns the hotel schema.
    """
    payload = CreateTemplateRequest(
        template=TemplateWizardResponse(
            name="Hotel reservations",
            description="Phone intake for a boutique hotel",
            domain_hint="hotel",
            fields_schema=[
                FieldDefinition(
                    key="guest_name",
                    type="string",
                    label="Guest name",
                    required=True,
                )
            ],
            action_types=[
                ActionDefinitionDraft(
                    key="booking.create",
                    label="Create reservation",
                    execution_mode="auto",
                    preconditions=["guest_name"],
                    confidence_threshold=0.7,
                    evidence_required=True,
                )
            ],
            prompt_hints=[],
        ),
    )
    tpl = payload.template
    enriched = _enrich_action_types_with_catalog_schemas(
        [a.model_dump() for a in tpl.action_types],
        template_domain_hint=tpl.domain_hint or "generic",
    )
    schema = enriched[0]["payload_schema"]
    assert set(schema["required"]) == {
        "guest_name",
        "booking_date",
        "check_out_date",
    }
    assert "booking_time" in schema["properties"]
