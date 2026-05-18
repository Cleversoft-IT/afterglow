"""Bookings API — list reservation actions across verticals.

"Booking" in the UI covers both restaurant reservations (booking.create) and
clinical/auto-service appointments (appointment.create) — they share the same
operator workflow: a slot got reserved as a result of the call. Cancellations
follow the same pattern. The Home Bookings filter and the customer detail
"Upcoming bookings" row both feed off this endpoint."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter_seedable,
)
from app.db.engine import get_session
from app.db.models import Customer, ExecutedAction
from app.integrations import action_catalog
from app.schemas.bookings import BookingListItem

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])

BOOKING_ACTION_TYPES = (
    "booking.create",
    "booking.cancel",
    "appointment.create",
    "appointment.cancel",
)


@router.get("", response_model=list[BookingListItem])
async def list_bookings(
    limit: int = Query(50, ge=1, le=200),
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> list[BookingListItem]:
    stmt = (
        select(ExecutedAction, Customer.display_name, Customer.phone_e164)
        .outerjoin(Customer, Customer.id == ExecutedAction.customer_id)
        .where(
            ExecutedAction.action_type.in_(BOOKING_ACTION_TYPES),
            visibility_filter_seedable(
                ExecutedAction.session_id, ExecutedAction.is_seed, ctx
            ),
        )
        .order_by(ExecutedAction.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    out: list[BookingListItem] = []
    for action, display_name, phone in rows:
        out.append(
            BookingListItem(
                id=action.id,
                call_id=action.call_id,
                customer_id=action.customer_id,
                action_type=action.action_type,
                title=action.title,
                summary=action.summary,
                payload=action.payload or {},
                status=action.status,
                created_at=action.created_at,
                customer_display_name=display_name,
                customer_phone_e164=phone,
                is_simulated=action_catalog.is_simulated(action.action_type),
                can_undo=action_catalog.can_undo(action.action_type),
            )
        )
    return out
