"""Operational diagnostics + dry-run for the Vultr Vector Store side of the
pipeline.

Three endpoints:
- `GET /api/v1/admin/rag-stats` (read-only) reports how many preseed chunks
  landed in Postgres for the active collection. The lifespan preseed task
  and the runtime memory-updater both write `CustomerMemoryChunk` rows; the
  preseed marker discriminates them.
- `GET /api/v1/admin/rag-probe?phone=...` (read-only) issues a real
  `chat_completion_rag` call against Vultr and returns the raw retrieved
  text + token usage so a judge can confirm the integration is live, not
  stubbed.
- `POST /api/v1/admin/dry-run-pipeline` (writes a `Call`) accepts a custom
  transcript + phone, creates a Call row, and runs the agentic pipeline
  end-to-end so a judge can exercise the AI loop without recording an MP3.
  Honors `X-Demo-Session` so the resulting call is scoped to the same demo
  UI the judge is viewing.

The first two endpoints don't require demo-session scoping; the dry-run
endpoint optionally honors the `X-Demo-Session` header when present.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import asyncio
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.agents import memory_retrieval
from app.agents.orchestrator import run_pipeline
from app.api.session_context import SessionContext, get_session_context
from app.config import get_settings
from app.db.engine import SessionLocal, get_session
from app.db.models import Call, Customer, CustomerMemoryChunk, Template
from app.integrations import vultr_inference

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

settings = get_settings()


@router.get("/rag-stats")
async def rag_stats(
    session: AsyncSession = Depends(get_session),
) -> dict:
    collection_id = settings.vultr_vector_default_collection or None
    api_key_configured = bool(settings.vultr_inference_api_key)

    preseed_count = await session.scalar(
        select(func.count(CustomerMemoryChunk.id)).where(
            CustomerMemoryChunk.chunk_metadata["preseed"].as_boolean().is_(True),
            CustomerMemoryChunk.vultr_collection_id == (collection_id or ""),
        )
    )
    total_count = await session.scalar(
        select(func.count(CustomerMemoryChunk.id)).where(
            CustomerMemoryChunk.vultr_collection_id == (collection_id or "")
        )
    )
    last_chunk = await session.scalar(
        select(CustomerMemoryChunk.created_at)
        .where(CustomerMemoryChunk.vultr_collection_id == (collection_id or ""))
        .order_by(CustomerMemoryChunk.created_at.desc())
        .limit(1)
    )
    return {
        "collection_id": collection_id,
        "api_key_configured": api_key_configured,
        "inference_base_url": settings.vultr_inference_base_url,
        "inference_model": settings.vultr_inference_model,
        "preseed_chunks": int(preseed_count or 0),
        "total_chunks": int(total_count or 0),
        "runtime_chunks": int((total_count or 0) - (preseed_count or 0)),
        "last_chunk_at": last_chunk.isoformat() if last_chunk else None,
    }


@router.get("/rag-probe")
async def rag_probe(
    phone: str = Query(..., description="E.164 phone number to probe"),
    domain: str = Query("restaurant"),
) -> dict:
    """Round-trip Vultr RAG and return the retrieved facts verbatim.

    Returns an empty `prior_facts` (with 200) when the collection is empty
    or Vultr returns NO_MEMORY for this phone. Returns 503 when the SDK
    is unconfigured. Surfaces the raw token usage so the caller can verify
    the request actually hit Vultr (input_tokens > 0 ≠ stub).
    """
    collection_id = settings.vultr_vector_default_collection or None
    if not collection_id or not settings.vultr_inference_api_key:
        raise HTTPException(
            status_code=503,
            detail="Vultr inference not configured",
        )

    prior_facts, input_tokens, output_tokens = (
        await memory_retrieval.retrieve_customer_context(
            collection_id=collection_id,
            phone_e164=phone,
            domain_hint=domain,
            is_demo=False,
            preseed_available=False,
        )
    )

    # Raw round-trip so the caller can see what Vultr actually returned
    # before any post-processing (`<think>` strip, NO_MEMORY collapse).
    raw_messages = [
        {
            "role": "system",
            "content": (
                "You retrieve facts from a customer-memory store. "
                "Return ONLY the relevant facts about the given phone number, "
                "in 2-4 short sentences. If no facts are found, reply with 'NO_MEMORY'."
            ),
        },
        {
            "role": "user",
            "content": f"Domain: {domain}\nPhone number: {phone}\nReturn any prior call facts.",
        },
    ]
    raw = await vultr_inference.chat_completion_rag(raw_messages, collection=collection_id)
    raw_content = ""
    raw_usage = {}
    try:
        raw_content = raw["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        pass
    if isinstance(raw, dict):
        raw_usage = raw.get("usage") or {}

    return {
        "phone": phone,
        "domain": domain,
        "collection_id": collection_id,
        "prior_facts": prior_facts,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "hit": bool(prior_facts.strip()),
        "raw_response_preview": raw_content[:1200],
        "raw_usage": raw_usage,
    }


class DryRunRequest(BaseModel):
    phone_e164: str
    transcript: str
    language: str = "en"
    template_id: Optional[str] = None  # default = active template


async def _bg_run_pipeline(call_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        try:
            await run_pipeline(session, call_id)
        except Exception:  # noqa: BLE001
            await session.rollback()
            raise


@router.post("/dry-run-pipeline")
async def dry_run_pipeline(
    body: DryRunRequest,
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Inject a custom transcript and run the full agent pipeline against it.

    Probes the post-transcription stack (`call_agent` loop + RAG tool +
    executor + memory writeback) with a hand-written utterance, so the
    `lookup_customer_memory` tool can be exercised on a transcript that
    actually requires prior history (e.g. "same order as last time").

    Schedules `run_pipeline` as a background task — the response returns
    the new call_id immediately and the caller polls `/api/v1/calls/{id}`.

    Honors `X-Demo-Session`: when the caller is in demo mode the call is
    scoped to that session so it shows up in the same UI as a regular
    simulator-triggered call.
    """
    # Pick the requested template, or fall back to the first seed template
    # with the requested domain (default: restaurant).
    if body.template_id:
        template = await session.get(Template, uuid.UUID(body.template_id))
    else:
        template = (
            await session.execute(
                select(Template).where(Template.is_seed.is_(True)).limit(1)
            )
        ).scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="No template available")

    call_id = uuid.uuid4()
    session.add(
        Call(
            id=call_id,
            phone_e164=body.phone_e164,
            template_id=template.id,
            status="pending",
            raw_transcript={"text": body.transcript},
            detected_language=body.language,
            session_id=ctx.session_id,
            created_at=datetime.now(tz=timezone.utc),
        )
    )
    await session.commit()

    asyncio.create_task(_bg_run_pipeline(call_id))

    return {
        "call_id": str(call_id),
        "template_id": str(template.id),
        "domain_hint": template.domain_hint,
        "status": "pending",
        "note": "poll /api/v1/calls/{id} for completion",
    }
