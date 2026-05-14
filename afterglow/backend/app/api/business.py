"""Business API — list/view businesses (used by the landing/business selector)."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
