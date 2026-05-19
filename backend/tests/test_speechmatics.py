"""Tests for the Speechmatics batch wrapper.

Only the pure-function bits are covered here — we never spin the real
SDK in CI. The actual `transcribe_audio` integration is exercised in
production smoke (see Phase A verification in the plan file).
"""
from __future__ import annotations

from types import SimpleNamespace

from app.integrations.speechmatics import _diarized_text


def _word(content, *, speaker=None, channel=None, rtype="word"):
    """Build a fake Speechmatics result row. The SDK's real shape is
    `result.alternatives[0].content` + `.speaker`, with `channel` either
    on the alternative or on the result itself for channel diarization."""
    alt = SimpleNamespace(content=content, speaker=speaker, channel=None)
    return SimpleNamespace(type=rtype, alternatives=[alt], channel=channel)


def test_diarized_text_inserts_newline_before_each_speaker_change():
    """Multi-turn transcripts MUST emit one newline per speaker change so
    `TranscriptList.tsx` can split lines and render each turn separately.
    Before this fix, every turn was glued onto a single line and the
    component collapsed the transcript to '1 turns'."""
    results = [
        _word("Hi", speaker="S1"),
        _word("there", speaker="S1"),
        _word(".", speaker="S1", rtype="punctuation"),
        _word("Hello", speaker="S2"),
        _word("how", speaker="S2"),
        _word("can", speaker="S2"),
        _word("I", speaker="S2"),
        _word("help", speaker="S2"),
        _word("?", speaker="S2", rtype="punctuation"),
        _word("Yes", speaker="S1"),
        _word("please", speaker="S1"),
        _word(".", speaker="S1", rtype="punctuation"),
    ]
    text = _diarized_text(results)
    lines = text.split("\n")
    assert len(lines) == 3, f"expected 3 turns, got: {lines!r}"
    assert lines[0].startswith("S1: ")
    assert lines[1].startswith("S2: ")
    assert lines[2].startswith("S1: ")
    assert "Hi there." in lines[0]
    assert "Hello how can I help?" in lines[1]
    assert "Yes please." in lines[2]


def test_diarized_text_uses_channel_when_speaker_is_missing():
    """Channel diarization populates `result.channel` instead of
    `alternative.speaker`. The renderer must accept both."""
    results = [
        _word("Buongiorno", channel="S1"),
        _word(",", channel="S1", rtype="punctuation"),
        _word("salve", channel="S2"),
        _word(".", channel="S2", rtype="punctuation"),
    ]
    text = _diarized_text(results)
    assert text.startswith("S1: Buongiorno,")
    assert "\nS2: salve." in text


def test_diarized_text_no_blank_first_line():
    """First speaker should NOT be preceded by a leading newline,
    otherwise the frontend renders a phantom empty turn at the top."""
    results = [_word("Hello", speaker="S1"), _word(".", speaker="S1", rtype="punctuation")]
    text = _diarized_text(results)
    assert not text.startswith("\n")
    assert text == "S1: Hello."


def test_diarized_text_drops_empty_content():
    """Results with no `content` (silence / noise / SDK quirk) must be
    skipped — not turn into an empty Sn: prefix."""
    results = [
        _word("Hi", speaker="S1"),
        _word("", speaker="S2"),
        _word("again", speaker="S1"),
    ]
    text = _diarized_text(results)
    assert "S2:" not in text  # the empty S2 result is dropped
    assert text == "S1: Hi again"


def test_diarized_text_handles_single_speaker_run():
    """Pre-channel-diarization the TTS audio collapsed to a single
    speaker. `_diarized_text` should still produce a usable transcript
    (no crash, single Sn: prefix)."""
    results = [
        _word("Solo", speaker="S1"),
        _word("speaker", speaker="S1"),
        _word("here", speaker="S1"),
    ]
    text = _diarized_text(results)
    assert text == "S1: Solo speaker here"
    assert "\n" not in text
