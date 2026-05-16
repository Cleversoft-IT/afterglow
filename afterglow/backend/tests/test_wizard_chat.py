"""Smoke tests for the wizard chat agent.

We do NOT call Gemini in tests — the agent's structured-output contract is
tested at the schema/validation level. Coverage here:
- Module-level imports work (catalog + validator chain are reachable).
- `_system_instruction` mentions every catalog key (the agent uses this
  list to constrain action_types).
- An empty message list raises WizardChatError, even before any Gemini call.
"""
from __future__ import annotations

import asyncio

import pytest

from app.agents.wizard_chat import (
    WizardChatError,
    _WizardModelOutput,
    _system_instruction,
    run_wizard_chat,
)
from app.integrations import action_catalog
from app.schemas.templates import WizardChatRequest


def test_system_instruction_lists_every_catalog_key():
    instruction = _system_instruction(
        language="en", catalog_keys=action_catalog.available_keys()
    )
    for key in action_catalog.available_keys():
        assert key in instruction, f"system instruction missing catalog key {key}"


def test_empty_messages_raises():
    payload = WizardChatRequest(messages=[])
    with pytest.raises(WizardChatError):
        asyncio.run(run_wizard_chat(payload))


def test_wizard_model_output_schema_has_no_additional_properties():
    # Gemini's structured-output endpoint rejects schemas that contain
    # `additionalProperties` (a flag Pydantic emits for any `dict[str, Any]`
    # field). Guard against regressing the workaround we apply on
    # `_WizardModelOutput.slots_filled` (and any future field added here).
    schema_json = _WizardModelOutput.model_json_schema()

    def _walk(node):
        if isinstance(node, dict):
            assert "additionalProperties" not in node, (
                "_WizardModelOutput JSON schema contains additionalProperties, "
                "which Gemini does not accept. Switch the offending dict[str, Any] "
                "field to Any (see PlannedAction.payload for the pattern)."
            )
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(schema_json)
