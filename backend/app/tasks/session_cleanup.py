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
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
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


def _audio_paths_from_simulation_config(sim: dict[str, Any] | None) -> list[Path]:
    """Pull every on-disk audio path referenced by a Template.simulation_config.

    Covers both the legacy flat `audio_url` shape and the
    `scenarios.{existing,new}.audio_url` shape used since 2026-05-18.
    """
    if not sim:
        return []
    out: list[Path] = []
    flat = sim.get("audio_url")
    if isinstance(flat, str) and flat:
        out.append(Path(flat))
    scenarios = sim.get("scenarios") or {}
    for scenario in scenarios.values():
        if not isinstance(scenario, dict):
            continue
        url = scenario.get("audio_url")
        if isinstance(url, str) and url:
            out.append(Path(url))
    return out


def unlink_audio_files(paths: Iterable[Path]) -> None:
    """Best-effort unlink, restricted to the configured audio storage dir.

    The restriction guards against rogue audio_url values escaping the
    sandbox (e.g. a future code path that stores `/etc/passwd` in the
    column) — we only ever remove files we own.
    """
    storage_root = Path(get_settings().audio_storage_dir).resolve()
    for raw in paths:
        try:
            target = raw.resolve()
            if not target.is_file():
                continue
            # `is_relative_to` is 3.9+; backend pins 3.11 so this is safe.
            if not target.is_relative_to(storage_root):
                logger.warning(
                    "session_cleanup: refusing to unlink path outside audio "
                    "storage root: %s",
                    target,
                )
                continue
            target.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("session_cleanup: unlink failed for %s: %s", raw, exc)


async def purge_session_data(
    session: AsyncSession, demo_id, *, drop_session_row: bool = True
) -> list[Path]:
    """Wipe every row owned by `demo_id`.

    Returns the list of on-disk audio paths that were referenced by the
    deleted rows so the caller can unlink them after the DB commit lands.
    We deliberately collect the paths BEFORE the DELETEs and unlink AFTER
    the caller commits — if the filesystem step fails we end up with
    orphan files (cheap) rather than orphan DB rows pointing at gone
    files (loud bug).

    When `drop_session_row=True` (default, used by the cron) the `DemoSession`
    row itself is removed too. When called from the on-demand reset endpoint we
    pass `drop_session_row=False` to keep the same session alive — the caller
    then resets `active_template_id` and bumps `last_seen_at`, so the visitor
    keeps the same uuid in localStorage with no need for a fresh handshake.
    """
    # Collect audio paths owned by this session BEFORE the deletes.
    audio_paths: list[Path] = []
    template_configs = (
        await session.execute(
            select(Template.simulation_config).where(Template.session_id == demo_id)
        )
    ).scalars().all()
    for sim in template_configs:
        audio_paths.extend(_audio_paths_from_simulation_config(sim))
    call_paths = (
        await session.execute(
            select(Call.audio_url).where(Call.session_id == demo_id)
        )
    ).scalars().all()
    audio_paths.extend(Path(p) for p in call_paths if p)

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
    if drop_session_row:
        await session.execute(delete(DemoSession).where(DemoSession.id == demo_id))

    return audio_paths


async def cleanup_stale_sessions() -> int:
    """Delete idle demo sessions and everything they own. Returns count."""
    cutoff = datetime.now(tz=timezone.utc) - SESSION_TTL
    async with SessionLocal() as session:
        stale = (
            await session.execute(
                select(DemoSession.id).where(DemoSession.last_seen_at < cutoff)
            )
        ).scalars().all()

        all_audio_paths: list[Path] = []
        for demo_id in stale:
            all_audio_paths.extend(
                await purge_session_data(session, demo_id, drop_session_row=True)
            )

        if stale:
            await session.commit()
            unlink_audio_files(all_audio_paths)
            logger.info(
                "session_cleanup: purged %d stale demo session(s), %d audio file(s)",
                len(stale),
                len(all_audio_paths),
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
