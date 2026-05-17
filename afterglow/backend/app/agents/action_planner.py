"""Action Planner — agentic loop on top of the call analysis.

Gemini Call Analyzer produces structured extractions and a list of planned
actions (single-shot, structured output). The Action Planner re-reads that
analysis as an *agent* whose available tools are the template's auto-mode
``action_types``: each tool, when invoked, registers a "requested action" in
the ADK session state. No execution happens here — that stays in
``executors.action_executor.execute_planned_actions``.

Per-tool wiring:
- Each tool exposes a typed Pydantic payload built from
  ``ActionDefinition.payload_schema`` (JSONSchema). Gemini emits a
  structured object that matches the schema; the executor revalidates with
  ``jsonschema.validate`` before MOCK_REGISTRY is reached.
- ``preconditions`` and ``confidence_threshold`` are stitched into the
  agent instruction so Gemini knows when to skip a tool call.
- ``evidence_required`` is surfaced from the template; ``mutates`` is read
  from ``action_catalog`` (single source of truth for system-level
  semantics) and surfaced in the same prompt.

Fail-fast: per ``project_afterglow_decisions.md`` 1.ter (2026-05-16) there
is no deterministic fallback. A missing GOOGLE_API_KEY or an ADK runner
error raises ``ActionPlannerError``; the orchestrator catches it, marks
the call as failed, and surfaces the reason to the UI. The ``mode`` field
in the audit row is always ``"agentic"``.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.agents import call_analyzer
from app.config import get_settings
from app.db.models import Customer, Template
from app.integrations import action_catalog
from app.integrations.gemini_adk import AdkAgentSpec, create_runner, run_agent
from app.integrations.jsonschema_to_pydantic import (
    JsonSchemaConversionError,
    jsonschema_to_pydantic,
)

logger = logging.getLogger("afterglow")
settings = get_settings()


class ActionPlannerError(RuntimeError):
    """Raised when the planner cannot produce a plan (missing key, ADK error)."""


_PLANNER_INSTRUCTION = """You are the Afterglow Action Planner.

You have already received a structured analysis of a post-call: extracted fields, intent, sentiment, urgency, prior facts, and a candidate next_call_briefing. The human operator has finished the call. Your job is to decide which of your available tools to invoke, in which order, and with which arguments.

