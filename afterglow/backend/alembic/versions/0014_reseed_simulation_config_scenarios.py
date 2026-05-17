"""Reseed templates so simulation_config.scenarios.{new,existing} lands.

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-17

Commit 8fd128d rewrote `seed._bundled_simulation_config` to emit a
two-scenario shape — `simulation_config.scenarios.{existing,new}` pointing
to per-mode MP3s (`restaurant_existing.mp3` / `restaurant_new.mp3`, etc.).
But `seed()` short-circuits when templates already exist, so an
installation that was seeded before that commit keeps the legacy flat
shape (`simulation_config.audio_url = "/app/sample_audio/restaurant.mp3"`,
no `scenarios` key) and the per-mode MP3s on disk are never reached.

In production the symptom is `GET /api/v1/templates/{id}/simulation/audio
?mode=new` returning `404 "Audio file is missing on disk"` because the
flat path `restaurant.mp3` no longer exists — only `restaurant_new.mp3` /
`restaurant_existing.mp3` do.

DB content is disposable (see `.claude/memory/feedback_db_disposable.md`),
so we TRUNCATE the same tables as 0011 / 0013 and let entrypoint.sh
re-run seed.py against the current code.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = (
    "audit_log",
    "customer_memory_chunks",
    "executed_actions",
    "extracted_fields",
    "calls",
    "demo_sessions",
    "templates",
    "customers",
)


def upgrade() -> None:
    op.execute(
        "TRUNCATE TABLE "
        + ", ".join(_TABLES)
        + " RESTART IDENTITY CASCADE"
    )


def downgrade() -> None:
    pass
