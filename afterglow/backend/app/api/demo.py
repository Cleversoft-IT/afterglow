"""Demo sandbox controls.

Endpoints intended for the iframe demo experience. They are only meaningful
when the request carries a real `X-Demo-Session` uuid — production traffic
(no header or bypass-token) is refused with 403.

Today the only operation is `POST /reset`, which wipes every row owned by the
current visitor's sandbox and clears their active template selection. The
`DemoSession` row itself is kept so the client's localStorage uuid stays
valid and no fresh handshake is needed after the reset.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session_context import SessionContext, get_session_context
from app.db.engine import get_session
from app.db.models import DemoSession
from app.tasks.session_cleanup import unlink_audio_files, purge_session_data

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.post("/reset")
async def reset_demo(
    ctx: SessionContext = Depends(get_session_context),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    if not ctx.is_demo:
        raise HTTPException(
            status_code=403, detail="Reset is only available in demo mode"
        )

    audio_paths = await purge_session_data(
        session, ctx.session_id, drop_session_row=False
    )
    await session.execute(
        update(DemoSession)
        .where(DemoSession.id == ctx.session_id)
        .values(
            active_template_id=None,
            last_seen_at=datetime.now(tz=timezone.utc),
        )
    )
    await session.commit()
    unlink_audio_files(audio_paths)
    return {"ok": True, "session_id": str(ctx.session_id)}
