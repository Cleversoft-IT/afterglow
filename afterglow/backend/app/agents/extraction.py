"""Extraction Agent — Gemini ADK, multimodal audio + transcript."""
from __future__ import annotations

from pathlib import Path

from app.integrations.gemini_adk import AdkAgentSpec
from app.tools.extraction_tools import (
    save_bodyshop_quote,
    save_dentist_appointment,
    save_restaurant_booking,
)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "extraction.md"


def build_spec() -> AdkAgentSpec:
    instruction = _PROMPT_PATH.read_text(encoding="utf-8")
    return AdkAgentSpec(
        name="afterglow_extraction",
        description="Extracts structured fields from a phone-call transcript and audio.",
        instruction=instruction,
        tools=[
            save_restaurant_booking,
            save_dentist_appointment,
            save_bodyshop_quote,
        ],
    )
