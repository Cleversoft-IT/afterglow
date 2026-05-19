"""Tests for the TTS-audio-ready metadata stamp.

The `generate_simulation_audio` endpoint mutates the template's
`simulation_config` JSONB after Speechmatics TTS returns the MP3.
The shape it writes is what the rest of the pipeline keys off of:

  - `audio_url`            — where the MP3 lives on disk
  - `audio_status="ready"` — UI gate for the "Audio ready" chip
  - `audio_generated_at`   — surfaced in Simulator + audit log
  - `audio_source="tts_generated"` — distinguishes from user uploads
  - `audio_diarization="channel"` — routes ASR to channel diarization
                                    in `submit_audio_call`

We extracted the metadata stamp into `mark_tts_audio_ready` so it can be
unit-tested without spinning up FastAPI + DB + Speechmatics TTS.
"""
from __future__ import annotations

from app.api.templates import mark_tts_audio_ready


def test_mark_tts_audio_ready_writes_full_metadata_set():
    """All five keys must land — missing any of them silently breaks a
    downstream consumer (Simulator chip, ASR routing, audit, file fetch)."""
    scenario: dict = {}
    mark_tts_audio_ready(
        scenario,
        audio_url="/tmp/templates/abc_existing.mp3",
        now_iso="2026-05-19T12:00:00+00:00",
    )
    assert scenario == {
        "audio_url": "/tmp/templates/abc_existing.mp3",
        "audio_status": "ready",
        "audio_generated_at": "2026-05-19T12:00:00+00:00",
        "audio_source": "tts_generated",
        "audio_diarization": "channel",
    }


def test_mark_tts_audio_ready_preserves_unrelated_keys():
    """The scenario dict carries other state we must NOT clobber —
    `script_turns`, `caller_phone_e164`, etc."""
    scenario: dict = {
        "script_turns": [{"speaker": "operator", "voice": "sarah", "text": "Hi"}],
        "caller_phone_e164": "+15551112233",
    }
    mark_tts_audio_ready(
        scenario,
        audio_url="/tmp/templates/abc_existing.mp3",
        now_iso="2026-05-19T12:00:00+00:00",
    )
    assert scenario["script_turns"] == [
        {"speaker": "operator", "voice": "sarah", "text": "Hi"}
    ]
    assert scenario["caller_phone_e164"] == "+15551112233"
    assert scenario["audio_diarization"] == "channel"


def test_mark_tts_audio_ready_overwrites_previous_failure_state():
    """A previous TTS attempt may have stamped `audio_status='failed'`
    on the scenario. A successful re-run must clear the failure marker
    by overwriting status + generated_at."""
    scenario: dict = {
        "audio_status": "failed",
        "audio_generated_at": "2026-05-19T11:00:00+00:00",
    }
    mark_tts_audio_ready(
        scenario,
        audio_url="/tmp/templates/abc_existing.mp3",
        now_iso="2026-05-19T12:00:00+00:00",
    )
    assert scenario["audio_status"] == "ready"
    assert scenario["audio_generated_at"] == "2026-05-19T12:00:00+00:00"
    assert scenario["audio_diarization"] == "channel"


def test_mark_tts_audio_ready_works_on_flat_legacy_shape():
    """Templates generated before the scenarios refactor use a flat
    `simulation_config`. The same helper applies — `derive_audio_diarization`
    falls back to the flat shape on the read side."""
    config: dict = {"audio_url": None, "audio_status": "pending"}
    mark_tts_audio_ready(
        config,
        audio_url="/tmp/templates/legacy.mp3",
        now_iso="2026-05-19T12:00:00+00:00",
    )
    assert config["audio_diarization"] == "channel"
    assert config["audio_source"] == "tts_generated"
