"""Tests for app.agents.template_validator deterministic checks.

The deterministic step never calls Gemini and must catch:
  - non-snake_case field keys
  - duplicate field keys
  - depends_on cycles + unknown deps
  - non-dot.namespaced action keys
  - actions whose key is not in MOCK_REGISTRY (warning, not error)
  - invalid JSONSchema in payload_schema
  - prompt_hints `when` expressions outside the supported grammar
"""
from __future__ import annotations

from app.agents.template_validator import validate_template_deterministic
from app.schemas.templates import (
    ActionDefinitionDraft,
    FieldDefinition,
    PromptHintRule,
    TemplateWizardResponse,
)


# Wizard responses carry the draft shape (no payload_schema). Tests that need
# to exercise payload_schema validity construct an ActionDefinition (the
# runtime shape) and call the validator directly.
ActionDefinition = ActionDefinitionDraft  # noqa: N816 — preserve test ergonomics


def _draft(**over) -> TemplateWizardResponse:
    return TemplateWizardResponse(
        name=over.get("name", "X"),
        description=over.get("description", "d"),
        domain_hint=over.get("domain_hint", "generic"),
        fields_schema=over.get("fields_schema", []),
        action_types=over.get("action_types", []),
        prompt_hints=over.get("prompt_hints", []),
    )


def test_non_snake_case_field_key_flagged():
    d = _draft(
        fields_schema=[
            FieldDefinition(key="CustomerName", type="string", label="Name"),
        ]
    )
    issues = validate_template_deterministic(d)
    paths = [i.field_path for i in issues if i.severity == "error"]
    assert any("CustomerName" in p or p.startswith("fields_schema[0].key") for p in paths)


def test_duplicate_field_keys_flagged():
    d = _draft(
        fields_schema=[
            FieldDefinition(key="x", type="string", label="X"),
            FieldDefinition(key="x", type="string", label="X dup"),
        ]
    )
    issues = validate_template_deterministic(d)
    assert any("duplicate field key" in i.message for i in issues)


def test_depends_on_unknown_key_flagged():
    d = _draft(
        fields_schema=[
            FieldDefinition(key="a", type="string", label="A", depends_on=["b"]),
        ]
    )
    issues = validate_template_deterministic(d)
    assert any("unknown dependency" in i.message for i in issues)


def test_depends_on_cycle_flagged():
    d = _draft(
        fields_schema=[
            FieldDefinition(key="a", type="string", label="A", depends_on=["b"]),
            FieldDefinition(key="b", type="string", label="B", depends_on=["a"]),
        ]
    )
    issues = validate_template_deterministic(d)
    assert any("cycle" in i.message.lower() for i in issues)


def test_action_key_not_dot_namespaced_flagged():
    d = _draft(action_types=[ActionDefinition(key="booking", label="b")])
    issues = validate_template_deterministic(d)
    assert any("dot.namespaced" in i.message for i in issues)


def test_unknown_action_key_warned_not_errored():
    d = _draft(
        action_types=[
            ActionDefinition(key="invented.thing", label="x"),
        ]
    )
    issues = validate_template_deterministic(d)
    matching = [i for i in issues if "MOCK_REGISTRY" in i.message]
    assert len(matching) == 1
    assert matching[0].severity == "warning"


def test_invalid_payload_schema_flagged():
    """Wizard responses don't carry payload_schema (Gemini structured output
    can't emit additionalProperties). We feed the validator a runtime
    `ActionDefinition` via a lightweight stub so we can still exercise the
    payload_schema branch.
    """
    from types import SimpleNamespace

    stub_action = SimpleNamespace(
        key="booking.create",
        label="b",
        execution_mode="auto",
        description=None,
        preconditions=[],
        confidence_threshold=0.7,
        evidence_required=True,
        payload_schema={"type": "not_a_real_type"},
    )
    draft = _draft()
    # Append the stub directly so we bypass Pydantic's draft validation.
    draft.action_types.append(stub_action)  # type: ignore[arg-type]
    issues = validate_template_deterministic(draft)
    assert any("invalid JSONSchema" in i.message for i in issues)


def test_preconditions_reference_unknown_field_flagged():
    d = _draft(
        fields_schema=[FieldDefinition(key="a", type="string", label="A")],
        action_types=[
            ActionDefinition(key="booking.create", label="b", preconditions=["b"]),
        ],
    )
    issues = validate_template_deterministic(d)
    assert any("precondition" in i.message and "'b'" in i.message for i in issues)


def test_unsupported_when_grammar_warned():
    d = _draft(
        prompt_hints=[
            PromptHintRule(when="if field.x > 5", then="do something"),
        ]
    )
    issues = validate_template_deterministic(d)
    assert any("supported grammar" in i.message for i in issues)


def test_clean_template_produces_no_errors():
    d = _draft(
        fields_schema=[
            FieldDefinition(key="party_size", type="integer", label="Guests"),
            FieldDefinition(key="customer_name", type="string", label="Name"),
        ],
        action_types=[
            ActionDefinition(
                key="booking.create",
                label="Create booking",
                preconditions=["party_size", "customer_name"],
            )
        ],
        prompt_hints=[PromptHintRule(when="always", then="be concise")],
    )
    issues = validate_template_deterministic(d)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []
