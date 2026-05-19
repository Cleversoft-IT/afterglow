"""Call Agent — the agentic post-call pipeline (round-10).

Single Gemini/ADK agent that fuses what used to be three separate stages:

  - call_analyzer (single-shot CallAnalysis structured output) — REMOVED
  - action_planner (single-turn ADK loop registering actions) — REMOVED
  - action_executor (deterministic batch) — now called INLINE by action tools

The agent receives the diarized transcript and the active template, then
decides turn by turn which tool to invoke:

  - lookup_customer_memory(query)    → on-demand RAG against Vultr Vector Store
  - search_transcript(keyword)       → diarization-aware substring search
  - read_transcript_segment(s, e)    → word-indexed slice of the transcript
  - <action_key>(payload, ...)       → execute the action via execute_single_action
                                       and receive {status, result, attempt}
  - flag_for_review(reason, sev)     → mark Call.review_flag for human escalation
  - finalize_call(payload)           → emit FinalizeCallPayload, end the loop

Contract (no-raise):
  - This function NEVER raises for ADK/tool/model errors.
  - Every failure mode is translated into a `CallAgentResult` with
    `completion_reason="error"` and an `error` string.
  - This is what lets `orchestrator.run_pipeline` keep already-flushed
    ExecutedAction rows visible — the rollback path of
    `api/calls._run_pipeline_isolated` is only the safety net for truly
    uncaught exceptions (e.g. DB connection drop).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.call_analyzer import FieldExtraction, TokenUsage
from app.agents.tools.action_tool import make_action_tool
from app.agents.tools.control_tool import (
    FinalizeCallPayload,
    make_finalize_call,
    make_flag_for_review,
)
from app.agents.tools.memory_tool import make_memory_tool
from app.agents.tools.transcript_tool import (
    make_read_segment,
    make_search_transcript,
)
from app.config import get_settings
from app.db.models import Call, Customer, Template
from app.integrations.gemini_adk import AdkAgentSpec, create_runner, run_agent_loop

logger = logging.getLogger("afterglow")
settings = get_settings()


CompletionReason = Literal["finalize", "max_turns", "error"]


_SYSTEM_INSTRUCTION = """You are Afterglow's post-call agent. A human operator just finished a phone call. You receive the diarized transcript and the active template. Your job:

  1. Understand what the caller needs and what was said.
  2. Decide WHEN you need extra context (prior calls via lookup_customer_memory; transcript re-reads via search_transcript / read_transcript_segment).
  3. Execute the right actions from the template, OBSERVING each result and correcting course on failures.
  4. Call finalize_call exactly once with the full structured analysis.

Tool-use policy:
- Prefer lookup_customer_memory with a SPECIFIC question (not "any facts"). Skip it entirely if the caller is clearly new or context isn't needed.
- Action tools EXECUTE immediately. Read the result:
    * `validation_failed` → you may retry once with a corrected payload.
    * `evidence_missing` → add a real transcript span before retrying.
    * `failed` → retry once or flag_for_review.
    * Mutating actions (booking, payment, profile updates) cannot be retried after a successful execution.
- Use flag_for_review for ambiguous evidence, conflicts, high-stakes uncertainty.
- prior_facts from lookup_customer_memory are for the briefing only — NEVER use them as field evidence.
- Field evidence must be a verbatim span from the CURRENT transcript.

