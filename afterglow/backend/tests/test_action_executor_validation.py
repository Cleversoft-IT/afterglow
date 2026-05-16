"""Tests for app.executors.action_executor v2 enforcement.

Covers:
- payload_schema validation rejects malformed payloads before MOCK_REGISTRY
- evidence_required=True + empty evidence is refused
- mutates=True propagates to audit + ExecutedAction.result
"""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from app.executors import action_executor


@asynccontextmanager
async def _fake_audit_step(**kwargs):
    """Stand-in for audit.logger.audit_step that does NOT open a DB session."""
    yield SimpleNamespace(payload=None, status="success")


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    monkeypatch.setattr(action_executor, "audit_step", _fake_audit_step)


class FakeSession:
    """Minimal AsyncSession stand-in: collects everything added without I/O."""

    def __init__(self):
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


def _booking_action() -> dict[str, Any]:
    return {
        "key": "booking.create",
        "label": "Create booking",
        "execution_mode": "auto",
        "mock_target": "booking",
        "preconditions": ["party_size"],
        "confidence_threshold": 0.75,
        "mutates": True,
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


def _make_template(action: dict[str, Any]):
    return SimpleNamespace(action_types=[action])


def _make_call():
    return SimpleNamespace(id=uuid.uuid4(), session_id=None)


def test_payload_schema_violation_is_refused(monkeypatch):
    """Payload missing a required key → validation_failed, MOCK_REGISTRY skipped."""
    invoked: list[Any] = []

    def fake_mock(payload: Any) -> dict[str, Any]:
        invoked.append(payload)
        return {"ok": True}

    monkeypatch.setattr(
        action_executor, "MOCK_REGISTRY", {"booking.create": fake_mock}
    )

    template = _make_template(_booking_action())
    call = _make_call()
    plan = [
        {
            "action_type": "booking.create",
            "title": "Create booking",
            "summary": "",
            "payload": {"party_size": 4},  # missing booking_date
            "confidence": 0.9,
            "evidence": ["table for 4"],
        }
    ]
    fake = FakeSession()
    persisted = asyncio.run(
        action_executor.execute_planned_actions(
            fake, call=call, customer=None, template=template, plan=plan
        )
    )
    assert len(persisted) == 1
    assert persisted[0].status == "validation_failed"
    assert invoked == []  # MOCK_REGISTRY never called


def test_evidence_required_with_empty_list_is_refused(monkeypatch):
    invoked: list[Any] = []

    def fake_mock(payload: Any) -> dict[str, Any]:
        invoked.append(payload)
        return {"ok": True}

    monkeypatch.setattr(
        action_executor, "MOCK_REGISTRY", {"booking.create": fake_mock}
    )

    template = _make_template(_booking_action())
    call = _make_call()
    plan = [
        {
            "action_type": "booking.create",
            "title": "Create booking",
            "summary": "",
            "payload": {"party_size": 4, "booking_date": "2026-05-20"},
            "confidence": 0.9,
            "evidence": [],
        }
    ]
    fake = FakeSession()
    persisted = asyncio.run(
        action_executor.execute_planned_actions(
            fake, call=call, customer=None, template=template, plan=plan
        )
    )
    assert len(persisted) == 1
    assert persisted[0].status == "evidence_missing"
    assert invoked == []


def test_mutates_flag_propagates_to_result(monkeypatch):
    monkeypatch.setattr(
        action_executor,
        "MOCK_REGISTRY",
        {"booking.create": lambda payload: {"booked": True}},
    )

    template = _make_template(_booking_action())
    call = _make_call()
    plan = [
        {
            "action_type": "booking.create",
            "title": "Create booking",
            "summary": "",
            "payload": {"party_size": 4, "booking_date": "2026-05-20"},
            "confidence": 0.9,
            "evidence": ["table for 4"],
        }
    ]
    fake = FakeSession()
    persisted = asyncio.run(
        action_executor.execute_planned_actions(
            fake, call=call, customer=None, template=template, plan=plan
        )
    )
    assert len(persisted) == 1
    assert persisted[0].status == "executed"
    # `mock: True` is added by the executor so the UI can render a "Simulated"
    # badge on every MOCK_REGISTRY-backed action — see project_afterglow_decisions
    # 'production = hackathon' (mock registry is the boundary judges see).
    assert persisted[0].result == {"booked": True, "mutates": True, "mock": True}


def test_hallucinated_action_is_rejected(monkeypatch):
    """An action_type not in the template's action_types is dropped."""
    invoked: list[Any] = []

    def fake_mock(payload: Any) -> dict[str, Any]:
        invoked.append(payload)
        return {"ok": True}

    monkeypatch.setattr(
        action_executor, "MOCK_REGISTRY", {"booking.create": fake_mock}
    )

    template = _make_template(_booking_action())
    call = _make_call()
    plan = [
        {
            "action_type": "rocket.launch",  # not in template
            "title": "Launch",
            "payload": {},
            "evidence": ["x"],
        }
    ]
    fake = FakeSession()
    persisted = asyncio.run(
        action_executor.execute_planned_actions(
            fake, call=call, customer=None, template=template, plan=plan
        )
    )
    assert persisted == []
    assert invoked == []


def test_manual_only_action_queued_not_executed(monkeypatch):
    invoked: list[Any] = []

    def fake_mock(payload: Any) -> dict[str, Any]:
        invoked.append(payload)
        return {"ok": True}

    monkeypatch.setattr(
        action_executor, "MOCK_REGISTRY", {"booking.create": fake_mock}
    )
    action = _booking_action()
    action["execution_mode"] = "manual-only"
    template = _make_template(action)
    call = _make_call()
    plan = [
        {
            "action_type": "booking.create",
            "title": "Create booking",
            "summary": "",
            "payload": {"party_size": 4, "booking_date": "2026-05-20"},
            "confidence": 0.9,
            "evidence": ["table for 4"],
        }
    ]
    fake = FakeSession()
    persisted = asyncio.run(
        action_executor.execute_planned_actions(
            fake, call=call, customer=None, template=template, plan=plan
        )
    )
    assert len(persisted) == 1
    assert persisted[0].status == "manual_required"
    assert persisted[0].result == {"mutates": True}
    assert invoked == []
