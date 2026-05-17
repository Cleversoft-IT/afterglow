---
name: project-wizard-template-new-only
description: Wizard-built templates expose only the "Call from new customer" Simulator button; "existing" is hidden until a per-mode scenario flow exists.
metadata:
  type: project
---

The Simulator on a wizard-built template shows **only** the "Call from
new customer" button. "Call from existing customer" is rendered only
when `simulation_config.scenarios.existing` AND
`simulation_config.scenarios.new` both exist — i.e. the seeded
restaurant / dentist / bodyshop presets.

**Why.** `agents/simulation_script.build_simulation_script()` returns
a single script with one `caller_name` + `caller_phone_e164`, and
`script_response_to_simulation_config()` writes it in the flat shape
(no `scenarios.*`). The generated phone number is fabricated, so it
doesn't match any seeded `Customer` and `getCustomerByPhone` returns
null — the "existing" path would always degrade into "New caller"
anyway, which misled the operator into thinking the existing flow was
broken.

**How to apply.** When touching the Simulator card or the simulation
script flow, keep the `hasTwoScenarios` guard in `app/simulator.tsx`.
If you want to restore the existing button for custom templates, the
real fix is either (a) make the script generator emit two scenarios
and a customer seeded into the demo session, or (b) reuse a seeded
customer's phone for the existing scenario — pick one and update both
`script_response_to_simulation_config` and the simulator UI in the
same PR. See also [[feedback-audio-blob-url-for-session-endpoints]]
for how that audio reaches the player.
