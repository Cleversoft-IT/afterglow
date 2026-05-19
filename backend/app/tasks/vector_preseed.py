"""Pre-populate the Vultr Vector Store with a chunk per seed call.

Why: the demo sandbox skips the runtime write-back to Vultr (cross-visitor
pollution) but the *read* path is what makes Vultr visible to the judges.
Without a populated collection, every demo call's `memory_lookup` step
falls back to the empty structured history and the RAG narrative misses
the punch line. Seeding the collection at boot makes "Call from existing
customer" produce a real RAG retrieval audit row on the very first try.

Idempotency strategy: **per-call**. We compute the expected set of seed
call IDs (`Call.is_seed AND raw_transcript IS NOT NULL`), diff against the
chunks already marked `chunk_metadata.preseed = true` for this collection,
and insert only the missing ones. A partial failure (Vultr 500 mid-loop)
recovers naturally on the next boot — no "skip if any preseed exists"
trap that would strand the remaining inserts.

Failure mode: each per-call insert is wrapped; we log and continue. The
collection ends up partially populated and the next boot fills the gap.
The lifespan caller treats the whole task as best-effort (warning, not
error).
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import _format_briefing_chunk
from app.config import get_settings
from app.db.models import (
    Call,
    Customer,
    CustomerMemoryChunk,
    ExtractedFields,
    Template,
)
from app.integrations import vultr_inference

logger = logging.getLogger("afterglow")
settings = get_settings()


async def preseed_demo_collection(session: AsyncSession) -> int:
    """Insert any missing preseed chunks into the Vultr Vector Store.

    Returns the number of chunks newly inserted (0 if up-to-date or
    disabled). Never raises — Vultr being unreachable is reported via the
    return value and a warning log.
    """
    collection_id = settings.vultr_vector_default_collection
    if not collection_id:
        logger.info(
            "vector_preseed: VULTR_VECTOR_DEFAULT_COLLECTION not set — skipping"
        )
        return 0
    if not settings.vultr_inference_api_key:
        logger.info(
            "vector_preseed: VULTR_INFERENCE_API_KEY not set — skipping"
        )
        return 0

    # 1) Expected: every seed call with a non-empty transcript. Personal
    # calls (missed / unknown / human-handled) carry no briefing and are
    # not worth indexing.
    expected_call_ids: set[uuid.UUID] = set(
        (
            await session.execute(
                select(Call.id).where(
                    Call.is_seed.is_(True),
                    Call.raw_transcript.is_not(None),
                )
            )
        ).scalars().all()
    )

    # 2) Already preseeded for this collection. Filter by marker so that
    # production single-tenant chunks (no `preseed` key in metadata) don't
    # accidentally count and short-circuit the loop.
    preseeded_call_ids: set[uuid.UUID] = set(
        (
            await session.execute(
                select(CustomerMemoryChunk.call_id).where(
                    CustomerMemoryChunk.vultr_collection_id == collection_id,
                    CustomerMemoryChunk.chunk_metadata["preseed"].as_boolean().is_(True),
                    CustomerMemoryChunk.call_id.is_not(None),
                )
            )
        ).scalars().all()
    )

    missing = expected_call_ids - preseeded_call_ids
    if not missing:
        logger.info(
            "vector_preseed: collection already up to date (%d chunks)",
            len(preseeded_call_ids),
        )
        return 0

    logger.info(
        "vector_preseed: inserting %d missing chunks "
        "(expected=%d, already preseeded=%d)",
        len(missing),
        len(expected_call_ids),
        len(preseeded_call_ids),
    )

    inserted = 0
    for call_id in missing:
        try:
            ok = await _preseed_one(session, call_id, collection_id)
            if ok:
                inserted += 1
        except (httpx.HTTPError, IntegrityError) as exc:
            # Per-call failure: log and keep going. Next boot fills the gap.
            logger.warning(
                "vector_preseed: failed to insert chunk for call %s (%s) — continuing",
                call_id,
                exc,
            )

    logger.info("vector_preseed: inserted %d new chunk(s)", inserted)
    return inserted


async def _preseed_one(
    session: AsyncSession,
    call_id: uuid.UUID,
    collection_id: str,
) -> bool:
    """Materialize and insert a single preseed chunk. Returns True on success."""
    row = (
        await session.execute(
            select(Call, ExtractedFields, Customer, Template)
            .join(ExtractedFields, ExtractedFields.call_id == Call.id)
            .join(Customer, Customer.id == Call.customer_id)
            .join(Template, Template.id == Call.template_id)
            .where(Call.id == call_id)
        )
    ).first()
    if row is None:
        logger.debug(
            "vector_preseed: call %s missing extracted/customer/template — skipping",
            call_id,
        )
        return False

    call, extracted, customer, template = row
    briefing = (extracted.briefing_snapshot or "").strip()
    if not briefing:
        logger.debug(
            "vector_preseed: call %s has empty briefing — skipping",
            call_id,
        )
        return False

    classification = {
        "intent": extracted.intent or "unknown",
        "sentiment": extracted.sentiment or "unknown",
        "urgency": extracted.urgency or "unknown",
        "language": (call.detected_language or "en").lower(),
    }
    # Seed transcripts are EN-only (see feedback-code-language), so the
    # bilingual EN tail is None — the chunk is already in English.
    chunk_content = _format_briefing_chunk(
        call=call,
        customer=customer,
        template=template,
        briefing=briefing,
        briefing_en=None,
        classification=classification,
    )

    item_id: Optional[str] = await vultr_inference.add_vector_item(
        collection_id,
        content=chunk_content,
        description=f"call_{call.id} phone_{customer.phone_e164} preseed",
    )
    if item_id is None:
        # Stub mode or other no-op — don't write a fake ledger row.
        return False

    session.add(
        CustomerMemoryChunk(
            id=uuid.uuid4(),
            customer_id=customer.id,
            call_id=call.id,
            vultr_collection_id=collection_id,
            vultr_item_id=item_id,
            summary=briefing,
            chunk_metadata={
                **classification,
                "phone_e164": customer.phone_e164,
                "customer_id": str(customer.id),
                "preseed": True,
            },
            session_id=None,
        )
    )
    return True
