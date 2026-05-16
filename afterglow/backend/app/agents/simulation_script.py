"""Simulation script builder — Gemini call that writes a plausible phone-call
script for a custom template, so the Simulator can render a demo MP3 via
Speechmatics TTS without the operator having to write dialogue.

The output is a list of `{speaker, voice, text}` turns: operator + caller
alternating, ~6–10 turns. Speakers are tagged so the UI can render labels
and the diarization is preserved if we ever wanted to use this script as
ground truth for an extractor evaluation harness.

Fail-fast on missing GOOGLE_API_KEY or empty Gemini output via
`ScriptBuilderError`. No offline stub.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.config import get_settings
from app.db.models import Template

logger = logging.getLogger("afterglow")


class ScriptBuilderError(RuntimeError):
    """Raised when the simulation script cannot be generated."""


_ALLOWED_VOICES = ("sarah", "theo", "megan", "jack")


class _ScriptTurn(BaseModel):
    speaker: Literal["operator", "caller"]
    voice: Literal["sarah", "theo", "megan", "jack"]
    text: str = Field(min_length=2)


class _ScriptResponse(BaseModel):
    caller_name: str
    caller_phone_e164: str
    turns: list[_ScriptTurn]


SYSTEM_INSTRUCTION = (
    "You are the Afterglow Simulation Script Builder.\n\n"
    "Given a template (the operator's intake schema for an inbound phone "
    "call), write a SHORT, REALISTIC dialogue between an OPERATOR (front "
    "desk) and a CALLER. The script is read aloud by a TTS engine for the "
    "demo simulator.\n\n"
    "Rules:\n"
    "- Use ENGLISH (UK or US — pick whichever fits). Speechmatics TTS "
    "preview only exposes EN voices.\n"
    "- 6–10 turns total, alternating operator / caller.\n"
    "- Pick two voices: one for operator, one for caller. Allowed voices: "
    f"{', '.join(_ALLOWED_VOICES)}.\n"
    "- The dialogue must surface enough information to ground at least the "
    "REQUIRED fields in the template. Mention them naturally, no headers.\n"
    "- End with a short goodbye exchange.\n"
    "- Pick a caller name and a US phone number for the demo (`+1 (555) "
    "AAA-BBBB` shape, never a real number).\n"
)


async def build_simulation_script(template: Template) -> _ScriptResponse:
    settings = get_settings()
    if not settings.google_api_key:
        raise ScriptBuilderError("GOOGLE_API_KEY is not set")

    from google import genai
    from google.genai import types as genai_types

    user_prompt = (
        f"Template name: {template.name}\n"
        f"Domain: {template.domain_hint}\n"
        f"Description: {template.description or '(none)'}\n\n"
        f"Required fields to cover:\n"
        + "\n".join(
            f"- {f.get('label', f.get('key'))} (key: {f.get('key')}, type: {f.get('type')})"
            for f in (template.fields_schema or [])
            if isinstance(f, dict) and f.get("required")
        )
        + "\n\nWrite the script now."
    )

    client = genai.Client(api_key=settings.google_api_key)
    try:
        resp = await client.aio.models.generate_content(
            model=settings.gemini_template_builder_model or settings.gemini_default_model,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=_ScriptResponse,
                temperature=0.5,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise ScriptBuilderError(f"Gemini call failed: {exc}") from exc

    text = (resp.text or "").strip()
    if not text:
        raise ScriptBuilderError("Gemini returned an empty response")
    try:
        parsed = _ScriptResponse.model_validate_json(text)
    except Exception as exc:  # noqa: BLE001
        raise ScriptBuilderError(f"schema validation failed: {exc}") from exc
    if not parsed.turns:
        raise ScriptBuilderError("script has no turns")
    return parsed


def script_response_to_simulation_config(
    parsed: _ScriptResponse,
    *,
    audio_url: Optional[str] = None,
    audio_status: Optional[Literal["pending", "ready", "failed"]] = None,
) -> dict:
    """Project a `_ScriptResponse` into the JSONB shape stored on the template."""
    return {
        "caller_name": parsed.caller_name,
        "caller_phone_e164": parsed.caller_phone_e164,
        "script_turns": [t.model_dump() for t in parsed.turns],
        "audio_url": audio_url,
        "audio_status": audio_status,
        "audio_generated_at": None,
        "audio_source": "tts_generated" if audio_url else None,
    }
