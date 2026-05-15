"""Demo sandbox session cleanup.

Periodically walks `demo_sessions` and deletes everything that belongs to
sessions that have been idle longer than the TTL. Runs as a single asyncio
task launched in the FastAPI lifespan event (see `app/main.py`).

Order of deletion matters: child rows that carry `session_id` go first to
avoid FK conflicts, then `customers` (after `extracted_fields` and
`customer_memory_chunks` cascaded from `calls`/`customers`), finally the
`demo_sessions` row itself.

Vultr Vector Store is intentionally not touched here. In demo mode we never
push chunks to Vultr (see `orchestrator._persist_memory`), so there is
nothing to clean up on the Vultr side.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import SessionLocal
from app.db.models import (
    AuditLog,
    Call,
    Customer,
    CustomerMemoryChunk,
    DemoSession,
    ExecutedAction,
    Template,
)

logger = logging.getLogger("afterglow")

# How long a demo session can stay idle before we wipe it. 24h matches the
# judging-day cadence: a judge who comes back the next day gets a fresh box.
SESSION_TTL = timedelta(hours=24)
CLEANUP_INTERVAL_SECONDS = 30 * 60


async def _purge_session(session: AsyncSession, demo_id) -> None:
    # Children that carry a direct session_id.
    await session.execute(
        delete(ExecutedAction).where(ExecutedAction.session_id == demo_id)
    )
    await session.execute(
        delete(CustomerMemoryChunk).where(CustomerMemoryChunk.session_id == demo_id)
    )
    await session.execute(
        delete(AuditLog).where(AuditLog.session_id == demo_id)
    )
    # `calls` cascades to `extracted_fields`, `executed_actions`,
    # `customer_memory_chunks` — but we already cleared those above to avoid
    # FK conflicts on `customers` deletion below.
    await session.execute(delete(Call).where(Call.session_id == demo_id))
    await session.execute(delete(Customer).where(Customer.session_id == demo_id))
    await session.execute(delete(Template).where(Template.session_id == demo_id))
    await session.execute(delete(DemoSession).where(DemoSession.id == demo_id))


async def cleanup_stale_sessions() -> int:
    """Delete idle demo sessions and everything they own. Returns count."""
    cutoff = datetime.now(tz=timezone.utc) - SESSION_TTL
    async with SessionLocal() as session:
        stale = (
            await session.execute(
                select(DemoSession.id).where(DemoSession.last_seen_at < cutoff)
            )
        ).scalars().all()

        for demo_id in stale:
            await _purge_session(session, demo_id)

        if stale:
            await session.commit()
            logger.info(
                "session_cleanup: purged %d stale demo session(s)", len(stale)
            )
        return len(stale)


async def run_cleanup_loop() -> None:
    """Long-running task: sweep every CLEANUP_INTERVAL_SECONDS forever."""
    logger.info(
        "session_cleanup: started (interval=%ds, ttl=%s)",
        CLEANUP_INTERVAL_SECONDS,
        SESSION_TTL,
    )
    while True:
        try:
            await cleanup_stale_sessions()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("session_cleanup: sweep failed; will retry")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
