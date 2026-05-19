"""Mark stuck calls as failed at startup.

When the backend container restarts mid-pipeline (deploy, OOM, crash), any
``Call`` row left in ``transcribing`` or ``analyzing`` is orphaned: no
BackgroundTasks worker will ever resume it, and the client polling on it
will eventually time out without a clear cause. This sweep, run once on
lifespan startup, marks rows older than the cut-off as ``failed`` so the
dashboard reflects reality and orphan_recovery shows up in the audit log.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.audit.logger import audit_step
from app.db.engine import SessionLocal
from app.db.models import Call

logger = logging.getLogger("afterglow")

ORPHAN_THRESHOLD = timedelta(minutes=10)
STUCK_STATUSES = ("transcribing", "analyzing")


async def recover_orphans() -> int:
    """Mark any Call stuck in transcribing/analyzing for > threshold as failed.

    Returns the number of rows touched.
    """
    cutoff = datetime.now(tz=timezone.utc) - ORPHAN_THRESHOLD
    async with SessionLocal() as session:
        stmt = (
            select(Call)
            .where(Call.status.in_(STUCK_STATUSES))
            .where(Call.started_at.is_not(None))
            .where(Call.started_at < cutoff)
        )
        rows = (await session.execute(stmt)).scalars().all()
        if not rows:
            return 0

        for call in rows:
            previous_status = call.status
            started_at_iso = call.started_at.isoformat() if call.started_at else None
            call.status = "failed"
            call.error = "orphaned_after_restart"
            call.completed_at = datetime.now(tz=timezone.utc)
            async with audit_step(
                call_id=call.id,
                session_id=call.session_id,
                agent_name="orphan_recovery",
                step_type="orphan_recovery",
                payload={"previous_status": previous_status, "started_at": started_at_iso},
            ):
                pass

        await session.commit()
        logger.info("orphan_recovery: marked %d stuck calls as failed", len(rows))
        return len(rows)
