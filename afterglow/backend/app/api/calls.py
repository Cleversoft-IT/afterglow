"""Calls API — upload audio, kick off pipeline, poll status."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_pipeline
from app.api.session_context import (
    SessionContext,
    get_session_context,
    visibility_filter,
    visibility_filter_seedable,
)
from app.config import get_settings
from app.db.engine import SessionLocal, get_session
from app.db.models import (
    Call,
    Customer,
    DemoSession,
    ExecutedAction,
    ExtractedFields,
    Template,
)
from app.integrations import action_catalog
from app.schemas import (
    CallActionView,
    CallDetailView,
    CallExtractedView,
    CallListItem,
    CallSubmittedResponse,
    CustomerCard,
    FieldDefinitionLite,
)

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

settings = get_settings()

_SUPPORTED_AUDIO = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/webm": "webm",
}


async def _get_active_template(
    session: AsyncSession, ctx: SessionContext
) -> Template:
    if ctx.is_demo:
        demo = (
            await session.execute(
                select(DemoSession).where(DemoSession.id == ctx.session_id)
            )
        ).scalar_one_or_none()
        if demo is not None and demo.active_template_id is not None:
            template = (
                await session.execute(
                    select(Template).where(Template.id == demo.active_template_id)
                )
            ).scalar_one_or_none()
            if template is not None:
                return template
        # Fallback for a brand-new demo session: the SEED-active template only.
        # Never fall back to a production tenant's own active row.
        stmt = select(Template).where(
            Template.is_active.is_(True),
            Template.is_seed.is_(True),
        )
        template = (await session.execute(stmt)).scalar_one_or_none()
        if template is None:
            raise HTTPException(status_code=409, detail="no active template set")
        return template

    stmt = select(Template).where(
        Template.is_active.is_(True),
        Template.session_id.is_(None),
    )
    template = (await session.execute(stmt)).scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=409,
            detail="no active template set",
        )
    return template


@router.post("", response_model=CallSubmittedResponse, status_code=202)
async def submit_audio_call(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    phone_e164: str = Form(...),
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> CallSubmittedResponse:
    content_type = (audio.content_type or "").lower()
    if content_type not in _SUPPORTED_AUDIO:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio mime type: {content_type}",
        )

    raw = await audio.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail="Audio file too large")
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio file")

    template = await _get_active_template(session, ctx)

    storage_dir = Path(settings.audio_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    ext = _SUPPORTED_AUDIO[content_type]
    call_id = uuid.uuid4()
    audio_path = storage_dir / f"{call_id}.{ext}"
    audio_path.write_bytes(raw)

    # Eager customer link: if we can resolve a Customer for this phone right
    # now (clone-first / seed-fallback in demo, session-scoped in prod), the
    # call list can render the proper name immediately instead of showing
    # the bare phone number while the pipeline runs.
    # NB: a seed FK is temporary — the pipeline's `_resolve_customer` will
    # clone the seed into a session-scoped row and may rewrite this FK.
    eager_customer_id: Optional[uuid.UUID] = None
    if ctx.is_demo:
        clone = (
            await session.execute(
                select(Customer).where(
                    Customer.phone_e164 == phone_e164,
                    Customer.session_id == ctx.session_id,
                )
            )
        ).scalar_one_or_none()
        if clone is not None:
            eager_customer_id = clone.id
        else:
            seed = (
                await session.execute(
                    select(Customer).where(
                        Customer.phone_e164 == phone_e164,
                        Customer.is_seed.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if seed is not None:
                eager_customer_id = seed.id
    else:
        row = (
            await session.execute(
                select(Customer).where(
                    Customer.phone_e164 == phone_e164,
                    Customer.session_id.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            eager_customer_id = row.id

    call = Call(
        id=call_id,
        template_id=template.id,
        customer_id=eager_customer_id,
        phone_e164=phone_e164,
        audio_url=str(audio_path),
        status="pending",
        session_id=ctx.session_id,
        created_at=datetime.now(tz=timezone.utc),
    )
    session.add(call)
    await session.commit()

    background_tasks.add_task(_run_pipeline_isolated, call_id)
    return CallSubmittedResponse(call_id=call_id, status="pending")


async def _run_pipeline_isolated(call_id: uuid.UUID) -> None:
    """Open a fresh session for the background task — FastAPI's request scope is gone."""
    async with SessionLocal() as bg_session:
        try:
            await run_pipeline(bg_session, call_id)
        except Exception as exc:  # noqa: BLE001
            await bg_session.rollback()
            stmt = select(Call).where(Call.id == call_id)
            call = (await bg_session.execute(stmt)).scalar_one_or_none()
            if call is not None:
                call.status = "failed"
                call.error = str(exc)[:1000]
                await bg_session.commit()


