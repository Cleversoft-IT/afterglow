"""Tests for the agentic wizard chat agent.

Coverage:
- Schema invariants (no `additionalProperties`, all catalog keys in prompt).
- Prompt content (no obsolete fields, agentic markers present, no template
  name asks).
- User-prompt meta-block (questions asked count, budget ceiling marker,
  first-turn marker).
- Behavior with a mocked Gemini client (rich input → draft, vague input →
  question, hallucinated actions stripped, contradictory ready=True without
  draft is down-graded).

Gemini itself is never hit: behavior tests monkeypatch `genai.Client` with
a fake that returns a pre-built `_WizardModelOutput`.
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.agents.wizard_chat import (
    QUESTION_BUDGET,
    WizardChatError,
    _WizardModelOutput,
    _questions_asked_after_user_started,
    _system_instruction,
    _user_prompt,
    run_wizard_chat,
)
from app.integrations import action_catalog
from app.schemas.templates import (
    ActionDefinitionDraft,
    FieldDefinition,
    TemplateWizardResponse,
    WizardChatRequest,
    WizardChatTurn,
)


# ---------------------------------------------------------------------------
# Schema invariants
# ---------------------------------------------------------------------------


def _all_entries() -> list[action_catalog.ActionCatalogEntry]:
    return [action_catalog.CATALOG[k] for k in action_catalog.available_keys()]


def test_system_instruction_lists_every_catalog_key():
    instruction = _system_instruction(
        language="en",
        catalog_entries=_all_entries(),
        known_domains=action_catalog.KNOWN_DOMAINS,
    )
    for key in action_catalog.available_keys():
        assert key in instruction, f"system instruction missing catalog key {key}"


def test_system_instruction_contains_label_kind_and_domains_per_entry():
    """Every catalog entry must surface label, integration kind tag (MOCK/LIVE)
    and its compatible_domains so Gemini can match user intent → action_key
    with awareness of which actions fit which business verticals.
    """
    instruction = _system_instruction(
        language="en",
        catalog_entries=_all_entries(),
        known_domains=action_catalog.KNOWN_DOMAINS,
    )
    for entry in _all_entries():
        assert entry.label in instruction, f"missing label for {entry.key}"
    assert "[MOCK," in instruction, "missing MOCK marker on mock_external entries"
    assert "[LIVE," in instruction, "missing LIVE marker on internal_real entries"
    assert "domains:" in instruction, "missing compatible_domains surface"


def test_system_instruction_lists_known_domains():
    instruction = _system_instruction(
        language="en",
        catalog_entries=_all_entries(),
        known_domains=action_catalog.KNOWN_DOMAINS,
    )
    # Every new domain must be advertised so Gemini can assign it as a hint.
    for domain in ("hotel", "salon", "clinic", "legal", "realestate", "gym", "events"):
        assert domain in instruction, f"missing domain {domain}"


def test_system_instruction_hard_rule_covers_new_buckets():
    instruction = _system_instruction(
        language="en",
        catalog_entries=_all_entries(),
        known_domains=action_catalog.KNOWN_DOMAINS,
    )
    for prefix in ("whatsapp.*", "sms.*", "email.*", "calendar.*", "payment.*", "review.*"):
        assert prefix in instruction, f"HARD RULE missing prefix {prefix}"
    assert "channel-dependent" in instruction.lower()
    assert "operational" in instruction.lower()


def test_empty_messages_raises():
    payload = WizardChatRequest(messages=[])
    with pytest.raises(WizardChatError):
        asyncio.run(run_wizard_chat(payload))


def test_wizard_model_output_schema_has_no_additional_properties():
    schema_json = _WizardModelOutput.model_json_schema()

    def _walk(node):
        if isinstance(node, dict):
            assert "additionalProperties" not in node, (
                "_WizardModelOutput JSON schema contains additionalProperties, "
                "which Gemini does not accept."
            )
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(schema_json)


# ---------------------------------------------------------------------------
# Prompt content
# ---------------------------------------------------------------------------


def _instruction() -> str:
    return _system_instruction(
        language="en",
        catalog_entries=_all_entries(),
        known_domains=action_catalog.KNOWN_DOMAINS,
    )


def test_system_instruction_does_not_ask_for_template_name():
    instruction = _instruction()
    # The agent must be explicitly told NOT to ask for the template name.
    assert "Do NOT ask for the template name" in instruction
    # Obsolete slot key must be gone entirely.
    assert "customer_facing_name" not in instruction
    # No asking patterns should appear (only the negation above).
    forbidden_asks = [
        "name the template",
        "what should the template be called",
        "what name should",
        "give the template a name",
    ]
    lowered = instruction.lower()
    for needle in forbidden_asks:
        assert needle.lower() not in lowered, (
            f"system instruction should not ask for the template name: found {needle!r}"
        )


def test_system_instruction_drops_obsolete_fields():
    instruction = _instruction()
    forbidden = [
        "dictionary_terms",
        "pii_class",
        "sensitive",
        "custom_dictionary",
        "mock_target",
        "simulation_config",
        "Slots to collect",
        "Confidence climbs",
    ]
    for needle in forbidden:
        assert needle not in instruction, (
            f"system instruction should not mention obsolete field {needle!r}"
        )


def test_system_instruction_mentions_agentic_draft_first():
    instruction = _instruction()
    # The "Prefer drafting over interrogating" line was replaced by an
    # explicit Integration discovery rule that gates channel actions
    # behind a clarification turn. The agentic framing and budget ceiling
    # are still there.
    assert "Integration discovery" in instruction
    assert "agent, not a form" in instruction
    assert "ready=True" in instruction
    assert "5" in instruction  # question budget ceiling


def test_system_instruction_forces_integration_discovery():
    instruction = _instruction()
    # Channel-dependent actions must not be drafted without an explicit
    # user confirmation about the channels in use.
    assert "whatsapp" in instruction.lower()
    assert "Never default to WhatsApp" in instruction


def test_mock_dispatch_keeps_new_bucket_action(monkeypatch):
    """Lock di non-regressione: una action key in un bucket nuovo
    (`payment.request_deposit` su un template hotel) deve sopravvivere al
    post-processing del wizard — il catalog la conosce, quindi
    `proposed_actions_from_catalog` resta vuoto."""
    hotel_draft = TemplateWizardResponse(
        name="Hotel reception",
        description="Phone calls for a small boutique hotel.",
        domain_hint="hotel",
        fields_schema=[
            FieldDefinition(key="guest_name", type="string", label="Guest name", required=True),
            FieldDefinition(key="check_in_date", type="date", label="Check-in", required=True),
            FieldDefinition(key="nights", type="integer", label="Nights", required=True),
            FieldDefinition(key="party_size", type="integer", label="Party size", required=True),
        ],
        action_types=[
            ActionDefinitionDraft(key="booking.create", label="Create booking", execution_mode="auto"),
            ActionDefinitionDraft(key="payment.request_deposit", label="Request deposit", execution_mode="auto"),
        ],
        prompt_hints=[],
    )
    parsed = _WizardModelOutput(
        assistant_message="Drafted a hotel template.",
        slots_filled={"business_type": "hotel"},
        confidence=0.85,
        ready=True,
        draft_partial=hotel_draft,
    )
    _install_fake_gemini(monkeypatch, parsed)

    payload = WizardChatRequest(
        messages=[
            WizardChatTurn(
                role="user",
                content="I run a boutique hotel, we take reservations on the phone and ask for a deposit.",
            )
        ]
    )
    resp = asyncio.run(run_wizard_chat(payload))
    keys = [a.key for a in resp.draft_partial.action_types]
    assert "payment.request_deposit" in keys
    assert resp.proposed_actions_from_catalog == []


# ---------------------------------------------------------------------------
# _user_prompt meta-block
# ---------------------------------------------------------------------------


def _payload(turns: list[tuple[str, str]]) -> WizardChatRequest:
    return WizardChatRequest(
        messages=[WizardChatTurn(role=role, content=content) for role, content in turns]
    )


def test_user_prompt_marks_first_turn():
    payload = _payload([("user", "I run a restaurant for bookings")])
    prompt = _user_prompt(payload)
    assert "Questions asked so far: 0 / 5" in prompt
    assert "First turn" in prompt
    assert "BUDGET EXHAUSTED" not in prompt


def test_user_prompt_ignores_client_side_greeting_for_question_budget():
    payload = _payload(
        [
            (
                "assistant",
                "Hi! Tell me a bit about your business — what kind of phone calls do you usually take?",
            ),
            ("user", "I run a restaurant and take booking calls"),
        ]
    )
    prompt = _user_prompt(payload)
    assert _questions_asked_after_user_started(payload) == 0
    assert "Questions asked so far: 0 / 5" in prompt
    assert "First turn" in prompt


def test_user_prompt_includes_question_count():
    payload = _payload(
        [
            ("user", "I have a business"),
            ("assistant", "What kind of business?"),
            ("user", "A dental clinic"),
            ("assistant", "What calls do you receive?"),
            ("user", "Bookings mostly"),
        ]
    )
    prompt = _user_prompt(payload)
    assert "Questions asked so far: 2 / 5" in prompt
    assert "BUDGET EXHAUSTED" not in prompt
    assert "First turn" not in prompt


def test_user_prompt_forces_draft_at_budget_ceiling():
    turns: list[tuple[str, str]] = [("assistant", "Hi"), ("user", "hi")]
    for i in range(QUESTION_BUDGET):
        turns.append(("assistant", f"Question {i + 1}?"))
        turns.append(("user", f"Answer {i + 1}"))
    payload = _payload(turns)
    prompt = _user_prompt(payload)
    assert f"Questions asked so far: {QUESTION_BUDGET} / {QUESTION_BUDGET}" in prompt
    assert "BUDGET EXHAUSTED" in prompt


# ---------------------------------------------------------------------------
# Behavior tests (mocked Gemini)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, parsed: _WizardModelOutput):
        self.text = parsed.model_dump_json()


class _FakeModels:
    def __init__(self, parsed: _WizardModelOutput):
        self._parsed = parsed

    async def generate_content(self, **_kw: Any) -> _FakeResponse:
        return _FakeResponse(self._parsed)


class _FakeAio:
    def __init__(self, parsed: _WizardModelOutput):
        self.models = _FakeModels(parsed)


class _FakeClient:
    def __init__(self, parsed: _WizardModelOutput):
        self.aio = _FakeAio(parsed)


def _install_fake_gemini(monkeypatch, parsed: _WizardModelOutput) -> None:
    # Patch settings.google_api_key so the early fail-fast passes.
    from app.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-test-key")

    import google.genai as genai_module

    monkeypatch.setattr(genai_module, "Client", lambda **_kw: _FakeClient(parsed))


def _rich_draft() -> TemplateWizardResponse:
    return TemplateWizardResponse(
        name="Restaurant booking",
        description="Phone bookings for a restaurant.",
        domain_hint="restaurant",
        fields_schema=[
            FieldDefinition(key="customer_name", type="string", label="Customer name", required=True),
            FieldDefinition(key="party_size", type="integer", label="Party size", required=True),
            FieldDefinition(key="booking_date", type="date", label="Date", required=True),
            FieldDefinition(key="booking_time", type="time", label="Time", required=True, depends_on=["booking_date"]),
            FieldDefinition(key="allergies", type="string_list", label="Allergies"),
        ],
        action_types=[
            ActionDefinitionDraft(key="booking.create", label="Create booking", execution_mode="auto"),
            ActionDefinitionDraft(key="whatsapp.send_confirmation", label="Send WhatsApp confirmation", execution_mode="auto"),
        ],
        prompt_hints=[],
    )


def test_rich_first_message_returns_ready_draft(monkeypatch):
    parsed = _WizardModelOutput(
        assistant_message="I drafted a restaurant booking template. You can adjust fields and actions before saving.",
        slots_filled={"business_type": "restaurant"},
        confidence=0.9,
        ready=True,
        draft_partial=_rich_draft(),
    )
    _install_fake_gemini(monkeypatch, parsed)

    payload = WizardChatRequest(
        messages=[
            WizardChatTurn(
                role="user",
                content="I run a restaurant and we receive calls for bookings, changes and cancellations.",
            )
        ]
    )
    resp = asyncio.run(run_wizard_chat(payload))
    assert resp.ready is True
    assert resp.draft_partial is not None
    assert len(resp.draft_partial.fields_schema) >= 4
    assert len(resp.draft_partial.action_types) >= 2
    assert resp.proposed_actions_from_catalog == []


def test_vague_first_message_returns_question(monkeypatch):
    parsed = _WizardModelOutput(
        assistant_message="What kind of calls do you mostly receive?",
        slots_filled={},
        confidence=0.2,
        ready=False,
        draft_partial=None,
    )
    _install_fake_gemini(monkeypatch, parsed)

    payload = WizardChatRequest(
        messages=[WizardChatTurn(role="user", content="I have a business and want to manage calls.")]
    )
    resp = asyncio.run(run_wizard_chat(payload))
    assert resp.ready is False
    assert resp.draft_partial is None
    assert "?" in resp.assistant_message


def test_hallucinated_action_keys_are_stripped(monkeypatch):
    draft = _rich_draft()
    # Inject a hallucinated key alongside the real ones.
    draft = draft.model_copy(
        update={
            "action_types": draft.action_types
            + [ActionDefinitionDraft(key="nonexistent.action", label="Bogus", execution_mode="auto")]
        }
    )
    parsed = _WizardModelOutput(
        assistant_message="Drafted.",
        slots_filled={},
        confidence=0.9,
        ready=True,
        draft_partial=draft,
    )
    _install_fake_gemini(monkeypatch, parsed)

    payload = WizardChatRequest(
        messages=[WizardChatTurn(role="user", content="I run a restaurant for bookings")]
    )
    resp = asyncio.run(run_wizard_chat(payload))
    assert resp.draft_partial is not None
    keys = [a.key for a in resp.draft_partial.action_types]
    assert "nonexistent.action" not in keys
    assert "nonexistent.action" in resp.proposed_actions_from_catalog


def test_ready_true_without_draft_is_downgraded(monkeypatch):
    parsed = _WizardModelOutput(
        assistant_message="(contradiction)",
        slots_filled={},
        confidence=0.9,
        ready=True,
        draft_partial=None,
    )
    _install_fake_gemini(monkeypatch, parsed)

    payload = WizardChatRequest(
        messages=[WizardChatTurn(role="user", content="I run a restaurant for bookings")]
    )
    resp = asyncio.run(run_wizard_chat(payload))
    assert resp.ready is False
    assert resp.draft_partial is None
