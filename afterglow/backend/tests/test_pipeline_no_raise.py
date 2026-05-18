"""End-to-end test of the no-raise contract at `run_pipeline` level.

The contract: when `run_call_agent` returns `completion_reason="error"`
or `"max_turns"`, `run_pipeline` MUST:
  - never re-raise (the caller is `api/calls._run_pipeline_isolated`
    which would rollback the session on exception, wiping flushed
    `ExecutedAction` rows);
  - commit the final `Call.status` (failed / needs_review);
  - set `Call.completed_at`;
  - NOT persist `ExtractedFields` (only `finalize` writes those);
  - leave `Call.review_flag` populated on `max_turns`.

We stub out the I/O-heavy pieces (Speechmatics, audit_step, customer
resolution, memory write-back, the agent itself) and drive `run_pipeline`
with a fake `AsyncSession` so the assertions are about CONTROL FLOW, not
SQL behaviour.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Optional

import pytest

from app.agents import orchestrator
from app.agents.call_agent import CallAgentResult
from app.agents.call_analyzer import TokenUsage


@asynccontextmanager
async def _fake_audit_step(**kwargs):
    yield SimpleNamespace(payload=kwargs.get("payload"), status="success",
                          input_tokens=None, output_tokens=None)


class FakeResult:
    def __init__(self, *, scalar=None, scalars_all=None, all_rows=None):
        self._scalar = scalar
        self._scalars_all = scalars_all or []
        self._all = all_rows or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalar_one(self):
        return self._scalar

    def scalar(self):
        return self._scalar

    def scalars(self):
        s = SimpleNamespace()
        s.all = lambda: self._scalars_all
        return s

    def all(self):
        return self._all


class FakeSession:
    """Captures every query/commit so we can assert control flow."""

    def __init__(self, *, call: Any, template: Any, customer: Any):
        self._call = call
        self._template = template
        self._customer = customer
        self.added: list[Any] = []
        self.commits: int = 0
        self.rolledback: int = 0
        self._lookups: list[Any] = []

    async def execute(self, stmt: Any):
        self._lookups.append(stmt)
        # Disambiguate by inspecting the FROM clause. `SELECT calls.id, ...`
        # includes "customer_id" as a column even when the table is `calls`,
        # so a naïve "customer in text" check is wrong. Use the column
        # description instead.
        try:
            desc = stmt.column_descriptions  # list of dicts with "entity"
        except Exception:  # noqa: BLE001
            desc = []
        primary = None
        if desc:
            entity = desc[0].get("entity")
            primary = getattr(entity, "__tablename__", None) if entity else None
            if primary is None and entity is not None:
                primary = getattr(entity, "__name__", None)

        if primary in ("calls", "Call"):
            return FakeResult(scalar=self._call)
        if primary in ("templates", "Template"):
            return FakeResult(scalar=self._template)
        if primary in ("customers", "Customer"):
            return FakeResult(scalar=self._customer)
        return FakeResult(scalar=None, all_rows=[])

    async def scalar(self, stmt: Any):
        return None

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rolledback += 1


def _fake_transcript(text: str = "Hello operator, this is a real call about a booking for four people."):
    return SimpleNamespace(
        text=text,
        speakers=[{"speaker": "S1", "text": text}],
        language="en",
        raw={},
    )


def _fake_call(call_id: uuid.UUID, status: str = "pending") -> Any:
    return SimpleNamespace(
        id=call_id,
        session_id=None,
        phone_e164="+393331112233",
        template_id=uuid.uuid4(),
        audio_url=None,
        raw_transcript=None,
        detected_language=None,
        status=status,
        error=None,
        review_flag=None,
        started_at=None,
        completed_at=None,
        customer_id=None,
    )


def _fake_template() -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Restaurant",
        domain_hint="restaurant",
        fields_schema=[{"key": "party_size", "type": "integer"}],
        action_types=[],
        prompt_hints=None,
    )


def _fake_customer() -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        phone_e164="+393331112233",
        display_name=None,
        total_calls=0,
        memory_summary=None,
        last_call_at=None,
        tags=[],
        is_seed=False,
        session_id=None,
        preferred_language="en",
    )


@pytest.fixture
def _stub_orchestrator_deps(monkeypatch):
    """Patch out everything the orchestrator touches besides the agent."""
    monkeypatch.setattr(orchestrator, "audit_step", _fake_audit_step)

    async def _fake_transcribe(*args, **kwargs):
        return _fake_transcript()

    monkeypatch.setattr(
        orchestrator.speechmatics, "transcribe_audio", _fake_transcribe
    )

    async def _fake_retrieve_facts(session, customer):
        return {}

    monkeypatch.setattr(
        orchestrator.memory_retrieval,
        "retrieve_structured_facts",
        _fake_retrieve_facts,
    )

    customer = _fake_customer()

    async def _fake_resolve(session, *, phone_e164, session_id, preferred_language):
        return customer

    monkeypatch.setattr(orchestrator, "_resolve_customer", _fake_resolve)

    async def _fake_persist_memory(session, *, call, customer, template, collection_id,
                                    briefing, classification):
        return None

    monkeypatch.setattr(orchestrator, "_persist_memory", _fake_persist_memory)

    return customer


@pytest.mark.asyncio
async def test_pipeline_max_turns_marks_needs_review_and_commits(
    monkeypatch, _stub_orchestrator_deps
):
    """On max_turns: status='needs_review', review_flag auto-filled,
    completed_at set, no ExtractedFields, no exception."""
    call_id = uuid.uuid4()
    call = _fake_call(call_id)
    template = _fake_template()
    call.template_id = template.id
    session = FakeSession(call=call, template=template, customer=_stub_orchestrator_deps)

    async def _fake_agent(session, **kwargs):
        return CallAgentResult(
            completion_reason="max_turns",
            turn_count=12,
            token_usage=TokenUsage(input_tokens=1200, output_tokens=240),
            turn_trail=[
                {"turn": 1, "tool": "search_transcript", "args_summary": "k=Saturday",
                 "result_summary": "matches=0"},
            ],
        )

    monkeypatch.setattr(orchestrator.call_agent, "run_call_agent", _fake_agent)

    # Must not raise — this is the no-raise contract.
    await orchestrator.run_pipeline(session, call_id)

    assert call.status == "needs_review"
    assert call.review_flag is not None
    assert call.review_flag["reason"] == "agent_did_not_finalize"
    assert call.review_flag["flagged_by"] == "system"
    assert call.review_flag["turn_count"] == 12
    assert isinstance(call.completed_at, datetime)
    assert call.completed_at.tzinfo is not None

    # No ExtractedFields persisted on the max_turns path.
    from app.db.models import ExtractedFields
    assert not any(isinstance(o, ExtractedFields) for o in session.added)

    # The orchestrator committed and DID NOT rollback.
    assert session.commits >= 1
    assert session.rolledback == 0


@pytest.mark.asyncio
async def test_pipeline_agent_error_marks_failed_and_commits(
    monkeypatch, _stub_orchestrator_deps
):
    """On error: status='failed', Call.error set, no ExtractedFields,
    commit clean, NO re-raise to the caller."""
    call_id = uuid.uuid4()
    call = _fake_call(call_id)
    template = _fake_template()
    call.template_id = template.id
    session = FakeSession(call=call, template=template, customer=_stub_orchestrator_deps)

    async def _fake_agent(session, **kwargs):
        return CallAgentResult(
            completion_reason="error",
            turn_count=2,
            token_usage=TokenUsage(input_tokens=200, output_tokens=80),
            error="adk_runner: simulated crash",
        )

    monkeypatch.setattr(orchestrator.call_agent, "run_call_agent", _fake_agent)

    # Must not raise.
    await orchestrator.run_pipeline(session, call_id)

    assert call.status == "failed"
    assert call.error == "adk_runner: simulated crash"
    assert isinstance(call.completed_at, datetime)
    # review_flag is left alone on the error path.
    assert call.review_flag is None

    from app.db.models import ExtractedFields
    assert not any(isinstance(o, ExtractedFields) for o in session.added)

    assert session.commits >= 1
    assert session.rolledback == 0


@pytest.mark.asyncio
async def test_pipeline_idempotency_skips_terminal_status(
    monkeypatch, _stub_orchestrator_deps
):
    """A re-invocation on a call already in `needs_review` must be a no-op
    (idempotency guard prevents the agent from running twice)."""
    call_id = uuid.uuid4()
    call = _fake_call(call_id, status="needs_review")
    template = _fake_template()
    call.template_id = template.id
    session = FakeSession(call=call, template=template, customer=_stub_orchestrator_deps)

    agent_called = False

    async def _fake_agent(session, **kwargs):
        nonlocal agent_called
        agent_called = True
        return CallAgentResult(completion_reason="finalize", token_usage=TokenUsage())

    monkeypatch.setattr(orchestrator.call_agent, "run_call_agent", _fake_agent)

    await orchestrator.run_pipeline(session, call_id)

    # The guard short-circuited before reaching the agent.
    assert agent_called is False
    assert call.status == "needs_review"  # unchanged
