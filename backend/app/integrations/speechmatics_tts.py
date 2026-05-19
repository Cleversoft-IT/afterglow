"""Speechmatics TTS — preview endpoint, used to render demo MP3s on the fly.

Used by the Simulator screen when a custom template has no bundled audio.
The script is rendered turn-by-turn against the `preview.tts.speechmatics.com`
endpoint (16kHz mono PCM WAV), concatenated with a short silence using
Python's `wave` stdlib, then transcoded to MP3 (mono, 48 kbps) via the
`lame` CLI so the volume stays sane when many demo visitors generate
audio in parallel. We use `lame` instead of `ffmpeg` because ffmpeg's
Debian trixie install OOM-kills the 4 GB Coolify build VM on cache miss
(see `.claude/memory/project_coolify_oom_silent_deploys.md`); lame is
the single-purpose tool that does exactly WAV → MP3 mono encoding.

Voice picks: `sarah` and `theo` for restaurant-style EN US/UK conversations.
The Wizard / API caller can override per-turn.

Fail-fast: missing `SPEECHMATICS_API_KEY`, an HTTP error from the TTS
service, a WAV with a non-16kHz mono header, or a failed `lame` transcode
→ raises `TtsError`. The caller persists the failure on
`simulation_config.audio_status="failed"`.
"""
from __future__ import annotations

import asyncio
import io
import logging
import tempfile
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
# Speechmatics TTS preview always returns mono — keep INPUT_CHANNELS as the
# parsing-side invariant. We OUTPUT stereo so Speechmatics ASR can use
# channel diarization (operator on the left, caller on the right) to
# separate the two voices reliably — speaker diarization on synthetic mono
# concat audio collapses every turn to a single speaker and breaks the
# transcript multi-turn render for custom templates. See
# `app/integrations/speechmatics.py::transcribe_audio` (diarization='channel').
INPUT_CHANNELS = 1
OUTPUT_CHANNELS = 2
SAMPLE_WIDTH = 2  # 16-bit


@dataclass(frozen=True)
class ScriptTurn:
    speaker: str  # logical label ("operator" / "caller") — UI only
    voice: str    # Speechmatics voice id: sarah | theo | megan | jack
    text: str


class TtsError(RuntimeError):
    """Raised when TTS rendering or concatenation fails."""


def _silence_stereo(seconds: float) -> bytes:
    """Return `seconds` of stereo 16-bit zero PCM (4 bytes per frame)."""
    frames = int(seconds * SAMPLE_RATE_HZ)
    return b"\x00\x00\x00\x00" * frames


def _interleave_mono_to_stereo(mono_pcm: bytes, channel: str) -> bytes:
    """Place the mono PCM samples on the requested side, silence on the other.

    `channel` is `"L"` or `"R"`. The output is stereo 16-bit PCM (each
    frame = 4 bytes: left LSB, left MSB, right LSB, right MSB).
    """
    if channel not in ("L", "R"):
        raise TtsError(f"channel must be 'L' or 'R', got {channel!r}")
    if len(mono_pcm) % SAMPLE_WIDTH != 0:
        raise TtsError(
            f"mono PCM length {len(mono_pcm)} not aligned to {SAMPLE_WIDTH}-byte samples"
        )
    zero = b"\x00\x00"
    out = bytearray(len(mono_pcm) * 2)
    for i in range(0, len(mono_pcm), SAMPLE_WIDTH):
        sample = mono_pcm[i:i + SAMPLE_WIDTH]
        j = i * 2
        if channel == "L":
            out[j:j + SAMPLE_WIDTH] = sample
            out[j + SAMPLE_WIDTH:j + 2 * SAMPLE_WIDTH] = zero
        else:
            out[j:j + SAMPLE_WIDTH] = zero
            out[j + SAMPLE_WIDTH:j + 2 * SAMPLE_WIDTH] = sample
    return bytes(out)


