"""Templates API — list/view + the prompt-to-template wizard."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import template_builder
from app.db.engine import get_session
from app.db.models import Template
from app.schemas import (
    TemplateView,
    TemplateWizardRequest,
    TemplateWizardResponse,
)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


@router.get("", response_model=list[TemplateView])
async def list_templates(
    business_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[TemplateView]:
    stmt = select(Template).order_by(Template.created_at.desc())
    if business_id:
        stmt = stmt.where(Template.business_id == business_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [TemplateView.model_validate(r, from_attributes=True) for r in rows]


@router.get("/{template_id}", response_model=TemplateView)
async def get_template(
    template_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> TemplateView:
    row = (
        await session.execute(select(Template).where(Template.id == template_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateView.model_validate(row, from_attributes=True)


@router.post("/wizard", response_model=TemplateWizardResponse)
async def template_wizard(payload: TemplateWizardRequest) -> TemplateWizardResponse:
    return await template_builder.build_template(payload.description, payload.language)
