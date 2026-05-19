"""Templates API — list/view, active template switching, conversational
wizard chat, draft validation, persistence + refine endpoints.

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
from sqlalchemy.orm.attributes import flag_modified

from app.agents import (
    simulation_script,
    template_validator,
    wizard_chat,
)
from app.agents.simulation_script import ScriptBuilderError
from app.agents.wizard_chat import WizardChatError
from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter_seedable,
)
from app.config import get_settings
from app.db.engine import get_session
from app.db.models import DemoSession, Template
from app.integrations import action_catalog, speechmatics_tts
from app.integrations.speechmatics_tts import TtsError
from app.schemas import (
    CreateTemplateRequest,
    TemplateView,
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


@router.post("/validate", response_model=ValidationReport)
async def validate_draft(
    payload: ValidateDraftRequest,
    ctx: SessionContext = Depends(get_session_context),
) -> ValidationReport:
    """Re-run the validator on a draft the refine UI just edited."""
    return template_validator.validate_template(payload.template)


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

    row.simulation_config = simulation_script.script_response_to_simulation_config(parsed)
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
    """Render the template's demo scripts to WAV via Speechmatics TTS.

    Iterates `simulation_config.scenarios.{existing,new}` and writes each to
    its own scenario-specific path. If one mode fails the other still
    persists — operator can retry. Falls back to the legacy flat
    `script_turns` shape for templates generated before 2026-05-18.
    """
    row = await _load_template_for_simulation(session, template_id, ctx)
    config = dict(row.simulation_config or {})
    scenarios = config.get("scenarios") or {}

    # Back-compat path: legacy flat shape (no `scenarios` map).
    if not scenarios:
        raw_turns = config.get("script_turns") or []
        try:
            turns = speechmatics_tts.script_turns_from_dicts(raw_turns)
        except TtsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        out_path = speechmatics_tts.template_audio_path(str(template_id))
        try:
            await speechmatics_tts.render_script_to_mp3(turns, out_path)
        except TtsError as exc:
            config["audio_status"] = "failed"
            config["audio_generated_at"] = datetime.now(tz=timezone.utc).isoformat()
            row.simulation_config = config
            await session.commit()
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        config["audio_url"] = str(out_path)
        config["audio_status"] = "ready"
        config["audio_generated_at"] = datetime.now(tz=timezone.utc).isoformat()
        config["audio_source"] = "tts_generated"
        # TTS pipeline renders stereo (one speaker per channel); flag the
        # config so submit_audio_call can route ASR to channel diarization
        # for any call made against this template.
        config["audio_diarization"] = "channel"
        row.simulation_config = config
        await session.commit()
        await session.refresh(row)
        active_id = await _active_template_id_for_session(session, ctx)
        return _project_active(row, active_id)

    # New scenarios shape: render each mode to its own WAV. Errors on one
    # mode do not abort the other.
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    errors: list[str] = []
    for mode in ("existing", "new"):
        scenario = scenarios.get(mode)
        if not scenario:
            continue
        raw_turns = scenario.get("script_turns") or []
        try:
            turns = speechmatics_tts.script_turns_from_dicts(raw_turns)
        except TtsError as exc:
            scenario["audio_status"] = "failed"
            scenario["audio_generated_at"] = now_iso
            errors.append(f"{mode}: {exc}")
            continue
        out_path = speechmatics_tts.template_audio_path(str(template_id), mode=mode)
        try:
            await speechmatics_tts.render_script_to_mp3(turns, out_path)
        except TtsError as exc:
            scenario["audio_status"] = "failed"
            scenario["audio_generated_at"] = now_iso
            errors.append(f"{mode}: {exc}")
            continue
        scenario["audio_url"] = str(out_path)
        scenario["audio_status"] = "ready"
        scenario["audio_generated_at"] = now_iso
        scenario["audio_source"] = "tts_generated"
        # Stereo TTS → channel diarization downstream (see ASR routing in
        # `submit_audio_call` and `transcribe_audio`).
        scenario["audio_diarization"] = "channel"

    config["scenarios"] = scenarios
    row.simulation_config = config
    # SQLAlchemy compares old/new JSONB by value; the inner `scenario` dicts
    # we just mutated are shared with the previously-committed state, so the
    # ORM would see no diff and skip the UPDATE. flag_modified forces the
    # column to be marked dirty so audio_status/audio_url actually persist.
    flag_modified(row, "simulation_config")
    await session.commit()
    await session.refresh(row)

    if errors and not any(
        (s or {}).get("audio_status") == "ready" for s in scenarios.values()
    ):
        # Every mode failed — surface 502 so the UI knows nothing rendered.
        raise HTTPException(status_code=502, detail="; ".join(errors))

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

    Both seeded and wizard-built templates expose
    `simulation_config.scenarios.<mode>.audio_url`. The flat `audio_url`
    fallback is preserved for back-compat with custom templates generated
    before 2026-05-18 — those keep a single recording reused across modes.
    """
    row = await _load_template_for_simulation(session, template_id, ctx)
    config = row.simulation_config or {}
    scenarios = config.get("scenarios") or {}
    scenario = scenarios.get(mode) or {}
    audio_url = scenario.get("audio_url") or config.get("audio_url")
    audio_status = scenario.get("audio_status") or config.get("audio_status")
    if not audio_url:
        # Template has no recording at all — 404 is the right shape: the
        # client should hide the "trigger demo call" button entirely.
        raise HTTPException(
            status_code=404,
            detail=f"No audio recorded for this template (mode={mode})",
        )
    path = Path(audio_url)
    if not path.exists():
        # The template was flagged ready but the file vanished (storage
        # cleanup after a redeploy, or a stale config row pointing at a
        # path that no longer exists). 409 — not 404 — so the client can
        # distinguish "regenerate the audio" from "this template has no
        # recording yet". The body is structured JSON so the frontend can
        # branch on `code`.
        if audio_status == "ready":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "audio_not_on_disk",
                    "detail": "Audio file is ready-flagged but missing on disk",
                    "template_id": str(template_id),
                    "mode": mode,
                },
            )
        raise HTTPException(status_code=404, detail="Audio file is missing on disk")
    media_type = "audio/wav" if path.suffix.lower() == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type, filename=path.name)


