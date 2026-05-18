"""Tests for the turn-counter correlation between agent_turn and action_exec.

The audit-log UI joins `agent_turn` rows (written by gemini_adk.run_agent_loop)
to the corresponding `action_exec` rows (written by execute_single_action)
via `payload.agent_turn`. This is the contract:

  - every tool wrapper bumps `tool_context.state["turn_counter"]` as its
    first instruction;
  - when an action tool invokes `execute_single_action`, it forwards that
    counter as `agent_turn=`;
  - the executor copies it into the `action_exec` audit payload.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from app.agents.tools import action_tool
from app.agents.tools.turn import bump_turn
from app.executors import action_executor


_captured_payloads: list[dict[str, Any]] = []


@asynccontextmanager
async def _capturing_audit_step(**kwargs):
    """Capture every audit_step payload so we can assert on agent_turn."""
    _captured_payloads.append(kwargs)
    yield SimpleNamespace(payload=kwargs.get("payload"), status="success")


@pytest.fixture(autouse=True)
def _reset_capture(monkeypatch):
    _captured_payloads.clear()
    monkeypatch.setattr(action_executor, "audit_step", _capturing_audit_step)


class FakeSession:
    def __init__(self):
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


class FakeToolContext:
    def __init__(self):
        self.state: dict[str, Any] = {}


def _booking_action() -> dict[str, Any]:
    return {
        "key": "booking.create",
        "label": "Create booking",
        "execution_mode": "auto",
        "preconditions": ["party_size"],
        "confidence_threshold": 0.75,
        "evidence_required": True,
        "payload_schema": {
            "type": "object",
            "properties": {
                "party_size": {"type": "integer", "minimum": 1},
                "booking_date": {"type": "string"},
            },
            "required": ["party_size", "booking_date"],
            "additionalProperties": False,
        },
    }


def test_bump_turn_is_monotonic_per_context():
    ctx = FakeToolContext()
    assert bump_turn(ctx) == 1
    assert bump_turn(ctx) == 2
    assert bump_turn(ctx) == 3
    assert ctx.state["turn_counter"] == 3


def test_bump_turn_tolerates_missing_context():
    # No tool_context at all → returns 0 (no crash).
    assert bump_turn(None) == 0


@pytest.mark.asyncio
async def test_agent_turn_lands_in_action_exec_payload():
    """End-to-end correlation: tool bumps counter → executor records it."""
    session = FakeSession()
    template = SimpleNamespace(action_types=[_booking_action()])
    tool = action_tool.make_action_tool(
        _booking_action(),
        session=session,
        call=SimpleNamespace(id=uuid.uuid4(), session_id=None),
        customer=SimpleNamespace(id=uuid.uuid4(), display_name=None, tags=[]),
        template=template,
    )
    ctx = FakeToolContext()
    # Pretend two earlier tool turns already happened (e.g. memory + search).
    ctx.state["turn_counter"] = 2

    payload_model = tool.__annotations__["payload"]
    payload = payload_model.model_validate(
        {"party_size": 4, "booking_date": "2026-06-01"}
    )
    result = await tool(
        payload, confidence=0.9, evidence=["yes please"], tool_context=ctx
    )
    # Counter advanced to 3, both in tool response and in the audit row.
    assert result["agent_turn"] == 3
    assert ctx.state["turn_counter"] == 3

    action_exec_rows = [
        p for p in _captured_payloads if p.get("step_type") == "action_exec"
    ]
    assert len(action_exec_rows) == 1
    assert action_exec_rows[0]["payload"]["agent_turn"] == 3
