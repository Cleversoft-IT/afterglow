# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
# sample_audio/ ships the three demo MP3s for the seed templates so the
# Simulator UI can stream them straight back through
# /api/v1/templates/{id}/simulation/audio without depending on /var/data
# being pre-populated.
COPY sample_audio/ ./sample_audio/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /var/data/audio

EXPOSE 8000

CMD ["/entrypoint.sh"]
