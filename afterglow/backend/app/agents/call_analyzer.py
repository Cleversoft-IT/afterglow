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
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.agents.pii_policy import PII_THRESHOLDS
from app.agents.prompt_hint_eval import applicable_hints
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
    # `payload` is typed as `Any` (not `dict[str, Any]`) because Gemini's
    # structured-output endpoint rejects any schema containing
    # `additionalProperties` — which Pydantic emits for `dict[str, Any]`.
    # `Any` generates an empty schema slot, which Gemini accepts and treats
    # as "any value"; the model still returns a JSON object literal in
    # practice. Downstream consumers must `isinstance(payload, dict)` before
    # treating it as a mapping.
    payload: Any = Field(
        default=None,
        description=(
            "Action arguments as a JSON object whose keys match the action's "
            'payload_schema when present. Example: {"party_size": 4, '
            '"booking_time": "20:30"}. Use null when there are no arguments.'
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


_PII_THRESHOLD_TABLE = ", ".join(
    f"{cls}={thr:.2f}" for cls, thr in PII_THRESHOLDS.items() if cls != "none"
)


_SYSTEM_INSTRUCTION = f"""You are the post-call analyzer for Afterglow, a human-first AI dialer.

A human operator just finished a phone call. You receive:
- the diarized transcript
- the template (fields the operator wants extracted, actions they pre-approved
  as auto-executable, plus contextual prompt hints)
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
   Populate `payload` as a JSON object whose keys match the action's
   payload_schema (when present). For each planned action include at least one
   `evidence` span when the action's `evidence_required` is true.
4. Write next_call_briefing: 1-3 sentences for the operator who will pick up
   the next call from this caller. Combine prior_facts with what was just
   learned. No headers, no bullet points. Write in the detected language.

Field extraction rules:
- Each FieldDefinition declares a `pii_class` and may declare a
  `confidence_threshold`. PII class defaults to: {_PII_THRESHOLD_TABLE}. If a
  field declares its own threshold, use that instead.
- Be conservative when an extraction crosses a class threshold; prefer to
  omit the field rather than guess.
- `extractor_hint` is a hint about how the value typically appears in
  conversation: regex (well-defined token e.g. license plate, date),
  freeform (natural language), enum (one of `options`), llm_only (semantic).
  Use it to calibrate confidence — regex-style fields should be near 1.0
  when matched cleanly, freeform around 0.7-0.9.
- `depends_on` lists field keys that must be present and grounded before
  this field is considered valid. If a dependency is missing, still extract
  the dependent field if you can but the downstream coercer will move it
  to manual_review.

PII gating (post-process — for your awareness):
- A separate sanitizer runs after you, redacting `next_call_briefing` for
  every field whose pii_class is not "none". You do NOT need to write
  redaction placeholders yourself — write the briefing normally with the
  raw values. The sanitizer will scrub them based on the same thresholds
  above.

Action planning rules:
- Respect each action's `preconditions`: do not plan an action if any
  precondition field is missing or below its confidence threshold.
- Respect `confidence_threshold` on the action itself: it is the floor for
  the action's own confidence (your reading of how strongly the call
  supports invoking it), NOT a copy of the field threshold.
- `mutates: true` means the action is irreversible — never plan it
  speculatively. `evidence_required: true` means you MUST include evidence."""


def _user_prompt(
    *,
    transcript_text: str,
    template_name: str,
    fields_schema: list[dict[str, Any]],
    action_types: list[dict[str, Any]],
    prompt_hints: Optional[list[dict[str, Any]]],
    prior_structured: dict[str, Any],
    domain_hint: str,
    prior_facts: str,
) -> str:
    # Explicit section markers prevent the model from confusing prior facts
    # with the current call. Flat concatenation used to bleed: Gemini would
    # occasionally cite a 6-months-old detail as if it had just been heard.

    # Evaluate prompt_hints rules against the caller's prior structured
    # fields. Only the `then` strings of matching rules end up in the
    # prompt — the operator's free-form intent stays predictable.
    hint_lines = applicable_hints(prompt_hints, prior_structured)
    hints_section = "\n".join(f"- {line}" for line in hint_lines) or "(none)"

    return (
        "=== DOMAIN & TEMPLATE ===\n"
        f"Domain: {domain_hint}\n"
        f"Template: {template_name}\n\n"
        f"fields_schema:\n{json.dumps(fields_schema, ensure_ascii=False)}\n\n"
        f"action_types:\n{json.dumps(action_types, ensure_ascii=False)}\n\n"
        "active prompt hints (evaluated against prior structured facts):\n"
        f"{hints_section}\n\n"
        "=== PRIOR FACTS (structured/RAG) ===\n"
        f"{prior_facts or '(no prior facts)'}\n\n"
        "=== CURRENT TRANSCRIPT ===\n"
        f"{transcript_text}\n"
    )


@dataclass
class TokenUsage:
    """Token-count snapshot extracted from a Gemini response's usage_metadata.

    Both fields are Optional[int] because the Gemini SDK does not always
    populate them (e.g. cached responses). The orchestrator writes them
    straight onto `audit_log.input_tokens` / `output_tokens`.
    """

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    @classmethod
    def from_gemini(cls, resp: Any) -> "TokenUsage":
        usage = getattr(resp, "usage_metadata", None)
        if usage is None:
            return cls()
        return cls(
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )


async def analyze_call(
    *,
    transcript_text: str,
    template_name: str,
    fields_schema: list[dict[str, Any]],
    action_types: list[dict[str, Any]],
    prompt_hints: Optional[list[dict[str, Any]]] = None,
    prior_structured: Optional[dict[str, Any]] = None,
    domain_hint: str,
    prior_facts: str,
) -> tuple[CallAnalysis, TokenUsage]:
    """Run the single Gemini call and return the parsed analysis + token usage.

    Fail-fast: missing GOOGLE_API_KEY, network/SDK exceptions, empty
    responses, and schema mismatches all raise `CallAnalysisError`. The
    orchestrator turns the exception into a `Call.status="failed"` row with
    the reason surfaced to the UI. There is no offline stub on purpose
    (see `.claude/memory/project_afterglow_decisions.md` 1.ter).
    """
    if not settings.google_api_key:
        raise CallAnalysisError("GOOGLE_API_KEY is not set")

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
        prior_structured=prior_structured or {},
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
        raise CallAnalysisError(f"Gemini call failed: {exc}") from exc

    text = (resp.text or "").strip()
    if not text:
        raise CallAnalysisError("Gemini returned empty response")

    try:
        return CallAnalysis.model_validate_json(text), TokenUsage.from_gemini(resp)
    except Exception as exc:  # noqa: BLE001
        raise CallAnalysisError(f"Gemini response failed schema validation: {exc}") from exc


class CallAnalysisError(RuntimeError):
    """Raised when the analyzer cannot produce a CallAnalysis.

    The orchestrator catches this, marks the Call as failed, and writes
    the audit step with `status="error"`. No stub data ever leaks into the
    persistence layer.
    """
