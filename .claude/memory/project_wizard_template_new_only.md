---
name: project-wizard-template-new-only
description: Wizard-built (non-seed) templates show ONLY "Call from new customer" in the Simulator — even though they now ship both `scenarios.{existing,new}` — because the fabricated existing-caller phone never matches a seeded Customer row.
metadata:
  type: project
---

## Current rule (2026-05-19 onward)

The Simulator (`app/app/(drawer)/simulator.tsx`) shows **only** "Call
from new customer" whenever `template.is_seed === false`, regardless of
how many scenarios the wizard wrote to `simulation_config`. The
`hasTwoScenarios` flag gates the existing-caller button:

```typescript
const hasTwoScenarios =
  !!(sim?.scenarios?.existing && sim?.scenarios?.new) && !!template.is_seed;
```

**Why.** `agents/simulation_script.build_simulation_script` now emits
BOTH scenarios with two distinct caller identities (since 2026-05-18),
and the audio pipeline renders one MP3 per scenario via Speechmatics +
`lame`. BUT the existing-caller phone is fabricated by Gemini ("never a
real number" — explicit prompt rule in `simulation_script.py`), and
the seeded `Customer` table only covers restaurant / dentist /
bodyshop. So `getCustomerByPhone(scenario.existing.caller_phone_e164)`
returns null for every wizard-built template, and `<CallerContext>`
falls back to the "New caller" chip on the incoming-call screen — the
operator would see the "existing" button but the call would mislabel
itself, confusing the demo. We keep the demo honest by hiding the
button.

**How to apply.** When touching the Simulator's scenario gating, the
incoming-call resolver, or the wizard's script output:

- Do NOT relax `hasTwoScenarios` to drop `template.is_seed`. The
  fabricated phone problem still applies until the wizard learns to
  seed a matching `Customer`.
- If you DO add Customer-seeding to the wizard, drop the `is_seed`
  guard in the same commit and update this file.
- The historical reason (pre 2026-05-18) was different — "wizard only
  generated one script". Don't conflate the two.

## How to evolve

The future-ideas doc tracks the proper fix: when the wizard generates
`scenarios.existing.caller_phone_e164`, also create a `Customer` row
in the same session with that phone, plus a minimal `memory_summary`
+ a couple of fake prior calls. Then the "existing customer" button
can return, and the incoming-call screen will resolve a real customer
display name instead of a generic chip.

See [[feedback-audio-blob-url-for-session-endpoints]] for how the
audio reaches the player and `docs/future-ideas.md` for the
post-hackathon roadmap.
