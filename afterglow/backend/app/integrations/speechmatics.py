"""Speechmatics batch transcription client.

Day 1: returns a deterministic fake transcript so the rest of the pipeline can run
without external credentials. Real wiring happens on day 2.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings

settings = get_settings()


@dataclass
class TranscriptResult:
    text: str
    language: str
    speakers: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


_FAKE_TRANSCRIPTS = {
    "restaurant_default": TranscriptResult(
        text=(
            "S1: Buonasera, vorrei prenotare un tavolo per venerdi sera. "
            "S2: Certo, per quante persone? "
            "S1: Siamo in quattro, verso le otto e mezza. Mi chiamo Marco. "
            "S1: Una persona e intollerante al glutine, riuscite a gestirla? "
            "S2: Assolutamente. "
            "S1: Mi potete confermare su WhatsApp?"
        ),
        language="it",
        speakers=[
            {"id": "S1", "label": "caller"},
            {"id": "S2", "label": "operator"},
        ],
        raw={"source": "fake"},
    ),
}


async def transcribe_audio(
    audio_path: Path,
    *,
    custom_dictionary: Optional[list[str]] = None,
    diarization: str = "speaker",
    language: str = "auto",
) -> TranscriptResult:
    """Transcribe an audio file via Speechmatics batch.

    In demo mode (or until day 2 wiring), returns a cached transcript so the rest
    of the pipeline can be exercised end-to-end without external calls.
    """
    if settings.demo_mode or not settings.speechmatics_api_key:
        await asyncio.sleep(0.2)  # simulate latency
        return _FAKE_TRANSCRIPTS["restaurant_default"]

    # TODO day 2: real speechmatics-batch SDK integration
    # from speechmatics.batch_client import BatchClient
    # ...
    raise NotImplementedError("Real Speechmatics wiring lands on day 2")
