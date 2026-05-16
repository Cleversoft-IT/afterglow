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

from app.agents.wizard_chat import WizardChatError, _system_instruction, run_wizard_chat
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
