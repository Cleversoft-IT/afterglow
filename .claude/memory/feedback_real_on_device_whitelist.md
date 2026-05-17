---
name: feedback-real-on-device-whitelist
description: The "Simulated" badge in Call Detail hides for booking/appointment actions via a UI-only whitelist (`REAL_ON_DEVICE` in `app/app/call/[id].tsx`). The backend integration_kind is still `mock_external` for those keys — do not document the change as "real backend execution".
metadata:
  type: feedback
---

**Why:** the operator's mental model is "the booking happens on this
phone". Showing a "Simulated" badge on `booking.create` /
`appointment.create` / `appointment.create_inspection` made the demo
look weaker than it is — the booking is in fact a real-on-device
artifact, just not against an external CRM. The badge stays useful for
WhatsApp/SMS/email outputs that *are* mocked because we have no
integration.

**How to apply:**
- The whitelist lives client-side in `app/app/call/[id].tsx` as the
  `REAL_ON_DEVICE` `Set<string>`. To add an action, append its key.
- **Do not** change the backend `action_catalog.py` `integration_kind`
  from `mock_external` to `internal_real` for these keys: that would
  re-wire the executor and audit semantics, which currently log
  `result.mock = True` and route through `MOCK_REGISTRY`. The UI
  whitelist is a presentation choice; the runtime stays simulated.
- In commit messages and ARCHITECTURE.md keep the wording explicit:
  "UI-only", "presentation choice", "the backend catalog and audit log
  still classify those actions as mock_external".
