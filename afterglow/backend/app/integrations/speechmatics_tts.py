"""Speechmatics TTS — preview endpoint, used to render demo MP3s on the fly.

Used by the Simulator screen when a custom template has no bundled audio.
The script is rendered turn-by-turn against the `preview.tts.speechmatics.com`
endpoint (16kHz mono PCM WAV), then concatenated with a short silence using
Python's `wave` stdlib — no ffmpeg dependency on the backend container.

Voice picks: `sarah` and `theo` for restaurant-style EN US/UK conversations.
The Wizard / API caller can override per-turn.

Fail-fast: missing `SPEECHMATICS_API_KEY`, an HTTP error from the TTS
service, or a WAV with a non-16kHz mono header → raises `TtsError`. The
caller persists the failure on `simulation_config.audio_status="failed"`.
"""
from __future__ import annotations

import io
import logging
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger("afterglow")


PREVIEW_BASE = "https://preview.tts.speechmatics.com/generate"
OUTPUT_FORMAT = "wav_16000"
SILENCE_BETWEEN_TURNS_SEC = 0.25
SAMPLE_RATE_HZ = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit


@dataclass(frozen=True)
class ScriptTurn:
    speaker: str  # logical label ("operator" / "caller") — UI only
    voice: str    # Speechmatics voice id: sarah | theo | megan | jack
    text: str


class TtsError(RuntimeError):
    """Raised when TTS rendering or concatenation fails."""


def _silence_bytes(seconds: float) -> bytes:
    frames = int(seconds * SAMPLE_RATE_HZ)
    return b"\x00\x00" * frames  # signed 16-bit zero PCM


def _read_wav_frames(raw: bytes) -> bytes:
    """Pull the PCM frames out of a WAV file, raising if the header is wrong."""
    with wave.open(io.BytesIO(raw), "rb") as w:
        if w.getnchannels() != CHANNELS:
            raise TtsError(
                f"WAV expected {CHANNELS} channel(s), got {w.getnchannels()}"
            )
        if w.getsampwidth() != SAMPLE_WIDTH:
            raise TtsError(
                f"WAV expected {SAMPLE_WIDTH * 8}-bit samples, got "
                f"{w.getsampwidth() * 8}-bit"
            )
        if w.getframerate() != SAMPLE_RATE_HZ:
            raise TtsError(
                f"WAV expected {SAMPLE_RATE_HZ} Hz, got {w.getframerate()} Hz"
            )
        return w.readframes(w.getnframes())


def _write_wav(out_path: Path, pcm_frames: bytes) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(CHANNELS)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(SAMPLE_RATE_HZ)
        w.writeframes(pcm_frames)


async def render_script_to_wav(
    script_turns: list[ScriptTurn], out_path: Path
) -> Path:
    """Render every turn via Speechmatics TTS preview and write a single WAV.

    Returns the path of the written file (same as `out_path`). Raises
    `TtsError` on missing key / API error / malformed audio.
    """
    if not script_turns:
        raise TtsError("script_turns is empty")

    settings = get_settings()
    if not settings.speechmatics_api_key:
        raise TtsError("SPEECHMATICS_API_KEY is not set")

    silence_pcm = _silence_bytes(SILENCE_BETWEEN_TURNS_SEC)
    chunks: list[bytes] = []
    headers = {
        "Authorization": f"Bearer {settings.speechmatics_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(headers=headers, timeout=60.0) as client:
        for idx, turn in enumerate(script_turns):
            url = f"{PREVIEW_BASE}/{turn.voice}"
            try:
                resp = await client.post(
                    url, params={"output_format": OUTPUT_FORMAT}, json={"text": turn.text}
                )
            except httpx.HTTPError as exc:
                raise TtsError(
                    f"network error rendering turn #{idx} (voice={turn.voice}): {exc}"
                ) from exc
            if resp.status_code >= 400:
                snippet = resp.text[:200].replace("\n", " ")
                raise TtsError(
                    f"Speechmatics TTS {resp.status_code} for turn #{idx} "
                    f"(voice={turn.voice}): {snippet}"
                )
            frames = _read_wav_frames(resp.content)
            chunks.append(frames)
            if idx < len(script_turns) - 1:
                chunks.append(silence_pcm)

    combined = b"".join(chunks)
    _write_wav(out_path, combined)
    return out_path


def script_turns_from_dicts(items: list[dict]) -> list[ScriptTurn]:
    """Coerce a list of `{speaker, voice, text}` dicts into ScriptTurn objects.

    Skips entries missing `text`; raises `TtsError` if the resulting list
    is empty.
    """
    out: list[ScriptTurn] = []
    for raw in items or []:
        text = (raw.get("text") or "").strip()
        if not text:
            continue
        out.append(
            ScriptTurn(
                speaker=(raw.get("speaker") or "caller").strip() or "caller",
                voice=(raw.get("voice") or "sarah").strip() or "sarah",
                text=text,
            )
        )
    if not out:
        raise TtsError("no usable script_turns supplied")
    return out


def template_audio_path(
    template_id: str,
    mode: Optional[Literal["existing", "new"]] = None,
    base_dir: Optional[Path] = None,
) -> Path:
    """Compute the on-disk path for a custom template's demo recording.

    `mode=None` returns the legacy single-recording path (preserved for
    back-compat with templates generated before 2026-05-18). `mode="existing"`
    and `mode="new"` return scenario-specific paths that match the
    `simulation_config.scenarios.{existing,new}` shape the wizard now emits.
    """
    base = base_dir or Path(get_settings().audio_storage_dir)
    if mode is None:
        filename = f"{template_id}.wav"
    else:
        filename = f"{template_id}_{mode}.wav"
    return base / "templates" / filename
