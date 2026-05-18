"""Action tools — one per `template.action_types` entry, executed inline.

Difference from the legacy single-turn planner (`agents/action_planner.py`,
now deleted): when the agent invokes an action tool, the action is
**executed immediately** through `executors.action_executor.execute_single_action`,
and the result (`executed`/`validation_failed`/`evidence_missing`/`failed`)
flows back to the model as the tool response. The model can then retry
with a corrected payload, change strategy, or call `flag_for_review`.

Self-correction guardrails:
  - per `action_type`, retries are capped at 2 attempts
    (`tool_context.state["attempts"][key]`).
  - mutating actions (`action_catalog.mutates(key) == True`) that already
    executed successfully are refused with `{"refused": "already_executed_mutating"}`
    on subsequent calls — irreversible side effects must not be replayed.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.turn import bump_turn
from app.db.models import Call, Customer, Template
from app.executors.action_executor import execute_single_action
from app.integrations import action_catalog
from app.integrations.jsonschema_to_pydantic import (
    JsonSchemaConversionError,
    jsonschema_to_pydantic,
)

logger = logging.getLogger("afterglow")


_MAX_ATTEMPTS_PER_ACTION = 2


def _format_action_docstring(action_def: dict[str, Any], *, mutates: bool) -> str:
    """Render the tool docstring shown to Gemini in the FunctionDeclaration."""
    lines = [action_def.get("description") or action_def.get("label") or action_def["key"]]
    preconditions = action_def.get("preconditions") or []
    if preconditions:
        lines.append(f"Preconditions (required fields): {', '.join(preconditions)}.")
    threshold = action_def.get("confidence_threshold")
    if threshold is not None:
        lines.append(f"Minimum confidence to invoke: {threshold}.")
    if action_def.get("evidence_required", True):
        lines.append("Evidence is REQUIRED — provide at least one verbatim transcript span.")
    if mutates:
        lines.append("This action mutates external state and CANNOT be replayed after success.")
    lines.append(
        "Invocation result: {status, result, attempt}. status ∈ {executed, "
        "validation_failed, evidence_missing, failed, refused}. On non-success, "
        "you may retry once with a corrected payload — second failures will be refused."
    )
    return "\n".join(lines)


def _track_attempt(tool_context: Any, key: str) -> int:
    if tool_context is None or not hasattr(tool_context, "state"):
        return 1
    attempts = tool_context.state.setdefault("attempts", {})
    attempts[key] = (attempts.get(key) or 0) + 1
    return attempts[key]


def _last_status_for(tool_context: Any, key: str) -> Optional[str]:
    if tool_context is None or not hasattr(tool_context, "state"):
        return None
    return (tool_context.state.get("last_status") or {}).get(key)


def _record_status(tool_context: Any, key: str, status: str) -> None:
    if tool_context is None or not hasattr(tool_context, "state"):
        return
    bucket = tool_context.state.setdefault("last_status", {})
    bucket[key] = status


def make_action_tool(
    action_def: dict[str, Any],
    *,
    session: AsyncSession,
    call: Call,
    customer: Optional[Customer],
    template: Template,
) -> Callable[..., Any]:
    """Build the executable ADK tool callable for one action_type entry.

    Strategy:
    - If `payload_schema` is present, build a Pydantic v2 model dynamically
      and use it as the `payload` annotation. ADK introspects this and emits
      a FunctionDeclaration with typed parameters.
    - Otherwise, fall back to `payload: Optional[dict]` (still validated by
      `execute_single_action` via `jsonschema.validate`).
    """
    key: str = action_def["key"]
    label: str = action_def.get("label") or key
    mutates = action_catalog.mutates(key)
    docstring = _format_action_docstring(action_def, mutates=mutates)
    payload_schema = action_def.get("payload_schema")

    payload_model = None
    if isinstance(payload_schema, dict) and payload_schema.get("type") == "object":
        try:
            payload_model = jsonschema_to_pydantic(payload_schema, name=key)
        except JsonSchemaConversionError as exc:
            logger.warning(
                "action_tool: payload_schema for %s could not be typed (%s); "
                "falling back to dict annotation.",
                key, exc,
            )
            payload_model = None

    async def _execute(payload_dict: dict[str, Any], confidence: float,
                       evidence: list[str], tool_context: Any) -> dict[str, Any]:
        turn = bump_turn(tool_context)
        attempt = _track_attempt(tool_context, key)
        last_status = _last_status_for(tool_context, key)

        # Refuse re-running mutating actions that already succeeded.
        if mutates and last_status == "executed":
            return {
                "status": "refused",
                "result": {"refused": "already_executed_mutating"},
                "attempt": attempt,
                "agent_turn": turn,
            }
        # Hard cap on retries — even non-mutating actions can't loop forever.
        if attempt > _MAX_ATTEMPTS_PER_ACTION:
            return {
                "status": "refused",
                "result": {"refused": "max_attempts_reached"},
                "attempt": attempt,
                "agent_turn": turn,
            }

        entry = {
            "action_type": key,
            "title": label,
            "summary": "",
            "payload": payload_dict,
            "confidence": float(confidence),
            "evidence": list(evidence or []),
        }
        record = await execute_single_action(
            session,
            call=call,
            customer=customer,
            template=template,
            entry=entry,
            agent_turn=turn,
        )
        status = record.status if record is not None else "hallucinated"
        result = record.result if record is not None else {"refused": "action_type not in template"}
        _record_status(tool_context, key, status)
        return {
            "status": status,
            "result": result,
            "attempt": attempt,
            "agent_turn": turn,
        }

    if payload_model is not None:
        async def tool(payload, confidence: float = 0.9,
                       evidence: list[str] = [], tool_context: Any = None) -> dict[str, Any]:
            # Drop None-valued keys so the JSONSchema validator does not
            # reject `null` on optional string/array fields.
            if hasattr(payload, "model_dump"):
                payload_dict = payload.model_dump(exclude_none=True)
            else:
                payload_dict = {k: v for k, v in dict(payload).items() if v is not None}
            return await _execute(payload_dict, confidence, evidence, tool_context)

        tool.__annotations__ = {
            "payload": payload_model,
            "confidence": float,
            "evidence": list[str],
            "tool_context": Any,
            "return": dict,
        }
    else:
        async def tool(payload: Optional[dict] = None, confidence: float = 0.9,
                       evidence: list[str] = [], tool_context: Any = None) -> dict[str, Any]:
            if payload is None:
                payload = {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload or "{}")
                except json.JSONDecodeError:
                    payload = {}
            if not isinstance(payload, dict):
                payload = {"value": payload}
            payload = {k: v for k, v in payload.items() if v is not None}
            return await _execute(payload, confidence, evidence, tool_context)

        tool.__annotations__ = {
            "payload": Optional[dict],
            "confidence": float,
            "evidence": list[str],
            "tool_context": Any,
            "return": dict,
        }

    tool.__name__ = key.replace(".", "_").replace("-", "_")
    tool.__doc__ = docstring
    return tool