def _read_wav_frames(raw: bytes) -> bytes:
    """Pull the mono PCM frames out of a WAV file from the TTS preview."""
    with wave.open(io.BytesIO(raw), "rb") as w:
        if w.getnchannels() != INPUT_CHANNELS:
            raise TtsError(
                f"WAV expected {INPUT_CHANNELS} channel(s), got {w.getnchannels()}"
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
    """Write a stereo 16-bit WAV with `OUTPUT_CHANNELS` channels."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(OUTPUT_CHANNELS)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(SAMPLE_RATE_HZ)
        w.writeframes(pcm_frames)


async def _transcode_wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    """Invoke `lame` to encode the (stereo) WAV into a small MP3.

    Flags: `-m s` forces **true stereo** (we feed stereo with operator on
    the left and caller on the right so Speechmatics ASR can pick them
    apart via channel diarization). `-b 64` CBR (speech is intelligible
    well below 64 kbps mono, but doubling to stereo we keep the channels
    clean at 64). `-q 7` picks the faster LAME preset (0=best/slow,
    9=worst/fastest — 7 is a good speed/quality knee for spoken demo
    audio). `--quiet` suppresses progress on stderr.
    """
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "lame",
        "-m", "s",
        "-b", "64",
        "-q", "7",
        "--quiet",
        str(wav_path),
        str(mp3_path),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
    except FileNotFoundError as exc:
        raise TtsError("lame is not installed on the backend image") from exc
    if proc.returncode != 0:
        snippet = (stderr or b"").decode("utf-8", "replace")[:200].replace("\n", " ")
        raise TtsError(f"lame transcode failed (rc={proc.returncode}): {snippet}")


async def render_script_to_mp3(
    script_turns: list[ScriptTurn], out_path: Path
) -> Path:
    """Render every turn via Speechmatics TTS preview, concat as STEREO PCM
    (operator left, caller right), then transcode to MP3 at `out_path`.

    The stereo split is what makes channel diarization work downstream:
    Speechmatics ASR receives an audio file where each speaker lives on
    a different channel, and emits results tagged with the channel label
    we pass via `channel_diarization_labels`.

    Returns the path of the written file (same as `out_path`). Raises
    `TtsError` on missing key / API error / malformed audio / encode failure.
    """
    if not script_turns:
        raise TtsError("script_turns is empty")

    settings = get_settings()
    if not settings.speechmatics_api_key:
        raise TtsError("SPEECHMATICS_API_KEY is not set")

    silence_pcm = _silence_stereo(SILENCE_BETWEEN_TURNS_SEC)
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
            mono = _read_wav_frames(resp.content)
            # Operator-flavored speakers ("operator", "agent", "host") get
            # the left channel; everything else (caller / customer / guest)
            # gets the right. Falls back to alternating L/R by index when
            # the speaker label is unrecognised so we never collapse both
            # turns onto the same channel.
            speaker_norm = (turn.speaker or "").strip().lower()
            if speaker_norm in {"operator", "agent", "host", "receptionist", "staff"}:
                channel = "L"
            elif speaker_norm in {"caller", "customer", "guest", "client", "patient"}:
                channel = "R"
            else:
                channel = "L" if idx % 2 == 0 else "R"
            stereo = _interleave_mono_to_stereo(mono, channel)
            chunks.append(stereo)
            if idx < len(script_turns) - 1:
                chunks.append(silence_pcm)

    combined = b"".join(chunks)
    # Write the concatenated PCM to a temp WAV so ffmpeg can read it, then
    # transcode to the caller-requested MP3 path and drop the temp file.
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _write_wav(tmp_path, combined)
        await _transcode_wav_to_mp3(tmp_path, out_path)
    finally:
        tmp_path.unlink(missing_ok=True)
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
        filename = f"{template_id}.mp3"
    else:
        filename = f"{template_id}_{mode}.mp3"
    return base / "templates" / filename
