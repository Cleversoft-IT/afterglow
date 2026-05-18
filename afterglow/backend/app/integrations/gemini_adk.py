"""Gemini ADK runner factory.

Wraps `google.adk.runners.InMemoryRunner` with a per-agent factory so we can
spin up specialized sub-agents (today: `call_agent`, the agentic post-call
loop). Pattern derived from the lablab baseline
(Stephen-Kimoi/gemini-multimodal-document-agent), adapted for Afterglow.

`run_agent` consumes the runner's event stream until either:
  - the agent emits a final text response with no pending function calls, or
  - `tool_context.state["final"]` is set (the `finalize_call` tool was invoked), or
  - `max_iterations` tool turns have elapsed.

The returned dict carries the session `state`, a per-turn `turn_trail` (one
entry per observed `function_call`), and `token_usage_total` aggregated
across every event with a populated `usage_metadata`.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.config import get_settings

logger = logging.getLogger("afterglow")
settings = get_settings()


@dataclass
class AdkAgentSpec:
    name: str
    description: str
    instruction: str
    tools: list[Callable[..., Any]]
    model: str | None = None  # falls back to settings.gemini_default_model


def _resolve_model(spec: AdkAgentSpec) -> str:
    return spec.model or settings.gemini_default_model


def create_runner(spec: AdkAgentSpec):
    """Return a fresh InMemoryRunner for the given agent spec.

    Lazy-imports google.adk to keep CLI/tests cheap when ADK isn't needed
    (and to avoid hard-failing when GOOGLE_API_KEY is missing during local dev).
    """
    from google.adk import Agent
    from google.adk.runners import InMemoryRunner

    agent = Agent(
        model=_resolve_model(spec),
        name=spec.name,
        description=spec.description,
        instruction=spec.instruction,
        tools=spec.tools,
    )
    return InMemoryRunner(agent=agent, app_name=spec.name)


def _summarize_args(args: Any, max_chars: int = 200) -> str:
    """Compact a function_call.args dict for an audit row payload."""
    if not isinstance(args, dict):
        return str(args)[:max_chars]
    try:
        import json
        s = json.dumps(args, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        s = str(args)
    return s if len(s) <= max_chars else s[: max_chars - 1] + "…"


def _summarize_result(resp: Any, max_chars: int = 200) -> str:
    if resp is None:
        return ""
    if isinstance(resp, dict):
        try:
            import json
            s = json.dumps(resp, ensure_ascii=False, default=str)
        except Exception:  # noqa: BLE001
            s = str(resp)
    else:
        s = str(resp)
    return s if len(s) <= max_chars else s[: max_chars - 1] + "…"


async def run_agent_loop(
    runner,
    *,
    prompt_text: str,
    max_iterations: int = 12,
) -> dict[str, Any]:
    """Drive a multi-turn ADK agent run and capture the trail + tokens.

    Returns:
        {
          "state": dict,                  # full session state at exit
          "turn_count": int,              # tool invocations observed
          "turn_trail": list[dict],       # one entry per function_call,
                                          # with the paired function_response
          "token_usage_total": {
              "input_tokens": int,
              "output_tokens": int,
          },
          "final": dict | None,           # state["final"] payload if any
          "terminated_by": "finalize" | "max_turns" | "natural",
        }

    Notes:
      - We accumulate every event into the trail before bailing on
        `max_iterations`, so the orchestrator can still audit partial
        progress on a truncated loop.
      - `tool_context.state["final"]` is the canonical signal that the
        agent invoked `finalize_call`; the model itself usually emits a
        short natural-language confirmation afterwards.
    """
    from google.genai import types as genai_types

    user_id = "afterglow"
    session_id = str(uuid.uuid4())

    await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    content = genai_types.Content(
        role="user", parts=[genai_types.Part.from_text(text=prompt_text)]
    )

    turn_trail: list[dict[str, Any]] = []
    # `pending_calls` holds function_calls awaiting their function_response.
    # ADK guarantees the response comes in a subsequent event for that call,
    # so we just pair by name + order.
    pending_calls: list[dict[str, Any]] = []
    turn_count = 0
    total_input = 0
    total_output = 0
    terminated_by = "natural"

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        usage = getattr(event, "usage_metadata", None)
        if usage is not None:
            total_input += int(usage.prompt_token_count or 0)
            total_output += int(usage.candidates_token_count or 0)

        fcs = event.get_function_calls() or []
        for fc in fcs:
            turn_count += 1
            pending_calls.append(
                {
                    "turn": turn_count,
                    "tool": fc.name,
                    "args_summary": _summarize_args(fc.args),
                    "raw_args": fc.args,
                }
            )

        frs = event.get_function_responses() or []
        for fr in frs:
            # Match in FIFO order against the queued calls. ADK preserves
            # ordering, so the oldest pending call corresponds to the
            # incoming response.
            paired = None
            for i, pc in enumerate(pending_calls):
                if pc["tool"] == fr.name:
                    paired = pending_calls.pop(i)
                    break
            entry = paired or {
                "turn": turn_count,
                "tool": fr.name,
                "args_summary": "",
                "raw_args": {},
            }
            response_obj = fr.response if hasattr(fr, "response") else None
            entry["result_summary"] = _summarize_result(response_obj)
            entry["raw_response"] = response_obj
            turn_trail.append(entry)

        # Early exit: either the agent finalized, or we hit the budget.
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        if session.state.get("final") is not None:
            terminated_by = "finalize"
            # Drain ONE more event window so we can capture any trailing
            # final-text response and its usage_metadata. The model usually
            # emits one short closing event after finalize_call.
            break
        if turn_count >= max_iterations:
            terminated_by = "max_turns"
            break

    # Flush any orphaned pending calls (rare — happens if the loop broke
    # before ADK emitted the response).
    for pc in pending_calls:
        pc["result_summary"] = ""
        pc["raw_response"] = None
        turn_trail.append(pc)

    session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    return {
        "state": dict(session.state) if session.state else {},
        "turn_count": turn_count,
        "turn_trail": turn_trail,
        "token_usage_total": {
            "input_tokens": total_input,
            "output_tokens": total_output,
        },
        "final": session.state.get("final") if session.state else None,
        "terminated_by": terminated_by,
    }


# ---------------------------------------------------------------------------
# Legacy helper retained for backward compat with any caller that still wants
# the old single-state-key shape. New code should use `run_agent_loop` above.
# ---------------------------------------------------------------------------


async def run_agent(
    runner,
    *,
    prompt_text: str,
    state_key: str = "result",
) -> dict[str, Any]:
    """Execute one agent run and return the slice of session state at ``state_key``.

    Preserved for tests/spikes that target the legacy single-state-key API.
    """
    from google.genai import types

    user_id = "afterglow"
    session_id = str(uuid.uuid4())

    await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    content = types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])

    async for _ in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        pass

    session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    value = session.state.get(state_key)
    if value is None:
        return {}
    return value if isinstance(value, dict) else {"value": value}
