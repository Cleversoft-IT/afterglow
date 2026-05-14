"""Actions API — revert an executed action."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.models import ExecutedAction
from app.executors.action_executor import revert_action
from app.schemas import CallActionView

router = APIRouter(prefix="/api/v1/actions", tags=["actions"])


@router.post("/{action_id}/revert", response_model=CallActionView)
async def revert(
    action_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> CallActionView:
    row = (
        await session.execute(
            select(ExecutedAction).where(ExecutedAction.id == action_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Action not found")

    await revert_action(session, row)
    await session.commit()

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
    )
