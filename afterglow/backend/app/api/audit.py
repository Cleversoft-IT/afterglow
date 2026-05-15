"""Audit log API — production-shape visibility into every agent step."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter,
)
from app.db.engine import get_session
from app.db.models import AuditLog
from app.schemas import AuditLogEntry

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogEntry])
async def list_audit(
    call_id: Optional[uuid.UUID] = Query(None),
    agent_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> list[AuditLogEntry]:
    stmt = (
        select(AuditLog)
        .where(visibility_filter(AuditLog.session_id, ctx))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if call_id:
        stmt = stmt.where(AuditLog.call_id == call_id)
    if agent_name:
        stmt = stmt.where(AuditLog.agent_name == agent_name)
    rows = (await session.execute(stmt)).scalars().all()
    return [AuditLogEntry.model_validate(r, from_attributes=True) for r in rows]
