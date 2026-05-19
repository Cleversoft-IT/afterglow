"""Tests for the anchor-day seed reposition logic in seed_date_refresh.

The reposition runs on every backend boot and keeps `Call.is_anchor_day`
rows positioned just before `now`, regardless of whether the day-level
shift fired. Without it, the day_offset=0 seed slots materialized at
07:00/08:30 UTC float in the future for visitors opening the demo before
mid-morning UTC and sort above legitimate "just now" simulator calls.

These tests use a hand-rolled `AsyncSession` mock that captures `.execute`
calls so we can assert per-row delta propagation without a real Postgres.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tasks import seed_date_refresh


def _make_call(
    *,
    is_anchor_day: bool = True,
    created_at: datetime,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    customer_id: uuid.UUID | None = None,
) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        is_anchor_day=is_anchor_day,
        session_id=None,
        created_at=created_at,
        started_at=started_at or created_at,
        completed_at=completed_at or created_at,
        customer_id=customer_id,
    )


class _FakeSession:
    """Minimal AsyncSession stand-in for the reposition path.

    `select(Call)...` returns the queued list of anchor-day calls; every
    `update(...)` becomes an entry in `update_calls` so the test can
    assert the per-row deltas were issued.
    """

    def __init__(self, anchor_day_calls: list[Any]) -> None:
        self._anchor_day_calls = anchor_day_calls
        self.update_calls: list[Any] = []

    async def execute(self, stmt: Any) -> Any:
        # Distinguish between SELECT (returns calls) and UPDATE (captured).
        compiled = str(stmt).lower()
        if compiled.startswith("select"):
            scalars = MagicMock()
            scalars.all.return_value = list(self._anchor_day_calls)
            result = MagicMock()
            result.scalars.return_value = scalars
            return result
        # UPDATE — record it. The test verifies count + presence; ORM
        # state on `Call` objects is mutated directly by the function
        # (no need to apply the UPDATE to the fake rows).
        self.update_calls.append(stmt)
        return MagicMock(rowcount=1)


# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_target_offsets_two_slots():
    """Two anchor-day slots → [now-5h, now-2h], oldest-first."""
    now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    older = _make_call(created_at=datetime(2026, 5, 19, 7, 0, tzinfo=timezone.utc))
    newer = _make_call(created_at=datetime(2026, 5, 19, 8, 30, tzinfo=timezone.utc))
    session = _FakeSession([older, newer])

    moved = await seed_date_refresh._reposition_anchor_day_calls(session, now)

    assert moved == 2
    assert older.created_at == now - timedelta(hours=5)
    assert newer.created_at == now - timedelta(hours=2)
    # Both squarely in the past.
    assert older.created_at < now
    assert newer.created_at < now


@pytest.mark.asyncio
async def test_target_offsets_three_slots_preserve_order():
    """Three slots → [5h, 3.5h, 2h], evenly spread, ordering preserved."""
    now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    c1 = _make_call(created_at=datetime(2026, 5, 19, 7, 0, tzinfo=timezone.utc))
    c2 = _make_call(created_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc))
    c3 = _make_call(created_at=datetime(2026, 5, 19, 9, 0, tzinfo=timezone.utc))
    session = _FakeSession([c1, c2, c3])

    await seed_date_refresh._reposition_anchor_day_calls(session, now)

    assert c1.created_at == now - timedelta(hours=5)
    assert c2.created_at == now - timedelta(hours=3, minutes=30)
    assert c3.created_at == now - timedelta(hours=2)
    assert c1.created_at < c2.created_at < c3.created_at < now


@pytest.mark.asyncio
async def test_single_slot_targets_3h():
    """A single anchor-day slot lands at exactly `now - 3h`."""
    now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    call = _make_call(created_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc))
    session = _FakeSession([call])

    await seed_date_refresh._reposition_anchor_day_calls(session, now)

    assert call.created_at == now - timedelta(hours=3)


@pytest.mark.asyncio
async def test_started_and_completed_shift_by_same_delta():
    """`started_at` + `completed_at` shift by the same delta as `created_at`."""
    now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    # Single slot target = now - 3h = 09:00. Original created_at = 07:00,
    # so the per-row delta is +2h.
    original = datetime(2026, 5, 19, 7, 0, tzinfo=timezone.utc)
    completed = datetime(2026, 5, 19, 7, 0, 45, tzinfo=timezone.utc)
    call = _make_call(
        created_at=original,
        started_at=original,
        completed_at=completed,
    )
    session = _FakeSession([call])

    await seed_date_refresh._reposition_anchor_day_calls(session, now)

    expected_delta = timedelta(hours=2)
    assert call.created_at == original + expected_delta
    assert call.started_at == original + expected_delta
    assert call.completed_at == completed + expected_delta


@pytest.mark.asyncio
async def test_idempotent_same_now():
    """Calling twice with the same `now` converges to the same positions."""
    now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    older = _make_call(created_at=datetime(2026, 5, 19, 7, 0, tzinfo=timezone.utc))
    newer = _make_call(created_at=datetime(2026, 5, 19, 8, 30, tzinfo=timezone.utc))
    session = _FakeSession([older, newer])

    await seed_date_refresh._reposition_anchor_day_calls(session, now)
    first_positions = (older.created_at, newer.created_at)

    await seed_date_refresh._reposition_anchor_day_calls(session, now)
    second_positions = (older.created_at, newer.created_at)

    assert first_positions == second_positions
    assert older.created_at < newer.created_at < now


@pytest.mark.asyncio
async def test_child_updates_are_emitted_per_call():
    """Each anchor-day call triggers UPDATE statements for the three child
    tables. Customer.last_call_at also gets an UPDATE per call with a
    customer_id. Skip the short-circuit by picking original timestamps
    that don't already match the reposition targets."""
    now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    # Target for N=2 is [now-5h, now-2h] = [07:00, 10:00]. We pick
    # 06:00 and 09:00 so both rows move (non-zero delta).
    c1 = _make_call(
        created_at=datetime(2026, 5, 19, 6, 0, tzinfo=timezone.utc),
        customer_id=uuid.uuid4(),
    )
    c2 = _make_call(
        created_at=datetime(2026, 5, 19, 9, 0, tzinfo=timezone.utc),
        customer_id=None,
    )
    session = _FakeSession([c1, c2])

    await seed_date_refresh._reposition_anchor_day_calls(session, now)

    # c1 has customer_id → 4 UPDATEs (ExtractedFields, ExecutedAction,
    #   AuditLog, Customer); c2 has no customer_id → 3 UPDATEs.
    assert len(session.update_calls) == 4 + 3


@pytest.mark.asyncio
async def test_no_anchor_day_rows_is_noop():
    """When no `is_anchor_day=True` rows exist, the function returns 0
    without touching anything."""
    now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    session = _FakeSession([])

    moved = await seed_date_refresh._reposition_anchor_day_calls(session, now)

    assert moved == 0
    assert session.update_calls == []
