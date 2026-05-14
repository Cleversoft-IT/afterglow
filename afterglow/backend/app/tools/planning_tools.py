"""ADK tool for Action Planner — collects the list of actions to execute."""
from __future__ import annotations

from typing import Optional

from google.adk.tools.tool_context import ToolContext


def save_action_plan(
    tool_context: ToolContext,
    action_types: list[str],
    titles: list[str],
    summaries: list[str],
    payloads_json: list[str],
    confidence_scores: list[str],
    evidence_quotes: Optional[list[str]] = None,
) -> str:
    """Persist the action plan into session state.

    The four list[str] params are positionally aligned: index i belongs to action i.

    Args:
        action_types: e.g. ["booking.create", "whatsapp.send_confirmation"].
        titles: Human-readable label per action.
        summaries: One-line description of what each action will do.
        payloads_json: JSON-stringified payload per action.
        confidence_scores: Confidence per action as a string ("0.92").
        evidence_quotes: Verbatim transcript fragments backing the plan.
    """
    tool_context.state["action_plan"] = {
        "actions": [
            {
                "action_type": a,
                "title": t,
                "summary": s,
                "payload_json": p,
                "confidence": c,
            }
            for a, t, s, p, c in zip(
                action_types, titles, summaries, payloads_json, confidence_scores
            )
        ],
        "evidence_quotes": evidence_quotes or [],
    }
    return f"Saved plan with {len(action_types)} action(s)."
