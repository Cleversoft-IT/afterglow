---
name: feedback-tts-stereo-channel-diarization
description: Custom-template demo audio is rendered STEREO (operator left, caller right) and the ASR is told to use channel diarization. Speaker diarization collapsed the mono-concat TTS to a single speaker, breaking multi-turn transcript rendering. Stereo + channel is propagated end-to-end via `Call.audio_diarization`.
metadata:
  type: feedback
---

Pipeline:

1. `backend/app/integrations/speechmatics_tts.py` — `render_script_to_mp3`
   writes a **stereo** WAV using `_interleave_mono_to_stereo` per turn
   (operator/agent/host → L, caller/customer/guest/patient → R, fallback
   alternates by turn index). `_silence_stereo` between turns. LAME uses
   `-m s` (NOT `-m m`) and `-b 64`.
2. `backend/app/api/templates.py::generate-audio` sets
   `scenario['audio_diarization'] = 'channel'` (and the legacy flat shape sets
   `config['audio_diarization'] = 'channel'`) whenever the TTS path runs.
3. Frontend `app/lib/api.ts::submitAudio` accepts a `callerMode` parameter and
   sends `caller_mode` as a form field; `app/app/incoming-call.tsx` passes the
   active mode through.
4. Backend `backend/app/api/calls.py::submit_audio_call` reads
   `template.simulation_config.scenarios[caller_mode].audio_diarization` (or
   the flat fallback) and persists it on `Call.audio_diarization`.
5. `backend/app/agents/orchestrator.py` passes
   `diarization=call.audio_diarization or 'speaker'` to
   `speechmatics.transcribe_audio`.
6. `backend/app/integrations/speechmatics.py::transcribe_audio` — when
   `diarization='channel'` it builds the SDK `TranscriptionConfig` with
   `channel_diarization_labels=['S1','S2']` instead of `diarization='speaker'`
   (the SDK only accepts `'none'/'speaker'` for that field). `_diarized_text`
   reads the `channel` attribute (on the result, with fallback to the
   alternative) when `speaker` is missing.

Migration: `0019_call_audio_diarization.py` adds the nullable `String(16)`
column.

**Why:** Custom templates produced a 1-turn transcript on the post-pitch
repro. Speechmatics' speaker diarization sees a single voice on the mono TTS
concat and collapses both speakers; channel diarization on stereo input
recovers the operator/caller separation reliably.

**How to apply:**

- The `caller_mode` form field is optional on `POST /api/v1/calls` (back-compat
  with older clients) but the frontend now always sends it.
- Seed audio + user-uploaded audio keep `audio_diarization=None` → defaults to
  `speaker` in the ASR path. Only TTS-generated stereo carries `'channel'`.
- If you regress LAME to `-m m`, the downmix erases the channel split and
  channel diarization silently degrades. `test_speechmatics_tts.py` guards the
  LAME command construction against the regression.
