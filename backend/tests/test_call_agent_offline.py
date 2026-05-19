"""Offline tests for `app.agents.call_agent.run_call_agent`.

Each test drives the agent loop via a scripted `ScriptedLlm` so we never
need a real Gemini key. We focus on:

  - the no-raise contract (every failure mode returns a `CallAgentResult`);
  - the completion_reason mapping (finalize / max_turns / error);
  - the finalize_call payload schema uses `fields` (not `extracted_fields`);
  - the turn counter increments and lands on action_exec audit payloads.
"""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, AsyncGenerator

import pytest

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app.agents import call_agent
from app.executors import action_executor


@asynccontextmanager
async def _fake_audit_step(**kwargs):
    yield SimpleNamespace(payload=None, status="success")


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    monkeypatch.setattr(action_executor, "audit_step", _fake_audit_step)


class ScriptedLlm(BaseLlm):
    """Fake LLM whose response stream is pre-baked at construction time."""

    script: list[LlmResponse] = []
    _cursor: int = 0

    model_config = {"arbitrary_types_allowed": True}

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if self._cursor >= len(self.script):
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="done")],
                ),
                turn_complete=True,
            )
            return
        resp = self.script[self._cursor]
        self._cursor += 1
        yield resp


def _fc(name: str, args: dict[str, Any]) -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_function_call(name=name, args=args)],
        ),
        turn_complete=True,
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=10,
            candidates_token_count=5,
            total_token_count=15,
        ),
    )


def _text(text: str) -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=text)],
        ),
        turn_complete=True,
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=3, candidates_token_count=2, total_token_count=5
        ),
    )


def _make_call() -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        session_id=None,
        phone_e164="+393331112233",
        raw_transcript={"text": "hello", "speakers": []},
        review_flag=None,
    )


def _make_customer() -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(), display_name="Test", phone_e164="+393331112233", total_calls=0
    )


def _make_template() -> Any:
    return SimpleNamespace(
        name="Restaurant",
        domain_hint="restaurant",
        fields_schema=[{"key": "party_size", "type": "integer"}],
        action_types=[],  # no action tools — simpler for control-flow tests
        prompt_hints=None,
    )


class FakeSession:
    def __init__(self):
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


def _patch_settings(monkeypatch, *, has_key: bool = True):
    monkeypatch.setattr(call_agent.settings, "google_api_key", "fake-key" if has_key else "")


def _install_scripted_runner(monkeypatch, script: list[LlmResponse]):
    """Patch `create_runner` so `run_agent_loop` uses our scripted Llm."""
    from google.adk import Agent
    from google.adk.runners import InMemoryRunner

    def _create(spec):
        agent = Agent(
            model=ScriptedLlm(model="scripted", script=script),
            name=spec.name,
            description=spec.description,
            instruction=spec.instruction,
            tools=spec.tools,
        )
        return InMemoryRunner(agent=agent, app_name=spec.name)

    monkeypatch.setattr(call_agent, "create_runner", _create)


@pytest.mark.asyncio
async def test_finalize_completion(monkeypatch):
    """Agent invokes finalize_call → completion_reason='finalize' + fields populated."""
    _patch_settings(monkeypatch)
    finalize_args = {
        "payload": {
            "fields": [
                {"key": "party_size", "value": "4", "confidence": 0.95, "evidence": "four people"}
            ],
            "intent": "booking",
            "sentiment": "neutral",
            "language": "en",
            "urgency": "normal",
            "briefing": "Mark booked dinner for 4.",
        }
    }
    _install_scripted_runner(monkeypatch, [
        _fc("finalize_call", finalize_args),
        _text("ok"),
    ])

    result = await call_agent.run_call_agent(
        FakeSession(),
        call=_make_call(),
        customer=_make_customer(),
        template=_make_template(),
        transcript_text="A simple test transcript",
        prompt_hints=None,
        prior_structured=None,
        is_demo=False,
        preseed_available=False,
        collection_id=None,
        max_iterations=12,
        session_lock=asyncio.Lock(),
    )
    assert result.completion_reason == "finalize"
    assert result.fields and result.fields[0].key == "party_size"
    assert result.intent == "booking"
    assert result.briefing == "Mark booked dinner for 4."
    assert result.token_usage.input_tokens and result.token_usage.input_tokens > 0


@pytest.mark.asyncio
async def test_max_turns_completion(monkeypatch):
    """Loop hits budget without finalize → completion_reason='max_turns', no-raise."""
    _patch_settings(monkeypatch)
    # Script: keep calling search_transcript forever.
    script = []
    for _ in range(20):
        script.append(_fc("search_transcript", {"keyword": "x"}))
    _install_scripted_runner(monkeypatch, script)

    result = await call_agent.run_call_agent(
        FakeSession(),
        call=_make_call(),
        customer=_make_customer(),
        template=_make_template(),
        transcript_text="A simple test transcript",
        prompt_hints=None,
        prior_structured=None,
        is_demo=False,
        preseed_available=False,
        collection_id=None,
        max_iterations=3,
        session_lock=asyncio.Lock(),
    )
    assert result.completion_reason == "max_turns"
    assert result.turn_count >= 3
    assert result.fields is None  # no finalize → no extracted fields


@pytest.mark.asyncio
async def test_missing_api_key_returns_error(monkeypatch):
    """No GOOGLE_API_KEY → completion_reason='error', no exception."""
    _patch_settings(monkeypatch, has_key=False)

    result = await call_agent.run_call_agent(
        FakeSession(),
        call=_make_call(),
        customer=_make_customer(),
        template=_make_template(),
        transcript_text="hi",
        prompt_hints=None,
        prior_structured=None,
        is_demo=False,
        preseed_available=False,
        collection_id=None,
        session_lock=asyncio.Lock(),
    )
    assert result.completion_reason == "error"
    assert "GOOGLE_API_KEY" in (result.error or "")


@pytest.mark.asyncio
async def test_runner_exception_returns_error(monkeypatch):
    """ADK runner that explodes → completion_reason='error', no exception."""
    _patch_settings(monkeypatch)

    def _broken(spec):
        raise RuntimeError("simulated ADK init crash")

    monkeypatch.setattr(call_agent, "create_runner", _broken)

    result = await call_agent.run_call_agent(
        FakeSession(),
        call=_make_call(),
        customer=_make_customer(),
        template=_make_template(),
        transcript_text="hi",
        prompt_hints=None,
        prior_structured=None,
        is_demo=False,
        preseed_available=False,
        collection_id=None,
        session_lock=asyncio.Lock(),
    )
    assert result.completion_reason == "error"
    assert "adk_runner" in (result.error or "")


@pytest.mark.asyncio
async def test_finalize_payload_uses_fields_not_extracted_fields(monkeypatch):
    """Schema sanity: the tool key is `fields`, never `extracted_fields`."""
    from app.agents.tools.control_tool import FinalizeCallPayload

    assert "fields" in FinalizeCallPayload.model_fields
    assert "extracted_fields" not in FinalizeCallPayload.model_fields
