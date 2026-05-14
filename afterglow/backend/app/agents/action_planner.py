"""Action Planner Agent — Gemini ADK."""
from __future__ import annotations

from pathlib import Path

from app.integrations.gemini_adk import AdkAgentSpec
from app.tools.planning_tools import save_action_plan

_PROMPT_PATH = Path(__file__).parent / "prompts" / "action_planner.md"


def build_spec() -> AdkAgentSpec:
    instruction = _PROMPT_PATH.read_text(encoding="utf-8")
    return AdkAgentSpec(
        name="afterglow_action_planner",
        description="Plans the autonomous follow-up actions for a completed call.",
        instruction=instruction,
        tools=[save_action_plan],
    )
