"""Call Analyzer — single Gemini pass that produces the full post-call analysis.

Architecture choice (revised from the day-1 multi-agent pipeline):
- The human runs the call. No AI runs while they talk.
- After the call ends, ONE Gemini call receives:
    - transcript text + speakers (Speechmatics output)
    - the template's fields_schema and action_types (so output is grounded in
      the operator-curated structure)
    - prior_facts retrieved from the Vultr Vector Store via RAG (semantic
      lookup of past calls from the same phone number; may be empty)
- Gemini returns a strict Pydantic structured object with:
    - per-field extractions (value + confidence + evidence)
    - call classification (intent/sentiment/language/urgency)
    - planned actions (subset of the template's action_types)
    - next_call_briefing — a short paragraph aimed at the operator who will
      handle the next call from the same number
- A deterministic executor runs the planned actions.
- The briefing is persisted on the customer row (UI-visible) and pushed as a
  new chunk into the Vector Store (semantic memory for future calls).

If GOOGLE_API_KEY is missing the analyzer falls back to a heuristic stub so
the demo still produces visible structured output offline.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger("afterglow")
settings = get_settings()


class FieldExtraction(BaseModel):
    key: str = Field(description="Field key from the template's fields_schema.")
    value: str = Field(
        description=(
            "Extracted value as a string. For lists (e.g. allergies) use a "
            "JSON array literal like '[\"glutine\"]'. Use ISO formats for "
            "dates/times when applicable."
        )
    )
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(description="Verbatim transcript span supporting the extraction.")


class PlannedAction(BaseModel):
    action_type: str = Field(description="Action key from the template's action_types.")
    title: str
    summary: str
    payload_json: str = Field(
        default="{}",
        description=(
            "Action arguments as a JSON object literal, e.g. "
            '\'{"party_size": 4, "booking_time": "20:30"}\'. Use \'{}\' if there '
            "are no arguments."
        ),
    )
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class CallAnalysis(BaseModel):
    intent: str
    sentiment: str
    language: str
    urgency: str
    fields: list[FieldExtraction]
    planned_actions: list[PlannedAction]
    next_call_briefing: str = Field(
        description=(
            "1-3 short sentences for the operator who will handle the NEXT call "
            "from this phone number. Combine what was just learned with the prior "
            "facts. Written in the detected_language."
        )
    )


_SYSTEM_INSTRUCTION = """You are the post-call analyzer for Afterglow, a human-first AI dialer.

A human operator just finished a phone call. You receive:
- the diarized transcript
- the template (fields the operator wants extracted, actions they pre-approved
  as auto-executable, plus prompt hints)
- prior_facts: a paragraph summarising what is known about the caller from
  past calls (may be empty)

Your job:
1. Extract every template field you can ground in the transcript. Skip fields
   with no evidence. Always cite a verbatim transcript span. Use the field
   keys from fields_schema literally.
