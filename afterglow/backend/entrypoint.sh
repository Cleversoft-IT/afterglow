#!/bin/sh
# Container entrypoint: idempotent schema migration + seed before serving.
#
# alembic upgrade head is always safe (no-op on an already-current DB).
# The seed script short-circuits when templates already exist, so reruns
# don't duplicate data.
#
# Either step can fail without taking the container down (we log + continue),
# so a bad seed doesn't block uvicorn from serving traffic for a degraded
# but inspectable deployment.
set -e

echo "[entrypoint] $(date -Iseconds) alembic upgrade head"
if ! alembic upgrade head; then
    echo "[entrypoint] WARNING: alembic upgrade failed — continuing" >&2
fi

echo "[entrypoint] $(date -Iseconds) python -m app.db.seed"
if ! python -m app.db.seed; then
    echo "[entrypoint] WARNING: seed failed — continuing" >&2
fi

echo "[entrypoint] $(date -Iseconds) starting uvicorn on 0.0.0.0:8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
