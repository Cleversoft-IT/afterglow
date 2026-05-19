---
name: feedback-wizard-budget-8
description: Wizard chat budget raised from 5 → 8 with a domain-aware "ASK BEFORE DRAFTING" rule and a fields<4 quality gate, after the 5-budget wizard finalized 95%-ready drafts in 2 turns and skipped the obvious follow-ups.
metadata:
  type: feedback
---

`backend/app/agents/wizard_chat.py`:

- `QUESTION_BUDGET = 8` (was 5).
- The system prompt grew an "ASK BEFORE DRAFTING" section listing domain-aware
  categories the wizard should cover before setting `ready=True` — restaurant
  (takeaway, walk-in, allergies, deposit), salon/barber (duration, walk-in,
  cancellation), dentist/medical (emergency vs routine, insurance, no-show),
  bodyshop (plate, photos, loaner, turnaround), generic fallback.
- The prompt also asks for 2-5 `prompt_hints` derived from the user's answers
  (where to encode the operator playbook). [[project_template_simplified_2026_05_17]]
- Backend-side quality gate: if `parsed.ready` AND fields_count < 4 AND budget
  not yet exhausted → forced back to `ready=False`. We do NOT gate on
  `prompt_hints` count alone — encouraged but not blocking, simple verticals
  may not need them.

**Why:** With budget=5 + no domain-aware rules, the wizard finalized a "Barber
Shop Booking" template in 2 user replies ("I run a barber shop, customers call
to book a haircut or shave" + "WhatsApp + email"), at 95% confidence,
without ever asking about appointment duration, walk-ins, cancellation policy,
or any of the actually-useful domain context. Stefano flagged this during the
post-pitch repro on 2026-05-19.

**How to apply:** When touching `wizard_chat.py`, preserve the budget=8 and the
ASK BEFORE DRAFTING prompt block. The frontend (`app/app/templates/wizard.tsx`)
should also detect user language via `app/lib/detectLanguage.ts` and forward it
to the request — the wizard answers in the language it receives.