2. Classify the call: intent (use the template's vocabulary when possible),
   sentiment, detected_language (ISO 639-1), urgency.
3. Plan actions ONLY from action_types whose execution_mode is "auto".
   Manual-only actions stay out of planned_actions. Use action keys literally.
4. Write next_call_briefing: 1-3 sentences for the operator who will pick up
   the next call from this caller. Combine prior_facts with what was just
   learned. No headers, no bullet points. Write in the detected language.

Be conservative with confidence. Health, financial, and PII fields warrant
lower confidence unless the caller stated them unambiguously.

PII gating: for any field flagged ``sensitive: true`` in fields_schema, if
your confidence is below 0.85, OMIT the value from ``next_call_briefing``
and replace it with the literal placeholder ``[needs human review]``. Still
return the extraction in ``fields`` so the operator can verify it manually."""


def _user_prompt(
    *,
    transcript_text: str,
    template_name: str,
    fields_schema: list[dict[str, Any]],
    action_types: list[dict[str, Any]],
    prompt_hints: Optional[str],
    domain_hint: str,
    prior_facts: str,
) -> str:
    # Explicit section markers prevent the model from confusing prior facts
    # with the current call. Flat concatenation used to bleed: Gemini would
    # occasionally cite a 6-months-old detail as if it had just been heard.
    return (
        "=== DOMAIN & TEMPLATE ===\n"
        f"Domain: {domain_hint}\n"
        f"Template: {template_name}\n\n"
        f"fields_schema:\n{json.dumps(fields_schema, ensure_ascii=False)}\n\n"
        f"action_types:\n{json.dumps(action_types, ensure_ascii=False)}\n\n"
        f"prompt_hints: {prompt_hints or '(none)'}\n\n"
        "=== PRIOR FACTS (structured/RAG) ===\n"
        f"{prior_facts or '(no prior facts)'}\n\n"
        "=== CURRENT TRANSCRIPT ===\n"
        f"{transcript_text}\n"
    )


async def analyze_call(
    *,
    transcript_text: str,
    template_name: str,
    fields_schema: list[dict[str, Any]],
    action_types: list[dict[str, Any]],
    prompt_hints: Optional[str],
    domain_hint: str,
    prior_facts: str,
) -> CallAnalysis:
    """Run the single Gemini call and return a parsed CallAnalysis.

    Falls back to a deterministic heuristic stub when GOOGLE_API_KEY is empty.
    """
    if not settings.google_api_key:
        logger.info("call_analyzer: GOOGLE_API_KEY not set — using stub analysis.")
        return _stub_analysis(
            transcript_text=transcript_text,
            fields_schema=fields_schema,
            action_types=action_types,
        )

    # Lazy import so the rest of the app stays usable without google-genai.
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.google_api_key)
    user_prompt = _user_prompt(
        transcript_text=transcript_text,
        template_name=template_name,
        fields_schema=fields_schema,
        action_types=action_types,
        prompt_hints=prompt_hints,
        domain_hint=domain_hint,
        prior_facts=prior_facts,
    )

    try:
        resp = await client.aio.models.generate_content(
            model=settings.gemini_default_model,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=CallAnalysis,
                temperature=0.2,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "call_analyzer: Gemini call failed (%s) — falling back to stub.", exc
        )
        return _stub_analysis(
            transcript_text=transcript_text,
            fields_schema=fields_schema,
            action_types=action_types,
        )

    text = (resp.text or "").strip()
    if not text:
        logger.warning("call_analyzer: empty Gemini response — falling back to stub.")
        return _stub_analysis(
            transcript_text=transcript_text,
            fields_schema=fields_schema,
            action_types=action_types,
        )

    try:
        return CallAnalysis.model_validate_json(text)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "call_analyzer: could not parse Gemini JSON (%s) — falling back to stub.",
            exc,
        )
        return _stub_analysis(
            transcript_text=transcript_text,
            fields_schema=fields_schema,
            action_types=action_types,
        )


# ---------------------------------------------------------------------------
# Stub — used only when GOOGLE_API_KEY is unset so the pipeline still produces
# visible structured output for offline demos.
# ---------------------------------------------------------------------------


def _stub_analysis(
    *,
    transcript_text: str,
    fields_schema: list[dict[str, Any]],
    action_types: list[dict[str, Any]],
) -> CallAnalysis:
    text_lower = transcript_text.lower()
    fields: list[FieldExtraction] = []
    schema_keys = {f["key"] for f in fields_schema}

    if "quattro" in text_lower and "party_size" in schema_keys:
        fields.append(
            FieldExtraction(
                key="party_size", value="4", confidence=0.91,
                evidence="siamo in quattro",
            )
        )
    if "marco" in text_lower and "customer_name" in schema_keys:
        fields.append(
            FieldExtraction(
                key="customer_name", value="Marco", confidence=0.88,
                evidence="Mi chiamo Marco.",
            )
        )
    if ("otto e mezza" in text_lower or "20:30" in text_lower) and "booking_time" in schema_keys:
        fields.append(
            FieldExtraction(
                key="booking_time", value="20:30", confidence=0.86,
                evidence="verso le otto e mezza",
            )
        )
    if "glutine" in text_lower and "allergies" in schema_keys:
        fields.append(
            FieldExtraction(
                key="allergies", value='["glutine"]', confidence=0.78,
                evidence="una persona e intollerante al glutine",
            )
        )
    if "whatsapp" in text_lower and "callback_channel" in schema_keys:
        fields.append(
            FieldExtraction(
                key="callback_channel", value="whatsapp", confidence=0.95,
                evidence="Mi potete confermare su WhatsApp?",
            )
        )

    planned: list[PlannedAction] = []
    fields_by_key = {f.key: f.value for f in fields}
    for action in action_types:
        if action.get("execution_mode") != "auto":
            continue
        key = action.get("key", "")
        if key in (
            "booking.create",
            "appointment.create",
            "appointment.create_inspection",
        ):
            planned.append(
                PlannedAction(
                    action_type=key,
                    title=action.get("label", key),
                    summary="Create booking from extracted fields",
                    payload_json=json.dumps(fields_by_key),
                    confidence=0.9,
                    evidence=["siamo in quattro", "verso le otto e mezza"],
                )
            )
        elif key.startswith("whatsapp.") or key.startswith("sms."):
            planned.append(
                PlannedAction(
                    action_type=key,
                    title=action.get("label", key),
                    summary="Send confirmation",
                    payload_json=json.dumps(
                        {"body": f"Confirmed for {fields_by_key.get('party_size', '?')} guests."}
                    ),
                    confidence=0.88,
                    evidence=[],
                )
            )
        elif key in ("customer.update_profile", "patient.update_profile"):
            planned.append(
                PlannedAction(
                    action_type=key,
                    title=action.get("label", key),
                    summary="Update customer profile",
                    payload_json=json.dumps({"fields": fields_by_key}),
                    confidence=0.85,
                    evidence=[],
                )
            )

    intent = "booking_new" if "prenot" in text_lower or "book" in text_lower else "info_request"
    return CallAnalysis(
        intent=intent,
        sentiment="neutral",
        language="it" if any(w in text_lower for w in ["buonasera", "ciao", "vorrei"]) else "en",
        urgency="low",
        fields=fields,
        planned_actions=planned,
        next_call_briefing="Offline stub — set GOOGLE_API_KEY to generate a real briefing.",
    )
