"""Template Builder Agent — Gemini 3 Flash Preview + structured output.

Stand-alone agent (not part of the call pipeline) — drives the prompt-to-template
wizard from the dashboard. Uses Pydantic schema-bound structured output instead
of function calling, since the contract is deterministic.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas.templates import TemplateWizardResponse


_SYSTEM_INSTRUCTION = (
    "You are the Template Builder Agent inside Afterglow.\n\n"
    "A small business owner describes their phone intake. Turn that description "
    "into a structured template:\n"
    "- fields_schema: 4-10 fields. Mark health/financial/PII as sensitive:true.\n"
    "- action_types: 2-5 actions. Use execution_mode='manual-only' for "
    "irreversible or sensitive actions (cancellations, insurance, prescriptions).\n"
    "- custom_dictionary: 8-20 domain-specific terms helpful for ASR.\n"
    "- prompt_hints: 1-3 sentences for the Extraction Agent.\n"
)


async def build_template(description: str, language: str = "it") -> TemplateWizardResponse:
    """Generate a TemplateWizardResponse from a free-text business description.

    Day 1: returns a hand-crafted barbershop template so the wizard UI can be
    demoed end-to-end without Gemini credentials. Day 4: switch to real Gemini 3
    Flash Preview with response_schema=TemplateWizardResponse.
    """
    settings = get_settings()

    if not settings.google_api_key:
        return _fake_barbershop_template(description)

    # TODO day 4: real call.
    # from google import genai
    # client = genai.Client(api_key=settings.google_api_key)
    # resp = client.models.generate_content(
    #     model=settings.gemini_template_builder_model,
    #     contents=f"{_SYSTEM_INSTRUCTION}\n\nUser description:\n{description}",
    #     config={
    #         "response_mime_type": "application/json",
    #         "response_schema": TemplateWizardResponse,
    #     },
    # )
    # return TemplateWizardResponse.model_validate_json(resp.text)
    return _fake_barbershop_template(description)


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
