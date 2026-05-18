"""Shift seed-row timestamps to keep the demo dataset "always today-ish".

The seed dataset materializes every Call/AuditLog/ExecutedAction/ExtractedFields
timestamp as `anchor + day_offset`. The anchor is persisted in the `settings`
table under `seed_anchor_date`. On every backend boot, this task compares the
persisted anchor with `today`. If they drift (typical: a deploy that lands
N days after the previous boot), all seed timestamps are BULK-shifted forward
by N days so the Home screen never shows "12 days ago" on a call that should
read "yesterday".

Bootstrap-aware: a fresh DB has no anchor row — `resolve_seed_anchor_for_materialization`
picks one (either inferred from existing seed `max(created_at)` for legacy
round-8 DBs, or today for empty DBs).

JSONB shift: `ExecutedAction.payload.booking_date` and
`ExtractedFields.fields.booking_date` are ISO date strings inside JSONB
columns; they are shifted via `jsonb_set` in the same transaction so a
booking that was "in 2 days" stays "in 2 days" relative to the new anchor.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    Call,
    Customer,
    ExecutedAction,
    ExtractedFields,
)
from app.services.settings import (
    get_seed_anchor,
    resolve_seed_anchor_for_materialization,
    set_seed_anchor,
)

logger = logging.getLogger("afterglow")


async def refresh_seed_dates_if_needed(
    session: AsyncSession, today: date
) -> int:
    """Bulk-shift seed timestamps by `today - persisted_anchor`.

    Returns the number of rows actually updated across all tables. Returns 0
    if no shift was needed (anchor == today or DB has no seed data).

    Idempotent: a second call with the same `today` is a no-op.
    """
    anchor = await get_seed_anchor(session)
    if anchor is None:
        # No anchor row yet. Either a fresh DB (no seed rows yet either —
        # zero shift, just write today) or a legacy round-8 DB (seed rows
        # exist with hardcoded dates anchored to 2026-05-17 — shift from
        # that inferred anchor).
        anchor = await resolve_seed_anchor_for_materialization(session, today)

    delta_days = (today - anchor).days
    if delta_days == 0:
        # Persist the anchor (covers the "first-time-ever" case where
        # `get_seed_anchor` returned None and inferred == today).
        await set_seed_anchor(session, today)
        return 0

    delta = timedelta(days=delta_days)
    logger.info(
        "seed_date_refresh: shifting seed timestamps by %+d days "
        "(anchor %s -> today %s)",
        delta_days,
        anchor.isoformat(),
        today.isoformat(),
    )

    total_rows = 0

    # 1) Call timestamps (seed only — demo-session clones keep their real
    # created_at; they're ephemeral and the user expects them "now").
    res = await session.execute(
        update(Call)
        .where(Call.is_seed.is_(True))
        .values(
            created_at=Call.created_at + delta,
            started_at=Call.started_at + delta,
            completed_at=Call.completed_at + delta,
        )
    )
    total_rows += res.rowcount or 0

    # 2) ExtractedFields.created_at — children of seed calls.
    # We can't filter on Call.is_seed in an UPDATE...JOIN reliably across
    # PG dialects, so use a subquery on call_id.
    seed_call_id_subq = select(Call.id).where(Call.is_seed.is_(True))
    res = await session.execute(
        update(ExtractedFields)
        .where(ExtractedFields.call_id.in_(seed_call_id_subq))
        .values(created_at=ExtractedFields.created_at + delta)
    )
    total_rows += res.rowcount or 0

    # 3) ExecutedAction.created_at — children of seed calls.
    res = await session.execute(
        update(ExecutedAction)
        .where(ExecutedAction.call_id.in_(seed_call_id_subq))
        .values(created_at=ExecutedAction.created_at + delta)
    )
    total_rows += res.rowcount or 0

    # 4) AuditLog.created_at — children of seed calls. AuditLog rows with
    # call_id IS NULL (lifespan events) are NOT shifted; they're operational
    # and should reflect real wall time.
    res = await session.execute(
        update(AuditLog)
        .where(
            and_(
                AuditLog.call_id.in_(seed_call_id_subq),
                AuditLog.session_id.is_(None),
            )
        )
        .values(created_at=AuditLog.created_at + delta)
    )
    total_rows += res.rowcount or 0

    # 5) Customer.last_call_at — seed customers only. total_calls is a
    # count, not a timestamp, so it stays put. created_at stays put too
    # (the customer "row" is older than any single call).
    res = await session.execute(
        update(Customer)
        .where(
            and_(
                Customer.is_seed.is_(True),
                Customer.last_call_at.is_not(None),
            )
        )
        .values(last_call_at=Customer.last_call_at + delta)
    )
    total_rows += res.rowcount or 0

    # 6) JSONB shift: ExecutedAction.payload.booking_date (and ExtractedFields.fields).
    # Raw SQL because SQLAlchemy's jsonb_set helper is verbose and the WHERE
    # clause needs `?` (jsonb has_key) operator. Scoped to seed rows only
    # via a join condition.
    await session.execute(
        text(
            """
            UPDATE executed_actions ea
            SET payload = jsonb_set(
                ea.payload,
                '{booking_date}',
                to_jsonb(
                    ((ea.payload->>'booking_date')::date + (:days || ' days')::interval)::date::text
                )
            )
            FROM calls c
            WHERE ea.call_id = c.id
              AND c.is_seed IS TRUE
              AND ea.payload ? 'booking_date'
              AND (ea.payload->>'booking_date') ~ '^\\d{4}-\\d{2}-\\d{2}$'
            """
        ),
        {"days": str(delta_days)},
    )

    await session.execute(
        text(
            """
            UPDATE extracted_fields ef
            SET fields = jsonb_set(
                ef.fields,
                '{booking_date}',
                to_jsonb(
                    ((ef.fields->>'booking_date')::date + (:days || ' days')::interval)::date::text
                )
            )
            FROM calls c
            WHERE ef.call_id = c.id
              AND c.is_seed IS TRUE
              AND ef.fields ? 'booking_date'
              AND (ef.fields->>'booking_date') ~ '^\\d{4}-\\d{2}-\\d{2}$'
            """
        ),
        {"days": str(delta_days)},
    )

    await set_seed_anchor(session, today)
    logger.info(
        "seed_date_refresh: %d row(s) updated; anchor now %s",
        total_rows,
        today.isoformat(),
    )
    return total_rows
