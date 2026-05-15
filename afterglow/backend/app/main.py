"""Afterglow FastAPI entrypoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import actions, audit, calls, customers, templates
from app.api.session_context import DEMO_SESSION_HEADER
from app.config import get_settings
from app.tasks.session_cleanup import run_cleanup_loop

load_dotenv()

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("afterglow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Afterglow API starting up (env=%s)", settings.app_env)
    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY not set — Gemini agents will run in stub mode.")
    if not settings.vultr_inference_api_key:
        logger.warning("VULTR_INFERENCE_API_KEY not set — Vultr inference in stub mode.")
    if not settings.speechmatics_api_key:
        logger.warning("SPEECHMATICS_API_KEY not set — Speechmatics in stub mode.")

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
app.include_router(audit.router)
