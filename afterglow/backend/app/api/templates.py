"""Templates API — list/view, active template switching, prompt-to-template wizard."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
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


class SetActiveTemplateRequest(BaseModel):
    template_id: uuid.UUID


@router.get("", response_model=list[TemplateView])
async def list_templates(
    session: AsyncSession = Depends(get_session),
) -> list[TemplateView]:
    rows = (
        await session.execute(select(Template).order_by(Template.created_at.desc()))
    ).scalars().all()
    return [TemplateView.model_validate(r, from_attributes=True) for r in rows]


@router.get("/active", response_model=TemplateView)
async def get_active_template(
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    row = (
        await session.execute(select(Template).where(Template.is_active.is_(True)))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=409, detail="no active template")
    return TemplateView.model_validate(row, from_attributes=True)


@router.put("/active", response_model=TemplateView)
async def set_active_template(
    payload: SetActiveTemplateRequest,
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    target = (
        await session.execute(
            select(Template).where(Template.id == payload.template_id)
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Template not found")

    # Two-step swap because of the partial unique index on is_active=TRUE:
    # clearing all first guarantees the next update is unique-safe.
    await session.execute(update(Template).values(is_active=False))
    await session.execute(
        update(Template).where(Template.id == target.id).values(is_active=True)
    )
    await session.commit()
    await session.refresh(target)
    return TemplateView.model_validate(target, from_attributes=True)


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
