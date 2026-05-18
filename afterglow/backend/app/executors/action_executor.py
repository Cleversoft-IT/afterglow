"""Deterministic (non-LLM) action executor.

Runs ONE action at a time against the action catalog, writing an audit row +
an ExecutedAction record. Two execution paths based on the catalog entry's
`integration_kind`:

  - `mock_external`: dispatch to `MOCK_REGISTRY`. Result stamped `mock=True`
    so the UI shows the "Simulated" badge.
  - `internal_real`:  dispatch to `INTERNAL_HANDLERS`. Result stamped
    `mock=False`. Postgres rows actually change (e.g. customer profile).

Actions marked `manual-only` are NOT executed automatically — they land as
`status='manual_required'` so the operator sees them in the post-call screen.

Enforcement on top of the catalog dispatch:
- `evidence_required=True` + empty evidence → refused, never reaches the catalog.
- `payload_schema` present → `jsonschema.validate(payload, schema)` before
  dispatch; validation failure → status=`validation_failed`.
- `mutates` is read from `action_catalog` (single source of truth) and
  flagged in audit + ExecutedAction.result["mutates"].

**No-raise contract**: `execute_single_action` MUST translate every failure
(validation, evidence, handler exception) into an `ExecutedAction` row with
the appropriate status. It never propagates exceptions to the caller — this
is what lets the agentic pipeline keep ExecutedAction rows visible even
when the agent loop later fails or stalls (see `agents/call_agent.py`).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

import jsonschema
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import audit_step
from app.db.models import Call, Customer, ExecutedAction, Template
from app.integrations import action_catalog
from app.integrations.internal import INTERNAL_HANDLERS, INTERNAL_REVERTERS
from app.integrations.mocks import MOCK_REGISTRY

logger = logging.getLogger("afterglow")


def _index_actions(template: Template) -> dict[str, dict[str, Any]]:
    return {a["key"]: a for a in template.action_types if a.get("key")}


def _refuse(
    *,
    call: Call,
    customer: Optional[Customer],
    template_action: dict[str, Any],
    entry: dict[str, Any],
    reason: str,
) -> ExecutedAction:
    return ExecutedAction(
        id=uuid.uuid4(),
        call_id=call.id,
        customer_id=customer.id if customer else None,
        action_type=template_action["key"],
        title=entry.get("title") or template_action.get("label") or template_action["key"],
        summary=entry.get("summary"),
        payload=entry.get("payload", {}),
        confidence=entry.get("confidence"),
        evidence=entry.get("evidence"),
        execution_mode=template_action.get("execution_mode", "auto"),
        status=reason,
        result={"refused": reason, "mutates": action_catalog.mutates(template_action["key"])},
        session_id=call.session_id,
    )


async def execute_single_action(
    session: AsyncSession,
    *,
    call: Call,
    customer: Optional[Customer],
    template: Template,
    entry: dict[str, Any],
    agent_turn: Optional[int] = None,
) -> Optional[ExecutedAction]:
    """Run ONE action and persist its ExecutedAction row.

    Returns the persisted row, or ``None`` when the action_type is not in
    the active template (hallucinated tool call — audited as `rejected` but
    no ExecutedAction is created on purpose).

    `agent_turn` is forwarded into the audit payload so the UI trail can
    pin the action under its source agent turn deterministically.

    Layered safety net:
      1. Hallucinated action_type (not in template) → audited + return None.
      2. `evidence_required=True` + empty evidence → refused.
      3. `payload_schema` present → jsonschema validation; on failure refused.
      4. Otherwise: invoke MOCK_REGISTRY for `auto`, queue `manual_required`
         for `manual-only`. The execution_mode is read from the TEMPLATE,
         never from the plan entry.
      5. Handler exceptions (mock/internal) are caught and surfaced as
         `status="failed"` with the exception text in `result.error`.
    """
    actions_by_key = _index_actions(template)
    action_type = entry["action_type"]
    template_action = actions_by_key.get(action_type)

    if template_action is None:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="action_executor",
            step_type="rejected",
            payload={
                "action_type": action_type,
                "reason": "action_type not in template",
                "agent_turn": agent_turn,
            },
        ):
            pass
        return None

    mode = template_action.get("execution_mode", "auto")
    mutates = action_catalog.mutates(action_type)
    evidence_required = bool(template_action.get("evidence_required", True))
    payload_schema = template_action.get("payload_schema")
    payload = entry.get("payload", {}) or {}
    evidence = entry.get("evidence") or []

    if evidence_required and not evidence:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="action_executor",
            step_type="rejected",
            payload={
                "action_type": action_type,
                "reason": "evidence_required",
                "agent_turn": agent_turn,
            },
        ):
            pass
        record = _refuse(
            call=call, customer=customer, template_action=template_action,
            entry=entry, reason="evidence_missing",
        )
        session.add(record)
        await session.flush()
        return record

    if isinstance(payload_schema, dict):
        try:
            jsonschema.validate(payload, payload_schema)
        except jsonschema.ValidationError as exc:
            async with audit_step(
                call_id=call.id,
                session_id=call.session_id,
                agent_name="action_executor",
                step_type="rejected",
                payload={
                    "action_type": action_type,
                    "reason": "payload_schema",
                    "error": exc.message,
                    "agent_turn": agent_turn,
                },
            ):
                pass
            record = _refuse(
                call=call, customer=customer, template_action=template_action,
                entry=entry, reason="validation_failed",
            )
            session.add(record)
            await session.flush()
            return record

    record = ExecutedAction(
        id=uuid.uuid4(),
        call_id=call.id,
        customer_id=customer.id if customer else None,
        action_type=action_type,
        title=entry.get("title") or template_action.get("label") or action_type,
        summary=entry.get("summary"),
        payload=payload,
        confidence=entry.get("confidence"),
        evidence=evidence,
        execution_mode=mode,
        status="executed" if mode == "auto" else "manual_required",
        session_id=call.session_id,
    )

    if mode == "auto":
        catalog_entry = action_catalog.get(action_type)
        integration_kind = (
            catalog_entry.integration_kind if catalog_entry else "mock_external"
        )
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="action_executor",
            step_type="action_exec",
            payload={
                "action_type": action_type,
                "integration_kind": integration_kind,
                "mutates": mutates,
                "agent_turn": agent_turn,
            },
        ):
            try:
                if integration_kind == "internal_real":
                    record.result = _run_internal_real(
                        catalog_entry, customer=customer, payload=payload, mutates=mutates
                    )
                    if not record.result.get("applied"):
                        record.status = "failed"
                else:
                    record.result = _run_mock_external(action_type, payload, mutates=mutates)
                    if "error" in record.result:
                        record.status = "failed"
            except Exception as exc:  # noqa: BLE001
                # Mock/internal handler crashed unexpectedly. Translate to
                # status=failed so the no-raise contract is preserved.
                logger.warning(
                    "action_executor: %s handler raised (%s) — recording as failed",
                    action_type, exc,
                )
                record.status = "failed"
                record.result = {
                    "error": f"handler_exception: {exc}"[:500],
                    "mutates": mutates,
                    "mock": (
                        catalog_entry is None
                        or catalog_entry.integration_kind == "mock_external"
                    ),
                }
    else:
        # manual-only: still surface mutates flag so the UI can render the
        # right warning ("irreversible — confirm before running"), and
        # carry integration_kind so the UI knows whether a future manual
        # run would touch real records or stubs.
        catalog_entry = action_catalog.get(action_type)
        record.result = {
            "mutates": mutates,
            "mock": (
                catalog_entry is None
                or catalog_entry.integration_kind == "mock_external"
            ),
        }

    session.add(record)
    await session.flush()
    return record


async def execute_planned_actions(
    session: AsyncSession,
    *,
    call: Call,
    customer: Optional[Customer],
    template: Template,
    plan: list[dict[str, Any]],
) -> list[ExecutedAction]:
    """Batch wrapper around `execute_single_action` — preserved for the legacy
    callers (and `test_action_executor_validation.py`). The agentic pipeline
    now calls `execute_single_action` directly from each action tool, one at
    a time, so this path is only exercised by tests."""
    persisted: list[ExecutedAction] = []
    for entry in plan:
        record = await execute_single_action(
            session,
            call=call,
            customer=customer,
            template=template,
            entry=entry,
        )
        if record is not None:
            persisted.append(record)
    return persisted


def _run_mock_external(
    action_type: str, payload: dict[str, Any], *, mutates: bool
) -> dict[str, Any]:
    mock_fn = MOCK_REGISTRY.get(action_type)
    if mock_fn is None:
        # Unknown action key but still in mock_external bucket — surface the
        # failure with `mock=True` so the UI badge stays honest.
        return {
            "error": f"no mock for {action_type}",
            "mutates": mutates,
            "mock": True,
        }
    mock_result = mock_fn(payload) or {}
    if not isinstance(mock_result, dict):
        mock_result = {"value": mock_result}
    return {**mock_result, "mutates": mutates, "mock": True}


def _run_internal_real(
    catalog_entry: Optional["action_catalog.ActionCatalogEntry"],
    *,
    customer: Optional[Customer],
    payload: dict[str, Any],
    mutates: bool,
) -> dict[str, Any]:
    if customer is None or catalog_entry is None or not catalog_entry.internal_handler:
        return {
            "applied": False,
            "error": "no_customer_or_handler",
            "mutates": mutates,
            "mock": False,
        }
    handler = INTERNAL_HANDLERS.get(catalog_entry.internal_handler)
    if handler is None:
        return {
            "applied": False,
            "error": f"unknown_internal_handler:{catalog_entry.internal_handler}",
            "mutates": mutates,
            "mock": False,
        }
    out = handler(customer, payload)
    # Stamp `mutates`/`mock` from the catalog (single source of truth) and
    # carry the handler name so the reverter can be re-resolved on undo.
    out["mutates"] = mutates
    out["mock"] = False
    out["internal_handler"] = catalog_entry.internal_handler
    return out


async def undo_action(
    session: AsyncSession,
    action: ExecutedAction,
    *,
    customer: Optional[Customer] = None,
    reverted_by: str = "operator",
) -> ExecutedAction:
    """Move an executed action into `undone` state + emit an audit row.

    For internal_real actions whose handler registered a reverter (today:
    `customer_profile.apply_update`) we also REPLAY the previous_state
    snapshot onto the customer row, so undoing a tag-add actually removes
    the tag from Postgres. For mock_external actions this is purely a
    status flip — the mock "world" has no memory of past calls anyway.

    Idempotent: undoing an already-undone action is a no-op.
    """
    if action.status in ("undone", "reverted"):
        return action

    from datetime import datetime, timezone

    reverter_summary: dict[str, Any] = {"replayed": False}
    if (
        customer is not None
        and isinstance(action.result, dict)
        and action.result.get("internal_handler")
    ):
        reverter = INTERNAL_REVERTERS.get(action.result["internal_handler"])
        if reverter is not None:
            reverter_summary = reverter(customer, action)

    async with audit_step(
        call_id=action.call_id,
        session_id=action.session_id,
        agent_name="action_executor",
        step_type="undo",
        payload={
            "action_id": str(action.id),
            "action_type": action.action_type,
            "by": reverted_by,
            "reverter": reverter_summary,
        },
    ):
        action.status = "undone"
        action.reverted_at = datetime.now(tz=timezone.utc)
        action.reverted_by = reverted_by

    await session.flush()
    return action


async def redo_action(
    session: AsyncSession, action: ExecutedAction, *, redone_by: str = "operator"
) -> ExecutedAction:
    """Flip an undone action back to `executed`. Status-only — no replay of
    the underlying mock or internal handler.

    Idempotent: redoing an action that is already executed is a no-op.
    """
    if action.status != "undone":
        return action

    async with audit_step(
        call_id=action.call_id,
        session_id=action.session_id,
        agent_name="action_executor",
        step_type="redo",
        payload={
            "action_id": str(action.id),
            "action_type": action.action_type,
            "by": redone_by,
        },
    ):
        action.status = "executed"
        action.reverted_at = None
        action.reverted_by = None

    await session.flush()
    return action


# Backwards-compat alias for the existing /actions/{id}/revert endpoint and
# any test that still imports the old name. New code should call undo_action
# / redo_action directly.
revert_action = undo_action
