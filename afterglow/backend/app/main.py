"""Afterglow FastAPI entrypoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    actions,
    audit,
    bookings,
    calls,
    customers,
    demo,
    integrations,
    templates,
)
from app.api.session_context import DEMO_SESSION_HEADER
from app.config import get_settings
from app.db.engine import SessionLocal
from app.tasks.orphan_recovery import recover_orphans
from app.tasks.seed_date_refresh import refresh_seed_dates_if_needed
from app.tasks.session_cleanup import run_cleanup_loop
from app.tasks.vector_preseed import preseed_demo_collection

load_dotenv()

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("afterglow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Afterglow API starting up (env=%s)", settings.app_env)
    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY not set — Gemini agents will fail fast.")
    if not settings.vultr_inference_api_key:
        logger.warning("VULTR_INFERENCE_API_KEY not set — Vultr memory lookup is disabled.")
    if not settings.speechmatics_api_key:
        logger.warning("SPEECHMATICS_API_KEY not set — transcription/TTS will fail fast.")

    try:
        recovered = await recover_orphans()
        if recovered:
            logger.info("orphan_recovery: marked %d stuck calls as failed", recovered)
    except Exception as exc:  # noqa: BLE001
        logger.warning("orphan_recovery failed at startup: %s", exc)

    today = datetime.now(timezone.utc).date()
    async with SessionLocal() as session:
        refresh_ok = False
        try:
            shifted = await refresh_seed_dates_if_needed(session, today)
            await session.commit()
            refresh_ok = True
            if shifted:
                logger.info("seed_date_refresh: shifted %d row(s)", shifted)
        except Exception as exc:  # noqa: BLE001
            # Refresh failure is a serious bug (broken SQL / missing settings
            # table) — log ERROR and skip preseed so we don't push stale-dated
            # chunks into the Vector Store.
            logger.error(
                "seed_date_refresh failed: %s — skipping vector preseed", exc
            )
            await session.rollback()

        if refresh_ok:
            try:
                await preseed_demo_collection(session)
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                # Vultr being down is tolerated: the runtime RAG path
                # degrades gracefully. Backend must start regardless.
                logger.warning(
                    "vector_preseed failed: %s — startup continues", exc
                )
                await session.rollback()

    cleanup_task = asyncio.create_task(run_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("Afterglow API shutting down")


app = FastAPI(
    title="Afterglow API",
    description=(
        "Multi-agent backend for Afterglow — turns booking phone calls into "
        "structured data, customer memory and autonomously executed actions."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Lets the iframe app read the freshly-minted demo session id and persist
    # it to localStorage on the first round-trip.
    expose_headers=[DEMO_SESSION_HEADER],
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(calls.router)
app.include_router(customers.router)
app.include_router(templates.router)
app.include_router(actions.router)
app.include_router(bookings.router)
app.include_router(audit.router)
app.include_router(demo.router)
app.include_router(integrations.router)
