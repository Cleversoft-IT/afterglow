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

Anchor-day reposition (round 12): seed calls flagged `is_anchor_day=True`
(the day_offset=0 slots — Sophie Walker booking + Rosie Stewart mock) are
ALWAYS repositioned to sit safely in the past relative to `now`, regardless
of whether the day-level shift ran. Without this, the slots materialized at
07:00/08:30 UTC would float in the future for any visitor opening the demo
before mid-morning UTC, sorting above legitimate "just now" simulator calls.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

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
    session: AsyncSession, today: date, now: datetime
) -> int:
    """Bulk-shift seed timestamps by `today - persisted_anchor`, then
    reposition every anchor-day seed Call to sit just before `now`.

    Returns the number of rows actually updated across all tables. The
    anchor-day reposition runs UNCONDITIONALLY (even when delta_days == 0)
    because the bug it fixes — day_offset=0 slots floating in the future
    relative to `now` — happens precisely when the anchor already equals
    today.

    Idempotent: a second call with the same `today`/`now` is a no-op for the
    day-level shift; the reposition will move anchor-day calls again but
    converges to the same `[now - N×h, ...]` positions.
    """
    anchor = await get_seed_anchor(session)
    if anchor is None:
        # No anchor row yet. Either a fresh DB (no seed rows yet either —
        # zero shift, just write today) or a legacy round-8 DB (seed rows
        # exist with hardcoded dates anchored to 2026-05-17 — shift from
        # that inferred anchor).
        anchor = await resolve_seed_anchor_for_materialization(session, today)

    delta_days = (today - anchor).days
    total_rows = 0

    if delta_days != 0:
        delta = timedelta(days=delta_days)
        logger.info(
            "seed_date_refresh: shifting seed timestamps by %+d days "
            "(anchor %s -> today %s)",
            delta_days,
            anchor.isoformat(),
            today.isoformat(),
        )

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

        logger.info(
            "seed_date_refresh: %d row(s) day-shifted; anchor now %s",
            total_rows,
            today.isoformat(),
        )

    # Always run the anchor-day reposition — that's the whole point of this
    # task on a same-day boot.
    total_rows += await _reposition_anchor_day_calls(session, now)
    await set_seed_anchor(session, today)
    return total_rows


async def _reposition_anchor_day_calls(
    session: AsyncSession, now: datetime
) -> int:
    """Move every `Call.is_anchor_day == True` row so it sits in the past
    relative to `now`, preserving the relative ordering between slots.

    Slot ordering is taken from the current `Call.created_at ASC` — that's
    stable across reposition runs because the formula always assigns the
    oldest target to slot 0 and the newest to the last slot.

    For two slots the targets are `[now - 5h, now - 2h]`. For N>2 slots
    they spread linearly between 5h and 2h ago. Children
    (`ExtractedFields`, `ExecutedAction`, `AuditLog`) and the linked
    `Customer.last_call_at` are shifted by the same per-row delta so the
    Customer "last call" subtitle and the audit timeline stay coherent.
    """
    rows = (
        await session.execute(
            select(Call)
            .where(
                Call.is_anchor_day.is_(True),
                Call.session_id.is_(None),
            )
            .order_by(Call.created_at.asc())
        )
    ).scalars().all()

    if not rows:
        return 0

    n = len(rows)
    if n == 1:
        target_offsets_hours = [3.0]
    else:
        span = 5.0 - 2.0
        target_offsets_hours = [5.0 - (span / (n - 1)) * i for i in range(n)]

    for call, hours in zip(rows, target_offsets_hours):
        new_created = now - timedelta(hours=hours)
        delta = new_created - call.created_at
        if delta == timedelta(0):
            continue
        old_created = call.created_at
        call.created_at = new_created
        if call.started_at is not None:
            call.started_at = call.started_at + delta
        if call.completed_at is not None:
            call.completed_at = call.completed_at + delta

        await session.execute(
            update(ExtractedFields)
            .where(ExtractedFields.call_id == call.id)
            .values(created_at=ExtractedFields.created_at + delta)
        )
        await session.execute(
            update(ExecutedAction)
            .where(ExecutedAction.call_id == call.id)
            .values(created_at=ExecutedAction.created_at + delta)
        )
        await session.execute(
            update(AuditLog)
            .where(
                and_(
                    AuditLog.call_id == call.id,
                    AuditLog.session_id.is_(None),
                )
            )
            .values(created_at=AuditLog.created_at + delta)
        )

        # Only move the Customer pointer when it was tracking exactly this
        # call. If a more recent call exists for the same customer, leave
        # it alone — the contact's "last call" subtitle is correct.
        if call.customer_id is not None:
            await session.execute(
                update(Customer)
                .where(
                    and_(
                        Customer.id == call.customer_id,
                        Customer.last_call_at == old_created,
                    )
                )
                .values(last_call_at=new_created)
            )

    logger.info(
        "seed_date_refresh: repositioned %d anchor-day call(s) "
        "to [now-%.1fh ... now-%.1fh]",
        n,
        target_offsets_hours[0],
        target_offsets_hours[-1],
    )
    return n
