"""Deterministic (non-LLM) action executor.

Walks the planned actions and runs each one against the mock registry, writing
audit rows + ExecutedAction records. Actions marked `manual-only` are NOT
executed automatically — they land as `status='manual_required'` so the operator
sees them in the post-call screen and can trigger them by hand.

Templates v2 enforcement (in addition to the legacy safety net):
- `evidence_required=True` + empty evidence → refused, never reaches MOCK_REGISTRY.
- `payload_schema` present → `jsonschema.validate(payload, schema)` before
  MOCK_REGISTRY; validation failure → status=`validation_failed`.
- `mutates=True` → flagged in audit + ExecutedAction.result["mutates"] so the
  UI marks the row irreversible and the (future) auto-retry loop skips it.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

import jsonschema
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import audit_step
from app.db.models import Call, Customer, ExecutedAction, Template
from app.integrations.mocks import MOCK_REGISTRY


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
        result={"refused": reason, "mutates": bool(template_action.get("mutates"))},
        session_id=call.session_id,
    )


async def execute_planned_actions(
    session: AsyncSession,
    *,
    call: Call,
    customer: Optional[Customer],
    template: Template,
    plan: list[dict[str, Any]],
) -> list[ExecutedAction]:
    """Run every action in `plan`. Return the persisted ExecutedAction rows.

    Layered safety net:
      1. Hallucinated action_type (not in template) → rejected.
      2. `evidence_required=True` + empty evidence → refused.
      3. `payload_schema` present → jsonschema validation; on failure refused.
      4. Otherwise: invoke MOCK_REGISTRY for `auto`, queue `manual_required`
         for `manual-only`. The execution_mode is read from the TEMPLATE,
         never from the plan entry (the planner cannot escalate a
         manual-only action to auto).
    """
    actions_by_key = _index_actions(template)

    persisted: list[ExecutedAction] = []
    for entry in plan:
        action_type = entry["action_type"]
        template_action = actions_by_key.get(action_type)

        if template_action is None:
            async with audit_step(
                call_id=call.id,
                session_id=call.session_id,
                agent_name="action_executor",
                step_type="rejected",
                payload={"action_type": action_type, "reason": "action_type not in template"},
            ):
                pass
            continue

        mode = template_action.get("execution_mode", "auto")
        mutates = bool(template_action.get("mutates", False))
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
                payload={"action_type": action_type, "reason": "evidence_required"},
            ):
                pass
            record = _refuse(
                call=call, customer=customer, template_action=template_action,
                entry=entry, reason="evidence_missing",
            )
            session.add(record)
            persisted.append(record)
            continue

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
                    },
                ):
                    pass
                record = _refuse(
                    call=call, customer=customer, template_action=template_action,
                    entry=entry, reason="validation_failed",
                )
                session.add(record)
                persisted.append(record)
                continue

        record = ExecutedAction(
            id=uuid.uuid4(),
            call_id=call.id,
            customer_id=customer.id if customer else None,
            action_type=action_type,
            title=entry["title"],
            summary=entry.get("summary"),
            payload=payload,
            confidence=entry.get("confidence"),
            evidence=evidence,
            execution_mode=mode,
            status="executed" if mode == "auto" else "manual_required",
            session_id=call.session_id,
        )

        if mode == "auto":
            async with audit_step(
                call_id=call.id,
                session_id=call.session_id,
                agent_name="action_executor",
                step_type="action_exec",
                payload={"action_type": action_type, "mutates": mutates},
            ):
                mock_fn = MOCK_REGISTRY.get(action_type)
                if mock_fn is None:
                    record.status = "failed"
                    record.result = {"error": f"no mock for {action_type}", "mutates": mutates}
                else:
                    mock_result = mock_fn(payload) or {}
                    if not isinstance(mock_result, dict):
                        mock_result = {"value": mock_result}
                    record.result = {**mock_result, "mutates": mutates}
        else:
            # manual-only: still surface mutates flag so the UI can render the
            # right warning ("irreversible — confirm before running").
            record.result = {"mutates": mutates}

        session.add(record)
        persisted.append(record)

    await session.flush()
    return persisted


async def revert_action(
    session: AsyncSession, action: ExecutedAction, *, reverted_by: str = "operator"
) -> ExecutedAction:
    """Mark an action as reverted + emit a compensating audit row.

    Idempotent: reverting an already-reverted action is a no-op.
    """
    if action.status == "reverted":
        return action

    from datetime import datetime, timezone

    async with audit_step(
        call_id=action.call_id,
        session_id=action.session_id,
        agent_name="action_executor",
        step_type="revert",
        payload={"action_id": str(action.id), "action_type": action.action_type, "by": reverted_by},
    ):
        action.status = "reverted"
        action.reverted_at = datetime.now(tz=timezone.utc)
        action.reverted_by = reverted_by

    await session.flush()
    return action
