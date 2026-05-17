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
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import (
    simulation_script,
    template_builder,
    template_validator,
    wizard_chat,
)
from app.agents.simulation_script import ScriptBuilderError
from app.agents.template_builder import TemplateBuilderError
from app.agents.wizard_chat import WizardChatError
from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter_seedable,
)
from app.config import get_settings
from app.db.engine import get_session
from app.db.models import DemoSession, Template
from app.integrations import speechmatics_tts
from app.integrations.speechmatics_tts import TtsError
from app.schemas import (
    CreateTemplateRequest,
    TemplateView,
    TemplateWizardRequest,
    TemplateWizardResponse,
    UpdateTemplateRequest,
    ValidateDraftRequest,
    ValidationReport,
    WizardChatRequest,
    WizardChatResponse,
)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


class SetActiveTemplateRequest(BaseModel):
    template_id: uuid.UUID


async def _active_template_id_for_session(
    session: AsyncSession, ctx: SessionContext
) -> uuid.UUID | None:
    """Resolve which template uuid is "active" for the current caller.

    Demo sessions read strictly from `DemoSession.active_template_id`: no
    fallback to the seed preset marked `is_active=TRUE`, so a fresh /
    post-reset visitor sees every template as non-active and is steered to
    the Templates screen to pick one. Production keeps the seed fallback so
    a brand-new install ships with a working default.
    """
    if ctx.is_demo:
        demo = (
            await session.execute(
                select(DemoSession).where(DemoSession.id == ctx.session_id)
            )
        ).scalar_one_or_none()
        return demo.active_template_id if demo is not None else None

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


@router.get("/active", response_model=None)
async def get_active_template(
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> Response | TemplateView:
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
        # Demo visitor has not picked a template yet (fresh access or post-
        # reset). Signal "no active" with 204 so the client can route to the
        # Templates screen — we do NOT fall back to a seed default here,
        # because the UX explicitly requires the visitor to choose.
        return Response(status_code=204)

    # Production tenant: keep the fallback to the seed template currently
    # marked is_active=TRUE, so a brand-new install ships with a working
    # default until the admin picks one.
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


@router.post("/wizard/chat", response_model=WizardChatResponse)
async def wizard_chat_turn(
    payload: WizardChatRequest,
    ctx: SessionContext = Depends(get_session_context),
) -> WizardChatResponse:
    """Drive one turn of the conversational template builder.

    Stateless: the client owns the message history + draft. Returns the next
    assistant message + updated slots + (when ready) a complete draft.
    """
    try:
        return await wizard_chat.run_wizard_chat(payload)
    except WizardChatError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Simulation config — script generator + Speechmatics TTS + upload
# ---------------------------------------------------------------------------


_SUPPORTED_UPLOAD_MIME = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
}


async def _load_template_for_simulation(
    session: AsyncSession, template_id: uuid.UUID, ctx: SessionContext
) -> Template:
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
    return row


@router.post("/{template_id}/simulation/script", response_model=TemplateView)
async def generate_simulation_script(
    template_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    """Generate the demo script for this template (no audio yet).

    Writes `simulation_config.script_turns` + `audio_status="pending"`. Call
    `POST /generate-audio` next to actually render the WAV.
    """
    row = await _load_template_for_simulation(session, template_id, ctx)
    try:
        parsed = await simulation_script.build_simulation_script(row)
    except ScriptBuilderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    row.simulation_config = simulation_script.script_response_to_simulation_config(
        parsed, audio_url=None, audio_status="pending"
    )
    await session.commit()
    await session.refresh(row)
    active_id = await _active_template_id_for_session(session, ctx)
    return _project_active(row, active_id)


@router.post("/{template_id}/simulation/generate-audio", response_model=TemplateView)
async def generate_simulation_audio(
    template_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    """Render `simulation_config.script_turns` to an MP3 via Speechmatics TTS.

    Requires the script to have been generated first (or supplied via PUT).
    """
    row = await _load_template_for_simulation(session, template_id, ctx)
    config = dict(row.simulation_config or {})
    raw_turns = config.get("script_turns") or []
    try:
        turns = speechmatics_tts.script_turns_from_dicts(raw_turns)
    except TtsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    out_path = speechmatics_tts.template_audio_path(str(template_id))
    try:
        await speechmatics_tts.render_script_to_wav(turns, out_path)
    except TtsError as exc:
        # Persist a `failed` audio_status so the UI can show the error.
        config["audio_status"] = "failed"
        config["audio_generated_at"] = datetime.now(tz=timezone.utc).isoformat()
        row.simulation_config = config
        await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    config["audio_url"] = str(out_path)
    config["audio_status"] = "ready"
    config["audio_generated_at"] = datetime.now(tz=timezone.utc).isoformat()
    config["audio_source"] = "tts_generated"
    row.simulation_config = config
    await session.commit()
    await session.refresh(row)
    active_id = await _active_template_id_for_session(session, ctx)
    return _project_active(row, active_id)


@router.post("/{template_id}/simulation/upload-audio", response_model=TemplateView)
async def upload_simulation_audio(
    template_id: uuid.UUID,
    audio: UploadFile = File(...),
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    """Operator-supplied demo recording for the active template.

    Used when the user has a real call recording they want to play back
    through the simulator instead of generating one via TTS.
    """
    row = await _load_template_for_simulation(session, template_id, ctx)

    content_type = (audio.content_type or "").lower()
    ext = _SUPPORTED_UPLOAD_MIME.get(content_type)
    if ext is None:
        raise HTTPException(
            status_code=415, detail=f"Unsupported audio mime type: {content_type}"
        )
    raw = await audio.read()
    settings = get_settings()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail="Audio file too large")
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio file")

    out_path = (
        Path(settings.audio_storage_dir) / "templates" / f"{template_id}.{ext}"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw)

    config = dict(row.simulation_config or {})
    config["audio_url"] = str(out_path)
    config["audio_status"] = "ready"
    config["audio_generated_at"] = datetime.now(tz=timezone.utc).isoformat()
    config["audio_source"] = "user_uploaded"
    row.simulation_config = config
    await session.commit()
    await session.refresh(row)
    active_id = await _active_template_id_for_session(session, ctx)
    return _project_active(row, active_id)


@router.get("/{template_id}/simulation/audio")
async def get_simulation_audio(
    template_id: uuid.UUID,
    mode: Literal["existing", "new"] = "existing",
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Stream back the demo audio so the dialer can play it.

    Seeded templates expose `simulation_config.scenarios.<mode>.audio_url`;
    custom wizard-built templates still use the flat `audio_url` and reuse
    the same recording for both modes (graceful fallback) until a future
    PR teaches the wizard to render two recordings.
    """
    row = await _load_template_for_simulation(session, template_id, ctx)
    config = row.simulation_config or {}
    scenarios = config.get("scenarios") or {}
    scenario = scenarios.get(mode) or {}
    audio_url = scenario.get("audio_url") or config.get("audio_url")
    if not audio_url:
        raise HTTPException(
            status_code=404,
            detail=f"No audio recorded for this template (mode={mode})",
        )
    path = Path(audio_url)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file is missing on disk")
    media_type = "audio/wav" if path.suffix.lower() == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type, filename=path.name)


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
    if payload.prompt_hints is not None:
        row.prompt_hints = [r.model_dump() for r in payload.prompt_hints]

    await session.commit()
    await session.refresh(row)
    active_id = await _active_template_id_for_session(session, ctx)
    return _project_active(row, active_id)