@router.get("/{call_id}", response_model=CallDetailView)
async def get_call(
    call_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> CallDetailView:
    call = (
        await session.execute(
            select(Call).where(
                Call.id == call_id,
                visibility_filter_seedable(Call.session_id, Call.is_seed, ctx),
            )
        )
    ).scalar_one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    extracted = (
        await session.execute(
            select(ExtractedFields).where(ExtractedFields.call_id == call.id)
        )
    ).scalar_one_or_none()

    actions = (
        await session.execute(
            select(ExecutedAction)
            .where(ExecutedAction.call_id == call.id)
            .order_by(ExecutedAction.created_at)
        )
    ).scalars().all()

    customer_row: Optional[Customer] = None
    if call.customer_id is not None:
        customer_row = (
            await session.execute(
                select(Customer).where(Customer.id == call.customer_id)
            )
        ).scalar_one_or_none()

    # Pull the template once so we can label extracted fields with their
    # human-readable label and type. Older rows may be missing keys, so
    # default everything defensively.
    template_row: Optional[Template] = (
        await session.execute(
            select(Template).where(Template.id == call.template_id)
        )
    ).scalar_one_or_none()

    extracted_view: Optional[CallExtractedView] = None
    if extracted is not None:
        field_defs: list[FieldDefinitionLite] = []
        if template_row is not None and extracted.fields:
            present_keys = set(extracted.fields.keys())
            for raw in (template_row.fields_schema or []):
                if not isinstance(raw, dict):
                    continue
                key = raw.get("key")
                if not key or key not in present_keys:
                    continue
                field_defs.append(
                    FieldDefinitionLite(
                        key=key,
                        label=raw.get("label") or key,
                        type=raw.get("type") or "string",
                    )
                )
        extracted_view = CallExtractedView(
            fields=extracted.fields or {},
            confidence=extracted.confidence or {},
            evidence=extracted.evidence or {},
            intent=extracted.intent,
            sentiment=extracted.sentiment,
            urgency=extracted.urgency,
            field_definitions=field_defs,
        )

    return CallDetailView(
        id=call.id,
        customer_id=call.customer_id,
        customer=(
            CustomerCard.model_validate(customer_row, from_attributes=True)
            if customer_row is not None
            else None
        ),
        template_id=call.template_id,
        phone_e164=call.phone_e164,
        detected_language=call.detected_language,
        raw_transcript=call.raw_transcript,
        status=call.status,
        error=call.error,
        started_at=call.started_at,
        completed_at=call.completed_at,
        created_at=call.created_at,
        extracted=extracted_view,
        executed_actions=[
            CallActionView(
                id=a.id,
                action_type=a.action_type,
                title=a.title,
                summary=a.summary,
                payload=a.payload or {},
                result=a.result,
                confidence=a.confidence,
                evidence=a.evidence,
                execution_mode=a.execution_mode,
                status=a.status,
                reverted_at=a.reverted_at,
                created_at=a.created_at,
                is_simulated=action_catalog.is_simulated(a.action_type),
                can_undo=action_catalog.can_undo(a.action_type),
            )
            for a in actions
        ],
    )


@router.get("", response_model=list[CallListItem])
async def list_calls(
    customer_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> list[CallListItem]:
    customer_filter_ids: Optional[list[uuid.UUID]] = None
    if customer_id:
        customer_filter_ids = [customer_id]
        # Demo sandbox: the visitor's Customer is a clone-on-write of a
        # seed Customer (see `_resolve_customer` in agents/orchestrator.py).
        # Calls created during the demo reference the clone; the seed
        # history references the seed row. Expand the filter to include
        # every Customer that shares the same phone_e164, so the customer
        # profile screen shows both the seed history and the visitor's
        # own calls under "Calls (N)".
        if ctx.is_demo:
            target = (
                await session.execute(
                    select(Customer.phone_e164).where(Customer.id == customer_id)
                )
            ).scalar_one_or_none()
            if target:
                twin_ids = (
                    await session.execute(
                        select(Customer.id).where(Customer.phone_e164 == target)
                    )
                ).scalars().all()
                if twin_ids:
                    customer_filter_ids = list(twin_ids)

    stmt = (
        select(Call, Customer.display_name)
        .join(Customer, Customer.id == Call.customer_id, isouter=True)
        .where(visibility_filter_seedable(Call.session_id, Call.is_seed, ctx))
        .order_by(Call.created_at.desc())
        .limit(limit)
    )
    if customer_filter_ids is not None:
        stmt = stmt.where(Call.customer_id.in_(customer_filter_ids))
    rows = (await session.execute(stmt)).all()
    return [
        CallListItem(
            id=c.id,
            phone_e164=c.phone_e164,
            customer_id=c.customer_id,
            customer_display_name=display_name,
            template_id=c.template_id,
            status=c.status,
            detected_language=c.detected_language,
            created_at=c.created_at,
        )
        for (c, display_name) in rows
    ]
