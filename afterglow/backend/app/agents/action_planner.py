"""Action Planner — agentic loop on top of the call analysis.

Gemini Call Analyzer produces structured extractions and a list of planned
actions (single-shot, structured output). The Action Planner re-reads that
analysis as an *agent* whose available tools are the template's auto-mode
action_types: each tool, when invoked, registers a "requested action" in the
ADK session state. No execution happens here — that stays in
``executors.action_executor.execute_planned_actions`` so:

  - the safety net (action_type validation, execution_mode read from the
    template) is enforced exactly once;
  - MOCK_REGISTRY is never invoked twice.

Default-on with two-tier fallback:
  1. If ``settings.google_api_key`` is empty, return the analyzer's
     ``planned_actions`` directly (deterministic fallback).
  2. If the ADK runner raises for any reason at runtime, log a warning and
     return the same deterministic fallback.

The audit row recorded by the orchestrator gets ``payload.mode = "agentic"``
on the happy path and ``"fallback"`` when degraded.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.agents import call_analyzer
from app.config import get_settings
from app.db.models import Customer, Template
from app.integrations.gemini_adk import AdkAgentSpec, create_runner, run_agent

logger = logging.getLogger("afterglow")
settings = get_settings()


_PLANNER_INSTRUCTION = """You are the Afterglow Action Planner.

You have already received a structured analysis of a post-call: extracted fields, intent, sentiment, urgency, prior facts, and a candidate next_call_briefing. The human operator has finished the call. Your job is to decide which of your available tools to invoke, in which order, and with which arguments.

Rules:
- One tool call = one requested action. The tool will queue the request; the deterministic executor will run it afterwards.
- Only invoke tools whose preconditions are grounded in the analysis. Cite the supporting evidence in the ``evidence`` argument.
- Use the extracted field values to populate ``payload_json``. ``payload_json`` MUST be a valid JSON object literal as a string (e.g. ``{"party_size": 4, "booking_time": "20:30"}``).
- Confidence must reflect how strongly the transcript supports invoking this tool, NOT the field-extraction confidence.
- Do not invent tools that are not listed. Do not invoke the same tool twice unless explicitly justified.
- After all useful tools have been called, stop.
"""


def _make_tool(action_def: dict[str, Any]):
    """Build a tool callable for one action_type entry from the template.

    The tool's only side-effect is to append a record to
    ``tool_context.state["requested_actions"]["items"]``. The dict-of-list
    shape is intentional: ``gemini_adk.run_agent`` returns the raw state
    value when it is a dict, so reading back ``result["items"]`` is a clean
    one-liner on the consumer side.
    """
    key: str = action_def["key"]
    label: str = action_def.get("label") or key
    description: str = action_def.get("description") or label

    def tool(
        title: str = "",
        summary: str = "",
        payload_json: str = "{}",
        confidence: float = 0.9,
        evidence: Optional[list[str]] = None,
        tool_context: Any = None,
    ) -> dict[str, Any]:
        """Queue an action for downstream execution."""
        try:
            payload = json.loads(payload_json or "{}")
            if not isinstance(payload, dict):
                payload = {"value": payload}
        except json.JSONDecodeError:
            payload = {}

        bucket = None
        if tool_context is not None and hasattr(tool_context, "state"):
            bucket = tool_context.state.setdefault(
                "requested_actions", {"items": []}
            )
            bucket["items"].append(
                {
                    "action_type": key,
                    "title": title or label,
                    "summary": summary,
                    "payload": payload,
                    "confidence": float(confidence),
                    "evidence": evidence or [],
                }
            )
        return {"queued": key}

    tool.__name__ = key.replace(".", "_").replace("-", "_")
    tool.__doc__ = description
    return tool


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
        f"- {p.action_type}: {p.title} (confidence={p.confidence:.2f}) payload={p.payload_json}"
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


def _fallback_planner(analysis: call_analyzer.CallAnalysis) -> list[dict[str, Any]]:
    """Deterministic fallback: replicate the orchestrator's pre-agentic plan.

    Reused both when ``GOOGLE_API_KEY`` is empty (offline / local dev) and
    when the ADK runner raises a runtime error.
    """
    plan: list[dict[str, Any]] = []
    for a in analysis.planned_actions:
        entry = a.model_dump()
        try:
            entry["payload"] = json.loads(entry.pop("payload_json") or "{}")
        except json.JSONDecodeError:
            entry["payload"] = {}
            entry.pop("payload_json", None)
        plan.append(entry)
    return plan


async def plan_actions(
    *,
    analysis: call_analyzer.CallAnalysis,
    template: Template,
    customer: Customer,
    transcript_text: str,
) -> tuple[list[dict[str, Any]], str]:
    """Return ``(plan, mode)`` where ``mode`` is one of ``agentic`` or ``fallback``.

    The orchestrator surfaces ``mode`` in the audit row so the trail tells the
    truth about which path produced the executed plan.
    """
    if not settings.google_api_key:
        return _fallback_planner(analysis), "fallback"

    auto_actions = [a for a in template.action_types if a.get("execution_mode") == "auto"]
    if not auto_actions:
        return _fallback_planner(analysis), "fallback"

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
        logger.warning(
            "action_planner: ADK runner failed (%s) — using deterministic fallback.",
            exc,
        )
        return _fallback_planner(analysis), "fallback"

    items = result.get("items") if isinstance(result, dict) else None
    if not items:
        # The agent produced no tool calls. Decide between two valid readings:
        # (a) it concluded no action was warranted — honour that and return [];
        # (b) the run failed silently — fall back to the analyzer hints.
        # Heuristic: if the analyzer suggested at least one action, prefer the
        # fallback so the demo never looks "dead".
        if analysis.planned_actions:
            logger.info(
                "action_planner: empty agent output — falling back to analyzer hints."
            )
            return _fallback_planner(analysis), "fallback"
        return [], "agentic"

    return list(items), "agentic"
