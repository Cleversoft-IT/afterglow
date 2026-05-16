"""Templates API — list/view, active template switching, prompt-to-template
wizard with persistence + refine endpoints.

Session-aware:
- production tenant (no `X-Demo-Session`) reads `Template.is_active`, writes
  flip the flag, list returns seed templates + tenant-owned non-seed.
- demo iframe visitor sees seed templates + its own wizard-generated ones;
  the "active template" lives in `DemoSession.active_template_id` and never
  touches the global `is_active` flag.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import template_builder, template_validator
from app.agents.template_builder import TemplateBuilderError
from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter_seedable,
)
from app.db.engine import get_session
from app.db.models import DemoSession, Template
from app.schemas import (
    CreateTemplateRequest,
    TemplateView,
    TemplateWizardRequest,
    TemplateWizardResponse,
    UpdateTemplateRequest,
    ValidateDraftRequest,
    ValidationReport,
)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


class SetActiveTemplateRequest(BaseModel):
    template_id: uuid.UUID


async def _active_template_id_for_session(
    session: AsyncSession, ctx: SessionContext
) -> uuid.UUID | None:
    """Resolve which template uuid is "active" for the current caller."""
    if ctx.is_demo:
        demo = (
            await session.execute(
                select(DemoSession).where(DemoSession.id == ctx.session_id)
            )
        ).scalar_one_or_none()
        if demo is not None and demo.active_template_id is not None:
            return demo.active_template_id
        seed = (
            await session.execute(
                select(Template.id).where(
                    Template.is_active.is_(True),
                    Template.is_seed.is_(True),
                )
            )
        ).scalar_one_or_none()
        return seed

    row = (
        await session.execute(
            select(Template.id).where(
                Template.is_active.is_(True),
                Template.session_id.is_(None),
            )
        )
    ).scalar_one_or_none()
    return row


def _project_active(
    row: Template, active_id: uuid.UUID | None
) -> TemplateView:
    """Pydantic view with is_active overridden by the caller's active template."""
    view = TemplateView.model_validate(row, from_attributes=True)
    view.is_active = active_id is not None and row.id == active_id
    return view


async def _set_active_for_ctx(
    session: AsyncSession, ctx: SessionContext, template_id: uuid.UUID
) -> None:
    """Promote `template_id` to active for the current caller.

    - Demo: write `DemoSession.active_template_id`.
    - Prod: two-step swap (clear all `is_active`, then set the target)
      because of the partial unique index on `is_active=TRUE AND
      session_id IS NULL`.
    """
    if ctx.is_demo:
        await session.execute(
            update(DemoSession)
            .where(DemoSession.id == ctx.session_id)
            .values(active_template_id=template_id)
        )
        return

    await session.execute(
        update(Template)
        .where(Template.session_id.is_(None))
        .values(is_active=False)
    )
    await session.execute(
        update(Template).where(Template.id == template_id).values(is_active=True)
    )


async def _next_version_for(
    session: AsyncSession, name: str, session_id: uuid.UUID | None
) -> int:
    """Return the next `version` to assign for `(name, session_id)`.

    The partial unique indexes (uq_template_name_version_prod,
    uq_template_name_version_session) treat `session_id IS NULL` and
    non-null session_ids as separate uniqueness scopes. We compute the
    next version within the caller's scope.
    """
    if session_id is None:
        stmt = (
            select(func.coalesce(func.max(Template.version), 0))
            .where(Template.name == name, Template.session_id.is_(None))
        )
    else:
        stmt = (
            select(func.coalesce(func.max(Template.version), 0))
            .where(Template.name == name, Template.session_id == session_id)
        )
    latest = (await session.execute(stmt)).scalar_one() or 0
    return int(latest) + 1


