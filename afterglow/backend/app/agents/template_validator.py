"""Template Validator Agent — deterministic checks + Gemini semantic pass.

Invoked from `wizard_chat.run_wizard_chat` once a candidate draft is ready,
and from the refine UI through `POST /templates/validate`. Returns a
`ValidationReport`:

  - `issues`: list of `{field_path, severity, message}`. Hard issues are
    produced deterministically (snake_case key violations, depends_on
    cycles, invalid JSONSchema, action keys with no registered mock target).
    Soft issues come from a small Gemini call that evaluates semantic
    consistency (prompt_hints make sense, action labels match what the
    actions actually do).

  - `proposed_mocks`: when an action key is not present in the action
    catalog, the Gemini step suggests an existing catalog `key` the
    operator should map it to.

The deterministic step never raises; it just records issues. The Gemini
step degrades gracefully to "no soft issues" on failure (the user still
gets the hard report).
"""
from __future__ import annotations

import logging
import re
from typing import Any

import jsonschema

from app.config import get_settings
from app.integrations.action_catalog import available_keys
from app.schemas.templates import (
    ProposedMock,
    TemplateWizardResponse,
    ValidationIssue,
    ValidationReport,
)

logger = logging.getLogger("afterglow")


_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_DOT_NAMESPACED_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def validate_template_deterministic(
    template: TemplateWizardResponse,
) -> list[ValidationIssue]:
    """Hard checks that do not require Gemini. Always run first."""
    issues: list[ValidationIssue] = []

    # 1. Field keys must be snake_case.
    seen_field_keys: set[str] = set()
    for i, f in enumerate(template.fields_schema):
        if not _SNAKE_CASE_RE.match(f.key):
            issues.append(
                ValidationIssue(
                    field_path=f"fields_schema[{i}].key",
                    severity="error",
                    message=(
                        f"key {f.key!r} must be lowercase snake_case "
                        "(e.g. customer_name)."
                    ),
                )
            )
        if f.key in seen_field_keys:
            issues.append(
                ValidationIssue(
                    field_path=f"fields_schema[{i}].key",
                    severity="error",
                    message=f"duplicate field key {f.key!r}.",
                )
            )
        seen_field_keys.add(f.key)

    # 2. depends_on must reference existing keys; no cycles.
    field_by_key = {f.key: f for f in template.fields_schema}
    for f in template.fields_schema:
        for dep in f.depends_on:
            if dep not in field_by_key:
                issues.append(
                    ValidationIssue(
                        field_path=f"fields_schema[{f.key}].depends_on",
                        severity="error",
                        message=f"unknown dependency key {dep!r}.",
                    )
                )
    cycle = _find_dependency_cycle(template)
    if cycle:
        issues.append(
            ValidationIssue(
                field_path="fields_schema.depends_on",
                severity="error",
                message=f"dependency cycle detected: {' -> '.join(cycle)}.",
            )
        )

    # 3. Action keys must be dot.namespaced; their payload_schema (if any)
    # must be a valid JSONSchema; their preconditions must reference fields
    # that exist.
    mock_keys = set(available_keys())
    seen_action_keys: set[str] = set()
    for i, a in enumerate(template.action_types):
        if not _DOT_NAMESPACED_RE.match(a.key):
            issues.append(
                ValidationIssue(
                    field_path=f"action_types[{i}].key",
                    severity="error",
                    message=(
                        f"action key {a.key!r} should be dot.namespaced "
                        "(e.g. booking.create)."
                    ),
                )
            )
        if a.key in seen_action_keys:
            issues.append(
                ValidationIssue(
                    field_path=f"action_types[{i}].key",
                    severity="error",
                    message=f"duplicate action key {a.key!r}.",
                )
            )
        seen_action_keys.add(a.key)

        if a.key not in mock_keys:
            issues.append(
                ValidationIssue(
                    field_path=f"action_types[{i}].key",
                    severity="warning",
                    message=(
                        f"action key {a.key!r} is not in MOCK_REGISTRY; the "
                        "executor will return status='failed' until a mock "
                        "target is wired. The validator may propose one."
                    ),
                )
            )

        for dep in a.preconditions:
            if dep not in field_by_key:
                issues.append(
                    ValidationIssue(
                        field_path=f"action_types[{a.key}].preconditions",
                        severity="error",
                        message=(
                            f"precondition {dep!r} refers to a field that is "
                            "not in fields_schema."
                        ),
                    )
                )

        # payload_schema is optional and lives on the runtime `ActionDefinition`,
        # not on the wizard-time `ActionDefinitionDraft`. Use getattr so the
        # validator works against either shape; missing attribute => no check.
        payload_schema = getattr(a, "payload_schema", None)
        if payload_schema is not None:
            try:
                jsonschema.Draft202012Validator.check_schema(payload_schema)
            except jsonschema.SchemaError as exc:
                issues.append(
                    ValidationIssue(
                        field_path=f"action_types[{a.key}].payload_schema",
                        severity="error",
                        message=f"invalid JSONSchema: {exc.message}",
                    )
                )

    # 4. prompt_hints `when` grammar — light check via the same regexes
    #    the runtime evaluator uses.
    _validate_prompt_hint_when_grammar(template, issues)

    return issues


