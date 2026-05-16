"""Template Builder Agent — Gemini structured-output.

Stand-alone agent (not part of the call pipeline) — drives the prompt-to-template
wizard from the dashboard. Uses Pydantic schema-bound structured output instead
of function calling, since the contract is deterministic.

Target model: settings.gemini_template_builder_model (default
gemini-3.1-flash-lite). Falls back to gemini_default_model on failure.

Fail-fast: per ``project_afterglow_decisions.md`` 1.ter (2026-05-16) there is
no offline stub. Missing GOOGLE_API_KEY or repeated Gemini failures raise
``TemplateBuilderError`` and the wizard endpoint returns 502 with the reason.
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.schemas.templates import TemplateWizardResponse

logger = logging.getLogger("afterglow")


class TemplateBuilderError(RuntimeError):
    """Raised when the wizard cannot produce a TemplateWizardResponse."""


_SYSTEM_INSTRUCTION = (
    "You are the Template Builder Agent inside Afterglow.\n\n"
    "A small business owner describes their phone intake. Turn that description "
    "into a structured template the operator can review and save. The output "
    "must match the Pydantic schema `TemplateWizardResponse` exactly.\n\n"
    "Rules:\n"
    "- `name`: short, Title-case, in the requested language.\n"
    "- `description`: 1-2 sentences, in the requested language.\n"
    "- `domain_hint`: short keyword (e.g. 'restaurant', 'dentist', 'bodyshop', "
    "'salon', 'gelateria') — lowercase, no spaces.\n"
    "- `fields_schema`: 4-10 fields. Use lowercase snake_case keys. Allowed `type` "
    "values: `string, integer, boolean, date, time, enum, string_list`. For each "
    "field:\n"
    "  - `pii_class` is one of `none|contact|health|financial|identity`. Use\n"
    "    'contact' for names/emails/phones, 'health' for symptoms/allergies/\n"
    "    diagnosis, 'financial' for amounts/iban/card, 'identity' for license\n"
    "    plates/IDs/fiscal codes, 'none' otherwise.\n"
    "  - `confidence_threshold` is optional and overrides the class default.\n"
    "  - `extractor_hint` is `regex|freeform|enum|llm_only`.\n"
    "  - `depends_on` lists field keys that must be present first (e.g. "
    "`booking_time` depends on `booking_date`).\n"
    "  - For `enum` types fill `options` with the valid values.\n"
    "- `action_types`: 2-5 follow-up actions. Use dot.namespaced keys "
    "(e.g. `booking.create`, `sms.send_reminder`). Set `execution_mode='manual-only'` "
    "for irreversible actions (cancellations, insurance claims, prescriptions); "
    "everything else is `auto`. For each action:\n"
    "  - `preconditions`: field keys required before invoking.\n"
    "  - `confidence_threshold`: 0.6-0.85, the planner floor.\n"
    "  - `mutates`: true when the action cannot be auto-retried.\n"
    "  - `evidence_required`: true for any user-visible side-effect.\n"
    "  - `payload_schema`: small JSONSchema (type=object) that the action "
    "executor will validate before calling the mock target.\n"
    "- `custom_dictionary`: 8-20 domain-specific terms an ASR engine should know.\n"
    "- `prompt_hints`: 1-4 rules of shape `{when, then}`. `when` is one of "
    "`always`, `field.<key> == '<value>'`, `field.<key> is null`, "
    "`field.<key> is not null`. `then` is a single-sentence instruction the "
    "analyzer should follow when the condition holds.\n"
)


async def build_template(description: str, language: str = "it") -> TemplateWizardResponse:
    """Generate a TemplateWizardResponse from a free-text business description.

    Tries the template-builder model first, then the default model. Raises
    ``TemplateBuilderError`` if both fail.
    """
    settings = get_settings()

    if not settings.google_api_key:
        raise TemplateBuilderError("GOOGLE_API_KEY is not set")

    user_prompt = (
        f"Output language: {language}\n\n"
        f"Business owner description:\n{description.strip()}\n"
    )

    last_error: Exception | None = None
    for model in _candidate_models(settings):
        try:
            return await _try_generate(model, user_prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "template_builder: model %s failed (%s) — trying next.", model, exc
            )
            last_error = exc

    raise TemplateBuilderError(
        f"every Gemini candidate failed: {last_error}"
    ) from last_error


def _candidate_models(settings: Any) -> list[str]:
    primary = settings.gemini_template_builder_model
    secondary = settings.gemini_default_model
    candidates: list[str] = []
    for m in (primary, secondary):
        if m and m not in candidates:
            candidates.append(m)
    return candidates


async def _try_generate(model: str, user_prompt: str) -> TemplateWizardResponse:
    from google import genai
    from google.genai import types as genai_types

    settings = get_settings()
    client = genai.Client(api_key=settings.google_api_key)

    resp = await client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=TemplateWizardResponse,
            temperature=0.3,
        ),
    )

    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("empty Gemini response")
    return TemplateWizardResponse.model_validate_json(text)
