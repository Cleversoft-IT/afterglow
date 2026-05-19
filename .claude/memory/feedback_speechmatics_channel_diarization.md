---
name: feedback-speechmatics-channel-diarization
description: Speechmatics Batch API requires explicit diarization="channel" when channel_diarization_labels is set; SDK docstring claims only "none"/"speaker" but that's wrong.
metadata:
  type: feedback
---

When building a `speechmatics.batch.TranscriptionConfig` for stereo audio (one speaker per channel), you MUST pass BOTH `diarization="channel"` AND `channel_diarization_labels=[...]`. Setting only `channel_diarization_labels` makes the SDK's `to_dict()` emit a payload with no `diarization` field, and the Batch API rejects it with `HTTP 400: transcription_config: Must validate at least one schema (anyOf)…`.

**Why**: the SDK dataclass docstring in `speechmatics/batch/_models.py` says `diarization` accepts only `"none" / "speaker"` and the dataclass default is `None` — both of which suggest channel mode is "implicit" when the labels are present. It isn't: the server-side schema has `anyOf/not/allOf` constraints that require the explicit `"channel"` value. This trap cost us a regression in commit `14cb2cb` ("fix(post-pitch): … stereo TTS …"): the channel branch of `transcribe_audio` in `backend/app/integrations/speechmatics.py` omitted `diarization="channel"` and every custom-template call failed with `BatchError HTTP 400` until the explicit value was added back.

**How to apply**: any future change to `backend/app/integrations/speechmatics.py` that touches the `TranscriptionConfig` construction for channel mode MUST keep `diarization="channel"` set. Don't trust the SDK docstring — trust the server schema. If you see `BatchError "transcription_config: Must validate at least one schema (anyOf)"` in `AuditLog.payload.exc` for calls with `audio_diarization='channel'`, it's the same trap.

Related: [[feedback-tts-stereo-channel-diarization]] (companion piece on why stereo TTS exists at all).
