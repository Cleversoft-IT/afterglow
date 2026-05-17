"""Wizard chat — multi-turn slot-filling for the template builder.

Replaces the one-shot textarea flow with a friendly conversation. The agent
asks one focused question per turn ("What kind of business?", "What facts
do you need to capture from each call?", ...), maintains a `slots_filled`
dictionary, and emits a candidate `TemplateWizardResponse` only once the
slots are complete enough.

Stateless: the client owns the conversation history and the running draft.
Each request carries `messages[]` (full history), `slots_filled` (server's
running view of what has been collected) and `draft_partial` (best-effort
template draft). The server returns the next assistant message + updated
slots + maybe a fresh draft.

Hard rule for action keys: the agent MUST pick action keys from the
catalog passed in `action_catalog_keys`. We surface that list in the prompt
and re-validate after the response — if Gemini hallucinates a key we drop
it from the draft and surface a validation issue.

Fail-fast on missing GOOGLE_API_KEY / Gemini errors via
`WizardChatError`; the endpoint maps it to HTTP 502.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.agents import template_validator
from app.config import get_settings
from app.integrations import action_catalog
from app.schemas.templates import (
    TemplateWizardResponse,
    WizardChatRequest,
    WizardChatResponse,
)

logger = logging.getLogger("afterglow")


class WizardChatError(RuntimeError):
    """Raised when the wizard chat agent cannot produce a response."""


class _WizardModelOutput(BaseModel):
    """Internal shape the LLM is asked to emit. We then build the public
    `WizardChatResponse` around it (adding validation, etc.).
    """

    assistant_message: str = Field(
        description="The next thing to say to the user — one focused question or a wrap-up."
    )
    # `slots_filled` is typed as `Any` (not `dict[str, Any]`) because Gemini's
    # structured-output endpoint rejects any schema containing
    # `additionalProperties` — which Pydantic emits for `dict[str, Any]`.
    # `Any` produces an empty schema slot that Gemini treats as "any value";
    # the model still returns a JSON object literal in practice. We coerce
    # to a dict downstream before forwarding to the public response.
    slots_filled: Any = Field(
        default=None,
        description=(
            "Running JSON object of what has been collected so far. Allowed keys: "
            "`business_type`, `customer_facing_name`, `fields_required`, "
            "`fields_optional`, `actions_needed`, `dictionary_terms`, "
            "`special_rules`. Always echo back the full slots dict (merge, "
            "do not drop existing keys)."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "0.0–1.0 estimate of how complete the slots are. Above 0.85 means "
            "you have enough to emit a final TemplateWizardResponse."
        ),
    )
    ready: bool = Field(
        default=False,
        description="True only when confidence >= 0.85 and a draft is provided.",
    )
    draft_partial: Optional[TemplateWizardResponse] = Field(
        default=None,
        description=(
            "Best-effort TemplateWizardResponse. May be partial in early "
            "turns (empty fields_schema is OK if nothing has been collected "
            "yet). At ready=True this must be a complete, valid template."
        ),
    )


def _system_instruction(language: str, catalog_keys: list[str]) -> str:
    catalog_block = "\n".join(f"  - {k}" for k in catalog_keys)
    return (
        f"You are the Afterglow Template Builder, talking to a small business "
        f"owner who wants their phone calls captured and turned into actions.\n\n"
        f"Reply language: {language}\n\n"
        "Rules of engagement:\n"
        "- Ask ONE focused question per turn. Be friendly, do not lecture.\n"
        "- Build up the `slots_filled` dict turn after turn. Always merge with "
        "the previous slots — never drop a key that was set earlier.\n"
        "- Slots to collect (in approximate order):\n"
        "    1. `business_type` — what kind of business (restaurant, gym, ...)\n"
        "    2. `customer_facing_name` — short display name for the template\n"
        "    3. `fields_required` and `fields_optional` — list of dicts "
        "{key, label, type} for each field to extract; keys must be "
        "snake_case.\n"
        "    4. `actions_needed` — list of action keys. MUST be a subset of "
        "the Action Catalog below; if the user describes an action that has "
        "no catalog entry, propose the closest match and explain.\n"
        "    5. `special_rules` — optional 1–3 `{when, then}` prompt hints.\n"
        "- Confidence climbs as you collect slots. <0.30 = just business_type; "
        "0.50 = some fields; 0.75 = fields + actions; 0.85+ = ready to draft.\n"
        "- `ready` is True ONLY when confidence >= 0.85 AND `draft_partial` "
        "is a fully-formed TemplateWizardResponse.\n"
        "- When `ready=True`, also write a `draft_partial` that the operator "
        "can save directly: every action.key must be from the catalog below; "
        "every field.key must be snake_case; `prompt_hints` are optional.\n"
        "- Output `ready=False` and a focused next question until you have "
        "enough information.\n\n"
        "Action Catalog (use action.key VERBATIM):\n"
        f"{catalog_block}\n"
    )


def _user_prompt(payload: WizardChatRequest) -> str:
    lines: list[str] = []
    if payload.slots_filled:
        lines.append("=== SLOTS SO FAR ===")
        for k, v in payload.slots_filled.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
    if payload.draft_partial is not None:
        lines.append("=== DRAFT SO FAR ===")
        lines.append(payload.draft_partial.model_dump_json())
        lines.append("")
    lines.append("=== CONVERSATION ===")
    for turn in payload.messages:
        prefix = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{prefix}: {turn.content}")
    lines.append("")
    lines.append(
        "Continue the conversation. Update slots_filled with anything the "
        "latest user message contributed, decide if you are ready, and reply "
        "with one focused next question (or the final wrap-up if ready)."
    )
    return "\n".join(lines)


async def run_wizard_chat(payload: WizardChatRequest) -> WizardChatResponse:
    settings = get_settings()
    if not settings.google_api_key:
        raise WizardChatError("GOOGLE_API_KEY is not set")

    if not payload.messages:
        raise WizardChatError("messages[] cannot be empty")

    from google import genai
    from google.genai import types as genai_types

    catalog_keys = action_catalog.available_keys()

    client = genai.Client(api_key=settings.google_api_key)
    try:
        resp = await client.aio.models.generate_content(
            model=settings.gemini_template_builder_model or settings.gemini_default_model,
            contents=_user_prompt(payload),
            config=genai_types.GenerateContentConfig(
                system_instruction=_system_instruction(payload.language, catalog_keys),
                response_mime_type="application/json",
                response_schema=_WizardModelOutput,
                temperature=0.4,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise WizardChatError(f"Gemini call failed: {exc}") from exc

    text = (resp.text or "").strip()
    if not text:
        raise WizardChatError("Gemini returned an empty response")

    try:
        parsed = _WizardModelOutput.model_validate_json(text)
    except Exception as exc:  # noqa: BLE001
        raise WizardChatError(f"Gemini response failed schema validation: {exc}") from exc

    # Strip hallucinated action keys.
    proposed: list[str] = []
    if parsed.draft_partial is not None:
        valid_actions = []
        for a in parsed.draft_partial.action_types:
            if a.key in action_catalog.CATALOG:
                valid_actions.append(a)
            else:
                proposed.append(a.key)
                logger.info(
                    "wizard_chat: dropping hallucinated action key %s", a.key
                )
        parsed.draft_partial = parsed.draft_partial.model_copy(
            update={"action_types": valid_actions}
        )

    validation = None
    if parsed.ready and parsed.draft_partial is not None:
        try:
            validation = await template_validator.validate_template(parsed.draft_partial)
        except Exception as exc:  # noqa: BLE001
            logger.warning("wizard_chat: validation pass skipped (%s)", exc)

    slots_dict: dict[str, Any] = parsed.slots_filled if isinstance(parsed.slots_filled, dict) else {}

    return WizardChatResponse(
        assistant_message=parsed.assistant_message,
        slots_filled=slots_dict,
        confidence=parsed.confidence,
        ready=parsed.ready,
        draft_partial=parsed.draft_partial,
        validation=validation,
        proposed_actions_from_catalog=sorted(set(proposed)),
    )
