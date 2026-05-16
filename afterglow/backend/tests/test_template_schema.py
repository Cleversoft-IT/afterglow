"""Unit tests for app.schemas.templates — v2 round-trip + defaults."""
from __future__ import annotations

from app.schemas.templates import (
    ActionDefinition,
    ActionDefinitionDraft,
    CreateTemplateRequest,
    FieldDefinition,
    PromptHintRule,
    TemplateWizardResponse,
    UpdateTemplateRequest,
    ValidateDraftRequest,
    ValidationIssue,
    ValidationReport,
)


def test_field_definition_defaults():
    f = FieldDefinition(key="x", type="string", label="X")
    assert f.pii_class == "none"
    assert f.extractor_hint == "freeform"
    assert f.depends_on == []
    assert f.confidence_threshold is None
    assert f.required is False
    assert f.sensitive is False


def test_field_definition_full_roundtrip():
    payload = {
        "key": "allergies",
        "type": "string_list",
        "label": "Allergies",
        "required": False,
        "sensitive": True,
        "options": [],
        "description": "comma-separated allergens",
        "pii_class": "health",
        "confidence_threshold": 0.9,
        "extractor_hint": "freeform",
        "depends_on": [],
    }
    f = FieldDefinition.model_validate(payload)
    again = f.model_dump()
    # All v2 keys must survive the round-trip.
    for key in ("pii_class", "confidence_threshold", "extractor_hint", "depends_on"):
        assert key in again


def test_action_definition_defaults():
    a = ActionDefinition(key="booking.create", label="Create")
    assert a.execution_mode == "auto"
    assert a.preconditions == []
    assert a.confidence_threshold == 0.7
    assert a.mutates is False
    assert a.evidence_required is True
    assert a.payload_schema is None


def test_action_definition_with_payload_schema():
    a = ActionDefinition(
        key="booking.create",
        label="Create",
        mutates=True,
        payload_schema={
            "type": "object",
            "properties": {"party_size": {"type": "integer"}},
            "required": ["party_size"],
        },
    )
    assert a.payload_schema is not None
    assert a.payload_schema["type"] == "object"


def test_prompt_hint_rule_defaults():
    r = PromptHintRule(then="say hi")
    assert r.when == "always"
    assert r.then == "say hi"


def test_template_wizard_response_with_validation():
    rep = ValidationReport(
        issues=[ValidationIssue(field_path="x", severity="error", message="bad")],
        proposed_mocks=[],
    )
    payload = TemplateWizardResponse(
        name="X",
        description="d",
        fields_schema=[FieldDefinition(key="a", type="string", label="A")],
        action_types=[ActionDefinitionDraft(key="x.y", label="y")],
        custom_dictionary=[],
        prompt_hints=[PromptHintRule(then="t")],
        validation=rep,
    )
    again = TemplateWizardResponse.model_validate_json(payload.model_dump_json())
    assert again.validation is not None
    assert again.validation.issues[0].field_path == "x"


def test_create_template_request_minimal():
    base = TemplateWizardResponse(
        name="X",
        description="d",
        fields_schema=[],
        action_types=[],
        custom_dictionary=[],
        prompt_hints=[],
    )
    req = CreateTemplateRequest(template=base)
    assert req.set_active is False
    assert req.parent_seed_id is None


def test_update_and_validate_requests_accept_partial():
    upd = UpdateTemplateRequest(description="d")
    assert upd.fields_schema is None
    base = TemplateWizardResponse(
        name="X",
        description="d",
        fields_schema=[],
        action_types=[],
        custom_dictionary=[],
        prompt_hints=[],
    )
    val = ValidateDraftRequest(template=base)
    assert val.template.name == "X"
