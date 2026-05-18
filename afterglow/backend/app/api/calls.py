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

from app.agents import briefing_regenerator, memory_retrieval
from app.agents.orchestrator import _seed_exists_for_phone, run_pipeline
from app.audit.logger import audit_step
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


# Failure-kind discriminator for `Call.status == "failed"`. The orchestrator
# stamps `Call.error` with one of these codes when the pipeline skips a call
# for non-technical reasons; any other error value is treated as a real
# pipeline crash (Gemini / ADK / executor). The set must match the strings
# the orchestrator writes — keep in sync with `app/agents/orchestrator.py`.
_MISSED_ERROR_CODES: frozenset[str] = frozenset({
    "empty_or_noise_audio",
    "missed_call",
})


def _failure_kind(status: str, error: Optional[str]) -> Optional[str]:
    if status != "failed":
        return None
    if error is None or error in _MISSED_ERROR_CODES:
        return "missed"
    return "pipeline_error"

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
            briefing=extracted.briefing_snapshot,
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
        failure_kind=_failure_kind(call.status, call.error),
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


@router.post("/{call_id}/regenerate-summary", response_model=CallDetailView)
async def regenerate_summary(
    call_id: uuid.UUID,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> CallDetailView:
    """Rewrite this call's next-call briefing without re-running fields or actions.

    Scoped intentionally narrow: only `ExtractedFields.briefing_snapshot`
    and `Customer.memory_summary` move. Extracted fields, executed actions,
    and the transcript are untouched — clicking Regenerate must not produce
    duplicate bookings or shift past data.

    Preconditions (409 otherwise):
      - `call.status == "completed"`
      - extracted_fields row exists
      - call.customer_id is set
    """
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
    if call.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Call is not completed (status={call.status})",
        )
    if call.customer_id is None:
        raise HTTPException(
            status_code=409, detail="Call has no linked customer"
        )

    extracted = (
        await session.execute(
            select(ExtractedFields).where(ExtractedFields.call_id == call.id)
        )
    ).scalar_one_or_none()
    if extracted is None:
        raise HTTPException(
            status_code=409, detail="Call has no extracted fields to refresh"
        )

    customer = (
        await session.execute(
            select(Customer).where(Customer.id == call.customer_id)
        )
    ).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=409, detail="Customer not found")

    template = (
        await session.execute(
            select(Template).where(Template.id == call.template_id)
        )
    ).scalar_one()

    # Re-fetch prior facts with the same demo/prod logic as the orchestrator.
    is_demo = call.session_id is not None
    collection_id = settings.vultr_vector_default_collection or None
    preseed_available = False
    if is_demo and collection_id:
        preseed_available = customer.is_seed or await _seed_exists_for_phone(
            session, call.phone_e164
        )
    demo_can_rag = is_demo and bool(collection_id) and preseed_available
    use_structured = not (
        demo_can_rag or (not is_demo and (customer.total_calls or 0) > 10)
    )
    if use_structured:
        prior_facts, _source = await memory_retrieval.retrieve_structured_history(
            session, customer
        )
    else:
        prior_facts, _in, _out = await memory_retrieval.retrieve_customer_context(
            collection_id=collection_id,
            phone_e164=call.phone_e164,
            domain_hint=template.domain_hint,
            is_demo=is_demo,
            preseed_available=preseed_available,
        )

    transcript_text = (call.raw_transcript or {}).get("text") or ""

    try:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="briefing_regenerator",
            step_type="llm_call",
            model=settings.gemini_default_model,
        ) as regen_audit:
            new_briefing, usage = await briefing_regenerator.regenerate_briefing(
                transcript_text=transcript_text,
                fields=extracted.fields or {},
                intent=extracted.intent,
                sentiment=extracted.sentiment,
                language=call.detected_language or customer.preferred_language,
                prior_facts=prior_facts,
            )
            regen_audit.input_tokens = usage.input_tokens
            regen_audit.output_tokens = usage.output_tokens
            regen_audit.payload = {
                "previous_briefing_chars": len(extracted.briefing_snapshot or ""),
                "new_briefing_chars": len(new_briefing),
            }
    except Exception as exc:  # noqa: BLE001
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="briefing_regenerator",
            step_type="llm_call",
            status="error",
            payload={"reason": str(exc)},
        ):
            pass
        await session.rollback()
        raise HTTPException(
            status_code=502, detail=f"briefing_regenerator: {exc}"
        ) from exc

    extracted.briefing_snapshot = new_briefing
    customer.memory_summary = new_briefing
    await session.commit()

    return await get_call(call_id=call_id, ctx=ctx, session=session)


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
        select(Call, Customer.display_name, Customer.tags)
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
            customer_tags=list(tags or []),
            template_id=c.template_id,
            status=c.status,
            failure_kind=_failure_kind(c.status, c.error),
            detected_language=c.detected_language,
            created_at=c.created_at,
        )
        for (c, display_name, tags) in rows
    ]
