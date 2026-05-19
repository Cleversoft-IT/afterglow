"""Speechmatics batch transcription client.

Always calls the real `speechmatics-batch` SDK — there is no offline fallback.
Missing API key or unreadable audio raise; callers must treat Speechmatics as
a mandatory dependency of the pipeline.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger("afterglow")


@dataclass
class TranscriptResult:
    text: str
    language: str
    speakers: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


async def transcribe_audio(
    audio_path: Path,
    *,
    diarization: str = "speaker",
    language: str = "auto",
    timeout_sec: float = 120.0,
    domain_hint: str = "restaurant",
) -> TranscriptResult:
    """Transcribe an audio file via Speechmatics batch.

    `diarization` accepts:
      - `"speaker"` (default): standard speaker diarization on mono input.
      - `"channel"`: the audio is stereo with one speaker per channel; we
        pass `diarization="channel"` and `channel_diarization_labels=["S1","S2"]`
        so Speechmatics tags results by channel and `_diarized_text` can
        render them with the same `S1:` / `S2:` prefixes the rest of the
        pipeline expects. The SDK dataclass docstring only lists `"none"` /
        `"speaker"`, but the Batch API schema requires `diarization="channel"`
        whenever `channel_diarization_labels` is present — omitting it makes
        the server reject the job with HTTP 400 (anyOf/not/allOf validation).
    """
    settings = get_settings()

    if not settings.speechmatics_api_key:
        raise RuntimeError("SPEECHMATICS_API_KEY is not configured")
    if not audio_path or not audio_path.exists():
        raise FileNotFoundError(f"audio file not found: {audio_path}")
    if audio_path.stat().st_size == 0:
        raise RuntimeError(f"audio file is empty: {audio_path}")

    # Lazy imports so the app stays importable even if the SDK is unavailable
    # (e.g. during local linting on a fresh checkout without `pip install`).
    from speechmatics.batch import AsyncClient, TranscriptionConfig

    if diarization == "channel":
        # Custom TTS produces stereo: speaker A on the left channel,
        # speaker B on the right. Channel diarization is more reliable
        # than speaker diarization on short synthetic mono runs.
        transcription_config = TranscriptionConfig(
            language=language,
            diarization="channel",
            channel_diarization_labels=["S1", "S2"],
        )
    else:
        transcription_config = TranscriptionConfig(
            language=language,
            diarization=diarization,
        )

    client = AsyncClient(
        api_key=settings.speechmatics_api_key,
        url=settings.speechmatics_batch_url,
    )
    try:
        transcript = await client.transcribe(
            audio_file=str(audio_path),
            transcription_config=transcription_config,
            timeout=timeout_sec,
        )
    finally:
        await client.close()

    return _to_transcript_result(transcript, requested_language=language)


def _to_transcript_result(transcript: Any, *, requested_language: str) -> TranscriptResult:
    """Convert speechmatics.batch.Transcript into our internal TranscriptResult."""
    results = getattr(transcript, "results", None) or []
    speakers_raw = getattr(transcript, "speakers", None) or []
    metadata = getattr(transcript, "metadata", None)

    text = _diarized_text(results)
    detected_language = _detect_language(metadata, results, fallback=requested_language)
    speakers = _normalize_speakers(speakers_raw, results)

    # Keep a compact subset of the raw payload — full transcripts can be huge.
    raw_payload: dict[str, Any] = {
        "source": "speechmatics-batch",
        "language_identification": (
            getattr(metadata, "language_identification", None) if metadata else None
        ),
        "result_count": len(results),
    }
    return TranscriptResult(
        text=text,
        language=detected_language,
        speakers=speakers,
        raw=raw_payload,
    )


def _diarized_text(results: list[Any]) -> str:
    """Render `[{speaker, content}, ...]` as

        S1: hi there
        S2: hello, how can I help?
        S1: I'd like to book a table

    one turn per line. The newline matters: the frontend transcript
    component (`app/components/TranscriptList.tsx`) splits on `\\n` and
    matches a `Speaker:` prefix at the start of each line. Inline
    concatenation collapsed every turn into a single block.

    Punctuation is appended to the current segment without a leading
    space. Falls back to the per-result `channel` attribute when
    `speaker` is not populated (Speechmatics emits `channel` instead of
    `speaker` when channel diarization is in use).
    """
    pieces: list[str] = []
    current_speaker: Optional[str] = None
    for r in results:
        alternatives = getattr(r, "alternatives", None) or []
        if not alternatives:
            continue
        alt = alternatives[0]
        content = getattr(alt, "content", None)
        if not content:
            continue
        # In channel-diarization mode the `channel` lives on the result
        # itself (`r.channel`), not on the alternative. Try both so the
        # rest of the pipeline keeps seeing the same `S1:` / `S2:` shape.
        speaker = (
            getattr(alt, "speaker", None)
            or getattr(r, "channel", None)
            or getattr(alt, "channel", None)
        )
        rtype = getattr(r, "type", "word")

        if speaker and speaker != current_speaker:
            current_speaker = speaker
            # Newline before every speaker change so the frontend can
            # split turns line-by-line. No leading newline for the very
            # first speaker (would render as a blank turn).
            pieces.append(f"\n{speaker}: " if pieces else f"{speaker}: ")
            pieces.append(content)
        else:
            if rtype == "punctuation":
                pieces.append(content)
            else:
                pieces.append(f" {content}")
    return "".join(pieces).strip()


def _detect_language(metadata: Any, results: list[Any], *, fallback: str) -> str:
    if metadata is not None:
        ident = getattr(metadata, "language_identification", None)
        if isinstance(ident, dict):
            for key in ("language", "predicted_language", "best_language"):
                value = ident.get(key)
                if isinstance(value, str) and value:
                    return value
        config = getattr(metadata, "transcription_config", None)
        if isinstance(config, dict):
            value = config.get("language")
            if isinstance(value, str) and value and value != "auto":
                return value
    for r in results:
        alts = getattr(r, "alternatives", None) or []
        for a in alts:
            lang = getattr(a, "language", None)
            if isinstance(lang, str) and lang:
                return lang
    return fallback if fallback != "auto" else "en"


def _normalize_speakers(speakers_raw: list[Any], results: list[Any]) -> list[dict[str, Any]]:
    if speakers_raw:
        out: list[dict[str, Any]] = []
        for s in speakers_raw:
            label = getattr(s, "label", None) or ""
            out.append({"id": label, "label": label})
        return out
    # Fall back: collect distinct speakers from the results stream.
    seen: list[str] = []
    for r in results:
        alts = getattr(r, "alternatives", None) or []
        for a in alts:
            sp = getattr(a, "speaker", None)
            if sp and sp not in seen:
                seen.append(sp)
    return [{"id": sp, "label": sp} for sp in seen]
