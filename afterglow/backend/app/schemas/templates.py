"""Pydantic schemas for template configuration + prompt-to-template wizard.

v2 (migration 0006): `FieldDefinition` and `ActionDefinition` carry the rich
metadata the post-call pipeline needs to enforce PII gating, field
dependencies, and typed action payloads. `prompt_hints` is a structured list
of `{when, then}` rules evaluated against the caller's prior structured
fields before the analyzer prompt is built.

There is no backward compatibility for the v1 shapes (`prompt_hints: str`,
`payload_json: str`). The DB was wiped by migration 0006; legacy rows do not
exist. See `.claude/memory/feedback_db_disposable.md`.
"""
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


PiiClass = Literal["none", "contact", "health", "financial", "identity"]
ExtractorHint = Literal["regex", "freeform", "enum", "llm_only"]
ExecutionMode = Literal["auto", "manual-only"]


class FieldDefinition(BaseModel):
    key: str
    type: str
    label: str
    required: bool = False
    sensitive: bool = False
    options: list[str] = Field(default_factory=list)
    description: Optional[str] = None

    # v2 additions
    pii_class: PiiClass = "none"
    # Per-field override of the default class threshold. `None` means "use
    # the policy default for the field's pii_class".
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    extractor_hint: ExtractorHint = "freeform"
    # Other field keys that must be present (and at-or-above threshold) for
    # this field to be considered grounded. Used by the orchestrator's
    # `_coerce_extractions` and by the Action Planner preconditions check.
    depends_on: list[str] = Field(default_factory=list)


class ActionDefinition(BaseModel):
    key: str
    label: str
    execution_mode: ExecutionMode = "auto"
    mock_target: str = "generic"
    description: Optional[str] = None

    # v2 additions
    # Field keys whose presence is required before this action can be planned.
    preconditions: list[str] = Field(default_factory=list)
    # Minimum confidence (returned by the analyzer for the action itself,
    # NOT for the fields) below which the planner must skip the call.
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    # Marks the action as irreversible: the Action Planner never auto-retries
    # it, and the executor flags `is_irreversible=True` in the audit row.
    mutates: bool = False
    # When True, the planner must supply at least one evidence span or the
    # executor refuses to invoke MOCK_REGISTRY.
    evidence_required: bool = True
    # Optional JSONSchema. When present:
    #   - Action Planner builds a Pydantic model dynamically and exposes the
    #     tool to Gemini ADK as a FunctionDeclaration with typed parameters.
    #   - Action Executor revalidates the payload with `jsonschema.validate`
    #     before calling MOCK_REGISTRY.
    payload_schema: Optional[dict[str, Any]] = None


class PromptHintRule(BaseModel):
    """A single `{when, then}` instruction prepended to the analyzer prompt
    when the `when` condition matches the caller's prior structured fields.

    `when` mini-grammar (deterministic Python evaluator — see
    `app/agents/prompt_hint_eval.py`):
        - "always"
        - "field.<key> == '<value>'"
        - "field.<key> is null"
        - "field.<key> is not null"
    """

    when: str = "always"
    then: str


class TemplateView(BaseModel):
    id: UUID
    name: str
    version: int
    description: Optional[str] = None
    domain_hint: str = "generic"
    fields_schema: list[FieldDefinition] = Field(default_factory=list)
    action_types: list[ActionDefinition] = Field(default_factory=list)
    custom_dictionary: list[str] = Field(default_factory=list)
    prompt_hints: Optional[list[PromptHintRule]] = None
    is_active: bool = False
    is_seed: bool = False
    session_id: Optional[UUID] = None
    created_at: datetime


# --- Wizard ---------------------------------------------------------------


class TemplateWizardRequest(BaseModel):
    description: str = Field(min_length=20)
    language: str = "it"


class ValidationIssue(BaseModel):
    field_path: str
    severity: Literal["error", "warning", "info"]
    message: str


class ProposedMock(BaseModel):
    action_key: str
    suggested_mock_target: str
    rationale: str


class ValidationReport(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list)
    proposed_mocks: list[ProposedMock] = Field(default_factory=list)


class ActionDefinitionDraft(BaseModel):
    """Wizard-time shape of an action.

    Identical to `ActionDefinition` minus `payload_schema`: Gemini's
    structured-output endpoint rejects schemas containing
    `additionalProperties` (which Pydantic emits for any `dict[str, Any]`
    field) and there is no way to suppress that flag from a Pydantic
    model without dropping the field. We let the LLM emit the skeleton
    and the operator (or a future validator iteration) supplies
    `payload_schema` post-generation.
    """

    key: str
    label: str
    execution_mode: ExecutionMode = "auto"
    mock_target: str = "generic"
    description: Optional[str] = None
    preconditions: list[str] = Field(default_factory=list)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    mutates: bool = False
    evidence_required: bool = True


class TemplateWizardResponse(BaseModel):
    name: str
    description: str
    domain_hint: str = "generic"
    fields_schema: list[FieldDefinition]
    action_types: list[ActionDefinitionDraft]
    custom_dictionary: list[str]
    prompt_hints: list[PromptHintRule] = Field(default_factory=list)
    # Populated by the wizard endpoint with the deterministic + LLM validation
    # report. The refine UI uses it to surface issues inline; the persist
    # endpoint does not require it to be clean (the operator can override).
    validation: Optional[ValidationReport] = None


class CreateTemplateRequest(BaseModel):
    """Body of POST /api/v1/templates.

    `template` carries the wizard output (after the operator's refinements).
    `set_active=True` flips the new template to the caller's active slot
    (DemoSession.active_template_id for demo callers, Template.is_active for
    prod). `parent_seed_id` is reserved for future lineage tracking (see
    `afterglow/docs/future-ideas.md`); it is accepted but ignored today.
    """

    template: TemplateWizardResponse
    set_active: bool = False
    parent_seed_id: Optional[UUID] = None


class UpdateTemplateRequest(BaseModel):
    """Body of PUT /api/v1/templates/{id} for the Refine post-persistence step.

    Only the editable fields are accepted; `name` and `version` are not
    re-bumped by an update (a new version is created via POST).
    """

    description: Optional[str] = None
    domain_hint: Optional[str] = None
    fields_schema: Optional[list[FieldDefinition]] = None
    action_types: Optional[list[ActionDefinition]] = None
    custom_dictionary: Optional[list[str]] = None
    prompt_hints: Optional[list[PromptHintRule]] = None


class ValidateDraftRequest(BaseModel):
    """Body of POST /api/v1/templates/validate.

    Reuses the wizard response shape so the refine UI can revalidate after
    an edit without re-running the Generate step.
    """

    template: TemplateWizardResponse
