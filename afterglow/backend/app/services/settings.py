"""Runtime settings backed by the `settings` table.

The only setting today is `seed_anchor_date`, which records the date the
seed dataset was last anchored to. `refresh_seed_dates_if_needed` reads
this on every backend boot and BULK-shifts seed timestamps when the
current date drifts past the anchor.

`resolve_seed_anchor_for_materialization` is the single source of truth
for "what anchor should we use right now?" — shared between `seed.py`
(when emitting new fixtures) and the refresh task (when calculating delta),
so a deploy onto a legacy DB (round-8 hardcoded dates, no `settings` row)
does the right thing instead of clobbering the anchor with today and
leaving old rows stranded in May 2026.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Call, Setting

SEED_ANCHOR_KEY = "seed_anchor_date"


async def get_seed_anchor(session: AsyncSession) -> Optional[date]:
    """Return the persisted seed anchor date, or None if never set."""
    row = await session.get(Setting, SEED_ANCHOR_KEY)
    if row is None:
        return None
    return date.fromisoformat(row.value)


async def set_seed_anchor(session: AsyncSession, anchor: date) -> None:
    """Upsert the seed anchor date. Uses ON CONFLICT so concurrent boots
    don't race on first write."""
    stmt = (
        insert(Setting)
        .values(key=SEED_ANCHOR_KEY, value=anchor.isoformat())
        .on_conflict_do_update(
            index_elements=[Setting.key],
            set_={"value": anchor.isoformat()},
        )
    )
    await session.execute(stmt)


async def resolve_seed_anchor_for_materialization(
    session: AsyncSession, today: date
) -> date:
    """Anchor to use when materializing new seed fixtures.

    - Persisted `seed_anchor_date` wins (consistency with rows already in
      the DB).
    - Otherwise, if seed calls already exist (round-8 legacy DB), infer
      from `max(Call.created_at)` scoped to `is_seed=True` — that's the
      canonical anchor of the hardcoded round-8 dataset (2026-05-17, the
      last day of the busy week). New fixtures get materialized around the
      same anchor so a subsequent `refresh_seed_dates_if_needed` shifts
      the whole set together.
    - Otherwise (empty DB on first boot) → today.

    Does NOT persist the anchor — that's `set_seed_anchor`'s job, called
    by the refresh task once it's decided what delta to apply.
    """
    persisted = await get_seed_anchor(session)
    if persisted is not None:
        return persisted

    latest_seed_call = await session.scalar(
        select(func.max(Call.created_at)).where(Call.is_seed.is_(True))
    )
    if latest_seed_call is not None:
        return latest_seed_call.date()

    return today
