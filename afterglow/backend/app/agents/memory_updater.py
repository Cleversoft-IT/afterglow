"""Memory Updater Agent — Gemini ADK summarizer."""
from __future__ import annotations

from pathlib import Path

from app.integrations.gemini_adk import AdkAgentSpec
from app.tools.memory_tools import save_memory_chunk

_PROMPT_PATH = Path(__file__).parent / "prompts" / "memory_updater.md"


def build_spec() -> AdkAgentSpec:
    instruction = _PROMPT_PATH.read_text(encoding="utf-8")
    return AdkAgentSpec(
        name="afterglow_memory_updater",
        description="Generates a short memory chunk to attach to the customer profile.",
        instruction=instruction,
        tools=[save_memory_chunk],
    )
