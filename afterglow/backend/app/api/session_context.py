"""Demo iframe sandbox: per-visitor SessionContext dependency.

Pattern:
    @router.get("/...")
    async def handler(
        ctx: SessionContext = Depends(get_session_context),
        db: AsyncSession = Depends(get_session),
    ): ...

The dependency reads `X-Demo-Session` from the incoming request and resolves it:

    header absent / empty     → SessionContext(None, is_demo=False)   (production)
    header == "bypass" + valid DEMO_BYPASS_TOKEN match
                              → SessionContext(None, is_demo=False)   (pitch live)
    header == "new"           → mint a fresh DemoSession, write the new uuid to
                                response headers, return SessionContext(uuid, True)
    header == "<valid uuid>"
        existing row          → bump last_seen_at, return SessionContext(uuid, True)
        unknown / malformed   → mint a fresh DemoSession (defensive: a stale
                                localStorage from an evicted session does not 403)

The response header `X-Demo-Session` is echoed back ONLY when the value changed
(new mint), saving wire bytes on the common case. The frontend reads it and
persists to localStorage.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Request, Response
from sqlalchemy import or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.config import get_settings
from app.db.engine import get_session
from app.db.models import DemoSession

settings = get_settings()

DEMO_SESSION_HEADER = "X-Demo-Session"


@dataclass(slots=True)
class SessionContext:
    session_id: Optional[uuid.UUID]

    @property
    def is_demo(self) -> bool:
        return self.session_id is not None


def _parse_uuid(raw: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        return None


async def _mint_session(db: AsyncSession) -> uuid.UUID:
    new_id = uuid.uuid4()
    db.add(DemoSession(id=new_id))
    await db.commit()
    return new_id


async def _touch_session(db: AsyncSession, session_id: uuid.UUID) -> bool:
    """Bump last_seen_at; return True if the session exists."""
    result = await db.execute(
        update(DemoSession)
        .where(DemoSession.id == session_id)
        .values(last_seen_at=datetime.now(tz=timezone.utc))
    )
    if result.rowcount:
        await db.commit()
        return True
    return False


async def get_session_context(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> SessionContext:
    raw = request.headers.get(DEMO_SESSION_HEADER, "").strip()

    if not raw:
        return SessionContext(session_id=None)

    if raw == "bypass":
        token = settings.demo_bypass_token
        if token and request.headers.get("X-Demo-Bypass-Token", "") == token:
            return SessionContext(session_id=None)
        # Token missing or wrong: degrade to a normal demo session.
        raw = "new"

    if raw != "new":
        parsed = _parse_uuid(raw)
        if parsed is not None and await _touch_session(db, parsed):
            return SessionContext(session_id=parsed)

    minted = await _mint_session(db)
    response.headers[DEMO_SESSION_HEADER] = str(minted)
    return SessionContext(session_id=minted)


def visibility_filter(
    session_column: ColumnElement, ctx: SessionContext
) -> ColumnElement:
    """SQL filter for activity-log tables (`calls`, `audit_log`, etc).

    These tables have no notion of "seed" — they are pure activity. Each
    caller sees strictly its own rows:
      - Production (no session) sees only `session_id IS NULL` rows.
      - Demo sees only its own `session_id = me` rows.

    This guarantees that the production tenant's call log can never leak
    into a public demo visitor's UI and vice versa.
    """
    if ctx.is_demo:
        return session_column == ctx.session_id
    return session_column.is_(None)


def visibility_filter_seedable(
    session_column: ColumnElement,
    is_seed_column: ColumnElement,
    ctx: SessionContext,
) -> ColumnElement:
    """SQL filter for `templates` and `customers`, which DO have seed rows.

    - Production tenant sees its own rows (`session_id IS NULL`). Seed
      rows have `session_id IS NULL AND is_seed = TRUE`, so the same
      filter naturally includes them.
    - Demo session sees its own rows (`session_id = me`) plus seed rows
      (`is_seed = TRUE`). Production-only writes (`session_id IS NULL,
      is_seed = FALSE`) are excluded so the demo sandbox never sees real
      tenant data.
    """
    if ctx.is_demo:
        return or_(session_column == ctx.session_id, is_seed_column.is_(True))
    return session_column.is_(None)
