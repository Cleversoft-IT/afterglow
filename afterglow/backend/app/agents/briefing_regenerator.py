"""Rewrite a single call's next-call briefing without re-running the full pipeline.

Why a separate module instead of reusing `call_analyzer.analyze_call`:
- `analyze_call` emits a full `CallAnalysis` (fields + actions + briefing),
  which would waste tokens on a structured output we don't need and would
  tempt callers to also overwrite `ExtractedFields.fields` and re-trigger
  the planner. The regenerate endpoint is explicitly scoped to the briefing.
- The shape mirrors `orchestrator._summarize_to_english`: a small Gemini
  call (~120 output tokens) with a tight system instruction. Same pattern,
  different prompt.

Fail-fast: missing key / empty response / SDK error raises. The caller
(`api.calls.regenerate_summary`) catches and returns 502 with the reason
so the UI can surface a Snackbar error without silent degradation.
"""
from __future__ import annotations

from typing import Optional

from app.agents.call_analyzer import TokenUsage
from app.config import get_settings

settings = get_settings()


_LANGUAGE_LABELS = {
    "en": "English",
    "it": "Italian",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
}


def _language_label(code: Optional[str]) -> str:
    if not code:
        return "English"
    return _LANGUAGE_LABELS.get(code.lower(), code)


_SYSTEM_INSTRUCTION = """You rewrite the next-call briefing the receptionist will read
on the caller's card the next time this number rings. Keep it operator-
actionable: who the caller is, what they care about, what to confirm or
flag on the next call.

Constraints:
- 1 or 2 short sentences, max 60 words.
- Write in {language}.
- No greeting, no headers, no bullet points.
- Reference concrete facts from the transcript and prior history when
  they would change how the receptionist handles the next call.
- Do not invent details that are not in the transcript or prior facts.
- Do not mention specific calendar dates ("9 May", "April 22") — the
  briefing may be read days or weeks later; use relative language
  ("last time", "recently", "the previous booking") instead.

Output the briefing text only.
"""


async def regenerate_briefing(
    *,
    transcript_text: str,
    fields: dict,
    intent: Optional[str],
    sentiment: Optional[str],
    language: Optional[str],
    prior_facts: str,
) -> tuple[str, TokenUsage]:
    """Run the briefing-only Gemini call. Returns (briefing_text, usage).

    Raises RuntimeError on missing `GOOGLE_API_KEY` or empty Gemini response.
    """
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY not set")

    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.google_api_key)

    fields_block = (
        "\n".join(f"- {k}: {v}" for k, v in fields.items())
        if fields
        else "(none)"
    )
    prior_block = prior_facts.strip() if prior_facts else "(no prior calls)"

    user_prompt = (
        f"TRANSCRIPT:\n{transcript_text.strip()}\n\n"
        f"EXTRACTED FIELDS:\n{fields_block}\n\n"
        f"INTENT: {intent or 'unknown'}\n"
        f"SENTIMENT: {sentiment or 'unknown'}\n\n"
        f"PRIOR FACTS:\n{prior_block}\n"
    )

    resp = await client.aio.models.generate_content(
        model=settings.gemini_default_model,
        contents=user_prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION.format(
                language=_language_label(language)
            ),
            temperature=0.1,
            max_output_tokens=160,
        ),
    )
    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("empty briefing response")
    return text, TokenUsage.from_gemini(resp)
