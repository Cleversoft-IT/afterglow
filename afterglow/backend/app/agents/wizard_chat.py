"""Wizard chat — agentic, draft-first template builder.

The single template-builder surface (the legacy one-shot textarea flow was
removed on 2026-05-17). The wizard behaves as an agent, not a form: at every
turn it decides whether the available context is rich enough to draft a
useful `TemplateWizardResponse` straight away, or whether one more focused
question would materially improve the result.

Conversation budget: 2-5 questions (hard ceiling 5). The very first user
message can already trigger a draft when it carries business type + call
flow. The server injects an "AGENT STATE" meta-block in the user prompt
telling the model how many questions it has already asked, and forces a
draft when the budget is exhausted.

Stateless: the client owns the conversation history and the running draft.
Each request carries `messages[]` (full history), `slots_filled` (optional
running notes the model may keep, no slot-filling pressure) and
`draft_partial` (best-effort template draft).

Hard rule for action keys: the model MUST pick action keys from the catalog
passed in `action_catalog_keys`. We surface that list in the prompt and
re-validate after the response — hallucinated keys are stripped from the
draft and surfaced via `proposed_actions_from_catalog`.

Fail-fast on missing GOOGLE_API_KEY / Gemini errors via `WizardChatError`;
the endpoint maps it to HTTP 502.
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

QUESTION_BUDGET = 5


class WizardChatError(RuntimeError):
    """Raised when the wizard chat agent cannot produce a response."""


class _WizardModelOutput(BaseModel):
    """Internal shape the LLM is asked to emit. We then build the public
    `WizardChatResponse` around it (adding validation, etc.).
    """

    assistant_message: str = Field(
        description=(
            "What to say to the user. Short and decisive. When drafting: "
            "one or two sentences confirming the draft. When asking: one "
            "focused question with concrete examples."
        )
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
            "Optional running summary of what the user has clarified so far "
            "— purely for your own bookkeeping. Suggested keys: "
            "`business_type`, `call_flow_summary`. Can be empty."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "0.0–1.0 self-estimate of draft quality. Not used to gate "
            "`ready`; only for telemetry."
        ),
    )
    ready: bool = Field(
        default=False,
        description=(
            "True when the draft contains a usable starting point: at least "
            "4 fields, at least 2 valid actions, plausible `name` / "
            "`description` / `domain_hint`. May be True on the very first "
            "turn if the user's message was already rich."
        ),
    )
    draft_partial: Optional[TemplateWizardResponse] = Field(
        default=None,
        description=(
            "Best-effort `TemplateWizardResponse`. When `ready=True` this "
            "MUST be a complete, valid template. When `ready=False` it can "
            "be `None` or partial."
        ),
    )


def _system_instruction(language: str, catalog_keys: list[str]) -> str:
    catalog_block = "\n".join(f"  - {k}" for k in catalog_keys)
    return (
        "You are the Afterglow Template Wizard.\n\n"
        "Afterglow is a human-first phone assistant: a human handles the "
        "call, and after the call the AI extracts operational fields, plans "
        "allowed follow-up actions, and writes a short next-call briefing.\n\n"
        f"Reply language: {language}\n\n"
        "Your job is to turn the user's business description into a "
        "practical template draft. You are an agent, not a form: you decide "
        "at every turn whether you have enough context to draft, or whether "
        "one more focused question would materially improve the result.\n\n"
        "Principles:\n"
        "- Prefer drafting over interrogating. Make reasonable assumptions "
        "and move forward; the user can refine fields and actions manually "
        "after.\n"
        "- Use business language. The user should feel they are describing "
        "how calls work, not configuring software.\n"
        "- Do NOT ask for the template name. Infer `name`, `description`, "
        "and `domain_hint` yourself from the business context.\n"
        "- Do NOT ask the user about technical internals: schemas, "
        "payloads, mock targets, privacy classes, ASR dictionaries, "
        "implementation details, or model configuration.\n\n"
        "Conversation budget (you are an agent, not a script — judge each "
        "turn):\n"
        "- If the very first user message is already rich (business type + "
        "call flow), draft immediately on turn 1 and set `ready=True`.\n"
        f"- If the context is vague, ask focused questions. Typical sessions need 2-{QUESTION_BUDGET} questions; never more than {QUESTION_BUDGET} (hard ceiling). The user prompt tells you how many questions you've already asked.\n"
        "- Each new question must materially change the resulting "
        "template. Don't pad. Don't ask multiple things at once.\n"
        f"- When the AGENT STATE block says the budget is exhausted, you MUST draft now, even with assumptions, regardless of remaining uncertainty.\n\n"
        "When generating a draft:\n"
        "- Create 4-8 useful fields that capture what an operator would "
        "normally write down after a call.\n"
        "- Use lowercase snake_case for field keys.\n"
        "- Use field types only from: string, integer, boolean, date, "
        "time, enum, string_list.\n"
        "- Use `options` for enum fields.\n"
        "- Use `depends_on` only when genuinely useful (e.g. time depends "
        "on date).\n"
        "- Create 2-4 follow-up actions using ONLY keys from the Action "
        "Catalog below. If the user describes an action that has no catalog "
        "entry, pick the closest match or omit it.\n"
        "- Use `execution_mode=\"auto\"` for safe routine actions and "
        "`execution_mode=\"manual-only\"` for actions that require human "
        "judgement (e.g. cancellations, insurance cases).\n"
        "- Add 1-3 `prompt_hints` only when they express real business "
        "rules.\n"
        "- Don't set `ready=True` unless the draft has at least 4 fields "
        "and at least 2 valid actions (unless the question budget forced "
        "you to draft).\n\n"
        "Assistant message style:\n"
        "- Short, decisive, in business voice.\n"
        "- When drafting: one or two sentences max, e.g. \"I drafted a "
        "restaurant booking template. You can adjust fields and actions "
        "before saving.\"\n"
        "- When asking: one clear question with 2-3 concrete examples if "
        "it helps the user answer.\n\n"
        "Action Catalog (use action.key VERBATIM):\n"
        f"{catalog_block}\n"
    )


def _user_prompt(payload: WizardChatRequest) -> str:
    questions_asked = sum(1 for m in payload.messages if m.role == "assistant")
    lines: list[str] = []
    lines.append("=== AGENT STATE ===")
    lines.append(f"Questions asked so far: {questions_asked} / {QUESTION_BUDGET}")
    if questions_asked >= QUESTION_BUDGET:
        lines.append(
            "BUDGET EXHAUSTED: you MUST draft now with your best "
            "assumptions. Do NOT ask another question."
        )
    elif questions_asked == 0:
        lines.append(
            "First turn. If the user's message is already rich enough "
            "(business type + call flow), draft immediately. Otherwise ask "
            "one focused question."
        )
    lines.append("")
    if payload.slots_filled:
        lines.append("=== NOTES SO FAR ===")
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
        "Decide: do you have enough context to draft a useful template? "
        "If yes, emit a complete draft with `ready=True` and a short "
        "confirmation message. If not (and budget allows), ask ONE focused "
        "question with concrete examples and set `ready=False`."
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

    # Safety net: ready=True must come with a draft. Down-grade contradictions.
    if parsed.ready and parsed.draft_partial is None:
        logger.warning("wizard_chat: ready=True without draft_partial; down-grading")
        parsed = parsed.model_copy(update={"ready": False})

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
