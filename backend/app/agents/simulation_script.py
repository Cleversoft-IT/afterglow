"""Simulation script builder — Gemini call that writes a plausible phone-call
script for a custom template, so the Simulator can render demo recordings
via Speechmatics TTS without the operator having to write dialogue.

The output covers BOTH simulator buttons: `scenarios.new` (first-time caller,
full self-introduction) and `scenarios.existing` (returning caller who
references a small piece of shared history). Each scenario is a list of
`{speaker, voice, text}` turns; the wizard prompt forces the dialogue to
exercise 2-3 actions from the template's `action_types` so the post-call
pipeline produces observable work in the demo.

Quality directives live in the SYSTEM_INSTRUCTION below — see
`feedback_demo_scripts_quality.md` for the rule that applies to BOTH this
agent and the seed scripts in `scripts/generate_demo_audio.py`.

Fail-fast on missing GOOGLE_API_KEY or empty Gemini output via
`ScriptBuilderError`. No offline stub.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.config import get_settings
from app.db.models import Template
from app.integrations import action_catalog

logger = logging.getLogger("afterglow")


class ScriptBuilderError(RuntimeError):
    """Raised when the simulation script cannot be generated."""


_ALLOWED_VOICES = ("sarah", "theo", "megan", "jack")

# Stop-words that uniquely flag the dialogue as non-English. We trust the
# system prompt for the happy path, but Gemini sometimes drops back into
# the template's own language (e.g. "buongiorno" / "salve" when the
# template name is Italian) and the Speechmatics EN voices then render
# the audio as gibberish. This list is the safety net: any whole-word
# match (case-insensitive) raises ScriptBuilderError so the API returns
# 502 and the operator can retry the generation. Cognates that happen
# to appear in English ("via", "a", "no", "si") are deliberately
# excluded; only words that have no neutral English meaning are listed.
_NON_ENGLISH_STOPWORDS = frozenset(
    {
        # Italian
        "ciao", "salve", "buongiorno", "buonasera", "buonanotte",
        "prego", "grazie", "scusi", "scusa", "perché", "perche",
        "sono", "siamo", "siete",
        "vorrei", "vorremmo",
        "anche", "molto", "questa", "questo", "quella", "quello",
        "quindi", "allora", "comunque", "purtroppo", "soltanto", "soprattutto",
        # Spanish
        "hola", "buenos", "días", "tardes", "noches", "gracias",
        "señor", "señora", "señorita", "ustedes",
        # French
        "bonjour", "bonsoir", "merci", "voilà", "très", "monsieur", "madame", "mademoiselle",
        # German
        "guten", "danke", "bitte", "herr", "frau", "morgen",
    }
)
_WORD_RE = re.compile(r"[a-zà-ÿ']+", re.IGNORECASE)


def _validate_english_or_raise(parsed: "_ScriptResponse") -> None:
    """Reject scripts that contain whole-word non-English markers.

    See `_NON_ENGLISH_STOPWORDS` for the rationale — the system prompt
    forbids non-English output but Gemini drifts back to the template's
    declared language whenever the business name is in that language,
    and Speechmatics EN voices then produce unintelligible audio.
    """
    flagged: list[str] = []
    for scenario_name, scenario in (
        ("existing", parsed.scenarios_existing),
        ("new", parsed.scenarios_new),
    ):
        for idx, turn in enumerate(scenario.turns):
            for match in _WORD_RE.findall(turn.text):
                if match.lower() in _NON_ENGLISH_STOPWORDS:
                    flagged.append(f"{scenario_name}#{idx} '{turn.text[:60]}…': {match}")
                    break
    if flagged:
        sample = "; ".join(flagged[:3])
        raise ScriptBuilderError(
            f"generated script is not English (markers: {sample}). "
            "Speechmatics TTS preview only exposes EN voices — retry "
            "the generation."
        )

CallerMode = Literal["existing", "new"]


class _ScriptTurn(BaseModel):
    speaker: Literal["operator", "caller"]
    voice: Literal["sarah", "theo", "megan", "jack"]
    text: str = Field(min_length=2)


class _ScriptScenario(BaseModel):
    caller_name: str
    caller_phone_e164: str
    turns: list[_ScriptTurn]


class _ScriptResponse(BaseModel):
    """Two demo recordings — one for each Simulator button.

    The `existing` caller references a small piece of shared history with
    the business; the `new` caller is a first-time caller.
    """

    scenarios_existing: _ScriptScenario
    scenarios_new: _ScriptScenario


_DOMAIN_VOICE_HINTS: dict[str, str] = {
    "restaurant": "warm hospitality with sensory detail (the dish, the table, the room).",
    "dentist": "clinical-empathetic, restrained on pain description, factual on the procedure.",
    "bodyshop": "pragmatic-technical, plates and damage codes, tradesperson banter.",
    "hotel": "polished concierge tone, attention to the guest's stated occasion.",
    "salon": "personable and chatty, mentions the stylist by name.",
    "clinic": "calm clinical tone, careful with symptoms.",
    "legal": "formal but human, careful with confidentiality.",
    "realestate": "energetic, mentions the property reference / address.",
    "gym": "casual and motivating, mentions membership / class names.",
    "events": "high-energy, mentions the occasion and headcount.",
    "generic": "neutral business tone.",
}


SYSTEM_INSTRUCTION = (
    "You are the Afterglow Simulation Script Builder.\n\n"
    "Given a template (the operator's intake schema for an inbound phone "
    "call) and its action catalog, write TWO short realistic dialogues "
    "between an OPERATOR (front desk) and a CALLER:\n"
    "  - `scenarios_existing`: a RETURNING caller who already exists in "
    "the system. They reference a small piece of shared history with the "
    "business ('last month', 'the usual', 'when I came in for X'). They "
    "do NOT re-introduce themselves with a full bio.\n"
    "  - `scenarios_new`: a FIRST-TIME caller. They self-introduce with "
    "a full name and a fresh complication that requires the operator to "
    "collect every required field from scratch.\n\n"
    "Both scripts are read aloud by a TTS engine. They are visible to "
    "anyone judging this product — write something that would not "
    "embarrass anyone if played live.\n\n"
    "Hard rules:\n"
    "- ENGLISH only (UK or US, pick one and stay consistent within a "
    "scenario). Speechmatics TTS preview only exposes EN voices, and "
    "feeding them non-English text produces garbled audio that the ASR "
    "then transcribes as gibberish, breaking the entire demo.\n"
    "- This applies even when the template name, description, or domain "
    "is in another language. Examples: a template called \"Trattoria "
    "Bella Vita\" or \"Cabinet Dentaire Lumière\" still gets an "
    "ENGLISH dialogue. Translate the business label into a natural "
    "English phrasing (\"Bella Vita restaurant\", \"Lumière dental "
    "office\") or keep the proper noun as-is but switch to English "
    "immediately. Never write a full operator or caller turn in "
    "Italian, Spanish, French, German, or any non-English language. No "
    "\"buongiorno\", \"hola\", \"bonjour\", \"guten tag\" — write "
    "\"good morning\" or \"hello\" instead.\n"
    "- 6–12 turns per scenario, alternating operator / caller.\n"
    "- Pick two voices per scenario: one for operator, one for caller. "
    f"Allowed voices: {', '.join(_ALLOWED_VOICES)}. Use the SAME operator "
    "voice across both scenarios (front-desk identity is stable); switch "
    "the caller voice between scenarios so the two recordings sound like "
    "two different people.\n"
    "- Each dialogue must SURFACE enough information to plan at least "
    "2-3 actions from the template's `action_types`. Mention the "
    "relevant fields naturally inside the conversation — never recite "
    "them as a list.\n"
    "- Caller phone numbers: US format `+1 (555) AAA-BBBB`, never a real "
    "number.\n"
    "- End each scenario with a short goodbye exchange.\n\n"
    "Quality bar (apply rigorously):\n"
    "- Domain voice is distinctive — see the domain voice hint in the "
    "user prompt and lean into it.\n"
    "- Callers are people, not form-fillers. Give them at least ONE "
    "specific biographical detail. Short turns, hesitations are welcome "
    "('hmm', 'let me think').\n"
    "- No filler. Never write 'test test test', 'demo demo demo', "
    "'lorem ipsum', placeholder strings, or self-referential meta-talk "
    "like 'this is a demo call'.\n"
    "- Channel-dependent actions (sms, whatsapp, email, calendar, "
    "payment, review) only appear if the action catalog lists them for "
    "the template. The dialogue must justify why that channel is being "
    "used — don't drop them in randomly.\n"
)


def _format_catalog_entry_for_script(entry: action_catalog.ActionCatalogEntry) -> str:
    desc = entry.description.strip().replace("\n", " ")
    return f"  - {entry.key} — {entry.label}. {desc}"


def _build_user_prompt(template: Template) -> str:
    domain = template.domain_hint or "generic"
    voice_hint = _DOMAIN_VOICE_HINTS.get(domain, _DOMAIN_VOICE_HINTS["generic"])

    fields: list[dict[str, Any]] = list(template.fields_schema or [])
    required_fields = [
        f"  - {f.get('label', f.get('key'))} (key: {f.get('key')}, type: {f.get('type')})"
        for f in fields
        if isinstance(f, dict) and f.get("required")
    ]
    optional_fields = [
        f"  - {f.get('label', f.get('key'))} (key: {f.get('key')})"
        for f in fields
        if isinstance(f, dict) and not f.get("required")
    ]

    action_types: list[dict[str, Any]] = list(template.action_types or [])
    catalog_lines: list[str] = []
    for a in action_types:
        if not isinstance(a, dict):
            continue
        key = a.get("key")
        if not key:
            continue
        entry = action_catalog.CATALOG.get(key)
        if entry is None:
            # Template carries an action key the catalog does not know —
            # still surface it so the model sees what the template expects,
            # but it won't have label/description from the catalog.
            catalog_lines.append(f"  - {key} — {a.get('label', '(no catalog entry)')}.")
        else:
            catalog_lines.append(_format_catalog_entry_for_script(entry))

    parts: list[str] = [
        f"Template name: {template.name}",
        f"Domain: {domain}",
        f"Domain voice hint: {voice_hint}",
        f"Description: {template.description or '(none)'}",
        "",
        "Required fields the dialogue must ground:",
        "\n".join(required_fields) if required_fields else "  (none flagged required)",
    ]
    if optional_fields:
        parts.append("")
        parts.append("Optional fields you may incorporate when natural:")
        parts.append("\n".join(optional_fields))

    parts.append("")
    parts.append(
        "Action catalog the post-call planner can run on this template "
        "(make the dialogue surface 2-3 of these naturally):"
    )
    parts.append("\n".join(catalog_lines) if catalog_lines else "  (no actions)")
    parts.append("")
    parts.append(
        "Write BOTH scenarios now — `scenarios_existing` and "
        "`scenarios_new`. The existing-mode caller references shared "
        "history; the new-mode caller self-introduces."
    )
    return "\n".join(parts)


async def build_simulation_script(template: Template) -> _ScriptResponse:
    settings = get_settings()
    if not settings.google_api_key:
        raise ScriptBuilderError("GOOGLE_API_KEY is not set")

    from google import genai
    from google.genai import types as genai_types

    user_prompt = _build_user_prompt(template)

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
    if not parsed.scenarios_new.turns or not parsed.scenarios_existing.turns:
        raise ScriptBuilderError("at least one scenario has no turns")
    _validate_english_or_raise(parsed)
    return parsed


def _scenario_to_dict(scenario: _ScriptScenario) -> dict[str, Any]:
    return {
        "caller_name": scenario.caller_name,
        "caller_phone_e164": scenario.caller_phone_e164,
        "script_turns": [t.model_dump() for t in scenario.turns],
        "audio_url": None,
        "audio_status": "pending",
        "audio_generated_at": None,
        "audio_source": None,
    }


def script_response_to_simulation_config(parsed: _ScriptResponse) -> dict[str, Any]:
    """Project a `_ScriptResponse` into the JSONB shape stored on the template.

    Always emits the `scenarios.{existing,new}` shape that matches the seed
    templates. The legacy flat shape is no longer produced by the wizard.
    """
    return {
        "scenarios": {
            "existing": _scenario_to_dict(parsed.scenarios_existing),
            "new": _scenario_to_dict(parsed.scenarios_new),
        }
    }