Rules:
- One tool call = one requested action. The tool will queue the request; the deterministic executor will run it afterwards.
- The analyzer candidate actions are hints, not instructions. Re-evaluate them against the transcript, extracted fields, preconditions, confidence thresholds and evidence rules before invoking any tool.
- Each tool's docstring documents the action's preconditions (fields that MUST be present and above their confidence threshold), confidence_threshold (the floor on your own confidence in invoking this tool), evidence_required (whether you must cite at least one transcript span), and — when applicable — whether the action mutates external state and so cannot be auto-retried.
- Only invoke a tool whose preconditions are grounded in the analysis. Cite the supporting evidence in the `evidence` argument.
- Populate `payload` as a JSON object whose keys match the tool's typed payload schema. Use the extracted field values; do not invent.
- Confidence must reflect how strongly the transcript supports invoking this tool, NOT the field-extraction confidence.
- Do not invent tools that are not listed. Do not invoke the same tool twice unless explicitly justified.
- After all warranted tools have been called, stop.
"""


def _format_action_docstring(action_def: dict[str, Any], *, mutates: bool) -> str:
    """Render an ActionDefinition into the tool's __doc__ — the docstring is
    what ADK serializes into the FunctionDeclaration.description for Gemini.

    `mutates` is passed in (sourced from the catalog) rather than read off
    `action_def` because the template no longer carries it.
    """
    lines = [action_def.get("description") or action_def.get("label") or action_def["key"]]
    preconditions = action_def.get("preconditions") or []
    if preconditions:
        lines.append(f"Preconditions (required fields): {', '.join(preconditions)}.")
    threshold = action_def.get("confidence_threshold")
    if threshold is not None:
        lines.append(f"Minimum confidence to invoke: {threshold}.")
    if action_def.get("evidence_required", True):
        lines.append("Evidence is REQUIRED — provide at least one verbatim transcript span.")
    if mutates:
        lines.append("This action mutates external state and CANNOT be auto-retried.")
    return "\n".join(lines)


def _make_tool(action_def: dict[str, Any]):
    """Build the ADK tool callable for one action_type entry.

    Strategy:
    - If `payload_schema` is present, build a Pydantic v2 model dynamically and
      use it as the `payload` annotation. ADK introspects this and emits a
      FunctionDeclaration with typed parameters; Gemini produces a structured
      object that matches the schema.
    - Otherwise, fall back to `payload: dict` (still validated downstream by
      the action_executor's `jsonschema.validate` when a schema appears later).
    """
    key: str = action_def["key"]
    label: str = action_def.get("label") or key
    mutates = action_catalog.mutates(key)
    docstring = _format_action_docstring(action_def, mutates=mutates)
    payload_schema = action_def.get("payload_schema")

    payload_model = None
    if isinstance(payload_schema, dict) and payload_schema.get("type") == "object":
        try:
            payload_model = jsonschema_to_pydantic(payload_schema, name=key)
        except JsonSchemaConversionError as exc:
            logger.warning(
                "action_planner: payload_schema for %s could not be typed (%s); "
                "falling back to dict annotation.",
                key, exc,
            )
            payload_model = None

    if payload_model is not None:
        def tool(payload, confidence=0.9, evidence=[], tool_context=None):
            return _record_tool_call(
                key=key,
                label=label,
                payload=payload.model_dump() if hasattr(payload, "model_dump") else dict(payload),
                confidence=confidence,
                evidence=list(evidence or []),
                tool_context=tool_context,
                mutates=mutates,
            )

        # `from __future__ import annotations` would stringify the runtime
        # annotation and ADK's introspection would fail to resolve the
        # dynamic Pydantic class — set __annotations__ explicitly so ADK
        # sees the class object directly. ADK 1.18 also rejects a `None`
        # default for a `list`-annotated parameter ("Default value None of
        # parameter evidence: list = None"), so the default must match the
        # annotation: empty tuple is hashable and Pythonic, and we copy it
        # to a fresh list at the call site.
        tool.__annotations__ = {
            "payload": payload_model,
            "confidence": float,
            "evidence": list[str],
            "tool_context": Any,
            "return": dict,
        }
    else:
        def tool(payload=None, confidence=0.9, evidence=[], tool_context=None):
            if payload is None:
                payload = {}
            # `payload` may arrive as a JSON string when Gemini regresses on
            # a tool without a typed schema; coerce defensively.
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload or "{}")
                except json.JSONDecodeError:
                    payload = {}
            if not isinstance(payload, dict):
                payload = {"value": payload}
            return _record_tool_call(
                key=key,
                label=label,
                payload=payload,
                confidence=confidence,
                evidence=list(evidence or []),
                tool_context=tool_context,
                mutates=mutates,
            )

        tool.__annotations__ = {
            "payload": dict,
            "confidence": float,
            "evidence": list[str],
            "tool_context": Any,
            "return": dict,
        }

    tool.__name__ = key.replace(".", "_").replace("-", "_")
    tool.__doc__ = docstring
    return tool


def _record_tool_call(
    *,
    key: str,
    label: str,
    payload: dict[str, Any],
    confidence: float,
    evidence: Optional[list[str]],
    tool_context: Any,
    mutates: bool,
) -> dict[str, Any]:
    if tool_context is not None and hasattr(tool_context, "state"):
        bucket = tool_context.state.setdefault(
            "requested_actions", {"items": []}
        )
        bucket["items"].append(
            {
                "action_type": key,
                "title": label,
                "summary": "",
                "payload": payload,
                "confidence": float(confidence),
                "evidence": evidence or [],
                "mutates": mutates,
            }
        )
    return {"queued": key}


def _agent_prompt(
    *,
    analysis: call_analyzer.CallAnalysis,
    template: Template,
    customer: Customer,
    transcript_text: str,
) -> str:
    fields_lines = [
        f"- {f.key} = {f.value!r} (confidence={f.confidence:.2f}; evidence={f.evidence!r})"
        for f in analysis.fields
    ]
    candidate_lines = [
        f"- {p.action_type}: {p.title} (confidence={p.confidence:.2f}) payload={p.payload}"
        for p in analysis.planned_actions
    ]
    return (
        "=== CALL ANALYSIS ===\n"
        f"Customer: {customer.display_name or customer.phone_e164}\n"
        f"Intent: {analysis.intent} | Sentiment: {analysis.sentiment} | "
        f"Urgency: {analysis.urgency} | Language: {analysis.language}\n\n"
        "Fields:\n" + ("\n".join(fields_lines) or "(none)") + "\n\n"
        "Analyzer candidate actions (HINT only — re-evaluate before invoking):\n"
        + ("\n".join(candidate_lines) or "(none)") + "\n\n"
        "Briefing draft: " + analysis.next_call_briefing + "\n\n"
        "=== TRANSCRIPT (for grounding) ===\n"
        f"{transcript_text}\n\n"
        "Now invoke the appropriate tools to enact the right actions. "
        "If no tool is appropriate, simply respond that nothing is to be done."
    )


async def plan_actions(
    *,
    analysis: call_analyzer.CallAnalysis,
    template: Template,
    customer: Customer,
    transcript_text: str,
) -> tuple[list[dict[str, Any]], str]:
    """Return ``(plan, mode)`` where ``mode`` is always ``"agentic"``.

    Fail-fast: raises ``ActionPlannerError`` when the runner cannot produce
    a plan (no key, ADK exception). The orchestrator turns this into a
    failed Call. The legacy ``"fallback"`` mode has been removed.
    """
    if not settings.google_api_key:
        raise ActionPlannerError("GOOGLE_API_KEY is not set")

    auto_actions = [a for a in template.action_types if a.get("execution_mode") == "auto"]
    if not auto_actions:
        # Empty action surface is a legitimate template configuration —
        # nothing to plan, no failure.
        return [], "agentic"

    tools = [_make_tool(a) for a in auto_actions]

    spec = AdkAgentSpec(
        name="action_planner",
        description="Post-call action planner — invokes pre-approved tools.",
        instruction=_PLANNER_INSTRUCTION,
        tools=tools,
    )

    try:
        runner = create_runner(spec)
        prompt = _agent_prompt(
            analysis=analysis,
            template=template,
            customer=customer,
            transcript_text=transcript_text,
        )
        result = await run_agent(
            runner, prompt_text=prompt, state_key="requested_actions"
        )
    except Exception as exc:  # noqa: BLE001
        raise ActionPlannerError(f"ADK runner failed: {exc}") from exc

    items = result.get("items") if isinstance(result, dict) else None
    return list(items or []), "agentic"