@router.get("", response_model=list[TemplateView])
async def list_templates(
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> list[TemplateView]:
    stmt = (
        select(Template)
        .where(visibility_filter_seedable(Template.session_id, Template.is_seed, ctx))
        .order_by(Template.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    active_id = await _active_template_id_for_session(session, ctx)
    return [_project_active(r, active_id) for r in rows]


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
                return _project_active(target, target.id)
        # Fallback: seed template currently marked active.

    fallback_filter = (
        Template.is_seed.is_(True) if ctx.is_demo else Template.session_id.is_(None)
    )
    row = (
        await session.execute(
            select(Template).where(
                Template.is_active.is_(True),
                fallback_filter,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=409, detail="no active template")
    return _project_active(row, row.id)


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
                visibility_filter_seedable(Template.session_id, Template.is_seed, ctx),
            )
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Template not found")

    await _set_active_for_ctx(session, ctx, target.id)
    await session.commit()
    await session.refresh(target)
    return _project_active(target, target.id)


@router.post("/wizard", response_model=TemplateWizardResponse)
async def template_wizard(
    payload: TemplateWizardRequest,
    ctx: SessionContext = Depends(get_session_context),
) -> TemplateWizardResponse:
    """Run the prompt-to-template Generate step + an initial Validate pass.

    The wizard does NOT persist anything; the refine UI calls POST /templates
    when the operator is happy with the draft.
    """
    try:
        draft = await template_builder.build_template(
            payload.description, payload.language
        )
    except TemplateBuilderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    draft.validation = await template_validator.validate_template(draft)
    return draft


@router.post("/validate", response_model=ValidationReport)
async def validate_draft(
    payload: ValidateDraftRequest,
    ctx: SessionContext = Depends(get_session_context),
) -> ValidationReport:
    """Re-run the validator on a draft the refine UI just edited."""
    return await template_validator.validate_template(payload.template)


@router.post("", response_model=TemplateView, status_code=201)
async def create_template(
    payload: CreateTemplateRequest,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    tpl = payload.template
    target_session_id = ctx.session_id if ctx.is_demo else None
    version = await _next_version_for(session, tpl.name, target_session_id)

    row = Template(
        id=uuid.uuid4(),
        name=tpl.name,
        version=version,
        description=tpl.description,
        domain_hint=tpl.domain_hint,
        fields_schema=[f.model_dump() for f in tpl.fields_schema],
        action_types=[a.model_dump() for a in tpl.action_types],
        custom_dictionary=list(tpl.custom_dictionary),
        prompt_hints=[r.model_dump() for r in tpl.prompt_hints],
        is_active=False,
        session_id=target_session_id,
        is_seed=False,
    )
    session.add(row)
    await session.flush()

    if payload.set_active:
        await _set_active_for_ctx(session, ctx, row.id)

    await session.commit()
    await session.refresh(row)
    return _project_active(row, row.id if payload.set_active else None)


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
                visibility_filter_seedable(Template.session_id, Template.is_seed, ctx),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    active_id = await _active_template_id_for_session(session, ctx)
    return _project_active(row, active_id)


@router.put("/{template_id}", response_model=TemplateView)
async def update_template(
    template_id: uuid.UUID,
    payload: UpdateTemplateRequest,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    """Edit a session-owned template (refine post-persistence). Seed templates
    are read-only and return 409.
    """
    row = (
        await session.execute(
            select(Template).where(
                Template.id == template_id,
                visibility_filter_seedable(Template.session_id, Template.is_seed, ctx),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    if row.is_seed:
        raise HTTPException(status_code=409, detail="Seed templates are read-only")
    if ctx.is_demo and row.session_id != ctx.session_id:
        raise HTTPException(status_code=403, detail="Template belongs to another session")
    if not ctx.is_demo and row.session_id is not None:
        raise HTTPException(status_code=403, detail="Template is a session-owned draft")

    if payload.description is not None:
        row.description = payload.description
    if payload.domain_hint is not None:
        row.domain_hint = payload.domain_hint
    if payload.fields_schema is not None:
        row.fields_schema = [f.model_dump() for f in payload.fields_schema]
    if payload.action_types is not None:
        row.action_types = [a.model_dump() for a in payload.action_types]
    if payload.custom_dictionary is not None:
        row.custom_dictionary = list(payload.custom_dictionary)
    if payload.prompt_hints is not None:
        row.prompt_hints = [r.model_dump() for r in payload.prompt_hints]

    await session.commit()
    await session.refresh(row)
    active_id = await _active_template_id_for_session(session, ctx)
    return _project_active(row, active_id)