def _find_dependency_cycle(template: TemplateWizardResponse) -> list[str] | None:
    """Return a representative cycle as `[a, b, c, a]`, or None when acyclic."""
    graph: dict[str, list[str]] = {
        f.key: list(f.depends_on) for f in template.fields_schema
    }
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {k: WHITE for k in graph}
    parent: dict[str, str] = {}

    def dfs(node: str) -> list[str] | None:
        color[node] = GRAY
        for nxt in graph.get(node, []):
            if nxt not in color:
                continue
            if color[nxt] == GRAY:
                # Reconstruct cycle.
                cycle = [nxt, node]
                while parent.get(cycle[-1]) and cycle[-1] != nxt:
                    cycle.append(parent[cycle[-1]])
                cycle.append(nxt)
                return cycle
            if color[nxt] == WHITE:
                parent[nxt] = node
                found = dfs(nxt)
                if found:
                    return found
        color[node] = BLACK
        return None

    for k in graph:
        if color[k] == WHITE:
            found = dfs(k)
            if found:
                return found
    return None


_HINT_WHEN_RE = re.compile(
    r"^(always"
    r"|field\.[a-z][a-z0-9_]*\s*==\s*['\"][^'\"]*['\"]"
    r"|field\.[a-z][a-z0-9_]*\s+is\s+(not\s+)?null)$",
    re.IGNORECASE,
)


def _validate_prompt_hint_when_grammar(
    template: TemplateWizardResponse, issues: list[ValidationIssue]
) -> None:
    for i, rule in enumerate(template.prompt_hints):
        when = (rule.when or "").strip()
        if not when:
            continue
        if not _HINT_WHEN_RE.match(when):
            issues.append(
                ValidationIssue(
                    field_path=f"prompt_hints[{i}].when",
                    severity="warning",
                    message=(
                        f"`when` expression {when!r} is not in the supported "
                        "grammar (`always`, `field.<key> == '<value>'`, "
                        "`field.<key> is [not] null`); rule will be skipped "
                        "at runtime."
                    ),
                )
            )


async def validate_template(
    template: TemplateWizardResponse,
) -> ValidationReport:
    """Combine deterministic + Gemini semantic checks."""
    hard_issues = validate_template_deterministic(template)

    soft_issues: list[ValidationIssue] = []
    proposed_mocks: list[ProposedMock] = []
    try:
        soft = await _semantic_review(template)
        soft_issues = soft.issues
        proposed_mocks = soft.proposed_mocks
    except Exception as exc:  # noqa: BLE001
        logger.warning("template_validator: semantic review skipped (%s).", exc)

    return ValidationReport(
        issues=hard_issues + soft_issues,
        proposed_mocks=proposed_mocks,
    )


_SEMANTIC_INSTRUCTION = (
    "You are the Template Validator Agent inside Afterglow.\n\n"
    "Inspect the candidate template the prompt-to-template wizard just "
    "produced. Return a ValidationReport with two parts:\n\n"
    "- `issues[]`: semantic problems (severity `error|warning|info`) that the "
    "deterministic validator cannot catch. Look for: (a) prompt_hints whose "
    "`then` instruction is ambiguous; (b) action `label` strings that do not "
    "match what the action actually does; (c) field `label` or `description` "
    "that do not match the field `key`.\n\n"
    "- `proposed_mocks[]`: for every action key the operator listed that is "
    "NOT in `mock_registry_keys` (passed in the user prompt), propose the "
    "closest matching catalog `key` from that registry, with a one-sentence "
    "rationale. If no reasonable mapping exists, omit the entry — do not "
    "invent a target.\n\n"
    "Be concise; one sentence per issue is enough."
)


async def _semantic_review(
    template: TemplateWizardResponse,
) -> ValidationReport:
    """Single Gemini structured-output call. Raises on missing key / error."""
    settings = get_settings()
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY not set")

    from google import genai
    from google.genai import types as genai_types

    user_payload: dict[str, Any] = {
        "template": template.model_dump(),
        "mock_registry_keys": available_keys(),
    }

    client = genai.Client(api_key=settings.google_api_key)
    resp = await client.aio.models.generate_content(
        model=settings.gemini_default_model,
        contents=str(user_payload),
        config=genai_types.GenerateContentConfig(
            system_instruction=_SEMANTIC_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ValidationReport,
            temperature=0.2,
        ),
    )
    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("empty Gemini response")
    return ValidationReport.model_validate_json(text)
