"""Tests for the WAV-concat helpers used inside speechmatics_tts.

We do NOT exercise the live Speechmatics endpoint or the `lame`
transcode step — those are integration concerns. We do verify:
- `_read_wav_frames` returns the raw mono PCM block from the Speechmatics
  TTS preview WAV.
- `_silence_stereo` produces the right number of zero bytes for stereo
  16-bit PCM (4 bytes per frame).
- `_interleave_mono_to_stereo` lands the mono samples on the correct
  channel and leaves the opposite channel silent.
- `script_turns_from_dicts` filters empty turns and defaults voice/speaker.
"""
from __future__ import annotations

import io
import wave

import pytest

from app.integrations.speechmatics_tts import (
    INPUT_CHANNELS,
    OUTPUT_CHANNELS,
    SAMPLE_RATE_HZ,
    SAMPLE_WIDTH,
    TtsError,
    _interleave_mono_to_stereo,
    _read_wav_frames,
    _silence_stereo,
    _transcode_wav_to_mp3,
    script_turns_from_dicts,
)


def _make_wav(frames: bytes, channels: int = INPUT_CHANNELS) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(SAMPLE_RATE_HZ)
        w.writeframes(frames)
    return buf.getvalue()


def test_silence_stereo_size_matches_seconds():
    out = _silence_stereo(0.5)
    # Stereo: 2 channels × 2 bytes/sample × N frames.
    expected = int(0.5 * SAMPLE_RATE_HZ) * SAMPLE_WIDTH * OUTPUT_CHANNELS
    assert len(out) == expected
    assert all(b == 0 for b in out)


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


def test_read_wav_frames_rejects_stereo_input():
    # Speechmatics TTS preview returns mono — anything else is malformed
    # and should be rejected on parse.
    stereo = _make_wav(b"\x01\x00\x00\x00\x02\x00\x00\x00", channels=2)
    with pytest.raises(TtsError):
        _read_wav_frames(stereo)


def test_interleave_mono_to_stereo_left():
    # Two samples on the left channel, silence on the right.
    out = _interleave_mono_to_stereo(b"\x11\x22\x33\x44", "L")
    assert out == b"\x11\x22\x00\x00\x33\x44\x00\x00"


def test_interleave_mono_to_stereo_right():
    out = _interleave_mono_to_stereo(b"\xaa\xbb\xcc\xdd", "R")
    assert out == b"\x00\x00\xaa\xbb\x00\x00\xcc\xdd"


def test_interleave_mono_to_stereo_rejects_unknown_channel():
    with pytest.raises(TtsError):
        _interleave_mono_to_stereo(b"\x00\x00", "X")


def test_transcode_lame_command_uses_stereo_flag():
    # The lame transcode is async, but the command construction is the
    # interesting bit — we don't want a future refactor to slip `-m m`
    # back in, which would downmix our stereo WAV to mono and break
    # channel diarization downstream.
    import inspect

    src = inspect.getsource(_transcode_wav_to_mp3)
    assert '"-m", "s"' in src or "'-m', 's'" in src
    assert '"-m", "m"' not in src and "'-m', 'm'" not in src


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
