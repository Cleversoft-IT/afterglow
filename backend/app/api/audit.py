"""Audit log API — production-shape visibility into every agent step."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter,
)
from app.db.engine import get_session
from app.db.models import AuditLog, Call, Customer
from app.schemas import AuditLogEntry

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def _audit_visibility(ctx: SessionContext) -> ColumnElement:
    """Demo visitors see their own steps plus seed pipeline rows.

    Seed audit rows keep ``session_id IS NULL`` (written before any demo
    session exists). Calls/bookings use ``visibility_filter_seedable`` via
    ``Call.is_seed``; audit must join the call for the same behaviour.
    """
    base = visibility_filter(AuditLog.session_id, ctx)
    if not ctx.is_demo:
        return base
    seed_call_ids = select(Call.id).where(Call.is_seed.is_(True))
    return or_(
        base,
        and_(AuditLog.session_id.is_(None), AuditLog.call_id.in_(seed_call_ids)),
    )


@router.get("", response_model=list[AuditLogEntry])
async def list_audit(
    call_id: Optional[uuid.UUID] = Query(None),
    agent_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> list[AuditLogEntry]:
    stmt = (
        select(
            AuditLog,
            Call.phone_e164,
            Call.status,
            Customer.display_name,
        )
        .join(Call, Call.id == AuditLog.call_id, isouter=True)
        .join(Customer, Customer.id == Call.customer_id, isouter=True)
        .where(_audit_visibility(ctx))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if call_id:
        stmt = stmt.where(AuditLog.call_id == call_id)
    if agent_name:
        stmt = stmt.where(AuditLog.agent_name == agent_name)
    rows = (await session.execute(stmt)).all()

    out: list[AuditLogEntry] = []
    for row, phone, call_status, display_name in rows:
        entry = AuditLogEntry.model_validate(row, from_attributes=True)
        entry.call_phone_e164 = phone
        entry.call_status = call_status
        entry.call_display_name = display_name
        out.append(entry)
    return out
