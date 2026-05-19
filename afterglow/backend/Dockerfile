# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

# `lame` is the LAME MP3 encoder CLI — single-purpose tool we use to
# transcode the concatenated PCM WAV from Speechmatics into a small
# MP3 (see `app/integrations/speechmatics_tts.py`). Picked over `ffmpeg`
# specifically because ffmpeg on Debian trixie pulls in ~200 packages
# (libllvm19, X11, GL, video codecs, font/subtitle rendering) for a
# ~600-800 MB install that has nuked the 4 GB Coolify VM with a silent
# OOM during fresh layer cache misses (see
# `.claude/memory/project_coolify_oom_silent_deploys.md`). `lame` deps
# are just `libmp3lame0` + `libsndfile1` ≈ 2 MB. We only need
# mono-WAV-16kHz → mono-MP3-48kbps, which is exactly the LAME use case.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc lame \
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
