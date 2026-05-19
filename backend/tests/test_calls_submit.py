"""Tests for the audio-diarization derivation that `submit_audio_call`
runs at the point of persisting a Call row.

Pure-function tests against `derive_audio_diarization` — we avoid
spinning up FastAPI + a DB session because the routing logic is
self-contained and the rest of the upload path is exercised by
`test_pipeline_smoke` / `test_pipeline_no_raise`.
"""
from __future__ import annotations

from app.api.calls import derive_audio_diarization


def test_returns_none_when_no_caller_mode():
    """Back-compat: a legacy client that doesn't send `caller_mode`
    must leave `Call.audio_diarization` unset so the orchestrator falls
    back to the default `'speaker'`."""
    cfg = {"scenarios": {"existing": {"audio_diarization": "channel"}}}
    assert derive_audio_diarization(cfg, None) is None


def test_returns_none_when_simulation_config_missing():
    """A template without simulation_config (e.g. seed before the
    round-10 refactor) must not crash — just defer to default."""
    assert derive_audio_diarization(None, "existing") is None
    assert derive_audio_diarization({}, "existing") is None


def test_channel_diarization_picked_up_from_scenario():
    """TTS-stereo templates flag the scenario with `audio_diarization='channel'`
    when `POST /simulation/generate-audio` saves the recording. The
    submit path must surface that to the Call row."""
    cfg = {
        "scenarios": {
            "existing": {"audio_diarization": "channel"},
            "new": {"audio_diarization": "channel"},
        }
    }
    assert derive_audio_diarization(cfg, "existing") == "channel"
    assert derive_audio_diarization(cfg, "new") == "channel"


def test_missing_scenario_falls_back_to_none():
    """Asking for a scenario the template never declared (e.g. wizard
    template only has 'new') must NOT inherit from the other scenario."""
    cfg = {"scenarios": {"new": {"audio_diarization": "channel"}}}
    assert derive_audio_diarization(cfg, "existing") is None


def test_legacy_flat_shape_back_compat():
    """Templates generated before the scenarios refactor stored the
    diarization on the root of `simulation_config`. We accept that
    shape so old wizard-built rows keep working post-redeploy."""
    cfg = {"audio_diarization": "channel"}
    assert derive_audio_diarization(cfg, "existing") == "channel"
    assert derive_audio_diarization(cfg, "new") == "channel"


def test_unknown_value_is_rejected():
    """Defense in depth: a stray value in the JSONB (typo, corruption,
    fuzz) must not bleed into the Call row — we restrict to the two
    enum-shaped strings the orchestrator + Speechmatics wrapper accept."""
    cfg = {"scenarios": {"existing": {"audio_diarization": "garbage"}}}
    assert derive_audio_diarization(cfg, "existing") is None


def test_scenario_overrides_flat_value():
    """When BOTH the new shape and the flat shape are present, the
    scenarios-keyed value wins — that's how the TTS save path actually
    writes it today."""
    cfg = {
        "audio_diarization": "speaker",  # legacy flat
        "scenarios": {"existing": {"audio_diarization": "channel"}},
    }
    assert derive_audio_diarization(cfg, "existing") == "channel"


def test_explicit_speaker_value_passes_through():
    """If a template explicitly declares `speaker` (e.g. a future
    user-uploaded mono recording for a TTS template), preserve it."""
    cfg = {"scenarios": {"existing": {"audio_diarization": "speaker"}}}
    assert derive_audio_diarization(cfg, "existing") == "speaker"
