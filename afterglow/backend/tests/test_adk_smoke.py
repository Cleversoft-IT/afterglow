"""Smoke test ADK 1.18 — gate bloccante per la pipeline agentica multi-turn.

Verifica i quattro punti che il piano richiede prima di costruire `call_agent`:

  1. `Agent(tools=[async_callable])` registra e invoca tool async.
  2. `tool_context.state` è leggibile/scrivibile dentro un tool.
  3. Gli event stream da `runner.run_async` espongono `function_call`,
     `function_response` e `usage_metadata` per turno.
  4. Un tool async che fa lavoro asincrono (e.g. `asyncio.sleep`) non
     deadlocka né blocca il loop del runner.

Niente chiamate Gemini reali: usiamo un fake `BaseLlm` che emette risposte
scriptate (tool call → tool response → final text).
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

import pytest
from google.adk import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types


class ScriptedLlm(BaseLlm):
    """Fake LLM that walks through a pre-baked list of LlmResponse objects.

    Each call to `generate_content_async` yields one response from the script.
    The Agent will keep calling us until it sees a non-partial response with
    `turn_complete=True` and no function_call (i.e. a final text).
    """

    script: list[LlmResponse] = []
    _cursor: int = 0

    model_config = {"arbitrary_types_allowed": True}

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if self._cursor >= len(self.script):
            # Out of script — emit a terminal "done" message so ADK stops.
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


def _fn_call_response(name: str, args: dict[str, Any]) -> LlmResponse:
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


def _final_text_response(text: str) -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=text)],
        ),
        turn_complete=True,
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=3,
            candidates_token_count=2,
            total_token_count=5,
        ),
    )


@pytest.mark.asyncio
async def test_adk_async_tool_with_state_and_events():
    """Single end-to-end test that asserts all 4 smoke-test points."""
    tool_call_log: list[dict[str, Any]] = []

    async def my_async_tool(query: str, tool_context=None) -> dict[str, Any]:
        """A tool that does async work and writes/reads state."""
        # Point 4: real async work must not deadlock the runner.
        await asyncio.sleep(0)

        # Point 2a: state is readable & writable from inside the tool.
        prev_count = (tool_context.state.get("turn_counter") or 0) if tool_context else 0
        turn = prev_count + 1
        if tool_context is not None:
            tool_context.state["turn_counter"] = turn
            tool_context.state["last_query"] = query

        tool_call_log.append({"turn": turn, "query": query})
        return {"echo": query, "turn": turn}

    my_async_tool.__annotations__ = {
        "query": str,
        "tool_context": Any,
        "return": dict,
    }

    # Script:
    #   1. model calls my_async_tool with query="ping"
    #   2. model sees tool result, emits final text
    scripted = ScriptedLlm(
        model="scripted-test",
        script=[
            _fn_call_response("my_async_tool", {"query": "ping"}),
            _final_text_response("ok"),
        ],
    )

    agent = Agent(
        model=scripted,
        name="smoke_agent",
        description="ADK smoke test",
        instruction="You are a test agent.",
        tools=[my_async_tool],
    )
    runner = InMemoryRunner(agent=agent, app_name="smoke")

    user_id = "u"
    session_id = "s"
    await runner.session_service.create_session(
        app_name="smoke", user_id=user_id, session_id=session_id
    )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text="please call the tool")],
    )

    # Point 3: collect all events to inspect function_call / function_response / usage.
    events = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        events.append(event)

    # --- Point 1: tool was actually invoked (async!) ---
    assert tool_call_log == [{"turn": 1, "query": "ping"}], (
        f"Expected exactly one async tool invocation, got {tool_call_log}"
    )

    # --- Point 2b: state survived and is observable post-run ---
    session = await runner.session_service.get_session(
        app_name="smoke", user_id=user_id, session_id=session_id
    )
    assert session.state.get("turn_counter") == 1
    assert session.state.get("last_query") == "ping"

    # --- Point 3: events expose function_call AND function_response ---
    function_calls = []
    function_responses = []
    usage_seen = []
    for ev in events:
        function_calls.extend(ev.get_function_calls() or [])
        function_responses.extend(ev.get_function_responses() or [])
        if ev.usage_metadata is not None:
            usage_seen.append(ev.usage_metadata)

    assert len(function_calls) == 1, f"Expected 1 function_call, got {len(function_calls)}"
    assert function_calls[0].name == "my_async_tool"
    assert function_calls[0].args == {"query": "ping"}

    assert len(function_responses) == 1, (
        f"Expected 1 function_response, got {len(function_responses)}"
    )
    fr = function_responses[0]
    # The tool's return dict should be reachable from the response payload.
    assert fr.name == "my_async_tool"
    # Different ADK versions wrap it slightly differently — accept either shape.
    assert (
        fr.response == {"echo": "ping", "turn": 1}
        or fr.response.get("result") == {"echo": "ping", "turn": 1}
    ), f"function_response payload shape unexpected: {fr.response!r}"

    # --- Point 3b: usage_metadata flowed through at least one event ---
    assert usage_seen, "Expected at least one event carrying usage_metadata"
    # Token totals come from our scripted responses (10+5+15 first, 3+2+5 second).
    total_input = sum(u.prompt_token_count or 0 for u in usage_seen)
    total_output = sum(u.candidates_token_count or 0 for u in usage_seen)
    assert total_input == 13, f"Expected prompt tokens 10+3=13, got {total_input}"
    assert total_output == 7, f"Expected candidate tokens 5+2=7, got {total_output}"
