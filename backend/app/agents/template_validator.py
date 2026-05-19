"""Template Validator — deterministic guardrail for wizard drafts.

Despite the historical name, this module is **not an agent**: it runs zero
LLM calls. It is a synchronous, deterministic check that fires once a
candidate `TemplateWizardResponse` is ready (from `wizard_chat.run_wizard_chat`)
and from the refine UI via `POST /templates/validate`.

It catches things that would otherwise crash silently at runtime:

  - field keys not in snake_case, or duplicated
  - `depends_on` graphs with unknown references or cycles
  - action keys not dot.namespaced or duplicated
  - action keys not present in `integrations/action_catalog.py` (warning —
    the executor would refuse them)
  - action `preconditions` referencing fields outside `fields_schema`
  - `payload_schema` that is not a valid JSONSchema (would crash
    `jsonschema.validate` in `action_executor`)
  - `prompt_hints[].when` expressions outside the mini-grammar that
    `prompt_hint_eval.py` understands (silently ignored at runtime otherwise)

History: an earlier revision also ran a Gemini "semantic review" pass that
emitted soft narrative issues ("instruction ambiguous", "label mismatch")
and `proposed_mocks` for hallucinated action keys. The narrative issues
were suppressed before reaching the UI (they confused operators), and the
proposed_mocks surface was already covered by the wizard's
`proposed_actions_from_catalog` (the wizard server-side strips hallucinated
keys in `wizard_chat.py` before the validator ever sees them). The Gemini
call was removed 2026-05-17.
"""
from __future__ import annotations

import logging
import re

import jsonschema

from app.integrations.action_catalog import available_keys
from app.schemas.templates import (
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
    """Hard checks against a wizard draft. Never raises."""
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
    catalog_keys = set(available_keys())
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

        if a.key not in catalog_keys:
            issues.append(
                ValidationIssue(
                    field_path=f"action_types[{i}].key",
                    severity="warning",
                    message=(
                        f"action key {a.key!r} is not in the action catalog; "
                        "the executor will reject it until a catalog entry is "
                        "wired."
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
                    severity="error",
                    message=(
                        f"Prompt hint #{i + 1}: the rule \"when: {when}\" "
                        "doesn't match a recognized condition. Use "
                        "\"always\", \"field.<key> == 'value'\", or "
                        "\"field.<key> is [not] null\"."
                    ),
                )
            )


def validate_template(template: TemplateWizardResponse) -> ValidationReport:
    """Public entrypoint used by the wizard and `POST /templates/validate`.

    Synchronous: no LLM call, no network, no I/O.
    """
    return ValidationReport(issues=validate_template_deterministic(template))
