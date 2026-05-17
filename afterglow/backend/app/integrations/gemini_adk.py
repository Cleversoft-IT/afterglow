"""Gemini ADK runner factory.

Wraps `google.adk.runners.InMemoryRunner` with a per-agent factory so we can spin
up specialized sub-agents (extraction, action_planner, memory_updater)
sharing one Gemini client + thought signatures.

Pattern derived from the lablab baseline (Stephen-Kimoi/gemini-multimodal-document-agent),
adapted for Afterglow's multi-agent layout.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable

from app.config import get_settings

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


async def run_agent(
    runner,
    *,
    prompt_text: str,
    state_key: str = "result",
) -> dict[str, Any]:
    """Execute one agent turn and return the slice of session state at ``state_key``.

    Pattern: the agent calls a tool which writes into ``tool_context.state[state_key]``.
    No JSON prompt-engineering tricks needed.
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
