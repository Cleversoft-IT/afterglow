"""Spike: can google.adk introspect a dynamically-built Pydantic model
annotation on a tool callable and route a typed payload to it?

Why we need to know: the Action Planner today exposes one tool per
auto-mode action_type, with a `payload_json: str` parameter. Templates v2
declares a `payload_schema` (JSONSchema) per action, and we want the ADK
FunctionDeclaration to expose those typed parameters directly to Gemini so
the model produces a structured object — not a JSON string that we have to
parse and pray for.

The plan calls this spike a gate (see
`.claude/plans/non-hai-capito-non-sequential-mist.md` Blocco 0a). It runs in
two phases:

1. **Offline phase**: build a Pydantic model with `pydantic.create_model`,
   wrap it in a tool callable, hand it to `google.adk.Agent`, and verify the
   ADK side does not raise during introspection / `InMemoryRunner`
   construction. This phase does *not* call Gemini and runs even without an
   API key.
2. **Live phase**: with `GOOGLE_API_KEY` set, actually issue one agent turn
   and assert the tool received a dict whose keys come from the dynamic
   Pydantic model. Skipped otherwise.

Run with:
    cd afterglow/backend && pytest spikes/spike_adk_typed_tool.py -q -s

A green spike means Blocco 2 `_make_tool` can use the typed approach. A red
spike means we fall back to plain `payload: dict` with executor-side
jsonschema validation (also designed in the plan).
"""
from __future__ import annotations

import asyncio
import os
from datetime import date
from typing import Any, Optional

import pytest
from pydantic import BaseModel, create_model


def _build_dynamic_payload_model() -> type[BaseModel]:
    """Mirror what `_make_tool` will do at runtime: turn a JSONSchema-ish
    spec into a Pydantic model via `create_model`. The schema is the one
    on `seed.RESTAURANT_TEMPLATE["action_types"][0].payload_schema` minus
    `required` (Pydantic represents required by `...`).
    """
    return create_model(
        "BookingCreatePayload",
        party_size=(int, ...),
        booking_date=(str, ...),
        booking_time=(str, ...),
        customer_name=(str, ...),
        seating_preference=(Optional[str], None),
        occasion=(Optional[str], None),
    )


def _capture_box() -> dict[str, Any]:
    """Mutable container so the closure-tool can write back without
    relying on ADK's tool_context.state (the offline phase does not have a
    real session running).
    """
    return {"captured": None}


def _make_typed_tool(payload_model: type[BaseModel], capture: dict[str, Any]):
    """Build the closure exactly the way Blocco 2 `_make_tool` will.

    Crucially, the annotation on `payload` is the *dynamic* Pydantic model
    — not a forward ref, not Any. ADK reads `__annotations__` during agent
    construction; this is the line that breaks if ADK cannot serialize a
    dynamic Pydantic model into a FunctionDeclaration.
    """

    def booking_create(
        payload: payload_model,  # type: ignore[valid-type]
        evidence: list[str],
        confidence: float = 0.9,
        tool_context: Any = None,
    ) -> dict[str, Any]:
        """Queue a booking.create request. Returns {queued: True}."""
        # Pydantic v2 models expose .model_dump(); plain dicts (if ADK
        # downcasts) also pass through.
        if hasattr(payload, "model_dump"):
            payload_dict = payload.model_dump()
        elif isinstance(payload, dict):
            payload_dict = payload
        else:
            payload_dict = {"raw": str(payload)}

        capture["captured"] = {
            "payload": payload_dict,
            "evidence": evidence,
            "confidence": confidence,
        }

        # Also write to ADK session state when running live, so the same
        # consumer pattern used by action_planner.py works.
        if tool_context is not None and hasattr(tool_context, "state"):
            bucket = tool_context.state.setdefault(
                "requested_actions", {"items": []}
            )
            bucket["items"].append(
                {
                    "action_type": "booking.create",
                    "payload": payload_dict,
                    "evidence": evidence,
                    "confidence": float(confidence),
                }
            )

        return {"queued": True}

    booking_create.__name__ = "booking_create"
    return booking_create


def test_phase1_adk_accepts_dynamic_pydantic_annotation() -> None:
    """Offline gate: does `google.adk.Agent(tools=[...])` raise when a tool
    has a dynamically-built Pydantic annotation? If yes, the typed approach
    is dead and we fall back to `payload: dict`. If no, proceed.
    """
    payload_model = _build_dynamic_payload_model()
    capture = _capture_box()
    tool = _make_typed_tool(payload_model, capture)

    # Import here so the spike can be collected even on machines without
    # google-adk installed (it will skip instead of erroring at import time).
    google_adk = pytest.importorskip("google.adk")

    agent = google_adk.Agent(
        model=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-flash-latest"),
        name="spike_booking_planner",
        description="Spike agent: verifies ADK handles dynamic Pydantic.",
        instruction=(
            "You are a spike. Always call booking_create exactly once with "
            "party_size=2, booking_date='2026-05-20', booking_time='20:30', "
            "customer_name='Mario Rossi', evidence=['spike test']."
        ),
        tools=[tool],
    )

    # Constructing the InMemoryRunner forces ADK to finalize the
    # FunctionDeclaration list. If anything is going to choke on the
    # dynamic Pydantic annotation, this is where it happens.
    runner_mod = pytest.importorskip("google.adk.runners")
    runner = runner_mod.InMemoryRunner(agent=agent, app_name="spike")

    assert runner is not None, "InMemoryRunner build returned None"


@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="needs GOOGLE_API_KEY to actually call Gemini",
)
def test_phase2_live_gemini_routes_typed_payload() -> None:
    """Live gate: with a real API key, send one turn and assert the tool
    received a dict whose keys come from the dynamic Pydantic model.
    """
    payload_model = _build_dynamic_payload_model()
    capture = _capture_box()
    tool = _make_typed_tool(payload_model, capture)

    from app.integrations.gemini_adk import AdkAgentSpec, create_runner, run_agent

    spec = AdkAgentSpec(
        name="spike_booking_planner",
        description="Spike agent: verifies typed payload routing.",
        instruction=(
            "Always call booking_create exactly once with party_size=2, "
            "booking_date='2026-05-20', booking_time='20:30', "
            "customer_name='Mario Rossi', evidence=['spike test']. "
            "Then stop."
        ),
        tools=[tool],
    )
    runner = create_runner(spec)

    result = asyncio.run(
        run_agent(
            runner,
            prompt_text="Schedule the booking now.",
            state_key="requested_actions",
        )
    )

    assert "items" in result, f"no items in result: {result!r}"
    assert result["items"], "agent did not invoke the tool"

    first = result["items"][0]
    payload = first["payload"]
    assert isinstance(payload, dict), f"payload is not a dict: {payload!r}"
    assert payload.get("party_size") == 2, payload
    assert payload.get("booking_date") == "2026-05-20", payload
    assert payload.get("customer_name") == "Mario Rossi", payload
