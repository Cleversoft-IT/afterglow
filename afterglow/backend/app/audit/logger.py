"""Structured audit logger — every agent step + every action + every revert lands here."""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


@asynccontextmanager
async def audit_step(
    session: AsyncSession,
    *,
    agent_name: str,
    step_type: str,
    call_id: Optional[uuid.UUID] = None,
    model: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
):
    """Async context manager that writes one audit row per agent step.

    Captures duration_ms and status automatically.
    """
    start = time.perf_counter()
    entry = AuditLog(
        call_id=call_id,
        agent_name=agent_name,
        step_type=step_type,
        model=model,
        payload=payload,
        status="success",
    )

    try:
        yield entry
    except Exception as exc:  # noqa: BLE001
        entry.status = "error"
        entry.error = str(exc)[:1000]
        raise
    finally:
        entry.duration_ms = int((time.perf_counter() - start) * 1000)
        session.add(entry)
        await session.flush()