Budget: at most ~12 tool turns. Be efficient.
End with exactly one finalize_call.
"""


@dataclass
class CallAgentResult:
    """Outcome of a single agent run. Always populated — no-raise contract."""

    completion_reason: CompletionReason
    turn_count: int = 0
    fields: Optional[list[FieldExtraction]] = None
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    language: Optional[str] = None
    urgency: Optional[str] = None
    briefing: Optional[str] = None
    flagged: bool = False
    review_flag: Optional[dict[str, Any]] = None
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    turn_trail: list[dict[str, Any]] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    error: Optional[str] = None


def _build_user_prompt(
    *,
    template: Template,
    customer: Customer,
    transcript_text: str,
    prompt_hints: list[dict[str, Any]] | None,
    prior_structured: dict[str, Any] | None,
    domain_hint: str,
) -> str:
    """Compose the per-call user-message. Tools handle prior_facts on demand."""
    import json

    from app.agents.prompt_hint_eval import applicable_hints

    hint_lines = applicable_hints(prompt_hints, prior_structured or {})
    hints_section = "\n".join(f"- {line}" for line in hint_lines) or "(none)"

    return (
        "=== DOMAIN & TEMPLATE ===\n"
        f"Domain: {domain_hint}\n"
        f"Template: {template.name}\n\n"
        f"fields_schema:\n{json.dumps(template.fields_schema, ensure_ascii=False)}\n\n"
        "active prompt hints (evaluated against prior structured facts):\n"
        f"{hints_section}\n\n"
        "=== CALLER ===\n"
        f"Display name: {customer.display_name or '(unknown)'}\n"
        f"Phone: {customer.phone_e164}\n"
        f"Total prior calls: {customer.total_calls or 0}\n\n"
        "=== CURRENT TRANSCRIPT (diarized) ===\n"
        f"{transcript_text}\n\n"
        "Decide which tools to invoke, then call finalize_call exactly once."
    )


async def run_call_agent(
    session: AsyncSession,
    *,
    call: Call,
    customer: Customer,
    template: Template,
    transcript_text: str,
    prompt_hints: list[dict[str, Any]] | None,
    prior_structured: dict[str, Any] | None,
    is_demo: bool,
    preseed_available: bool,
    collection_id: Optional[str],
    session_lock: asyncio.Lock,
    max_iterations: int = 12,
) -> CallAgentResult:
    """Run the agentic loop for one call. Always returns; never raises.

    `session_lock` is a required asyncio.Lock owned by the orchestrator and
    shared with every tool that mutates `session`. Gemini may emit parallel
    function calls in a single turn; without the lock two concurrent
    `session.flush()` coroutines would trigger SQLAlchemy's
    "Session is already flushing" InvalidRequestError.
    """
    if not settings.google_api_key:
        return CallAgentResult(
            completion_reason="error",
            error="GOOGLE_API_KEY is not set",
        )

    # --- build the tool surface from the template + closures over this call ---
    auto_actions = [a for a in template.action_types if a.get("execution_mode") == "auto"]
    action_tools = [
        make_action_tool(
            a,
            session=session,
            call=call,
            customer=customer,
            template=template,
            session_lock=session_lock,
        )
        for a in auto_actions
    ]

    memory_tool = make_memory_tool(
        phone_e164=call.phone_e164,
        domain_hint=template.domain_hint,
        collection_id=collection_id,
        is_demo=is_demo,
        preseed_available=preseed_available,
    )
    search_tool = make_search_transcript(
        transcript_text=transcript_text,
        speakers=(call.raw_transcript or {}).get("speakers"),
    )
    read_segment_tool = make_read_segment(
        transcript_text=transcript_text,
        speakers=(call.raw_transcript or {}).get("speakers"),
    )
    flag_tool = make_flag_for_review(session=session, call=call, session_lock=session_lock)
    finalize_tool = make_finalize_call()

    tools: list[Any] = [
        memory_tool,
        search_tool,
        read_segment_tool,
        flag_tool,
        finalize_tool,
        *action_tools,
    ]

    available_tools = [t.__name__ for t in tools if hasattr(t, "__name__")]

    spec = AdkAgentSpec(
        name="call_agent",
        description="Afterglow's agentic post-call analyst + planner + executor.",
        instruction=_SYSTEM_INSTRUCTION,
        tools=tools,
    )

    user_prompt = _build_user_prompt(
        template=template,
        customer=customer,
        transcript_text=transcript_text,
        prompt_hints=prompt_hints,
        prior_structured=prior_structured,
        domain_hint=template.domain_hint,
    )

    try:
        runner = create_runner(spec)
        loop_result = await run_agent_loop(
            runner, prompt_text=user_prompt, max_iterations=max_iterations
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("call_agent: ADK runner failed")
        return CallAgentResult(
            completion_reason="error",
            error=f"adk_runner [{type(exc).__name__}]: {exc}"[:1000],
            available_tools=available_tools,
        )

    turn_count = int(loop_result.get("turn_count") or 0)
    turn_trail = loop_result.get("turn_trail") or []
    usage = loop_result.get("token_usage_total") or {}
    token_usage = TokenUsage(
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
    )
    final_state = loop_result.get("final")
    terminated_by = loop_result.get("terminated_by") or "natural"

    if final_state is None:
        # The loop ended without finalize_call: either we hit the budget, or
        # the model emitted a final text without finalizing first. Both map
        # to needs_review at the orchestrator level.
        return CallAgentResult(
            completion_reason="max_turns",
            turn_count=turn_count,
            turn_trail=turn_trail,
            token_usage=token_usage,
            flagged=call.review_flag is not None,
            review_flag=call.review_flag,
            available_tools=available_tools,
            error=None if terminated_by == "max_turns" else "no_finalize",
        )

    # Successful finalize — validate the payload one more time on our side.
    try:
        payload = FinalizeCallPayload.model_validate(final_state)
    except Exception as exc:  # noqa: BLE001
        logger.warning("call_agent: finalize payload validation failed (%s)", exc)
        return CallAgentResult(
            completion_reason="error",
            turn_count=turn_count,
            turn_trail=turn_trail,
            token_usage=token_usage,
            available_tools=available_tools,
            error=f"finalize_validation: {exc}"[:500],
        )

    return CallAgentResult(
        completion_reason="finalize",
        turn_count=turn_count,
        turn_trail=turn_trail,
        token_usage=token_usage,
        fields=payload.fields,
        intent=payload.intent,
        sentiment=payload.sentiment,
        language=payload.language,
        urgency=payload.urgency,
        briefing=payload.briefing,
        flagged=call.review_flag is not None,
        review_flag=call.review_flag,
        available_tools=available_tools,
    )
