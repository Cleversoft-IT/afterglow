"""Actions API — undo / redo an executed action, expose the catalog."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter_seedable,
)
from app.db.engine import get_session
from app.db.models import Customer, ExecutedAction
from app.executors.action_executor import redo_action, undo_action
from app.integrations import action_catalog
from app.schemas import CallActionView

router = APIRouter(prefix="/api/v1/actions", tags=["actions"])


async def _resolve_action(
    session: AsyncSession, action_id: uuid.UUID, ctx: SessionContext
) -> ExecutedAction:
    row = (
        await session.execute(
            select(ExecutedAction).where(
                ExecutedAction.id == action_id,
                visibility_filter_seedable(
                    ExecutedAction.session_id, ExecutedAction.is_seed, ctx
                ),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return row


async def _customer_for(
    session: AsyncSession, action: ExecutedAction
) -> Optional[Customer]:
    if action.customer_id is None:
        return None
    return (
        await session.execute(
            select(Customer).where(Customer.id == action.customer_id)
        )
    ).scalar_one_or_none()


def _project(row: ExecutedAction) -> CallActionView:
    return CallActionView(
        id=row.id,
        action_type=row.action_type,
        title=row.title,
        summary=row.summary,
        payload=row.payload or {},
        result=row.result,
        confidence=row.confidence,
        evidence=row.evidence,
        execution_mode=row.execution_mode,
        status=row.status,
        reverted_at=row.reverted_at,
        created_at=row.created_at,
        is_simulated=action_catalog.is_simulated(row.action_type),
        can_undo=action_catalog.can_undo(row.action_type),
    )


@router.get("/catalog")
async def list_catalog() -> list[dict]:
    """Return every action entry the catalog knows about.

    The wizard chat reads this to suggest valid action keys; the template
    validator reads it to flag template entries whose key has no registered
    handler. UI clients use it to know `is_simulated` / `can_undo`
    declaratively without having to maintain a parallel table.
    """
    return [entry.to_dict() for entry in action_catalog.CATALOG.values()]


@router.post("/{action_id}/undo", response_model=CallActionView)
async def undo(
    action_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> CallActionView:
    row = await _resolve_action(session, action_id, ctx)
    customer = await _customer_for(session, row)
    await undo_action(session, row, customer=customer)
    await session.commit()
    return _project(row)


@router.post("/{action_id}/redo", response_model=CallActionView)
async def redo(
    action_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> CallActionView:
    row = await _resolve_action(session, action_id, ctx)
    await redo_action(session, row)
    await session.commit()
    return _project(row)


# Backwards-compat alias for the historical endpoint. New clients should
# call /undo directly.
@router.post("/{action_id}/revert", response_model=CallActionView)
async def revert(
    action_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> CallActionView:
    return await undo(action_id=action_id, ctx=ctx, session=session)