def _enrich_action_types_with_catalog_schemas(
    action_types: list[dict[str, object]],
    template_domain_hint: str | None = None,
) -> list[dict[str, object]]:
    """Merge a payload_schema from the action catalog into any action_type
    dict that does not already carry an explicit `payload_schema`.

    When `template_domain_hint` matches a key in
    `ActionCatalogEntry.domain_payload_schemas`, that override wins
    (e.g. a Hotel template gets the hotel-shaped `booking.create`
    schema with `check_out_date` instead of the restaurant-shaped
    default). Falls back to `default_payload_schema` for unknown /
    generic / `None` domains, so existing seed templates keep the same
    behaviour they had before per-domain overrides existed.

    Run this at the persistence boundary (create_template /
    update_template) so the wizard's `ActionDefinitionDraft` (which
    cannot expose `payload_schema` because Gemini structured-output
    rejects `additionalProperties`) still lands typed in the database.
    The call_agent's `make_action_tool` builds a typed Pydantic model
    for Gemini, instead of falling back to the untyped `dict`
    annotation that ADK 1.18+ rejects.
    """
    enriched: list[dict[str, object]] = []
    for data in action_types:
        if not data.get("payload_schema"):
            key = data.get("key")
            entry = action_catalog.get(key) if isinstance(key, str) else None
            if entry is not None:
                schema = entry.payload_schema_for_domain(template_domain_hint)
                if schema is not None:
                    data = {**data, "payload_schema": schema}
        enriched.append(data)
    return enriched


@router.post("", response_model=TemplateView, status_code=201)
async def create_template(
    payload: CreateTemplateRequest,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> TemplateView:
    tpl = payload.template
    target_session_id = ctx.session_id if ctx.is_demo else None
    version = await _next_version_for(session, tpl.name, target_session_id)

    action_types_data = _enrich_action_types_with_catalog_schemas(
        [a.model_dump() for a in tpl.action_types],
        template_domain_hint=tpl.domain_hint or "generic",
    )

    row = Template(
        id=uuid.uuid4(),
        name=tpl.name,
        version=version,
        description=tpl.description,
        domain_hint=tpl.domain_hint,
        fields_schema=[f.model_dump() for f in tpl.fields_schema],
        action_types=action_types_data,
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

    if payload.name is not None:
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(status_code=422, detail="Template name cannot be empty")
        # Uniqueness scope: every template visible to this session (seed +
        # session-owned). Keeps the list view free of homonyms across the
        # seed/custom split.
        clash = (
            await session.execute(
                select(Template.id).where(
                    Template.name == new_name,
                    Template.id != template_id,
                    visibility_filter_seedable(
                        Template.session_id, Template.is_seed, ctx
                    ),
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise HTTPException(
                status_code=409,
                detail="A template with this name already exists",
            )
        row.name = new_name
    if payload.description is not None:
        row.description = payload.description
    if payload.domain_hint is not None:
        row.domain_hint = payload.domain_hint
    if payload.fields_schema is not None:
        row.fields_schema = [f.model_dump() for f in payload.fields_schema]
    if payload.action_types is not None:
        row.action_types = _enrich_action_types_with_catalog_schemas(
            [a.model_dump() for a in payload.action_types],
            template_domain_hint=row.domain_hint or "generic",
        )
    if payload.prompt_hints is not None:
        row.prompt_hints = [r.model_dump() for r in payload.prompt_hints]

    await session.commit()
    await session.refresh(row)
    active_id = await _active_template_id_for_session(session, ctx)
    return _project_active(row, active_id)
