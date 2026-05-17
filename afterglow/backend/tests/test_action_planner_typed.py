"""Unit tests for `app.agents.action_planner._make_tool` typed surface.

These tests verify the offline behaviour:
- when `payload_schema` is present, the tool annotation is a Pydantic
  model dynamically built from the schema
- when `payload_schema` is absent, the tool falls back to a `dict`
  annotation (Gemini can still pass `payload_json` as a string)
- the tool, when called with a `tool_context`, records the request
  with the `mutates` flag

We never call the live ADK runner here — that lives in
`afterglow/backend/spikes/spike_adk_typed_tool.py` and requires GOOGLE_API_KEY.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.agents.action_planner import _make_tool, ActionPlannerError, plan_actions


def _get_payload_annotation(tool):
    """Read the tool's payload annotation directly from __annotations__ to
    bypass PEP 563 string-annotation resolution issues. _make_tool sets
    __annotations__ to the live class object, which is what ADK reads too.
    """
    return tool.__annotations__["payload"]


def _booking_action() -> dict[str, Any]:
    # mock_target / mutates live in the catalog; `booking.create` resolves to
    # mutates=True via action_catalog.mutates(key).
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
                "booking_date": {"type": "string", "format": "date"},
            },
            "required": ["party_size", "booking_date"],
            "additionalProperties": False,
        },
    }


def test_make_tool_with_payload_schema_has_pydantic_annotation():
    tool = _make_tool(_booking_action())

    # The dynamic Pydantic model surfaces as the payload annotation.
    payload_type = _get_payload_annotation(tool)

    # It must be a BaseModel subclass with the schema's properties.
    fields = getattr(payload_type, "model_fields", None)
    assert fields is not None, "payload annotation is not a Pydantic model"
    assert "party_size" in fields
    assert "booking_date" in fields


def test_make_tool_records_call_with_mutates_flag():
    tool = _make_tool(_booking_action())
    # Mock the ADK tool_context
    state: dict[str, Any] = {}
    tool_context = SimpleNamespace(state=state)

    payload_model = _get_payload_annotation(tool)
    payload = payload_model(party_size=4, booking_date="2026-05-20")

    result = tool(payload=payload, confidence=0.9, evidence=["table for 4"], tool_context=tool_context)

    assert result == {"queued": "booking.create"}
    items = state["requested_actions"]["items"]
    assert len(items) == 1
    entry = items[0]
    assert entry["action_type"] == "booking.create"
    assert entry["mutates"] is True
    assert entry["payload"] == {"party_size": 4, "booking_date": "2026-05-20"}
    assert entry["evidence"] == ["table for 4"]


def test_make_tool_without_payload_schema_falls_back_to_dict():
    # whatsapp.send_confirmation: mutates=False in the catalog.
    action = {
        "key": "whatsapp.send_confirmation",
        "label": "Send confirmation",
        "execution_mode": "auto",
        "preconditions": [],
        "confidence_threshold": 0.7,
        "evidence_required": False,
    }
    tool = _make_tool(action)
    # No payload_schema → Optional[dict] annotation (ADK 1.18+ rejects a
    # `None` default on a bare `dict`-typed parameter, so the fallback
    # branch uses an explicit union).
    from typing import Optional
    assert _get_payload_annotation(tool) == Optional[dict]

    state: dict[str, Any] = {}
    tool_context = SimpleNamespace(state=state)
    tool(payload={"customer_name": "Marco"}, confidence=0.8, evidence=[], tool_context=tool_context)
    assert state["requested_actions"]["items"][0]["payload"] == {"customer_name": "Marco"}


def test_make_tool_coerces_json_string_when_no_schema():
    """When Gemini regresses and sends `payload` as a JSON string instead
    of an object, the dict fallback tool parses it."""
    action = {
        "key": "x.y",
        "label": "x",
        "execution_mode": "auto",
        "preconditions": [],
        "confidence_threshold": 0.7,
        "evidence_required": False,
    }
    tool = _make_tool(action)
    state: dict[str, Any] = {}
    tool_context = SimpleNamespace(state=state)
    tool(payload='{"a": 1}', tool_context=tool_context)  # type: ignore[arg-type]
    assert state["requested_actions"]["items"][0]["payload"] == {"a": 1}


def _booking_action_with_optionals() -> dict[str, Any]:
    # Schema mirroring the seed restaurant template: `occasion` and
    # `seating_preference` are optional `{"type": "string"}` — null is NOT
    # in the type union, so an `{"occasion": null}` payload would fail
    # jsonschema.validate downstream.
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
                "booking_date": {"type": "string", "format": "date"},
                "occasion": {"type": "string"},
                "seating_preference": {"type": "string"},
            },
            "required": ["party_size", "booking_date"],
            "additionalProperties": False,
        },
    }


def test_typed_tool_drops_none_values_from_payload():
    """Regression for the 2026-05-17 prod incident: Gemini emitted
    `{"occasion": null, ...}` for optional string fields and the executor's
    jsonschema.validate rejected it with `"None is not of type 'string'"`,
    flipping the action to status='validation_failed'. The planner must
    strip null values before recording the request so downstream validation
    only sees keys with real values."""
    tool = _make_tool(_booking_action_with_optionals())
    state: dict[str, Any] = {}
    tool_context = SimpleNamespace(state=state)

    payload_model = _get_payload_annotation(tool)
    # Gemini emits null for optional fields when uncertain — replicate that.
    payload = payload_model(
        party_size=3,
        booking_date="2026-05-23",
        occasion=None,
        seating_preference=None,
    )
    tool(payload=payload, confidence=0.9, evidence=["table for three"], tool_context=tool_context)

    recorded = state["requested_actions"]["items"][0]["payload"]
    assert recorded == {"party_size": 3, "booking_date": "2026-05-23"}
    assert "occasion" not in recorded
    assert "seating_preference" not in recorded


def test_dict_fallback_tool_drops_none_values_from_payload():
    """Same regression as above, but for the dict-fallback branch (used
    when an action has no payload_schema)."""
    action = {
        "key": "whatsapp.send_confirmation",
        "label": "Send confirmation",
        "execution_mode": "auto",
        "preconditions": [],
        "confidence_threshold": 0.7,
        "evidence_required": False,
    }
    tool = _make_tool(action)
    state: dict[str, Any] = {}
    tool_context = SimpleNamespace(state=state)
    tool(
        payload={"customer_name": "Marco", "channel": None, "booking_date": None},
        tool_context=tool_context,
    )
    recorded = state["requested_actions"]["items"][0]["payload"]
    assert recorded == {"customer_name": "Marco"}
    assert "channel" not in recorded
    assert "booking_date" not in recorded


def test_plan_actions_raises_when_no_api_key(monkeypatch):
    """plan_actions must fail-fast (no fallback) when GOOGLE_API_KEY is unset."""
    import app.agents.action_planner as ap

    monkeypatch.setattr(ap.settings, "google_api_key", "")

    # Minimal stubs
    template = SimpleNamespace(action_types=[_booking_action()])
    customer = SimpleNamespace(display_name="Marco", phone_e164="+15551112233")
    analysis = SimpleNamespace(
        fields=[], planned_actions=[], intent="x", sentiment="x",
        urgency="low", language="en", next_call_briefing="",
    )
    import asyncio

    async def go():
        await ap.plan_actions(
            analysis=analysis,
            template=template,
            customer=customer,
            transcript_text="",
        )

    with pytest.raises(ActionPlannerError):
        asyncio.run(go())
