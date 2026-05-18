"""Operational diagnostics — read-only probes for the Vultr Vector Store
side of the pipeline.

Two endpoints:
- `GET /api/v1/admin/rag-stats` reports how many preseed chunks landed in
  Postgres for the active collection. The lifespan preseed task and the
  runtime memory-updater both write `CustomerMemoryChunk` rows; the preseed
  marker discriminates them.
- `GET /api/v1/admin/rag-probe?phone=...` issues a real `chat_completion_rag`
  call against Vultr and returns the raw retrieved text + token usage so a
  judge can confirm the integration is live, not stubbed.

Both endpoints are read-only and do not require demo-session scoping.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import memory_retrieval
from app.config import get_settings
from app.db.engine import get_session
from app.db.models import CustomerMemoryChunk
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
