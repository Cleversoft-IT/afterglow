"""Templates API — list/view, active template switching, prompt-to-template wizard.

Session-aware:
- production tenant (no `X-Demo-Session`) reads `Template.is_active`, writes flip
  the flag, list returns seed templates only (`session_id IS NULL`).
- demo iframe visitor sees seed templates + its own wizard-generated ones; the
  "active template" lives in `DemoSession.active_template_id` and never touches
  the global `is_active` flag.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import template_builder
from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter,
)
from app.db.engine import get_session
from app.db.models import DemoSession, Template
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
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> list[TemplateView]:
    stmt = (
        select(Template)
        .where(visibility_filter(Template.session_id, ctx))
        .order_by(Template.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [TemplateView.model_validate(r, from_attributes=True) for r in rows]


@router.get("/active", response_model=TemplateView)
async def get_active_template(
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    if ctx.is_demo:
        demo = (
            await session.execute(
                select(DemoSession).where(DemoSession.id == ctx.session_id)
            )
        ).scalar_one_or_none()
        if demo is not None and demo.active_template_id is not None:
            target = (
                await session.execute(
                    select(Template).where(Template.id == demo.active_template_id)
                )
            ).scalar_one_or_none()
            if target is not None:
                return TemplateView.model_validate(target, from_attributes=True)
        # Fallback: seed template currently marked active.

    row = (
        await session.execute(
            select(Template).where(
                Template.is_active.is_(True),
                Template.session_id.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=409, detail="no active template")
    return TemplateView.model_validate(row, from_attributes=True)


@router.put("/active", response_model=TemplateView)
async def set_active_template(
    payload: SetActiveTemplateRequest,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    target = (
        await session.execute(
            select(Template).where(
                Template.id == payload.template_id,
                visibility_filter(Template.session_id, ctx),
            )
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Template not found")

    if ctx.is_demo:
        await session.execute(
            update(DemoSession)
            .where(DemoSession.id == ctx.session_id)
            .values(active_template_id=target.id)
        )
        await session.commit()
        return TemplateView.model_validate(target, from_attributes=True)

    # Production: two-step swap because of the partial unique index on
    # is_active=TRUE AND session_id IS NULL. Clearing all first guarantees
    # the next update is unique-safe.
    await session.execute(
        update(Template)
        .where(Template.session_id.is_(None))
        .values(is_active=False)
    )
    await session.execute(
        update(Template).where(Template.id == target.id).values(is_active=True)
    )
    await session.commit()
    await session.refresh(target)
    return TemplateView.model_validate(target, from_attributes=True)


@router.get("/{template_id}", response_model=TemplateView)
async def get_template(
    template_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    row = (
        await session.execute(
            select(Template).where(
                Template.id == template_id,
                visibility_filter(Template.session_id, ctx),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateView.model_validate(row, from_attributes=True)


@router.post("/wizard", response_model=TemplateWizardResponse)
async def template_wizard(
    payload: TemplateWizardRequest,
    ctx: SessionContext = Depends(get_session_context),
) -> TemplateWizardResponse:
    # The wizard agent today only generates the template shape — it does not
    # persist anything. If we ever persist, mark `session_id=ctx.session_id`
    # so demo visitors do not pollute the shared library.
    return await template_builder.build_template(payload.description, payload.language)
