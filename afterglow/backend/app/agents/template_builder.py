"""Template Builder Agent — Gemini structured-output.

Stand-alone agent (not part of the call pipeline) — drives the prompt-to-template
wizard from the dashboard. Uses Pydantic schema-bound structured output instead
of function calling, since the contract is deterministic.

Target model: settings.gemini_template_builder_model (default
gemini-3-flash-preview, paid-tier free on Google AI Studio). Falls back to
gemini_default_model on failure, and finally to a hand-crafted barbershop
template if Gemini is unreachable or no API key is set.
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.schemas.templates import TemplateWizardResponse

logger = logging.getLogger("afterglow")


_SYSTEM_INSTRUCTION = (
    "You are the Template Builder Agent inside Afterglow.\n\n"
    "A small business owner describes their phone intake. Turn that description "
    "into a structured template the operator can review and save. Rules:\n"
    "- name: short, in the requested language. Title-case.\n"
    "- description: 1-2 sentences, in the requested language.\n"
    "- fields_schema: 4-10 fields. Use lowercase snake_case keys. "
    "Allowed types: string, integer, boolean, date, time, enum, string_list. "
    "Mark health/financial/PII fields as sensitive:true. "
    "For enum types fill `options` with the valid values.\n"
    "- action_types: 2-5 follow-up actions. Use dot.namespaced keys "
    "(e.g. booking.create, sms.send_reminder). "
    "Set execution_mode='manual-only' for irreversible or sensitive actions "
    "(cancellations, insurance claims, prescriptions). All other actions are 'auto'.\n"
    "- custom_dictionary: 8-20 domain-specific terms an ASR engine should know "
    "(slang, brand names, jargon) in the requested language.\n"
    "- prompt_hints: 1-3 sentences guiding the Extraction Agent on edge cases "
    "and ambiguous wording it should expect in this domain.\n"
)


async def build_template(description: str, language: str = "it") -> TemplateWizardResponse:
    """Generate a TemplateWizardResponse from a free-text business description.

    Tries the template-builder model first, then the default model, then the
    offline stub. Each fallback is logged so the operator sees what happened.
    """
    settings = get_settings()

    if not settings.google_api_key:
        logger.info("template_builder: GOOGLE_API_KEY not set — returning stub.")
        return _fake_barbershop_template(description)

    user_prompt = (
        f"Output language: {language}\n\n"
        f"Business owner description:\n{description.strip()}\n"
    )

    for model in _candidate_models(settings):
        result = await _try_generate(model, user_prompt)
        if result is not None:
            return result

    logger.warning(
        "template_builder: every Gemini candidate failed — returning offline stub."
    )
    return _fake_barbershop_template(description)


def _candidate_models(settings: Any) -> list[str]:
    primary = settings.gemini_template_builder_model
    secondary = settings.gemini_default_model
    candidates: list[str] = []
    for m in (primary, secondary):
        if m and m not in candidates:
            candidates.append(m)
    return candidates


async def _try_generate(model: str, user_prompt: str) -> TemplateWizardResponse | None:
    from google import genai
    from google.genai import types as genai_types

    settings = get_settings()
    client = genai.Client(api_key=settings.google_api_key)

    try:
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("template_builder: model %s raised %s — trying next.", model, exc)
        return None

    text = (resp.text or "").strip()
    if not text:
        logger.warning("template_builder: model %s returned empty text — trying next.", model)
        return None

    try:
        return TemplateWizardResponse.model_validate_json(text)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "template_builder: model %s output failed schema validation (%s) — trying next.",
            model,
            exc,
        )
        return None


def _fake_barbershop_template(description: str) -> TemplateWizardResponse:
    return TemplateWizardResponse(
        name="Barbershop appointments",
        description=description[:200],
        fields_schema=[
            {"key": "customer_name", "type": "string", "label": "Customer name", "required": True},
            {"key": "service", "type": "enum", "label": "Service", "options": ["haircut", "beard", "shave", "color"], "required": True},
            {"key": "preferred_date", "type": "date", "label": "Preferred date"},
            {"key": "preferred_time", "type": "time", "label": "Preferred time"},
            {"key": "preferred_barber", "type": "string", "label": "Preferred barber"},
            {"key": "callback_channel", "type": "enum", "label": "Confirmation", "options": ["sms", "whatsapp", "none"]},
        ],
        action_types=[
            {"key": "appointment.create", "label": "Create appointment", "execution_mode": "auto", "mock_target": "booking"},
            {"key": "sms.send_reminder", "label": "Send SMS reminder", "execution_mode": "auto", "mock_target": "whatsapp"},
            {"key": "appointment.cancel", "label": "Cancel appointment", "execution_mode": "manual-only", "mock_target": "booking"},
        ],
        custom_dictionary=[
            "fade", "skin fade", "shape-up", "beard trim", "buzz cut",
            "barba", "rifinitura", "shampoo", "balsamo",
        ],
        prompt_hints=(
            "Customers often request a specific barber by first name. "
            "If preferred_barber is missing, do NOT request a missing-field action — "
            "the shop will assign one. Confirm time in 24h format."
        ),
    )
