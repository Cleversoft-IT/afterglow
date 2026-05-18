"""Control tools — flag_for_review + finalize_call.

Both are agent-only sinks: they don't reach the action catalog or RAG, they
just record state that the orchestrator consumes after the loop exits.
"""
from __future__ import annotations

from typing import Any, Callable, Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.call_analyzer import FieldExtraction
from app.agents.tools.turn import bump_turn
from app.db.models import Call


class FinalizeCallPayload(BaseModel):
    """Structured analysis the agent emits as the LAST tool call.

    Mirrors what the legacy single-shot `CallAnalysis` used to return,
    minus `planned_actions` (the agent has already executed them inline
    via action tools). `fields` (not `extracted_fields`) so the orchestrator
    can pass the same `list[FieldExtraction]` shape through
    `_coerce_extractions` without translation.
    """

    fields: list[FieldExtraction] = Field(default_factory=list)
    intent: str = ""
    sentiment: str = ""
    language: str = ""
    urgency: str = ""
    briefing: str = ""


def make_flag_for_review(*, session: AsyncSession, call: Call) -> Callable[..., Any]:
    """Build the `flag_for_review` callable. Persists `call.review_flag`."""

    async def flag_for_review(
        reason: str,
        severity: Literal["low", "medium", "high"] = "medium",
        tool_context: Any = None,
    ) -> dict[str, Any]:
        """Flag this call for human review.

        Use when:
          - the caller's evidence is ambiguous or conflicting;
          - confidence on a high-stakes action would be below threshold;
          - the caller raised a complaint that needs a human follow-up.

        The orchestrator sets `Call.status="needs_review"` (banner in UI)
        when this tool is invoked but only at end-of-loop if the agent
        also returns `completion_reason="finalize"`. If the agent finalizes
        normally, `status="completed"` AND review_flag stays visible.
        """
        turn = bump_turn(tool_context)
        call.review_flag = {
            "reason": (reason or "").strip()[:500] or "unspecified",
            "severity": severity,
            "turn_count": turn,
            "flagged_by": "agent",
        }
        await session.flush()
        return {"flagged": True}

    flag_for_review.__annotations__ = {
        "reason": str,
        "severity": Literal["low", "medium", "high"],
        "tool_context": Any,
        "return": dict,
    }
    return flag_for_review


def make_finalize_call() -> Callable[..., Any]:
    """Build the `finalize_call` callable.

    Writes the validated payload into `tool_context.state["final"]`. The
    orchestrator reads that state slot after the loop returns and persists
    `ExtractedFields` from `payload.fields`.
    """

    async def finalize_call(
        payload: FinalizeCallPayload, tool_context: Any = None
    ) -> dict[str, Any]:
        """Emit the structured analysis and end the loop.

        Call exactly once, after all warranted actions are executed.
        `fields` must be grounded VERBATIM in the current transcript
        (`prior_facts` from lookup_customer_memory are for the briefing
        only, never for field evidence).
        """
        bump_turn(tool_context)
        if tool_context is not None and hasattr(tool_context, "state"):
            tool_context.state["final"] = payload.model_dump()
        return {"final": True}

    finalize_call.__annotations__ = {
        "payload": FinalizeCallPayload,
        "tool_context": Any,
        "return": dict,
    }
    return finalize_call
