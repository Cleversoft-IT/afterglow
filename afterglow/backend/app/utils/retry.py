"""Async retry helper with exponential backoff.

Used to wrap external network calls (Speechmatics, Gemini, Vultr) so a single
transient failure does not throw away an already-completed pipeline step. No
third-party dependency — vanilla ``asyncio.sleep`` is enough at our scale.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger("afterglow")

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    factor: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    label: str = "operation",
) -> T:
    """Run ``func`` up to ``attempts`` times with exponential backoff.

    Re-raises the last exception if every attempt fails. Logs each retry at
    warning level so the audit trail captures the recovery path.
    """
    last_exc: BaseException | None = None
    delay = base_delay
    for attempt in range(1, attempts + 1):
        try:
            return await func()
        except exceptions as exc:
            last_exc = exc
            if attempt == attempts:
                logger.warning(
                    "retry_async: %s failed after %d attempts (%s)",
                    label, attempt, exc,
                )
                raise
            logger.warning(
                "retry_async: %s attempt %d/%d failed (%s) — retrying in %.1fs",
                label, attempt, attempts, exc, delay,
            )
            await asyncio.sleep(delay)
            delay *= factor
    assert last_exc is not None  # unreachable
    raise last_exc
