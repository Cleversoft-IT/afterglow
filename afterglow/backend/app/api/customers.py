"""Customers API — lookup by id or by phone (for caller card).

Session-aware: demo callers see their own clone first (clone-on-write done in
the orchestrator the first time a call lands on a seed phone). If no clone
exists yet, the seed customer is surfaced read-only so the caller-memory
card on the dialer can still light up on the first ring.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter_seedable,
)
from app.db.engine import get_session
from app.db.models import Customer
from app.schemas import CustomerCard, CustomerProfileView

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("", response_model=list[CustomerCard])
async def list_customers(
    q: Optional[str] = None,
    limit: int = 50,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> list[CustomerCard]:
    capped = max(1, min(limit, 200))
    stmt = (
        select(Customer)
        .where(visibility_filter_seedable(Customer.session_id, Customer.is_seed, ctx))
        .order_by(
            Customer.last_call_at.desc().nulls_last(),
            Customer.created_at.desc(),
        )
        .limit(capped)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Customer.phone_e164.ilike(like),
                func.coalesce(Customer.display_name, "").ilike(like),
            )
        )
    rows = list((await session.execute(stmt)).scalars().all())
    # Demo dedup: when a seed and a session clone share the same phone the
    # visibility filter returns both. The clone is the source of truth (it
    # carries the post-call updates), so it wins.
    if ctx.is_demo:
        by_phone: dict[str, Customer] = {}
        for r in rows:
            existing = by_phone.get(r.phone_e164)
            if existing is None or (existing.is_seed and not r.is_seed):
                by_phone[r.phone_e164] = r
        rows = sorted(
            by_phone.values(),
            key=lambda c: (c.last_call_at or c.created_at),
            reverse=True,
        )[:capped]
    return [CustomerCard.model_validate(r, from_attributes=True) for r in rows]


@router.get("/by-phone/{phone_e164}", response_model=CustomerCard | None)
async def get_customer_by_phone(
    phone_e164: str,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> CustomerCard | None:
    if ctx.is_demo:
        clone = (
            await session.execute(
                select(Customer).where(
                    Customer.phone_e164 == phone_e164,
                    Customer.session_id == ctx.session_id,
                )
            )
        ).scalar_one_or_none()
        if clone is not None:
            return CustomerCard.model_validate(clone, from_attributes=True)
        # No clone yet — fall through to the seed row.
        seed = (
            await session.execute(
                select(Customer).where(
                    Customer.phone_e164 == phone_e164,
                    Customer.is_seed.is_(True),
                )
            )
        ).scalar_one_or_none()
        if seed is None:
            return None
        return CustomerCard.model_validate(seed, from_attributes=True)

    row = (
        await session.execute(
            select(Customer).where(
                Customer.phone_e164 == phone_e164,
                Customer.session_id.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return CustomerCard.model_validate(row, from_attributes=True)


@router.get("/{customer_id}", response_model=CustomerProfileView)
async def get_customer(
    customer_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> CustomerProfileView:
    row = (
        await session.execute(
            select(Customer).where(
                Customer.id == customer_id,
                visibility_filter_seedable(
                    Customer.session_id, Customer.is_seed, ctx
                ),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerProfileView.model_validate(row, from_attributes=True)
