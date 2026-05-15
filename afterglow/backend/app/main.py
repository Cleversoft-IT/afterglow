"""Afterglow FastAPI entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import actions, audit, business, calls, customers, templates
from app.config import get_settings

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
    yield
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

_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# Allow extra origins via comma-separated env var (e.g. the Coolify domain).
import os as _os

_extra = _os.environ.get("AFTERGLOW_CORS_EXTRA_ORIGINS", "").strip()
if _extra:
    _cors_origins.extend(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(business.router)
app.include_router(calls.router)
app.include_router(customers.router)
app.include_router(templates.router)
app.include_router(actions.router)
app.include_router(audit.router)
