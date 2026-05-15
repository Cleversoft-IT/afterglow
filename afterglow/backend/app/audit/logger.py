"""Structured audit logger — every agent step + every action + every revert lands here.

Each ``audit_step`` writes its row using its own short-lived session obtained from
``SessionLocal``. The row is committed immediately so it survives even if the
caller's business transaction rolls back (e.g. when ``run_pipeline`` raises and
the BackgroundTasks wrapper does a ``rollback``). The previous design — flushing
into the same session — meant a failure mid-pipeline wiped the entire audit trail.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from app.db.engine import SessionLocal
from app.db.models import AuditLog


@asynccontextmanager
async def audit_step(
    *,
    agent_name: str,
    step_type: str,
    call_id: Optional[uuid.UUID] = None,
    session_id: Optional[uuid.UUID] = None,
    model: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    status: str = "success",
):
    """Async context manager that writes one audit row per agent step.

    Captures duration_ms and status automatically. ``session_id`` is the demo
    sandbox session that owns this step (None for production single-tenant);
    it propagates the row so audit reads stay isolated per visitor. ``status``
    lets callers pre-flag rows as ``"skipped"`` without raising.

    Implementation note: this no longer takes an ``AsyncSession`` argument —
    every audit row gets its own session+commit so it survives external
    rollbacks. Callers that previously passed ``session`` should drop that arg.
    """
    start = time.perf_counter()
    entry = AuditLog(
        call_id=call_id,
        session_id=session_id,
        agent_name=agent_name,
        step_type=step_type,
        model=model,
        payload=payload,
        status=status,
    )

    try:
        yield entry
    except Exception as exc:  # noqa: BLE001
        entry.status = "error"
        entry.error = str(exc)[:1000]
        raise
    finally:
        entry.duration_ms = int((time.perf_counter() - start) * 1000)
        async with SessionLocal() as audit_session:
            audit_session.add(entry)
            await audit_session.commit()
