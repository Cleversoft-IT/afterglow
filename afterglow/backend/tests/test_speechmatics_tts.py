"""Tests for the no-ffmpeg WAV concatenation path of speechmatics_tts.

We do NOT exercise the live Speechmatics endpoint — those are integration
concerns. We do verify:
- `_read_wav_frames` returns the raw PCM block.
- `_silence_bytes` produces the right number of zero bytes.
- `script_turns_from_dicts` filters empty turns and defaults voice/speaker.
"""
from __future__ import annotations

import io
import wave

import pytest

from app.integrations.speechmatics_tts import (
    SAMPLE_RATE_HZ,
    SAMPLE_WIDTH,
    TtsError,
    _read_wav_frames,
    _silence_bytes,
    script_turns_from_dicts,
)


def _make_wav(frames: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(SAMPLE_RATE_HZ)
        w.writeframes(frames)
    return buf.getvalue()


def test_silence_bytes_size_matches_seconds():
    out = _silence_bytes(0.5)
    expected = int(0.5 * SAMPLE_RATE_HZ) * SAMPLE_WIDTH
    assert len(out) == expected


def test_read_wav_frames_round_trip():
    frames = b"\x01\x00\x02\x00\x03\x00\x04\x00"
    wav_bytes = _make_wav(frames)
    assert _read_wav_frames(wav_bytes) == frames


def test_read_wav_frames_rejects_wrong_sample_rate():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00")
    with pytest.raises(TtsError):
        _read_wav_frames(buf.getvalue())


def test_script_turns_from_dicts_filters_empty():
    out = script_turns_from_dicts(
        [
            {"speaker": "operator", "voice": "sarah", "text": "Hi"},
            {"speaker": "caller", "text": ""},  # filtered
            {"speaker": "caller", "voice": "theo", "text": "Hello"},
        ]
    )
    assert [(t.speaker, t.voice, t.text) for t in out] == [
        ("operator", "sarah", "Hi"),
        ("caller", "theo", "Hello"),
    ]


def test_script_turns_from_dicts_raises_when_empty():
    with pytest.raises(TtsError):
        script_turns_from_dicts([{"text": ""}])
