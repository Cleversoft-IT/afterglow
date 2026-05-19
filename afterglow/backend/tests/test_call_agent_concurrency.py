"""Regression: parallel tool calls must not race on the shared AsyncSession.

Gemini's ADK runner can fan out two `function_call`s in the same turn (parallel
function calling). Without the orchestrator's `session_lock`, two
`session.flush()` coroutines hit the same `AsyncSession` concurrently and
SQLAlchemy raises `InvalidRequestError("Session is already flushing")`. The
call agent surfaces it to operators as "adk_runner: ... pipeline error".

This test simulates two action tools fired with `asyncio.gather` and asserts
the lock serializes them — no overlap, no exception.
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest


class _FakeSession:
    """Mimics the bits of `AsyncSession` we exercise.

    `_in_flush` is the canary: if two coroutines reach `flush()` at the
    same time the assertion blows up, which is exactly what SQLAlchemy
    would do (modulo error message).
    """

    def __init__(self) -> None:
        self._in_flush = False
        self.flush_calls = 0

    def add(self, _obj: Any) -> None:  # noqa: D401
        return None

    async def flush(self) -> None:
        assert not self._in_flush, "concurrent flush — lock did NOT serialize"
        self._in_flush = True
        # Yield to the loop so a competing coroutine has a chance to race.
        await asyncio.sleep(0)
        self.flush_calls += 1
        self._in_flush = False


async def _do_flush(session: _FakeSession, session_lock: asyncio.Lock) -> None:
    async with session_lock:
        session.add(object())
        await session.flush()


@pytest.mark.asyncio
async def test_session_lock_serializes_parallel_flushes():
    """Two coroutines racing on `session.flush()` under the lock do not overlap."""
    session = _FakeSession()
    lock = asyncio.Lock()

    await asyncio.gather(
        _do_flush(session, lock),
        _do_flush(session, lock),
        _do_flush(session, lock),
    )

    assert session.flush_calls == 3
    assert not session._in_flush


@pytest.mark.asyncio
async def test_session_without_lock_raises_assertion():
    """Sanity: without the lock the fake session catches the race.

    Documents the failure mode the production fix prevents. If this stops
    failing, the `_FakeSession._in_flush` canary is broken.
    """
    session = _FakeSession()

    async def _unsafe() -> None:
        session.add(object())
        await session.flush()

    with pytest.raises(AssertionError, match="concurrent flush"):
        await asyncio.gather(_unsafe(), _unsafe())
