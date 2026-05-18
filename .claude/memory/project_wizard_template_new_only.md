---
name: project-wizard-template-new-only
description: SUPERSEDED 2026-05-18 — wizard-built templates now emit BOTH scenarios; preserved for historical context.
metadata:
  type: project
---

> ⚠️ **SUPERSEDED 2026-05-18.** Since the round-10 polish wave, wizard-built
> templates emit BOTH `scenarios.existing` AND `scenarios.new`, generated
> in a single LLM pass and rendered to two MP3 files
> (`<template_id>_existing.mp3` + `<template_id>_new.mp3`, concat'd in PCM
> via `wave` stdlib, transcoded to mono 48kbps MP3 via ffmpeg). The
> Simulator now shows BOTH buttons for wizard-built templates, identical
> to the seeded presets. See `CLAUDE.md` (constraint #3 "Custom wizard-built
> templates follow the same two-scenarios shape since 2026-05-18"),
> `afterglow/docs/ARCHITECTURE.md`, and `afterglow/backend/app/integrations/speechmatics_tts.py`.
> The `hasTwoScenarios` guard in `app/simulator.tsx` still exists for
> safety on legacy rows but in practice always evaluates true for
> templates created after 2026-05-18.

---

# Historical record (pre 2026-05-18)

The Simulator on a wizard-built template showed **only** the "Call from
new customer" button. "Call from existing customer" was rendered only
when `simulation_config.scenarios.existing` AND
`simulation_config.scenarios.new` both existed — i.e. the seeded
restaurant / dentist / bodyshop presets.

**Why.** `agents/simulation_script.build_simulation_script()` returned
a single script with one `caller_name` + `caller_phone_e164`, and
`script_response_to_simulation_config()` wrote it in the flat shape
(no `scenarios.*`). The generated phone number was fabricated, so it
didn't match any seeded `Customer` and `getCustomerByPhone` returned
null — the "existing" path would always degrade into "New caller"
anyway, which misled the operator into thinking the existing flow was
broken.

**Resolution shipped on 2026-05-18.** Option (a) from the original
"how to apply" was chosen: the script generator now emits two
scenarios with two distinct caller identities. See
[[feedback-audio-blob-url-for-session-endpoints]] for how the audio
reaches the player.
