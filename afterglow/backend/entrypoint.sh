#!/bin/sh
# Container entrypoint: idempotent schema migration + seed before serving.
#
# alembic upgrade head is always safe (no-op on an already-current DB), and
# the seed script short-circuits when templates already exist, so reruns
# don't duplicate data.
#
# Failure policy:
# - Alembic failure is FATAL: the ORM models reflect a schema we promise the
#   DB matches; running uvicorn on a stale DB silently corrupts behaviour.
# - Seed failure is logged + tolerated: the schema is correct, only demo
#   content is missing — the deployment is degraded but inspectable.
set -e

echo "[entrypoint] $(date -Iseconds) alembic upgrade head"
if ! alembic upgrade head; then
    echo "[entrypoint] FATAL: alembic upgrade failed — refusing to serve a stale schema" >&2
    exit 1
fi

echo "[entrypoint] $(date -Iseconds) python -m app.db.seed"
if ! python -m app.db.seed; then
    echo "[entrypoint] WARNING: seed failed — continuing without demo data" >&2
fi

echo "[entrypoint] $(date -Iseconds) starting uvicorn on 0.0.0.0:8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
