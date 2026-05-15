"""Customers API — lookup by id or by phone (for caller card)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.models import Customer
from app.schemas import CustomerCard, CustomerProfileView

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("/by-phone/{phone_e164}", response_model=CustomerCard | None)
async def get_customer_by_phone(
    phone_e164: str,
    session: AsyncSession = Depends(get_session),
) -> CustomerCard | None:
    row = (
        await session.execute(
            select(Customer).where(Customer.phone_e164 == phone_e164)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return CustomerCard.model_validate(row, from_attributes=True)


@router.get("/{customer_id}", response_model=CustomerProfileView)
async def get_customer(
    customer_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> CustomerProfileView:
    row = (
        await session.execute(select(Customer).where(Customer.id == customer_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerProfileView.model_validate(row, from_attributes=True)
