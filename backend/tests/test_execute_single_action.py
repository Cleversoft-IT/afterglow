"""Tests for `app.executors.action_executor.execute_single_action`.

Each branch must satisfy the **no-raise** contract: the function never
propagates exceptions; every failure mode becomes an `ExecutedAction` row
with the appropriate status.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from app.executors import action_executor


@asynccontextmanager
async def _fake_audit_step(**kwargs):
    yield SimpleNamespace(payload=None, status="success")


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    monkeypatch.setattr(action_executor, "audit_step", _fake_audit_step)


class FakeSession:
    def __init__(self):
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


def _make_template(action: dict[str, Any]) -> Any:
    return SimpleNamespace(action_types=[action])


def _make_call() -> Any:
    return SimpleNamespace(id=uuid.uuid4(), session_id=None)


def _make_customer() -> Any:
    return SimpleNamespace(id=uuid.uuid4(), display_name=None, tags=[])


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


@pytest.mark.asyncio
async def test_validation_failed_returns_no_raise():
    """payload_schema fails → status='validation_failed', no exception."""
    session = FakeSession()
    template = _make_template(_booking_action())
    record = await action_executor.execute_single_action(
        session,
        call=_make_call(),
        customer=_make_customer(),
        template=template,
        entry={
            "action_type": "booking.create",
            "title": "x",
            "payload": {"party_size": "not-a-number"},
            "confidence": 0.9,
            "evidence": ["yes"],
        },
        agent_turn=3,
    )
    assert record is not None
    assert record.status == "validation_failed"
    assert record.result["refused"] == "validation_failed"


@pytest.mark.asyncio
async def test_evidence_missing_returns_no_raise():
    session = FakeSession()
    template = _make_template(_booking_action())
    record = await action_executor.execute_single_action(
        session,
        call=_make_call(),
        customer=_make_customer(),
        template=template,
        entry={
            "action_type": "booking.create",
            "title": "x",
            "payload": {"party_size": 4, "booking_date": "2026-06-01"},
            "confidence": 0.9,
            "evidence": [],
        },
        agent_turn=2,
    )
    assert record is not None
    assert record.status == "evidence_missing"


@pytest.mark.asyncio
async def test_hallucinated_action_type_returns_none():
    """Action key not in template → audited and returns None (no row)."""
    session = FakeSession()
    template = _make_template(_booking_action())
    record = await action_executor.execute_single_action(
        session,
        call=_make_call(),
        customer=_make_customer(),
        template=template,
        entry={
            "action_type": "ghost.action",
            "title": "x",
            "payload": {},
            "confidence": 0.9,
            "evidence": ["y"],
        },
    )
    assert record is None
    assert session.added == []


@pytest.mark.asyncio
async def test_manual_only_lands_as_manual_required():
    manual_action = _booking_action()
    manual_action["execution_mode"] = "manual-only"
    session = FakeSession()
    template = _make_template(manual_action)
    record = await action_executor.execute_single_action(
        session,
        call=_make_call(),
        customer=_make_customer(),
        template=template,
        entry={
            "action_type": "booking.create",
            "title": "x",
            "payload": {"party_size": 4, "booking_date": "2026-06-01"},
            "confidence": 0.9,
            "evidence": ["y"],
        },
    )
    assert record is not None
    assert record.status == "manual_required"


@pytest.mark.asyncio
async def test_successful_mock_execution():
    session = FakeSession()
    template = _make_template(_booking_action())
    record = await action_executor.execute_single_action(
        session,
        call=_make_call(),
        customer=_make_customer(),
        template=template,
        entry={
            "action_type": "booking.create",
            "title": "x",
            "payload": {"party_size": 4, "booking_date": "2026-06-01"},
            "confidence": 0.9,
            "evidence": ["yes please"],
        },
        agent_turn=1,
    )
    assert record is not None
    assert record.status == "executed"
    assert isinstance(record.result, dict)
    assert record.result.get("mutates") is True
    assert record.result.get("mock") is True


@pytest.mark.asyncio
async def test_handler_exception_translates_to_failed_no_raise(monkeypatch):
    """A crash inside MOCK_REGISTRY must become status='failed', no exception."""
    def _boom(payload):
        raise RuntimeError("handler exploded")

    monkeypatch.setitem(action_executor.MOCK_REGISTRY, "booking.create", _boom)

    session = FakeSession()
    template = _make_template(_booking_action())
    record = await action_executor.execute_single_action(
        session,
        call=_make_call(),
        customer=_make_customer(),
        template=template,
        entry={
            "action_type": "booking.create",
            "title": "x",
            "payload": {"party_size": 4, "booking_date": "2026-06-01"},
            "confidence": 0.9,
            "evidence": ["yes please"],
        },
        agent_turn=4,
    )
    assert record is not None
    assert record.status == "failed"
    assert "handler_exception" in (record.result.get("error") or "")
