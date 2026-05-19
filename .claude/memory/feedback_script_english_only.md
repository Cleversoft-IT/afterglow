---
name: feedback-script-english-only
description: Simulation script builder must produce English-only dialogue; Gemini drifts to the template's language when the business name is non-English and Speechmatics EN voices then render gibberish.
metadata:
  type: feedback
---

The simulation script generator in `backend/app/agents/simulation_script.py` MUST produce English-only dialogue, no matter how the underlying Template is named or worded. The SYSTEM_INSTRUCTION already enforces this, but Gemini ignores it whenever the template name or description is in another language (e.g. an Italian restaurant called "Trattoria Bella Vita" pulls the operator turn into "buongiorno, come posso aiutarla?"). When that happens, the Speechmatics TTS preview voices — which only exist in EN — render the dialogue as garbled English-phoneme audio, the ASR transcribes random nonsense, and the post-call agent has no usable transcript.

**Why**: Speechmatics TTS preview supports only `sarah / theo / megan / jack`, all EN. There is no IT/ES/FR/DE voice in the bundled tier we use. Demo data is also required to be English by [[feedback-code-language]], so the constraint matches the project convention.

**How to apply**: keep both layers of defense in `simulation_script.py`:
1. The hard rule in SYSTEM_INSTRUCTION explicitly listing "buongiorno / hola / bonjour / guten tag" as forbidden, with the "Trattoria Bella Vita" example so Gemini sees the failure mode.
2. `_validate_english_or_raise` post-parse: whole-word match against `_NON_ENGLISH_STOPWORDS`. If a turn opens with a foreign greeting/honorific, raise `ScriptBuilderError` so the API returns 502 and the wizard can retry. Do NOT downgrade this to a warning — the audio path is unrecoverable downstream.

When adding stop-words, only include tokens that have no neutral English meaning. Cognates like "via", "a", "no", "si" must stay out of the list or the validator will reject legitimate English text.

Related: [[feedback-speechmatics-channel-diarization]] (the companion piece on the TTS → ASR path), [[feedback-tts-stereo-channel-diarization]], [[feedback-code-language]].
