"""Pydantic schemas for template configuration + prompt-to-template wizard.

The template carries the *product* surface — what the operator wants to
extract from each call and what actions the agent may plan / execute.

System-level concerns live elsewhere:
  - mock routing, integration kind, undo and `mutates` semantics live in
    `app/integrations/action_catalog.py` (one source of truth, keyed by
    the action's `key`);
  - PII / privacy classification is out of scope for the hackathon
    (see `afterglow/docs/future-ideas.md`);
  - the ASR custom dictionary was removed 2026-05-17 with migration
    `0012_drop_template_custom_dictionary`.

`prompt_hints` remains a structured list of `{when, then}` rules evaluated
against the caller's prior structured fields before the analyzer prompt is
built.
"""
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


ExtractorHint = Literal["regex", "freeform", "enum", "llm_only"]
ExecutionMode = Literal["auto", "manual-only"]


class FieldDefinition(BaseModel):
    key: str
    type: str
    label: str
    required: bool = False
    options: list[str] = Field(default_factory=list)
    description: Optional[str] = None

    # Floor on the analyzer's per-field confidence below which the field is
    # treated as unknown (orchestrator `_coerce_extractions`).
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
    description: Optional[str] = None

    # Field keys whose presence is required before this action can be planned.
    preconditions: list[str] = Field(default_factory=list)
    # Minimum confidence (returned by the analyzer for the action itself,
    # NOT for the fields) below which the planner must skip the call.
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
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


class SimulationScenario(BaseModel):
    """One demo recording variant — bound to a CallerMode ('existing' or
    'new'). Seeded templates ship a `scenarios` map with both modes; the
    wizard-built custom templates still emit the legacy flat shape on
    `SimulationConfig` until a future PR teaches them to produce two
    recordings."""

    caller_name: Optional[str] = None
    caller_phone_e164: Optional[str] = None
    script_turns: list[dict[str, Any]] = Field(default_factory=list)
    audio_url: Optional[str] = None
    audio_status: Optional[Literal["pending", "ready", "failed"]] = None
    audio_generated_at: Optional[str] = None
    audio_source: Optional[Literal["tts_generated", "user_uploaded", "bundled"]] = None


CallerMode = Literal["existing", "new"]


class SimulationConfig(BaseModel):
    """Per-template demo recording config — drives the Simulator UI.

    Two coexisting shapes are accepted because the wizard still produces
    the legacy flat one:
      - Seeded shape (preferred): only `scenarios` is populated.
      - Legacy / wizard shape: only the flat fields are populated.
    The Simulator UI and the dialer read `scenarios.<mode>` first and fall
    back to the flat fields when the scenarios map is missing.
    """

    # Seeded templates: per-mode recordings.
    scenarios: dict[CallerMode, SimulationScenario] = Field(default_factory=dict)

    # Legacy / wizard-built single-script fields.
    caller_name: Optional[str] = None
    caller_phone_e164: Optional[str] = None
    script_turns: list[dict[str, Any]] = Field(default_factory=list)
    audio_url: Optional[str] = None
    audio_status: Optional[Literal["pending", "ready", "failed"]] = None
    audio_generated_at: Optional[str] = None
    audio_source: Optional[Literal["tts_generated", "user_uploaded", "bundled"]] = None


class TemplateView(BaseModel):
    id: UUID
    name: str
    version: int
    description: Optional[str] = None
    domain_hint: str = "generic"
    fields_schema: list[FieldDefinition] = Field(default_factory=list)
    action_types: list[ActionDefinition] = Field(default_factory=list)
    prompt_hints: Optional[list[PromptHintRule]] = None
    is_active: bool = False
    is_seed: bool = False
    session_id: Optional[UUID] = None
    # Internal / demo-only: not part of the user-facing template editor.
    # The Simulator reads this to play the bundled (or wizard-generated) call.
    simulation_config: Optional[SimulationConfig] = None
    created_at: datetime


# --- Wizard ---------------------------------------------------------------


class ValidationIssue(BaseModel):
    field_path: str
    severity: Literal["error", "warning", "info"]
    message: str


class ValidationReport(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list)


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
    description: Optional[str] = None
    preconditions: list[str] = Field(default_factory=list)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    evidence_required: bool = True


class TemplateWizardResponse(BaseModel):
    name: str
    description: str
    domain_hint: str = "generic"
    fields_schema: list[FieldDefinition]
    action_types: list[ActionDefinitionDraft]
    prompt_hints: list[PromptHintRule] = Field(default_factory=list)
    # Populated by the wizard endpoint with the deterministic validation
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

    `name` is editable for non-seed templates (seed remain read-only at the
    handler level and return 409). `version` is not re-bumped by an update —
    a new version is created via POST.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    domain_hint: Optional[str] = None
    fields_schema: Optional[list[FieldDefinition]] = None
    action_types: Optional[list[ActionDefinition]] = None
    prompt_hints: Optional[list[PromptHintRule]] = None


class ValidateDraftRequest(BaseModel):
    """Body of POST /api/v1/templates/validate.

    Reuses the wizard response shape so the refine UI can revalidate after
    an edit without re-running the Generate step.
    """

    template: TemplateWizardResponse


# --- Wizard chat (stateless, multi-turn) ---------------------------------


WizardChatRole = Literal["user", "assistant"]


class WizardChatTurn(BaseModel):
    role: WizardChatRole
    content: str


class WizardChatRequest(BaseModel):
    """Client → server payload for each conversational turn.

    Stateless: the client owns the conversation history and the running
    `draft_partial` / `slots_filled`. Server returns the next assistant
    message along with the updated draft, so the client can re-render the
    sidebar preview and decide when to surface "Ready to save".
    """

    messages: list[WizardChatTurn]
    draft_partial: Optional[TemplateWizardResponse] = None
    slots_filled: dict[str, Any] = Field(default_factory=dict)
    language: str = "en"


class WizardChatResponse(BaseModel):
    assistant_message: str
    slots_filled: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    ready: bool = False
    draft_partial: Optional[TemplateWizardResponse] = None
    validation: Optional[ValidationReport] = None
    proposed_actions_from_catalog: list[str] = Field(default_factory=list)
