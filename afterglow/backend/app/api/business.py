"""Business API — list/view + current business resolver.

The /current endpoint returns the single business this instance serves
(env-pinned or the only one in DB). It backs the single-tenant UI flow.
The list/{id} endpoints stay live for the multi-domain demo dialer.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.engine import get_session
from app.db.models import Business


router = APIRouter(prefix="/api/v1/businesses", tags=["businesses"])


class BusinessView(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    default_language: str
    timezone: str
    settings: dict[str, Any] = {}
    vultr_collection_id: str | None = None


async def _resolve_current_business(session: AsyncSession) -> Business:
    settings = get_settings()
    if settings.default_business_id:
        row = (
            await session.execute(
                select(Business).where(Business.id == settings.default_business_id)
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "AFTERGLOW_DEFAULT_BUSINESS_ID is set but the business "
                    "does not exist in the database."
                ),
            )
        return row

    rows = (
        await session.execute(select(Business).order_by(Business.created_at))
    ).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="No business provisioned")
    # When no default is pinned, return the oldest business. This keeps the
    # single-tenant assumption explicit: if the operator wants a specific one
    # in a multi-business demo, they set AFTERGLOW_DEFAULT_BUSINESS_ID.
    return rows[0]


@router.get("/current", response_model=BusinessView)
async def get_current_business(
    session: AsyncSession = Depends(get_session),
) -> BusinessView:
    row = await _resolve_current_business(session)
    return BusinessView.model_validate(row, from_attributes=True)


@router.get("", response_model=list[BusinessView])
async def list_businesses(session: AsyncSession = Depends(get_session)) -> list[BusinessView]:
    rows = (await session.execute(select(Business).order_by(Business.created_at))).scalars().all()
    return [BusinessView.model_validate(r, from_attributes=True) for r in rows]


@router.get("/{business_id}", response_model=BusinessView)
async def get_business(
    business_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> BusinessView:
    row = (
        await session.execute(select(Business).where(Business.id == business_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return BusinessView.model_validate(row, from_attributes=True)
