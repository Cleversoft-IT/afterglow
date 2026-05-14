"""Deterministic (non-LLM) action executor.

Walks the planned actions and runs each one against the mock registry, writing
audit rows + ExecutedAction records. Actions marked `manual-only` are NOT
executed automatically — they land as `status='manual_required'` so the operator
sees them in the post-call screen and can trigger them by hand.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import audit_step
from app.db.models import Call, Customer, ExecutedAction, Template
from app.integrations.mocks import MOCK_REGISTRY


async def execute_planned_actions(
    session: AsyncSession,
    *,
    call: Call,
    customer: Optional[Customer],
    template: Template,
    plan: list[dict[str, Any]],
) -> list[ExecutedAction]:
    """Run every action in `plan`. Return the persisted ExecutedAction rows."""
    action_modes = {a["key"]: a.get("execution_mode", "auto") for a in template.action_types}

    persisted: list[ExecutedAction] = []
    for entry in plan:
        action_type = entry["action_type"]
        mode = action_modes.get(action_type, entry.get("execution_mode", "auto"))

        record = ExecutedAction(
            id=uuid.uuid4(),
            call_id=call.id,
            customer_id=customer.id if customer else None,
            action_type=action_type,
            title=entry["title"],
            summary=entry.get("summary"),
            payload=entry.get("payload", {}),
            confidence=entry.get("confidence"),
            evidence=entry.get("evidence"),
            execution_mode=mode,
            status="executed" if mode == "auto" else "manual_required",
        )

        if mode == "auto":
            async with audit_step(
                session,
                call_id=call.id,
                agent_name="action_executor",
                step_type="action_exec",
                payload={"action_type": action_type},
            ):
                mock_fn = MOCK_REGISTRY.get(action_type)
                if mock_fn is None:
                    record.status = "failed"
                    record.result = {"error": f"no mock for {action_type}"}
                else:
                    record.result = mock_fn(entry.get("payload", {}))

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
        session,
        call_id=action.call_id,
        agent_name="action_executor",
        step_type="revert",
        payload={"action_id": str(action.id), "action_type": action.action_type, "by": reverted_by},
    ):
        action.status = "reverted"
        action.reverted_at = datetime.now(tz=timezone.utc)
        action.reverted_by = reverted_by

    await session.flush()
    return action
