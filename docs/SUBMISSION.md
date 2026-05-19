# Afterglow — Submission Bible

**Status:** authoritative source of truth for the AI Agent Olympics (Milan AI Week 2026) submission.
**Snapshot date:** 2026-05-18 (T-1 to deadline).
**Deadline:** 2026-05-19 17:00 CEST. Submission portal: lablab.ai.

This document is the single place where every fact, copy, and asset spec
needed to ship the submission lives. Anyone preparing the video, the
slides, the lablab form, or briefing the team can quote directly from
this file without cross-checking the codebase. The cross-checks have
already been done — every claim here has a file-path citation pointing
at the live code at the snapshot date.

If you find a fact in this document that contradicts the code, the **code
wins** and this document must be updated in the same commit
(`feedback_docs_freshness` policy).

---

## Table of contents

1. [Identity card](#1-identity-card)
2. [The pitch narrative](#2-the-pitch-narrative)
3. [lablab.ai form — pre-filled fields](#3-lablabai-form--pre-filled-fields)
4. [Video pitch script — 5 minutes scene-by-scene](#4-video-pitch-script--5-minutes-scene-by-scene)
5. [Slide deck outline](#5-slide-deck-outline)
6. [Judge cheat sheet — live demo](#6-judge-cheat-sheet--live-demo)
7. [Architecture summary](#7-architecture-summary)
8. [Partner integration matrix](#8-partner-integration-matrix)
9. [The 10 differentiators](#9-the-10-differentiators)
10. [Judging criteria — coverage matrix](#10-judging-criteria--coverage-matrix)
11. [Real-vs-mocked — the honest table](#11-real-vs-mocked--the-honest-table)
12. [Compliance, IP, legal](#12-compliance-ip-legal)
13. [Pre-flight submission checklist](#13-pre-flight-submission-checklist)
14. [Future work — what we are deliberately NOT shipping](#14-future-work--what-we-are-deliberately-not-shipping)
15. [Source-file reference index](#15-source-file-reference-index)
16. [Live form schema — verified on lablab.ai](#16-live-form-schema--verified-on-lablabai)
17. [Decisions — final values to paste into the form](#17-decisions--final-values-to-paste-into-the-form)

---

## 1. Identity card

| Field | Value |
|---|---|
| **Project name** | Afterglow |
| **Claim (hero copy, 9 words)** | **Stay in the moment. We handle the after.** |
| **Tagline (≤8 words, lablab fallback)** | We handle the after |
| **One-liner (≤25 words)** | A phone app for small businesses. The human stays on the call. An agentic AI loop runs after — extract, execute, remember. |
| **Repo** | `https://github.com/Cleversoft-IT/afterglow` (public, MIT) |
| **Backend** | `https://api.afterglow.cleversoft.it` |
| **Operator app (Expo web)** | `https://app.afterglow.cleversoft.it` |
| **Landing + iframe demo** | `https://afterglow.cleversoft.it` |
| **Tracks (lablab.ai)** | Intelligent Reasoning · Agentic Workflows · Enterprise Utility · Multimodal Intelligence |
| **Partner tracks targeted** | **Vultr** · **Google (Gemini)** · **Speechmatics** |
| **Partner tracks NOT targeted** | Kraken (out-of-domain) · Featherless (we use Gemini, not Featherless catalog) |
| **License** | MIT (`LICENSE`) |
| **Team size** | 4 |

The three live URLs above are the only "production" we have, and the
only one judges will see. There is no separate staging or marketing
environment.

---

## 2. The pitch narrative

### The claim

> **Stay in the moment. We handle the after.**

This is the line on the title card, the close, every t-shirt, every
README hero. The whole product is in service of that sentence.

### The problem (the after)

The call itself is fine. Thirty seconds, two humans, a small order
of business. What breaks small businesses is everything that has to
happen *after* the call ends:

* a booking that has to be entered,
* a WhatsApp or email confirmation that has to be sent,
* an allergy, a license plate, a breed, a diagnosis that has to be
  remembered,
* a next-call briefing that should already exist before the phone
  rings again.

Today that *after* is post-its, short-term memory, and a second tab
open *"just in case"*. Multiply by every restaurant, dental clinic,
body shop, dog groomer, hair salon, garage and tutoring studio on
earth and you have the universal small-business call problem.

The "AI receptionist" wave answers this by replacing the human with a
voice agent. That solves the wrong problem. The reason a customer
dials a small business instead of clicking a form is **the human**.
Replace the human with a bot and you kill the only moat the small
business has.

### The bet

> **We don't replace the call. We replace the after.**

The call is not the problem. The after is — the booking that has to
be entered, the WhatsApp confirmation that has to be sent, the
allergy that has to be remembered, the next-call briefing that has
to exist before the phone rings again. Today the after is post-its
and short-term memory. Tomorrow it is an agentic loop that runs in
the background while the human stays with the dog.

### The solution

Afterglow is a drop-in phone app. The operator picks up live. Behind
the scenes, the moment they hang up:

1. The audio is transcribed and diarized by **Speechmatics** (real
   batch STT, diarization on, language auto-detect).
2. A **Gemini 3.1 Flash Lite** agent — running in **Google ADK** as a
   multi-turn loop with a typed tool surface — reads the diarized
   transcript and decides, turn by turn, which tools to call:
   * Re-read specific transcript segments.
   * Search the transcript by keyword.
   * Query **Vultr's Vector Store** through Vultr Serverless Inference
     RAG for prior-call memory of this caller — but only when the
     model judges that prior context is needed, with a specific
     question (not a default catch-all query).
   * Execute one of the template's action tools (`booking.create`,
     `whatsapp.send_confirmation`, `calendar.send_invite`,
     `payment.request_deposit`, …) with a typed payload that's
     validated against the template's JSON Schema. The result of the
     execution (`executed`, `validation_failed`, `evidence_missing`,
     `failed`, `refused`) flows back into the next turn so the model
     can self-correct — capped at 2 attempts per action.
   * Flag the call for human review.
   * Finalize: emit a structured `FinalizeCallPayload` containing the
     extracted fields, intent, sentiment, language, urgency, and a
     one-or-two-sentence **next-call briefing**.
3. The briefing lands on the customer's record. The next time the
   same phone number calls, the operator's screen shows it at the
   top of the customer card. "Mark Ross — gluten-free, last booked
   table for 4 on the 12th, asked about the tasting menu." Zero typing.
   Zero ChatGPT-in-another-tab. Just a screen that already knows
   what was said the last time, because the AI listened and wrote
   it down.

The result is an AI that disappears into the workflow instead of
fighting it. The operator never opened an app. Never typed a thing.
The UX is identical to the Pixel Phone app — because we built it
that way on purpose. The AI work is auditable turn-by-turn in a side
panel for anyone curious enough to look, and invisible for anyone
who isn't.

**Stay in the moment. We handle the after.**

### Why this is "agentic" and not "an LLM call"

Three things separate Afterglow's post-call pipeline from a single-shot
LLM analysis:

1. **The model chooses tools and corrects itself.** Inside the same
   call, we have seen the agent submit a `booking.create` payload,
   receive `validation_failed: party_size required to be > 0`,
   re-read the transcript at the relevant segment, and re-submit with
   the corrected number. This is verifiable in the audit log of any
   completed call — turn N action_exec returns failed, turn N+1
   re-emits, turn N+2 finalizes.
2. **RAG-on-demand, not RAG-as-prefix.** The model decides whether to
   spend tokens on the Vector Store. A first-time caller? Skip the
   call. A returning regular? Ask "what allergies does this customer
   have on file?" — specific question, specific answer.
3. **Loop exit conditions are explicit.** The agent either finalizes,
   hits the 12-turn budget (→ `needs_review` status, surfaced to the
   operator), or errors (→ `failed`). No silent fallback. ExecutedAction
   rows already flushed during the loop are preserved even when the
   loop stalls or errors, thanks to a per-layer no-raise contract.

### The persona for the demo

The live product demo runs the default "Restaurant — Standard
booking" template (seeded preset, fastest to click through). The
persona is the operator of a small restaurant — but the same loop
runs identically for dentists, body shops, dog groomers, salons.

* Existing-customer scenario: **Mark Ross** calls (he's in the seed,
  gluten-free, repeat customer). The transcript references a previous
  booking; the agent pulls the gluten-free fact from Vultr RAG;
  finalizes with `booking.create` + `whatsapp.send_confirmation`. The
  next-call briefing on Mark's card is updated.
* New-customer scenario: a fresh caller — no memory, no record. The
  agent creates a new `Customer`, extracts the booking, writes the
  first briefing.

Both scenarios run end-to-end on the live demo URL in under 60 seconds
each. The MP3s are real audio generated with Speechmatics TTS Preview,
not synthetic transcripts.

In the live demo we can build a fresh vertical on the spot through
the wizard (e.g. a dog groomer template) to show domain adaptability
— but the pitch does not depend on any single character.

---

## 3. lablab.ai form — pre-filled fields

> Copy each block verbatim into the lablab.ai submission form. Character
> counts already verified.
> **Live form constraints verified 2026-05-19** — see §16 for the full
> page-by-page schema and the option catalogs for Categories /
> Event Tracks / Technologies. The numbers below come from the live
> form (Step 1, character counters at the bottom of each textarea).

### Project title (min 5, max 50 characters)

```
Afterglow — we handle the after
```

(31 chars, within the 50-char limit.)

> **Current draft on lablab:** `Afterglow` (9 chars). Decide if we
> keep the bare wordmark or extend to the tagline — both pass the
> minimum.

### Short description (min 50, max 255 characters)

```
A drop-in phone for small businesses. The human stays on the call — the moat. After they hang up, an agentic AI loop extracts the booking, runs the follow-ups (WhatsApp, CRM), writes the next-call briefing. Stay in the moment. We handle the after.
```

(247 chars.)

### Long description (min 600, max 2000 characters)

> ⚠️ **The draft below is 2542 chars** — over the 2000-char cap by
> ~27%. Must be trimmed before paste-in. The previous "min 100 words"
> note was wrong (the form measures characters, not words, and
> enforces a hard ceiling). Suggested cuts: collapse the market-sizing
> paragraph into one sentence and drop the "Single-tenant" paragraph
> (already covered in slide 4 + the video). Target ~1900 chars to
> leave room for tweaks.

```
A call ends. Something else begins. A booking to enter, a confirmation to send, an allergy to remember, a briefing for the next call. Today, every small business handles that after with post-its, short-term memory, and a second tab "just in case". The current AI answer is to replace the human with a voice agent. That solves the wrong problem. The reason a customer dials a small business instead of clicking a form is the human. Replace the human, kill the moat.

Afterglow takes the opposite bet. The human stays on the call. We replace the after.

Afterglow is a drop-in phone app for small booking-driven businesses — restaurants, dental clinics, body shops, hair salons, dog groomers, garages, tutoring studios. The operator picks up live. The moment they hang up, an agentic loop runs in the background: Speechmatics transcribes the call with diarization on; a Gemini 3.1 Flash Lite agent — hosted in Google ADK — runs up to 12 turns over the transcript, deciding which tools to call. Re-read a segment, query the customer's prior-call memory through Vultr's Vector Store and Serverless Inference RAG, execute one of the template's action tools (booking, WhatsApp, calendar, payment, CRM, review), flag for human review, or finalize. Each action runs inline with typed Pydantic payloads built dynamically from the template's JSON Schema; the result feeds back into the next turn so the model can self-correct, capped at two attempts.

The output is a structured extraction (fields, intent, sentiment, urgency, language) plus a one-sentence next-call briefing written to the Customer record. The next time the same number calls, the operator's screen already knows the context — gluten-free, anniversary, Bichon Frisé, previous diagnosis — without anyone typing.

Single-tenant by design. Deployed on Vultr (Cloud Compute + Managed Postgres + Vector Store + Serverless Inference) through Coolify with auto-deploy on push to main. The full agent reasoning trail is a first-class UI surface, audited turn by turn.

Market: worldwide. The after-the-call gap is the same in Milan, Berlin, Brooklyn, São Paulo and Sydney — phone-led small businesses everywhere. We treat Italy as our rigorously-measured baseline (~478k booking-led businesses, ~185k phone-led subset, ~€50/seat/month, ~€110M/year initial Italian SAM) and expand from there: France, Germany, UK, Spain, the US service economy next. USP vs CallRail / Aircall / Dialpad AI: we don't replace the human. We replace the after.

Stay in the moment. We handle the after.
```

(442 words.)

### Market sizing notes for judges

Use this if the lablab form has an "Additional Information" field or if a
judge asks where the TAM/SAM numbers come from.

**The product is worldwide by design.** The after-the-call gap exists
in every phone-led small business on earth. Hair salons in Milan,
dog groomers in Brooklyn, body shops in São Paulo, dental clinics in
Berlin, tutoring studios in Sydney — same operator workflow, same
gap, same fix. The deck and the long description deliberately list
verticals across categories, not a single country's market.

**Italy is our rigorously-measured baseline**, not our limit. We
picked Italy because we had access to first-party sources and could
build a sector-by-sector number we'd be willing to defend in front of
a judge, rather than gesture at a global TAM with no methodology.

The Italian baseline is derived from the internal deep-research report
`tmp/deep-research-report (2).md`. It uses sources such as
FIPE/InfoCamere, ISTAT, Federalberghi, Cosmetica Italia, FNOMCeO,
Key-Stone, Confartigianato/CNA, AGCOM and UPB.

Key methodological point: we do **not** count every SMB as equally
reachable. The hard activity base is ~478k Italian booking-led
businesses across restaurants (195,471), hair salons (~100k), auto
repair (73k), dental practices (~38.5k, inferred from market value /
average practice revenue), beauty centers (~38.3k), and hotels
(32,943). The more relevant serviceable market is the **phone-led
subset**: businesses still coordinating appointments through personal
phones, WhatsApp, or lightweight manual processes. Using
sector-specific midpoint estimates, that subset is ~185k businesses:
hair salons ~62k, restaurants ~58.6k, auto repair ~30.7k, beauty
centers ~21.8k, dental practices ~10.8k, hotels ~1.6k. At
~€50/seat/month that is an initial Italian SAM of roughly
€110M/year — the **floor**, not the ceiling.

**Expansion order** (sized as we land partners, not modelled top-down):
France, Germany, UK, Spain, the US service economy. Same product,
same single-tenant deployment model per customer, same wizard for
local verticals. The Italian playbook is the template, not the cap.

Commercial ranking from the Italian research: hair salons first,
then auto repair, beauty centers, dentistry, restaurants, hotels.
Restaurants are the largest raw cluster, but the report treats them
as a mixed-fit volume market because walk-ins, fixed lines and
booking platforms are common. Hair and beauty are cleaner "personal
phone + recurring appointment" targets; dentistry has fewer logos
but higher likely ARPU; auto repair has strong phone friction around
slots, emergencies and rescheduling.

### Technology tags (must tag every partner you want to be judged by)

> The lablab catalog is an **AI-tech curated list** (185 entries — see
> §16 for the full inventory). Generic stack labels like Python /
> FastAPI / React Native / TypeScript / PostgreSQL / MIT do **not
> exist** in the catalog and cannot be tagged. Don't try to add them
> as free-text — the picker is `isMultiple + isSearchable` over the
> fixed list.

Tag exactly these (all confirmed present in the live catalog):

* `Vultr` — covers every Vultr surface (no separate Vector Store /
  Serverless Inference entries exist).
* `Speechmatics api` — covers batch STT and TTS Preview. (There is
  also a `Speechmatics flow` entry, but we don't use Flow.)
* `Gemini 3 Flash` — closest match for "Gemini 3.1 Flash Lite". The
  catalog also has `Gemini 3 pro` and `Gemini AI`; pick `Gemini 3
  Flash` as the primary, and we may add `Gemini AI` as a secondary
  to be sure we get bucketed into the Google judging pool.
* `AI Studio` — represents the Google AI Studio + ADK surface. The
  catalog has **no** `Google ADK` entry; `AI Studio` is the closest
  publicly Google-branded option (alternative: `Generative AI
  Studio`).

**Current draft on lablab has only `Vultr` + `Speechmatics api`** —
the Gemini / AI Studio tags are MISSING and must be added before
Submit or we lose Google-prize eligibility (cf. Joan's Q&A: untagged
tech is not judged).

### Tracks

Tag at minimum the partner tracks we are competing for:

* **Intelligent Reasoning**
* **Agentic Workflows**
* **Enterprise Utility**
* **Vultr** (partner track)
* **Google Track** (partner track)
* **Speechmatics** (partner track)

`Multimodal Intelligence` was in our previous wishlist but is **not
yet selected** in the draft — debatable whether to add it (we ingest
audio, but the call itself is the only modality and the agent
operates on transcript text). Decision: **skip for now**, the three
content tracks above already place us in the "Application of
Technology" pool, and adding multimodal-without-vision risks looking
overreaching.

**Current draft on lablab has all 6 of the above already selected.**
✓ No change needed here.

### Cover image spec

* Aspect ratio **16:9** (lablab recommendation).
* Source asset: a screenshot of the call detail with the Agent Reasoning
  Trail expanded on the right, customer card on the left, status chip
  `completed`. Captured on `https://app.afterglow.cleversoft.it`.
* Add the wordmark "**afterglow**" bottom-left and "AI Agent Olympics
  2026 — Milan AI Week" bottom-right in a thin sans-serif.
* Export as PNG, target ≤500 KB.

### Participation type

* The live form exposes only `Online` and `Onsite` radios — there is
  **no `Hybrid` option** (the docs/hackathon-reference page is wrong
  on this; the event itself is HYBRID per `formConfig.eventType`,
  but each team picks one).
* Pick **`Onsite`** — the team is in Milan today (2026-05-19).
* **Current draft on lablab already has `ONSITE` selected.** ✓ No
  change needed.

---

## 4. Video pitch script — 5 minutes scene-by-scene

**Constraints from lablab** (`docs/hackathon-reference/06-what-to-submit.md`):

* MP4, ≤5 min, ≤300 MB. Upload **direct** on lablab (no YouTube, no
  Drive). Problem→solution must land in the first 60 seconds.

**Two-act structure** (deliberate, see "Positioning" note below):

* **Act I — 0:00–0:30 · Typographic cold open.** No actors. No live
  footage. Black screen + sound design + type that lands one beat at
  a time. We're not going to out-shoot the studio that has six weeks
  and a real dog. So we play to our strengths: tight type, a single
  phone ring, silence, the claim.
* **Act II — 0:30–4:30 · Live product demo + proof + market.** The
  Pixel-style phone app, the agent loop, RAG, self-correction, memory
  across calls, the wizard, the honest real-vs-mocked table, the
  market sizing & USP.
* **Coda — 4:30–5:00 · Partners, stack, claim.** Vultr · Gemini ·
  Speechmatics. Close on the claim.

> **Pace** — narration runs at ~150 wpm (~2.5 words / second) with
> half-second beats at scene cuts. Each scene's narration block below
> is sized to fit its slot; don't pad in delivery.

> **Positioning** — the video is an *experience plus proof*, not a
> product walkthrough. Make the judges feel the moment of the dog
> moving. *Then* show the audit log.

### Tone & visual reference

* **Type-driven minimalism, not live-action drama.** Reference: Apple
  product page launch teasers (the static-image+type ones, not the
  hero films), Linear's "We build" page, the opening seconds of an
  A24 trailer where the title card is the entire screen.
* Mood arc still **Calm → Disruption → Calm**, but it's all carried by
  type weight, beat timing, and one phone ring.
* No actors, no animals, no live footage in Act I. Act II is screen
  capture of the real product.
* Type: tight grotesque sans (same family as the deck). Maximum
  contrast: deep black background, near-white type, one beat of
  Afterglow blue on the claim.

### Act I — Typographic spot · 0:00–0:30

Black background throughout. Centred type unless noted. Each beat
fades in and out; no cuts inside a beat.

**0:00–0:04 · Held black**

* Silent for two seconds. Then a single landline phone ring — one
  ring, low volume, distant.

**0:04–0:10 · Beat 1**

* Fade in, white type, weight 700:

  ```
  A call ends.
  ```

* Hold three seconds. Fade out.

**0:10–0:16 · Beat 2**

* Fade in, white type:

  ```
  Something else
  begins.
  ```

* Hold three seconds. Fade out.

**0:16–0:22 · Beat 3 — the proof points**

* Four short lines stack in, one every ~250 ms, in soft grey
  (`#94A3B8`):

  ```
  Booking to enter.
  Confirmation to send.
  Allergy to remember.
  Briefing to write.
  ```

* Hold one second. All four fade together.

**0:22–0:27 · The claim**

* Fade in, full bleed:

  ```
                  afterglow

  Stay in the moment.
  We handle the after.
  ```

* The second line is Afterglow blue (`#7DA9FF`). Hold.

**0:27–0:30 · Hand-off**

* Cross-fade to Act II's first frame (the operator app on the demo
  URL). No transition graphic.

**Audio for Act I.** One distant phone ring at 0:02. Silence under
beats 1 and 2. A subtle low-frequency pad fades in under beat 3 and
crests on the claim. No voice-over in Act I — the type is the
narration.

**Why no live shoot.** Production-budget honesty. A live action
opener that looks worse than what every judge has seen the day
before would actively hurt us. A type-led opener at this length is
the right risk-to-reward for what we can ship.

### Act II — Live product demo · 0:30–4:30

The whole act is screen capture of the real operator app at
`https://app.afterglow.cleversoft.it`. Voice-over starts here.

#### Scene II.A — 0:30–0:55 · The product, in one sentence

**Visual:** open the demo URL. Iframe shows the operator app in a
phone frame. Pan to the Home screen.

**Narration (verbatim):**

> "Afterglow is a phone app. The operator picks up — like always. The
> moment they hang up, the *after* begins. Transcript. Booking.
> Follow-ups. The briefing for the next call. The operator never
> opened the app. Never typed a thing. Stay in the moment. We handle
> the after."

#### Scene II.B — 0:55–1:55 · End-to-end run

**Visual:** **Drawer → Test simulator → Call from existing customer.**
The Pixel-style incoming-call screen takes over. Audio plays (the
real Speechmatics-generated MP3). Hang up. The Home now shows the
call with a progress chip moving `transcribing → analyzing →
completed`. Tap the call. The **Agent Reasoning Trail** is open on
the right.

**Narration:**

> "Mark Ross calls. He's a regular. The audio is real — generated by
> Speechmatics TTS, transcribed by the Speechmatics batch API, with
> diarization on.
>
> Trail on the right. Turn one, read the transcript. Turn two, Vultr's
> Vector Store — and notice the question is *specific*. *Allergies on
> file?* Not a catch-all. Comes back gluten-free. Turn three,
> `booking.create`, payload typed against the template's JSON schema.
> Turn four, WhatsApp confirmation. Turn five, finalize: fields,
> intent, sentiment, urgency, next-call briefing.
>
> Five turns. Two thousand tokens. Six seconds end to end."

#### Scene II.C — 1:55–2:25 · The agentic claim — self-correction

**Visual:** open a different completed call where the trail shows an
action `validation_failed` followed by a re-emit. Hover the failed
attempt; the result panel expands.

**Narration:**

> "Here it's a loop, not a script. The agent submits
> `party_size = 0`. The validator says no — `validation_failed`. Next
> turn: re-read the transcript, find *four people*, resubmit,
> executed. Two attempts per action, hard cap. A mutation that
> already succeeded cannot be replayed."

#### Scene II.D — 2:25–2:55 · Memory across calls

**Visual:** open Mark Ross's customer card. Point at the **briefing**
at the top. Trigger a second simulated call from the same number;
the briefing surfaces on the operator's screen during the incoming
call.

**Narration:**

> "The briefing the agent wrote at the end of the last call. Same
> number rings again — the operator sees it before picking up.
> Gluten-free. Last booking. Anniversary. No typing. No second tab.
> No CRM lookup.
>
> The *after* of one call is the *before* of the next."

#### Scene II.E — 2:55–3:30 · Templates · the wizard · any vertical, live

**Visual:** **Drawer → Templates → Wizard.** Type in 2–3 messages:
e.g. *"I run a small dog grooming studio. Two seats. Same-day
bookings, lots of repeat customers, allergies and breed-specific notes
matter."* (Or pick any other vertical on the day — bike repair, music
school, photography studio. The point is "anything you describe.")
The wizard produces a working template, action types, JSON Schema,
and two fresh demo MP3s generated by Speechmatics TTS. Switch the
active template to the new one. Trigger a fresh simulated call —
the briefing reflects the new domain.

**Narration:**

> "Three presets ship: restaurant, dentist, body shop. For everything
> else, a wizard. Two to five questions, out the other end a working
> template — JSON schema, action tools, two fresh demo MP3s rendered
> through Speechmatics TTS. Pick a vertical, any vertical. Same loop.
> Same audit trail. New domain in thirty seconds."

#### Scene II.F — 3:30–4:00 · Real where it matters

**Visual:** cut to a clean two-column on-screen card — REAL on the
left (green dot), MOCKED on the right (amber dot). As each line is
read, briefly cut to a verification proof: the `rag-probe` JSON
response in a terminal (non-zero `input_tokens`), the audit-log page
with a Speechmatics + Gemini + Vultr row stack, the Customer card
mutating after a `customer.update_profile`. End on the
`integrations/action_catalog.py` file open at the registry entries.

**Narration:**

> "What's real, what's a mock. Real, and billed: Speechmatics on
> every call. The Gemini ADK loop. Vultr RAG and Vector Store —
> audit the input tokens. Postgres. The profile mutation. The demo
> MP3s.
>
> Mocked, by design: the outbound integrations no public demo should
> fire. Booking. WhatsApp. Calendar. Payment. CRM.
>
> Replacing one is a line in the action catalog and an env var. Not
> a migration."

#### Scene II.G — 4:00–4:30 · Market & USP

**Visual:** an on-screen card (same Material aesthetic as the deck's
slide 7). Header: *"Worldwide. Italy is where we measured first."*
Below: the three metric chips for the Italian baseline — **478k**
booking-led / **185k** phone-led SAM / **€50** target ARPU per seat
per month, with the small label *"Italian baseline · floor, not
ceiling."* Then the USP table vs CallRail · Aircall · Dialpad AI,
single column of difference: *"After the call, not on it."*

**Narration:**

> "The after-the-call gap exists in every small business on earth.
> Italy is where we sized it first, sector by sector — four hundred
> seventy-eight thousand booking-led businesses, a phone-led subset of
> one hundred eighty-five thousand, fifty euro a seat a month, a
> hundred and ten million initial SAM. The floor, not the ceiling.
> France, Germany, the UK, the US service economy come next.
>
> Against CallRail, Aircall, Dialpad AI, one word of difference.
> *After*. They're on the call. We are everything that happens
> next."

### Coda — 4:30–5:00 · Partners, stack, close

**Visual:** brief pan across the README architecture diagram and the
partner pills on the demo landing. End on a clean type card.

**Narration:**

> "Vultr — Cloud Compute, Managed Postgres, Vector Store, Serverless
> Inference. One audit trail. Google ADK with Gemini 3.1 Flash Lite.
> Speechmatics for STT and TTS. MIT. One VM. Coolify, auto-deploy on
> push.
>
> Afterglow.
>
> Stay in the moment. We handle the after."

**End screen** (still, 2 seconds): wordmark + claim + demo URL +
GitHub link. Same composition as the title card in Act I.

### Recording tips

* **Act I is a typographic edit, not a shoot.** Compose in After
  Effects / Premiere / DaVinci with the same type family as the deck.
  Black background, full-bleed type, opacity transitions only — no
  motion graphics flourishes. A single phone-ring sample (royalty-free
  or library) + a low pad. Total render: a few minutes once the
  beats are timed.
* **Act II is screen capture** of the real product on the demo URL.
  Record the live iframe at `afterglow.cleversoft.it` with QuickTime / OBS
  (the standalone `scripts/record-demo.cjs` recorder has been removed —
  the demo site now embeds a live iframe instead of a baked GIF, so any
  screen-capture tool replaces the old Playwright pipeline).
* Pre-warm the backend right before recording: hit
  `/api/v1/admin/rag-stats` to confirm preseed chunks, then load Home
  so the cold start doesn't show.
* Resolution priority for Act II: **legibility of the Agent Reasoning
  Trail** text matters more than 4K. Bump font scale in Chrome if
  needed before recording.
* Audio: the silence around the Act I beats is doing the work.
  Don't underscore them. The pad only comes in on the proof points
  and crests on the claim.

---

## 5. Slide deck outline

**Constraint:** PDF, 16:9, 2–3 sentences per slide max
(`docs/hackathon-reference/06-what-to-submit.md`). 10 slides — the deck mirrors
the video's two-act shape: hook → antithesis → product → proof → close.

> The **claim** "Stay in the moment. We handle the after." is the spine
> of the deck. It shows up on slide 1 (hero), slide 3 (antithesis
> reveal), and slide 10 (close). Don't put it everywhere — let it land.

### Slide 1 — Title · the claim

* Wordmark **afterglow** small (top).
* Hero, display weight, two lines: **"Stay in the moment. // We handle
  the after."**
* Bottom: partner pill row (Vultr · Google ADK · Speechmatics) · the
  three live URLs · "AI Agent Olympics · Milan AI Week 2026 · MIT".

### Slide 2 — The after

* Two short text blocks, no icons. Display hero:
  *"A call ends. Something else begins."*
* Left ("THE CALL"): thirty seconds, two humans, works just fine.
* Right ("THE AFTER"): booking to enter, confirmation to send,
  allergy to remember, briefing for next time.
* Kicker: *"Every restaurant, dentist, body shop, dog groomer,
  garage on earth has this gap. Today it's post-its, short-term
  memory, a second tab open just in case."*

### Slide 3 — The bet · antithesis

* Two-line display:
  *"We don't replace the call.*
  *We replace **the after**."*
* Sub-line in muted ink: *"AI receptionists kill the moat. The reason
  a customer dials a small business is the human on the other end."*

### Slide 4 — The after, mechanically

* Section title: *"After they hang up."*
* The architecture diagram from §7 (audio → STT → Briefing on top;
  Gemini/ADK loop with tool chips + Vultr RAG underneath).
* Footer chips: `finalize → completed` · `max_turns → needs_review` ·
  `error → failed`.

### Slide 5 — Why it's agentic

* Four cards: self-correction · RAG-on-demand · explicit loop exit ·
  auditable turn-by-turn.
* Concrete proof snippet on card 1: `validation_failed → re-read →
  re-emit → executed`.

### Slide 6 — Partner integration depth

* Vultr (4 surfaces): Cloud Compute + Coolify · Managed Postgres ·
  Vector Store · Serverless Inference RAG.
* Google: Gemini 3.1 Flash Lite via ADK 1.18, typed tool surface,
  structured output from per-template JSON Schema.
* Speechmatics: batch STT (diarization on, language=auto) + TTS
  Preview powering every demo MP3.
* Each card carries one verifiable proof (e.g. `/admin/rag-probe`
  returns non-zero `input_tokens`).

### Slide 7 — Business value

* Header: *"Worldwide problem. Italy is where we measured first."*
* Italian-baseline card (tagged "floor, not ceiling") with three
  metric chips: **478k** booking-led / **185k** phone-led SAM /
  **€110M** initial Italian SAM/year. Note: sized sector by sector
  from first-party sources (FIPE · ISTAT · FNOMCeO · Key-Stone ·
  Confartigianato · AGCOM · UPB). Expansion order: France · Germany
  · UK · Spain · US service economy.
* Beachhead verticals line: hair salons · dog groomers · auto repair
  · beauty · dentistry.
* USP table vs CallRail / Aircall / Dialpad AI — the headline
  difference is *"After the call, not on it"*, with an explicit
  geo-model row (*"single-tenant per customer · worldwide"*).

### Slide 8 — Real where it matters

* Two columns: REAL (Speechmatics STT, Gemini ADK loop, Vultr RAG +
  Vector Store + Postgres, `customer.update_profile` mutates, TTS
  Preview generates every MP3).
* MOCKED (booking, WhatsApp, SMS, email, calendar, payment, CRM,
  review — and write-back to the shared demo collection).
* Footer kicker: *"Swap a mock for real = one file in
  `action_catalog.py` + an env var. Not an architecture migration."*

### Slide 9 — Try it

* Two cards: live URLs (demo / app / api / repo) + the 6-step
  click-path (Drawer → Test simulator → existing customer → call →
  trail → briefing → wizard).
* Proof line: *"multi-visitor sandboxed · per-tab `X-Demo-Session`
  isolates judges."*

### Slide 10 — Close

* Wordmark **afterglow** (display).
* The claim: *"Stay in the moment. We handle the after."*
* `afterglow.cleversoft.it` · `github.com/Cleversoft-IT/afterglow` · MIT.
* Partner pills row (final time).

> **Why we dropped QR codes from the original outline:** the slide PDF
> is a digital artifact — judges click links, they don't scan paper.
> Big legible URLs beat tiny QR squares every time. (If we ever print
> the deck, we add QRs back.)

---

## 6. Judge cheat sheet — live demo

> Print or pin this section. This is the click-path a judge should
> follow if they open the demo cold.

### Three live URLs

1. **`https://afterglow.cleversoft.it`** — landing page, the
   marketing front door. Scroll to the **"Live demo"** section to see
   the operator app in an iframe (390×845 phone frame). On mobile the
   iframe collapses to a CTA — click it to open the app full-screen.
2. **`https://app.afterglow.cleversoft.it`** — the operator app
   directly (Expo web build). This is where the work happens.
3. **`https://api.afterglow.cleversoft.it`** — the API. Open
   `/health`, `/docs`, or `/api/v1/admin/rag-stats` to confirm the
   integration is live (rag-stats returns the actual Vultr Vector Store
   chunk counts).

### Demo isolation

The app is **multi-visitor sandboxed**. Every browser tab gets its
own demo session (UUID stored in localStorage, sent as
`X-Demo-Session` header). Two judges browsing at the same time will
not interfere with each other's state. Their customer rows, template
edits, and simulated calls are isolated.

### Three-minute click path

1. Land on the demo URL. Watch the **"How to get the most out of this
   demo"** modal — if it doesn't auto-open, the help icon in the top-
   right opens it.
2. Open the operator app in the iframe (or click "Open the live app"
   on mobile).
3. **Drawer (burger top-left) → Test simulator → "Call from existing
   customer."** The Pixel-style incoming-call screen takes over;
   audio plays for ~25 seconds. Pick up, listen, hang up.
4. You're now back on Home. A new call appears at the top with a
   progress chip: `transcribing → analyzing → completed`. Total wait
   ~6–10 seconds.
5. **Tap the call.** The detail view opens. Scroll the right panel
   to expand the **Agent Reasoning Trail**. Walk through the turns.
6. Tap the customer name in the header to open the **customer card**.
   Note the **briefing** at the top — the AI-written one-sentence
   summary that will surface on the next call.
7. **Drawer → Audit log.** See the AuditLog overview — token counts,
   per-call breakdown.
8. **Drawer → Templates → Wizard.** Type "I run a small hair salon"
   in 2–3 messages. Watch the wizard produce a working template plus
   two new MP3 demo scripts.

### Reset

* **Drawer → Settings → Reset demo** — wipes the current visitor's
  sandbox state (their customers, calls, template edits) back to a
  fresh state with the seeded data only. Does not touch other
  visitors' sessions.

### "Is this thing real?" — verifications

Open the API directly and call these:

* `GET https://api.afterglow.cleversoft.it/api/v1/admin/rag-stats` —
  returns `{preseed_chunks: N, runtime_chunks: M, collection: "..."}`.
  Confirms the Vultr Vector Store is live and pre-populated.
* `GET https://api.afterglow.cleversoft.it/api/v1/admin/rag-probe?phone=+15552223344`
  — issues a real RAG query against the Vultr collection for Sophie
  Walker. Returns the RAG response **and** `input_tokens` from the
  Vultr Inference response. Non-zero tokens mean the call was billed
  to our Vultr account — not a stub; `hit=true` proves the preseeded
  memory store is returning customer facts.
* `GET https://api.afterglow.cleversoft.it/api/v1/audit?call_id=<id>`
  — full audit trail for any call: every agent turn, every tool call,
  token usage, durations.

### What can a judge break? (and how to recover)

* **Bypass the demo sandbox**: append `?bypass=<DEMO_BYPASS_TOKEN>` to
  the app URL. Talks to the real single-tenant data. Don't share the
  token publicly.
* **Force a `failed` call**: trigger the simulator with the actual
  audio API endpoint disabled (won't happen in normal use). The
  pipeline lands on `Call.status="failed"` with a human-readable
  `error` and the UI shows a red chip.
* **Force a `needs_review` call**: artificially constrain the
  `max_iterations` to 1 via the admin `/dry-run-pipeline` endpoint
  with a verbose transcript — the loop will hit the budget and the
  status becomes `needs_review` with a `review_flag`.

---

## 7. Architecture summary

> Compact version. Full architecture lives in `docs/ARCHITECTURE.md`
> (916 lines). This section is what you put on a slide and in the
> README.

### High-level flow

```
                  ┌────────────────────────┐
  audio MP3 ───▶  │  POST /api/v1/calls    │  ──▶  Call.status="pending"
                  │  (FastAPI, BG task)    │       (eager customer FK if known)
                  └──────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │  Speechmatics Batch STT  │   diarization=on, language=auto
                │  (real API, no fallback) │
                └──────────┬───────────────┘
                           │  raw_transcript (text + speakers + language)
                           ▼
                ┌──────────────────────────────────────────┐
                │  Orchestrator                            │
                │   ├─ pre-classifier (drop empty/noise)   │
                │   ├─ resolve customer (clone-on-write    │
                │   │   in demo sessions)                  │
                │   ├─ structured facts pass (SQL only,    │
                │   │   no LLM) → prompt hints             │
                │   └─ launch agent loop (max 12 turns)    │
                └──────────┬───────────────────────────────┘
                           │
                           ▼
            ┌─────────────────────────────────────────────┐
            │  Google ADK · Gemini 3.1 Flash Lite         │
            │  ┌─────────────────────────────────────┐    │
            │  │ tool surface bound on agent boot:   │    │
            │  │  · lookup_customer_memory(query)    │────┼─▶  Vultr RAG
            │  │  · search_transcript(keyword)       │    │    /v1/chat/completions/RAG
            │  │  · read_transcript_segment(a,b)     │    │    model=MiniMax-M2.7
            │  │  · flag_for_review(reason,severity) │    │    over collection
            │  │  · finalize_call(payload)           │    │
            │  │  · N domain action tools (typed     │    │
            │  │    Pydantic from JSON Schema)       │────┼─▶  execute_single_action
            │  └─────────────────────────────────────┘    │   (deterministic validator
            │  loop exit:                                  │   → MOCK_REGISTRY or
            │   · finalize       → status="completed"      │     INTERNAL_HANDLERS)
            │   · max_turns      → status="needs_review"   │
            │   · error          → status="failed"         │
            └──────────┬───────────────────────────────────┘
                       │
                       ▼
              ┌────────────────────────────┐
              │  Persist                   │
              │   · ExtractedFields        │
              │   · Customer.memory_summary│
              │   · Vultr add_vector_item  │  (prod only — skipped in demo)
              └────────────────────────────┘
                       │
                       ▼
              ┌────────────────────────────┐
              │  UI polls /calls every 2s  │
              │   · Home updates           │
              │   · Call detail with       │
              │     Agent Reasoning Trail  │
              │     (turn-by-turn, joined  │
              │      via payload.agent_turn│
              │      audit key)            │
              └────────────────────────────┘
```

### Status lifecycle (`Call.status`)

| Status | Set by | Terminal | Meaning |
|---|---|---|---|
| `pending` | `POST /calls` | no | row created, Speechmatics queued |
| `transcribing` | orchestrator | no | Speechmatics in flight |
| `analyzing` | orchestrator | no | agent loop in flight |
| `completed` | orchestrator on `finalize_call` | **yes** | success — ExtractedFields persisted, briefing surfaced |
| `needs_review` | orchestrator on `max_turns` (or agent's explicit `flag_for_review`) | **yes** | loop budget exhausted or agent asked for human eyes — UI banner + Home filter |
| `failed` | orchestrator on `completion_reason="error"` OR pre-classifier reject | **yes** | hard error — `error` field carries human-readable cause |

### Demo sandbox semantics

* Visitor browser → UUID in localStorage → sent as `X-Demo-Session`.
* `Customer`, `Call`, `Template`, `ExecutedAction`, `AuditLog` rows
  have a nullable `session_id`. Demo writes are scoped to the
  session; prod writes have `session_id IS NULL`.
* Seed customers are clone-on-write: if a demo session calls a seed
  number, the seed `Customer` row is cloned (with all its prior
  briefing and memory) into the session's namespace, so mutations
  don't pollute the shared seed.
* RAG write-back is **skipped in demo** (would pollute the shared
  collection); RAG read happens on the pre-seeded collection. Audit
  row: `memory_updater status=skipped reason=demo_sandbox_vector_store_disabled`.

### Audit correlation

Every tool call passes through `agents/tools/turn.bump_turn(tool_context)`
as its first instruction. This increments `tool_context.state["turn_counter"]`
and returns the int, which is then forwarded to `execute_single_action`
and stored in the audit row as `payload.agent_turn`. The UI joins
`agent_name="call_agent"` rows with `agent_name="action_executor"`
rows on this integer — **not** on timestamps — for deterministic
turn-by-turn rendering even when events land in the same millisecond.

---

## 8. Partner integration matrix

Tag each in the lablab form. Be prepared to demo each on screen.

### Vultr — used in **four** independent surfaces

| Surface | Where | Verification |
|---|---|---|
| **Cloud Compute + Coolify** | The VM hosting all 3 services. IP `95.179.245.107`. Auto-deploy on push to main. | `https://app.afterglow.cleversoft.it` loads. |
| **Managed Postgres 16** | System of record. Schema mirrored locally by Alembic in `backend/entrypoint.sh`. | Any call detail renders DB-backed data. |
| **Vector Store** | `customer_memory_chunks` table mirrors Vultr items. Preseed task populates it at backend boot with `chunk_metadata.preseed=true`. | `GET /api/v1/admin/rag-stats` returns `{preseed_chunks: N, runtime_chunks: M}`. |
| **Serverless Inference RAG** | `POST /v1/chat/completions/RAG` against `MiniMaxAI/MiniMax-M2.7`. Exposed to the agent as the `lookup_customer_memory` tool. | `GET /api/v1/admin/rag-probe?phone=+15552223344` returns `hit=true`, the RAG response, and `input_tokens > 0`. |

**Code:** `backend/app/integrations/vultr_inference.py`,
`backend/app/tasks/vector_preseed.py`,
`backend/app/agents/tools/memory_tool.py`.

### Google — **Gemini via ADK**

* **Model:** `gemini-3.1-flash-lite` (pinned in
  `backend/app/config.py:34-35`).
* **ADK:** `google.adk.runners.InMemoryRunner`, ADK 1.18.
* **Tool surface:** declared as typed Python callables; ADK introspects
  `__annotations__` and `__doc__` to auto-generate the Gemini
  `FunctionDeclaration`s.
* **Structured output:** `FinalizeCallPayload` is a Pydantic v2 model;
  action payloads are Pydantic models **built dynamically** from each
  template action's JSON Schema (`integrations/jsonschema_to_pydantic.py`).
* **Other Gemini surfaces:** wizard chat (template builder),
  briefing regenerator (one-shot direct API), bilingual EN
  summarizer for the RAG chunk (one-shot direct API).

**Code:** `backend/app/integrations/gemini_adk.py`,
`backend/app/agents/call_agent.py`,
`backend/app/agents/wizard_chat.py`,
`backend/app/agents/briefing_regenerator.py`.

### Speechmatics — **batch STT + TTS Preview**

* **Batch STT:** `speechmatics-batch>=0.4.8` SDK.
  `TranscriptionConfig(language="auto", diarization="speaker")`.
  Base URL `https://asr.api.speechmatics.com/v2`. Fail-loud on missing
  key or empty audio. Diarization is **always on** — speakers are
  rendered "S1: …", "S2: …" in the stored transcript.
* **TTS Preview:** `https://preview.tts.speechmatics.com/generate`
  with voices Sarah/Theo/Megan/Jack (UK/US). Used to produce:
    - the **6 bundled demo MP3s** (`app/assets/audio/{restaurant,dentist,bodyshop}_{existing,new}.mp3`)
    - **2 MP3s per wizard-generated template** (`<template_id>_{existing,new}.mp3`), concatenated PCM via Python `wave` and transcoded to mono 48 kbps MP3 via the `lame` CLI (chosen over ffmpeg because ffmpeg's apt-install OOM-kills the 4 GB Coolify build VM on cache miss).

**Code:** `backend/app/integrations/speechmatics.py`,
`backend/app/integrations/speechmatics_tts.py`,
`scripts/generate_demo_audio.py`.

### The three "bonus love" claims for the Speechmatics award

Edgars Adamovics (Speechmatics) stated three explicit scoring bonuses
at the AI Week kick-off:

1. **Speaker diarization used creatively** → ✅ we use diarization
   not just to label speakers but to feed the agent's
   `search_transcript` and `read_transcript_segment` tools with
   speaker-aware spans. The agent can re-read what S1 said vs S2.
2. **Multilingual** → ✅ `language="auto"` is set on STT; the agent
   loop captures `language` in the `FinalizeCallPayload`; the
   bilingual EN summarizer in `_persist_memory` generates an English
   tail for the RAG chunk when the briefing language is not English.
3. **Voice SDK** → we use the batch SDK rather than the real-time
   Voice SDK (because Afterglow's value is post-call, not in-call).
   **This bonus we explicitly forgo** — and we say so honestly in
   the pitch. The trade-off is intentional and product-driven.

### Why we are not chasing Featherless or Kraken

* **Featherless** wants open-source domain-specialized models. We use
  Gemini because the ADK function-calling stack is significantly
  cleaner for typed agentic loops, and our value proposition is
  not the model. Switching to a Featherless-hosted model would be an
  ablation, not a product improvement.
* **Kraken** is xStocks trading. Out of domain. Not pursued.

---

## 9. The 10 differentiators

Use these as bullet sources for the slide deck, the long description,
and the video Q&A. Each one is backed by code.

1. **Multi-turn agent loop with verified self-correction on tool errors.**
   `agents/call_agent.py:137-276` · `agents/tools/action_tool.py:117-164`.
   The model reads `{status: "validation_failed", result: {...}, attempt: 1}`
   and re-emits a corrected payload on the next turn. Hard cap at 2
   attempts. Visible in any completed call's reasoning trail.

2. **RAG as a tool the agent chooses to call, not as a prompt prefix.**
   `agents/tools/memory_tool.py:33-74` · `integrations/vultr_inference.py:44-74`.
   The system prompt instructs the agent to ask **specific** questions
   ("does the caller have allergies on file?") and to **skip** the
   lookup for clearly-new callers — saving tokens and making each RAG
   call auditable as a discrete decision.

3. **No-raise contract preserves executed actions across loop errors.**
   `executors/action_executor.py:218-233` · `agents/call_agent.py:210-221`
   · `agents/orchestrator.py:22-27`. Each layer converts exceptions to
   data. A `customer.update_profile` that succeeded before a downstream
   Gemini error stays in the DB and remains undoable through the UI.

4. **`needs_review` as a first-class terminal state.**
   `agents/orchestrator.py:397-411` · `db/models.py:171`. When the
   loop hits the 12-turn budget without finalizing, the call is marked
   `needs_review` with a structured `review_flag` and surfaces in a
   dedicated Home filter chip. No silent fallback.

5. **Deterministic audit correlation via `payload.agent_turn`.**
   `agents/tools/turn.py:14-26` · `executors/action_executor.py:204`
   · `app/components/AgentReasoningTrail.tsx:87-100`. The frontend joins
   the agent's turn rows with the action executor's rows on an explicit
   integer key, not on timestamps. Robust even at sub-ms event timing.

6. **Typed Pydantic payloads built dynamically from per-template JSON
   Schemas.** `integrations/jsonschema_to_pydantic.py`
   · `agents/tools/action_tool.py:107-115`. Gemini never sees
   untyped `dict` for the action tools; it emits structured-output
   JSON that fits the schema declared in the active template. Single
   source of truth: the template.

7. **Vultr triple-play in one audit trail.** Postgres + Vector Store
   + Inference RAG, all visible in the same `/audit` view for the
   same call, plus the `/admin/rag-probe` endpoint that proves
   non-zero token billing on real Vultr Inference round-trips.

8. **Single-tenant simplicity + per-visitor demo sandbox isolation.**
   `api/session_context.py` · `agents/orchestrator.py:487-571`. The
   product is single-tenant by design — but the demo serves N
   concurrent judges via session-scoped clone-on-write of seed data.
   `?bypass=<DEMO_BYPASS_TOKEN>` opens the real tenant for the live
   pitch.

9. **Seed-date drift refresh.** `tasks/seed_date_refresh.py:44-194`
   · `Setting.seed_anchor_date`. The demo never shows stale "12 days
   ago" timestamps on seed data. At boot, the backend bulk-updates
   timestamps and `jsonb_set`s the `booking_date` inside payload JSON
   so the demo is always temporally fresh.

10. **Domain-shaped tool surface at zero cost.** `integrations/action_catalog.py:397-422`.
    A dentist template exposes `patient_update_profile`; a restaurant
    template exposes `whatsapp_send_confirmation`. Same `customer_profile.apply_update`
    internal handler powers both `customer.update_profile` and
    `patient.update_profile` — the agent sees domain-coherent tool
    names, not the implementation.

---

## 10. Judging criteria — coverage matrix

The four criteria from `docs/hackathon-reference/07-judging-criteria.md` weight
equally (25% each). For each, this is our explicit evidence plus the
video timestamp where it lands.

### Application of Technology (25%)

| Evidence | Where in code | Where in video |
|---|---|---|
| Multi-turn agent loop with typed tool surface | `agents/call_agent.py` · `agents/tools/*.py` | Act II.B (0:55–1:55) |
| Self-correction on tool errors | `agents/tools/action_tool.py:117-164` | Act II.C (1:55–2:25) |
| RAG-on-demand as a tool decision | `agents/tools/memory_tool.py` | Act II.B (RAG turn) |
| Vultr 4-surface integration (Compute · Postgres · Vector · Inference) | §8 above | Act II.F (3:30–4:00) + Coda (4:30–5:00) |
| Gemini structured output via ADK function calling | `integrations/gemini_adk.py` · `agents/tools/action_tool.py:107-115` | Act II.B + Act II.C |
| Speechmatics diarization fed into transcript tools | `integrations/speechmatics.py` · `agents/tools/transcript_tool.py` | Act II.B |
| Real-vs-mocked transparency (action_catalog as integration boundary) | `integrations/action_catalog.py` + §11 | Act II.F (3:30–4:00) |

### Originality (25%)

| Evidence | Where in code | Where in video |
|---|---|---|
| Counter-bet thesis: keep the human, replace the after | product design | Act I (0:00–0:30) + Act II.A (0:30–0:55) |
| Typographic cold open — type, silence, one ring, the claim | video script §4 | Act I (0:00–0:30) |
| Drop-in Pixel-style phone app aesthetic for an AI product | `app/` Expo build | Act II.B + II.D |
| Agent reasoning trail as a first-class UI surface, not a buried log | `app/components/AgentReasoningTrail.tsx` | Act II.B |
| `needs_review` as terminal status, not silent fallback | `agents/orchestrator.py:397-411` | Cheat-sheet demonstration |
| Template wizard as a Gemini-driven 2-to-5-question interview | `agents/wizard_chat.py` | Act II.E (2:55–3:30) |
| Per-template Speechmatics TTS dual-scenario MP3 generation | `integrations/speechmatics_tts.py` | Act II.E |
| Live wizard build of an arbitrary vertical, end-to-end | `agents/wizard_chat.py` · `integrations/speechmatics_tts.py` | Act II.E |

### Business Value (25%)

| Evidence | Where |
|---|---|
| Concrete persona (small-business operator) described in operator-language, not LLM-speak; same loop runs across restaurants, dentists, body shops, dog groomers, salons | §2 + Act II.A + Slide 2 |
| TAM/SAM with named markets, source methodology and pricing band | §3 Long Description + Market sizing notes + Slide 7 + Act II.G (4:00–4:30) |
| USP table vs CallRail / Aircall / Dialpad AI ("we replace the after, not the call") | Slide 7 + Act II.G |
| Honest real-vs-mocked surface — trust-by-transparency, not by hiding | §11 + Slide 8 + Act II.F (3:30–4:00) |
| Concrete templates for three real verticals out of the box (restaurant · dentist · bodyshop) plus wizard-generated for any other (built live in the demo) | §8 + Act II.E |
| Auditable AI work (every action undoable where the catalog allows) — addresses the small-business operator's #1 AI concern (control) | UI: call detail Undo button · `INTERNAL_REVERTERS` |
| Single-tenant model = clear sales motion, no multi-tenant complexity | architecture decision in `CLAUDE.md` constraint #1 |

### Presentation (25%)

| Evidence | Where |
|---|---|
| Problem → solution lands in the first 60 seconds (lablab tip) | Scene 1 (0:00–0:15) → Scene 2 (0:15–0:45) |
| Video ≤5 min, MP4, ≤300 MB, **uploaded directly to lablab** (not YouTube/Drive) | Submission checklist §13 |
| Slide PDF with 2–3 sentences per slide (lablab tip) | §5 outline |
| README reproducible from `README.md` | repo root |
| Architecture diagram in the README and in the slides | §7 + Slide 4 |
| Live demo URL that works (cheat-sheet click path) | §6 |
| Public GitHub repo, MIT-licensed | repo root + `LICENSE` |

### Speechmatics bonuses (non-quantified, but stated by Edgars)

* **Multilingual:** ✅ STT `language="auto"`, bilingual EN summarizer in `_persist_memory`.
* **Creative diarization:** ✅ speaker-aware transcript tools.
* **Voice SDK:** ✗ we use the batch SDK; trade-off declared honestly in the pitch.

---

## 11. Real-vs-mocked — the honest table

This is the table to **lead with** if anyone asks. Showing this matrix
proactively builds trust; trying to hide it backfires.

### Why the audio path is real (not a script shortcut)

Every demo call follows the same wire: **operator presses the AI button →
Expo records the MP3 → `POST /api/v1/calls` uploads it → the orchestrator
calls Speechmatics Batch STT → the agent loop runs on the resulting
transcript**. There is no "skip ASR, read the script" hatch on this code
path. The only bypass that exists at all is `POST /admin/calls/probe`,
which is admin-only, never exposed to the demo URL, and labelled
`step_type="tool_call" status="skipped" reason="transcript_preloaded"`
in the audit log so the bypass is always visible if used.

For wizard-generated templates, the MP3 itself is built by
Speechmatics TTS Preview (one round-trip per script turn) — same
artifact the operator's microphone would produce in production. The
orchestrator's `agent_loop_start` audit row carries
`payload.audio_source = "speechmatics_batch"` plus the
on-disk basename, so the auditor can verify the path end-to-end
without trusting our story.

### What is REAL (billed, not stubbed)

| Surface | Why real |
|---|---|
| Speechmatics Batch STT on every uploaded call | Real API key, no offline fallback. `integrations/speechmatics.py:38-43` raises on missing key or empty audio. |
| Gemini 3.1 Flash Lite agent loop on every analyzed call | Real `GOOGLE_API_KEY`, ADK runner. Missing key → `Call.status="failed"` with human-readable error. No offline stub. |
| Vultr Serverless Inference RAG calls | `lookup_customer_memory` tool hits `POST /v1/chat/completions/RAG`. Verifiable via `/api/v1/admin/rag-probe` which exposes `input_tokens`. |
| Vultr Vector Store preseeded collection | At backend boot, `vector_preseed.py` pushes 1 chunk per seed call (idempotent per-call). Counted by `/admin/rag-stats`. |
| Vultr Vector Store write-back in production | Each completed prod call writes a chunk via `add_vector_item`. (Skipped in demo by design — see below.) |
| Vultr Managed Postgres | System of record for the entire pipeline. |
| `customer.update_profile` / `patient.update_profile` actions | `internal_real` execution kind. Actually mutates the `Customer` row. Undoable via `INTERNAL_REVERTERS`. |
| Speechmatics TTS Preview for demo audio | The 6 bundled MP3s + the 2-per-wizard-template MP3s are generated from real TTS calls. Not stock audio. |

### What is MOCKED, and why

| Surface | Why mocked | How to swap to real |
|---|---|---|
| `booking.create` (and reschedule) — restaurant + dentist + bodyshop | We don't have a real Resy / TheFork / OpenDental account; a demo with N concurrent judges can't write to a real booking system. | Add HTTP client in `integrations/mocks/booking.py`, swap registry entry. Catalog wiring is unchanged. |
| `whatsapp.send_confirmation`, `whatsapp.request_photos` | Real WhatsApp Business API requires a registered phone + per-message billing — inappropriate for a multi-visitor demo. | Plug Twilio or Meta Cloud API into `integrations/mocks/whatsapp.py`. |
| `sms.send_reminder` | Same as WhatsApp. | Plug Twilio. |
| `email.send` and `email.send_quote` | We don't have a verified sending domain for the demo. | Plug Resend / SendGrid / SES. |
| `calendar.send_invite`, `calendar.block_slot` | Real Google/Outlook calendar API requires per-tenant OAuth. | Plug Google Calendar API. |
| `payment.request_deposit`, `payment.send_invoice` | Mock by design — never test payments against a live processor in a demo. | Plug Stripe in `integrations/mocks/payment.py`. |
| `crm.create_lead`, `crm.create_ticket` | We don't pick a CRM for the user; this is a customer-by-customer integration. | Plug HubSpot / Pipedrive / Salesforce. |
| `review.request_feedback` | Tied to a review platform of the customer's choice. | Plug Trustpilot / Google Reviews. |
| Vector Store **write-back** in demo mode | Multi-visitor sandbox sharing one collection — writing per-visitor chunks would pollute the shared memory. Audit row logs `status=skipped reason=demo_sandbox_vector_store_disabled`. | In single-tenant production, the write happens (already implemented at `agents/orchestrator.py:574-697`). |

The architecture is **designed around** this distinction. `integrations/action_catalog.py`
is the single source of truth for `integration_kind`
(`mock_external` | `internal_real`), `mock_target`, `internal_handler`,
and `can_undo`. Replacing a `mock_external` with a real integration is
a one-file change to the mock registry plus an environment variable —
**not** an architecture migration.

This is the point to drive home: **the agentic loop, the RAG, and the
single-tenant deployment are all production-ready**. The mocks are
demo concessions, not architectural debt.

---

## 12. Compliance, IP, legal

| Requirement | Status |
|---|---|
| Original work | ✅ All code written by the team during the build week. Single fork acknowledgement: the project structure was informed by the lablab official tutorial baseline (`docs/hackathon-reference/14-tutorial-gemini-vultr-document-agent.md`) but no code is copied verbatim. |
| Open source | ✅ Public GitHub repo. |
| MIT License | ✅ `LICENSE` from day 1. |
| No GPL/AGPL dependencies | ✅ Audited. Three notable frontend deps: `react-native-paper` (MIT), `@material/material-color-utilities` (Apache-2.0), `@react-navigation/drawer` (MIT). Backend: FastAPI (MIT), SQLAlchemy (MIT), `speechmatics-batch` (MIT), `google-genai` (Apache-2.0), `httpx` (BSD), `pydantic` (MIT). All permissive. |
| AI usage disclosure | Not required by lablab terms (`docs/hackathon-reference/08-hackathon-details.md`). The repo contains AI-assistant config files openly. |
| Team size 1–6 | ✅ 4. |
| Age ≥18 | ✅. |
| Eligible jurisdiction | ✅. |
| IP ownership | Team retains IP; lablab/NativelyAI receives a non-exclusive promotional license per ToS §4. |

### Deadlines

| When | What |
|---|---|
| 2026-05-19 17:00 CEST | Submission deadline (form, video, slides, demo URL all live and linked). |
| 2026-05-19 to 2026-05-25 | Judging window. |
| 2026-05-20 | Winner announcement on the Main Stage of Milan AI Week. |

### Submission editing

The lablab form is editable until the deadline even after first
"Submit" (`docs/hackathon-reference/06-what-to-submit.md` lines 60–67).
**Submit a complete draft ≥24h before the deadline** to insure
against last-second upload failures, then refine.

---

## 13. Pre-flight submission checklist

Run through this list in order. Do not check a box you haven't visually
verified.

### Artifacts to produce

* [ ] **Video pitch MP4** — ≤5:00, ≤300 MB, 1080p min. Filename:
      `afterglow-pitch.mp4`. Recorded per the §4 script.
* [ ] **Slide PDF** — 10 slides per §5. Filename: `afterglow-slides.pdf`.
      Max 5 MB.
* [ ] **Cover image** — 16:9 PNG, per §3 spec. Filename:
      `afterglow-cover.png`. Max 500 KB.

### Live infrastructure

* [ ] `https://api.afterglow.cleversoft.it/health` returns 200.
* [ ] `https://app.afterglow.cleversoft.it` loads, Home renders with
      the busy-week seed data.
* [ ] `https://afterglow.cleversoft.it` loads, iframe shows the
      app, "How to get the most out of this demo" modal works.
* [ ] `GET /api/v1/admin/rag-stats` returns `preseed_chunks > 0`.
* [ ] `GET /api/v1/admin/rag-probe?phone=+15552223344` returns
      `hit=true` and `input_tokens > 0` (proves real Vultr billing
      and preseeded memory retrieval).
* [ ] Trigger a fresh simulated call — verify it lands `completed`
      within 15 seconds.

### Repo hygiene

* [ ] Repo is **public** on GitHub.
* [ ] `LICENSE` is MIT.
* [ ] `README.md` includes the architecture diagram, the
      three live URLs, and the partner integration matrix.
* [ ] No secrets in the repo (verify: `git grep -E "(API_KEY|TOKEN|SECRET).*=.*['\"][A-Za-z0-9]"`
      returns nothing real).
* [ ] All open `tmp/` files removed or `.gitignore`-d.
* [ ] `main` branch is the deployed branch (no uncommitted local diff
      that "should be there").

### lablab.ai form

* [ ] Project Title: from §3 (≤50 chars).
* [ ] Short Description: from §3 (≤255 chars).
* [ ] Long Description: from §3 (≥100 words; verify ~370 in the form
      counter).
* [ ] Tracks: tag all 4 from §1.
* [ ] Technology tags: tag every entry in §3.
* [ ] Participation Type: **Onsite** (team is at Fiera Milano Rho on 2026-05-19).
* [ ] Cover Image: upload `afterglow-cover.png`.
* [ ] Video Presentation: upload `afterglow-pitch.mp4` **directly to
      lablab** (not YouTube/Drive).
* [ ] Slide Presentation: upload `afterglow-slides.pdf`.
* [ ] GitHub Repo URL: filled.
* [ ] Application URL: `https://afterglow.cleversoft.it`.
* [ ] Demo Application Platform: "Custom — Vultr Cloud Compute via
      Coolify".

### Submit ASAP — the 24h safety window has lapsed

The original target ("first Submit by 2026-05-18 17:00 CEST") was
missed. We are now on the deadline day (2026-05-19, deadline 17:00
CEST). Operational priority is therefore:

* [ ] First **Submit** clicked **today, as soon as the MP4 video is
      ready** — even if the deck/copy still need a polish pass. The
      lablab form is editable after first Submit until the deadline.
* [ ] Sanity-check the public submission page renders correctly
      (cover loads, PDF opens, video plays inline, all URLs clickable).
* [ ] Final edit pass before 2026-05-19 17:00 CEST.

### Day-of (2026-05-19)

* [ ] Backend `/health` green at 16:00 CEST.
* [ ] All three URLs green at 16:30 CEST.
* [ ] Simulated call green at 16:45 CEST.
* [ ] Final form submission state confirmed at 16:50 CEST.
* [ ] Screenshot of confirmation saved.

---

## 14. Future work — what we are deliberately NOT shipping

These belong in the closing slide / video Scene 8 only. Don't pretend
they're in the demo.

* **Real CRM connectors** — swap the mock registry entry-by-entry as
  the customer onboards.
* **SIP trunk integration** — today the audio enters Afterglow via
  upload (or simulator); a Twilio/Plivo SIP trunk makes it a real
  phone, not a demo.
* **On-call operator suggestions** — a read-only AI side panel that
  surfaces facts/scripts to the operator **during** the call,
  without speaking on the line. We deliberately did not ship this
  for the hackathon because it would muddy the "AI is post-call"
  message.
* **Template lineage and versioning** (already designed in
  `docs/future-ideas.md`).
* **Multi-tenant SaaS shell** — explicitly out of scope (`CLAUDE.md`
  constraint #1 keeps single-tenant).
* **PII redaction** — designed and then deliberately removed
  2026-05-17 because it harms operator usefulness ("the customer is
  celiac" is the point, not a leak); see `docs/future-ideas.md`
  §4 for the archived design.
* **Real-time Speechmatics Voice SDK** — only useful when we add
  on-call assistance; deferred until then.

---

## 15. Source-file reference index

If you need to verify any claim in this document, here is the
authoritative source for each topic.

### Architecture & pipeline

* `docs/ARCHITECTURE.md` — 916 lines, the canonical
  architecture document.
* `backend/app/agents/orchestrator.py` — the pipeline glue.
* `backend/app/agents/call_agent.py` — the agent loop entry.
* `backend/app/agents/tools/` — the typed tool surface
  (action_tool, control_tool, memory_tool, transcript_tool, turn).
* `backend/app/executors/action_executor.py` — deterministic
  validator + MOCK/INTERNAL dispatcher.
* `backend/app/integrations/gemini_adk.py` — ADK runner
  wrapper.
* `backend/app/integrations/jsonschema_to_pydantic.py` —
  dynamic Pydantic from JSON Schema.

### Integrations

* `backend/app/integrations/vultr_inference.py` — RAG +
  Vector Store.
* `backend/app/integrations/speechmatics.py` — batch STT.
* `backend/app/integrations/speechmatics_tts.py` — TTS preview.
* `backend/app/integrations/action_catalog.py` — the
  authoritative catalog of 25 action keys across 8 mock buckets +
  1 internal real bucket.

### Data model + tasks

* `backend/app/db/models.py` — SQLAlchemy models.
* `backend/app/db/seed.py` — seed data (12 customers, 3
  templates, ~43 busy-week calls).
* `backend/app/tasks/vector_preseed.py` — RAG preseed at
  boot.
* `backend/app/tasks/seed_date_refresh.py` — anchor-date
  drift refresh.

### Market sizing

* `tmp/deep-research-report (2).md` — Italian TAM/SAM research for
  booking-led and phone-led businesses, with source-method notes and
  domain ranking.

### API + config + admin

* `backend/app/api/calls.py` — `POST /calls` ingest +
  detail view.
* `backend/app/api/admin.py` — `rag-stats`, `rag-probe`,
  `dry-run-pipeline`.
* `backend/app/api/session_context.py` — demo session
  middleware.
* `backend/app/config.py` — env-driven configuration.

### Frontend (the parts that matter for the pitch)

* `app/components/AgentReasoningTrail.tsx` — the reasoning
  trail UI.
* `app/app/(drawer)/(tabs)/index.tsx` — Home (Pixel Recents
  clone).
* `app/app/call/[id].tsx` — call detail.
* `app/app/(drawer)/simulator.tsx` — the demo simulator.
* `app/app/templates/wizard.tsx` — wizard chat UI.
* `demo-site/src/App.tsx` — the marketing landing.

### Memory (team-shared, in `.claude/memory/`)

* `MEMORY.md` — index.
* `project_afterglow_decisions.md` — locked architectural decisions,
  per-round.
* `project_agentic_pipeline.md` — round-10 spec.
* `project_afterglow_hackathon.md` — hackathon coordinates.
* `project_rag_demo_read_only.md` — RAG demo semantics.
* `reference_devops_pipeline.md` — Coolify + Vultr coordinates.
* `feedback_docs_freshness.md` — the docs-must-stay-in-sync policy
  that produced this document.

### Hackathon reference (external, in `docs/hackathon-reference/`)

* `02-challenge.md` — challenge thesis + 5 tracks.
* `06-what-to-submit.md` — submission form spec + MP4 rules.
* `07-judging-criteria.md` — the 4 criteria.
* `12-vultr-deep-dive.md` — Vultr award playbook.
* `13-gemini-deep-dive.md` — Gemini award playbook.

---

## 16. Live form schema — verified on lablab.ai

> Captured **2026-05-19** by inspecting the React state of the live
> form at
> `https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/claudio-opuscoli/submission`.
> Everything in this section comes from `formConfig` and the
> server-side draft snapshot (`data`) attached to the page React
> tree. The
> [`docs/hackathon-reference/06-what-to-submit.md`](hackathon-reference/06-what-to-submit.md)
> notes were partially out of date — when this section disagrees
> with that file, **this section wins**.

### 16.1 The form has 3 pages

`formConfig.layout.pages`:

| # | Page title | Description | Fields |
|---|---|---|---|
| 1 | Basic Information | Tell us about your project | `title`, `shortDescription`, `description`, `submissionType`, `categories`, `tracks`, `technologies`, `social_media_post_link_1..5` |
| 2 | Media | Upload your demo video, cover image, and pitch deck | `imageLink`, `videoLink`, `presentationLink` |
| 3 | Application | Share your code and live demo | `repoLink`, `demoPlatform`, `demoUrl`, `kraken_api_key_read_only` *(optional)*, `kraken_account_id_username` *(optional)*, `additionalInfo` |

`formConfig.standardOverrides` for this event:

* `submissionType` — options: `Online`, `Onsite` (no Hybrid).
* `tracks` — NOT required.
* `repoLink` — NOT required (we will set it anyway).
* `demoPlatform` — NOT required (we will set it anyway).

`eventName: "AI Agent Olympics Hackathon"`,
`eventType: "HYBRID"` (the event is hybrid; per-team participation
is still Online or Onsite).

### 16.2 Page 1 — character limits and required fields

| Field | Min | Max | Required? | Notes |
|---|---|---|---|---|
| `title` | 5 | 50 | ✅ | Plain text. |
| `shortDescription` | 50 | 255 | ✅ | One-liner. |
| `description` | **600** | **2000** | ✅ | Characters, **not words**. Cap is hard. |
| `submissionType` | — | — | (validation: see overrides) | Radio: `Online` \| `Onsite`. |
| `categories` | 1 | (no cap visible) | ✅ | Multi-select over 119 entries — see §16.5. |
| `tracks` | 0 | (no cap) | ❌ | Multi-select over 10 entries — see §16.6. |
| `technologies` | 1 | (no cap) | ✅ | Multi-select over 185 entries — see §16.7. |
| `social_media_post_link_1..5` | — | — | ❌ | URL fields, optional, type=URL. |

### 16.3 Page 2 — Media

Three upload fields: `imageLink`, `videoLink`, `presentationLink`.
The form is gated by Page 1 validation — we couldn't reach Page 2
during the readonly inspection without filling the required fields,
so the exact `accept` / `maxSizeMB` constraints aren't visible from
the page-1 React state. Use the canonical lablab limits from
`docs/hackathon-reference/06-what-to-submit.md` as authoritative:

* Cover image: PNG/JPG, 16:9, ≤500 KB recommended.
* Video: MP4, ≤5:00, ≤300 MB, **direct upload** (no YouTube/Drive).
* Presentation: PDF, sintetico.

We will verify the page-2 hard limits the moment Page 1 is filled
in.

### 16.4 Page 3 — Application

| Field | Type | Required? | Notes |
|---|---|---|---|
| `repoLink` | URL | ❌ (we set it) | `https://github.com/Cleversoft-IT/afterglow` |
| `demoPlatform` | text/select | ❌ (we set it) | "Custom — Vultr Cloud Compute via Coolify" (or the closest select option). |
| `demoUrl` | URL | ✅ (implied) | `https://afterglow.cleversoft.it` |
| `kraken_api_key_read_only` | text | ❌ | Leave empty — we don't compete in the Kraken challenge. |
| `kraken_account_id_username` | text | ❌ | Leave empty — same reason. |
| `additionalInfo` | text | ❌ | Free-form. Good place to drop the market-sizing notes (§3) and the "submit ≥24h" apology if needed. |

### 16.5 Categories — the full 119-option list

> Multi-select, searchable. **Currently 0 selected on the draft —
> required, must pick at least one.** The list mixes Afterglow-
> applicable industry categories with category-shaped tags reserved
> for other partner sub-tracks (e.g. `Qubic Track - Raise`,
> `Prosus Track - Raise`, `Blackbox AI Track - Raise`, `Vultr Track
> - Raise`) — those Raise-namespace entries belong to a different
> hackathon series; **do not pick them**.

**Recommended picks for Afterglow** (5–6 is enough, more dilutes
the signal):

* `Customer Support` — primary fit (post-call follow-ups for SMBs).
* `Business` — generic, helps discoverability.
* `Voice Assistant` — we ingest voice (close fit to the audio
  pipeline).
* `Communication` — call workflows.
* `Productivity` — the operator UX is a productivity surface.
* *(optional)* `Healthcare` — dentist preset; pick only if we lean
  on the dental demo.
* *(optional)* `Food` — restaurant preset; pick only if we lean on
  Mark Ross / restaurant demo.

Full alphabetical inventory of the 119 options (verbatim labels —
case and punctuation matter when searching the picker):

`Advertising`, `Agent Builder track - The INTERNET OF AGENTS`,
`App Builder track - The INTERNET OF AGENTS`, `Art`, `Assistant`,
`Augmented Reality`, `Automotive`, `Beauty`,
`Blackbox AI Track - Raise`, `Book and eBook Reading`,
`Browser Extension`, `Business`, `Career Development`, `Chatbot`,
`Climate`, `Cloud Application`, `Code Generation`, `Coding`,
`Coding excellence`, `Communication`,
`Conduct(or) X Raise Track - Raise`, `Connectivity`, `Content`,
`Cooking`, `Copywriting`, `Customer Support`, `Data Mastery`,
`Dating`, `Design`, `Designer Tool Plugin`, `Desktop Application`,
`Developer Tools`, `Documents`, `Drink`, `Ecommerce`, `Education`,
`Email`, `Entertainment`, `Environmental`, `Events`, `Family`,
`Fashion`, `Finance`, `Fitness`, `Food`, `Game Developement` (sic),
`Game Engine Extension`, `Games`, `Healthcare`, `Home`,
`Home Automation`, `Humor`, `IDE Extension`,
`Innovation Network Design & Strategic Planning`, `Investment`,
`Job Search`, `Knowledge Base`, `Language and Translation`,
`Language Learning`, `Late submission`, `Legal`, `Lifestyle`,
`Marketing`, `Marketplaces`, `Mental Health`, `Mobile Application`,
`Music and Audio`, `Network Decommissioning and Transition`,
`Network Implementation and Deployment`,
`Network Operations and Maintenance`,
`Network Optimization and Upgrades`,
`Network Planning and Design`, `News and Information`,
`Next Generation Telecommunications Solutions`, `Non-Profit`,
`Online`, `Onsite`, `Open-ended Agent Protocol`,
`Operating System (OS) Utility`, `Optimizing Resource Allocation`,
`Parenting`, `Personal Finance`, `Pet and Animal Care`,
`Photography`, `Planning`, `PreExistingProject`,
`Procurement & Policy`, `Productivity`, `ProjectFromScratch`,
`Project Management`, `Prosus Track - Raise`,
`Qualcomm Track - Raise`, `Qubic EasyConnect Integrations`,
`Qubic Nostromo Launchpad`, `Qubic Track - Raise`, `Real Estate`,
`Recruitment`, `Relaxation`,
`Returning Project - Giga Hackathon 1`, `Scrape and Synthesize`,
`Security`, `Seo`, `Shopping`, `Social Media`, `Sports`,
`Summarization`, `Sustainability`,
`Transportation and Delivery`, `Travel`, `Utility and Tools`,
`Video`, `Virtual Assistant`, `Virtual Reality`, `Voice Assistant`,
`Vultr Track - Raise`, `Weather Forecasting`, `Web Application`,
`Web Scraping & Data Extraction`, `Writing`.

### 16.6 Event Tracks — the full 10-option list

> Multi-select, not required. Currently **6 selected on the draft
> ✓** (Intelligent Reasoning, Agentic Workflows, Enterprise Utility,
> Vultr, Google Track, Speechmatics).

| Option | In draft? | Comment |
|---|---|---|
| `Agentic Workflows` | ✅ | Core fit. |
| `Collaborative Systems` | ❌ | Not us — single agent loop, not multi-agent collaboration. |
| `Enterprise Utility` | ✅ | SMB operations product. |
| `Featherless AI` | ❌ | We don't use Featherless. |
| `Google Track` | ✅ | Partner prize (Gemini). |
| `Intelligent Reasoning` | ✅ | Loop self-corrects, RAG-on-demand. |
| `Kraken` | ❌ | Out of domain. |
| `Multimodal Intelligence` | ❌ | Borderline (audio in → text reasoning); skip for now. |
| `Speechmatics` | ✅ | Partner prize (batch STT + TTS Preview). |
| `Vultr` | ✅ | Partner prize (4 surfaces). |

### 16.7 Technologies Used — the full 185-option list

> Multi-select, searchable, **required**. Currently 2 selected:
> `Vultr`, `Speechmatics api`. **Must add Gemini + AI Studio** to
> unlock Google judging.

Recommended final tag set (4 entries):

1. `Vultr`
2. `Speechmatics api`
3. `Gemini 3 Flash` (primary Gemini tag — closest to "Gemini 3.1 Flash Lite")
4. `AI Studio` (closest publicly Google-branded surface for ADK; no `Google ADK` entry exists)

Optional secondaries to consider:

* `Gemini AI` — adding it alongside `Gemini 3 Flash` widens the
  Google-bucket match.
* `Generative AI Studio` — alternative to `AI Studio`.

Full alphabetical inventory of all 185 catalog entries (verbatim
labels):

`AgentOps`, `AI21 Labs`, `Ai71`, `AI/ML API`, `AI Studio`,
`Alpaca`, `AMD Developer Cloud`, `AMD ROCm`, `Anthropic Claude`,
`Antigravity`, `Arc`, `Arize`, `Assistants API`, `AudioCraft`,
`AutoGen`, `Auto-GPT`, `Aws`, `AWS SageMaker`, `BabyAGI`, `Bert`,
`Camel`, `CAMEL-AI`, `ChatGPT`, `Chirp`, `Chroma`, `Circle`,
`Clarifai`, `Claude Code`, `Cloudflare Workers AI`, `Codex`,
`Codey`, `Codium`, `Cohere Classify`, `Cohere Coral`,
`Cohere Embed`, `Cohere Generate`, `Cohere Neural Search`,
`Cohere Rerank`, `complete`, `Composio`, `Coral Protocol`,
`CrewAI`, `Crossmint`, `Cursor`, `Custom GPTs`, `DALL-E-2`,
`DALL·E Image Generation API`, `Dall-e Mini`, `Databutton`,
`Deepmind`, `DeepSeek R1`, `DeepSeek V3`, `EasyOCR`, `ElevenLabs`,
`Falcon`, `Falcon 2 11B`, `Falcon 2 11B VLM`, `Featherless`,
`Fetch.ai`, `FineTuner.ai`, `Fuyu-8B`, `Gan`, `Gemini 3 Flash`,
`Gemini 3 pro`, `Gemini AI`, `Gemma`, `Gemma 2`,
`Generative Agents`, `Generative AI Studio`, `Get3d`, `Godmode AI`,
`Gorilla`, `GPT-3`, `GPT-3.5`, `GPT-4`, `gpt4all`, `GPT 4o`,
`GPT-4 Vision`, `GPT-5`, `Grok`, `Groq`,
`Grounded-Segment-Anything`, `HuggingFace Hub`,
`HuggingFace Spaces`, `Ibm`, `IBM Granite`,
`IBM watsonx Assistant`, `Imagen`, `kiro`, `Kraken cli`,
`Kraken Ink`, `Kraken Websocket api`, `LangChain`, `langflow`,
`LLaMA`, `Llama 2`, `Llama 3`, `Llama 3.1`, `Llama 3.2`, `Llama 4`,
`LlamaIndex`, `LLavA`, `Lobster Trap`, `LTM-2-mini`, `MetaGPT`,
`MindsDB Knowledge Base`, `Mistral AI`, `Model Garden`,
`Monday AI Assistant`, `Monday.com`, `MongoDB`, `MultiOn`, `n8n`,
`Nebius`, `Novita`, `Nvidia`, `o1`, `OpenAI`, `OpenAI gym`,
`openclaw`, `OpenELM`, `OpenGPTs`, `open-interpreter`, `Opus`,
`PaLM`, `Phi-3`, `Pinecone`, `Point-E`, `Portkey`, `privateGPT`,
`Qdrant`, `Qubic`, `Qwen3`, `Qwen3-Coder`, `Qwen3-MT`,
`Qwen3-VL`, `Qwen-Image-2.0`, `Redis`, `Reinforcement Learning`,
`Replit`, `Restack`, `rest api`, `Rhymes.ai`, `SambaNova`,
`SDXL Turbo`, `SeamlessM4T`, `Shap-E`, `Snowflake`,
`Solar Pro Preview`, `Solo Tech`, `Speechmatics api`,
`Speechmatics flow`, `StableCode`, `Stable Diffusion`,
`Stable Dreamfusion`, `Stable LM`, `Stable Video`, `Streamlit`,
`SuperAGI`, `Text Generation Web UI`, `TinyLlama`, `Together AI`,
`Tonic.ai`, `Toolhouse`, `Trae IDE`, `TruLens`, `Twelve Labs`,
`Unstructured IO`, `Upstage`, `Vectara`, `Vectorboard 💛`,
`Vercel`, `Vultr`, `watsonx.ai`, `Weaviate`, `WebGPU`, `Webots`,
`Whisper`, `x402`, `Yi-LLMS`, `YOLOv5`, `YOLOv6`, `YOLOv7`,
`YOLOv8`, `Zilliz`.

### 16.8 Server-side draft snapshot (as of 2026-05-19, edit version 5)

For reference — what the lablab server thinks our draft looks like
right now (before we touch it):

| Field | Server state | Action needed |
|---|---|---|
| `title` | `"Afterglow"` (9 chars) | Optional: extend to `Afterglow — we handle the after` |
| `shortDescription` | `null` | **Fill** with §3 short description |
| `description` | `""` | **Fill** with §3 long description, **trimmed to ≤2000 chars** |
| `submissionType` | `"ONSITE"` | ✓ correct — team is in Milan today |
| `categories` | `[]` | **Add 5–6** from §16.5 recommendation |
| `eventTracks` | 6 entries (Intelligent Reasoning, Agentic Workflows, Enterprise Utility, Vultr, Google Track, Speechmatics) | ✓ no change |
| `techIn` | `[Vultr, Speechmatics api]` | **Add** `Gemini 3 Flash`, `AI Studio` |
| `social_media_post_link_*` | all empty | Leave empty unless we post on Twitter/LinkedIn for the Speechmatics social bonus |
| `imageLink` | `null` | Upload `submission/afterglow-cover.png` |
| `videoLink` | `null` | Upload `submission/afterglow-pitch.mp4` (in regeneration) |
| `presentationLink` | `""` | Upload `submission/afterglow-slides.pdf` |
| `repoLink` | `null` | `https://github.com/Cleversoft-IT/afterglow` |
| `demoPlatform` | `null` | "Custom — Vultr Cloud Compute via Coolify" (or closest select option) |
| `demoUrl` | `null` | `https://afterglow.cleversoft.it` |
| `additionalInfo` | `null` | Optional — drop the §3 market-sizing notes here. |
| `isDraft` | `true` | Will flip to `false` when we click Submit. |

Team identity (from the draft): team slug `claudio-opuscoli`,
team picture / Discord channel already set. Draft was first created
on **2026-05-15 13:25 UTC** and last touched on
**2026-05-18 21:36 UTC** (edit version 5).

---

## 17. Decisions — final values to paste into the form

> Living checklist written **2026-05-19** while inspecting the live
> form together. Each row is one of:
>
> * **[DECIDED]** — value is locked, paste verbatim.
> * **[PROPOSED]** — value drafted, awaiting team sign-off before
>   paste-in.
> * **[OPEN]** — still needs discussion.
>
> When a row flips to DECIDED, do not silently revise it later —
> open a new discussion. The point of this section is to stop the
> "I changed my mind in the form and forgot to update the doc"
> failure mode.

### 17.1 `title` — [DECIDED]

```
Afterglow — Stay in the moment
```

* 30 / 50 chars.
* Why over `Afterglow — we handle the after`: the half-claim is more
  evocative (Apple/Linear-flavored) and pairs cleanly with the
  short description which already says "we handle the after" — no
  need to duplicate.
* Why over the bare `Afterglow` (9 chars): the listing card on
  lablab is a sea of single-word project names; a half-line of
  poetic copy makes us scan-stop without spelling out the product
  (the short description does that).
* Server currently has `Afterglow` — update on Page 1.

### 17.2 `shortDescription` — [DECIDED]

```
A drop-in phone for small businesses. The human stays on the call — the moat. After they hang up, an agentic AI loop extracts the booking, runs the follow-ups (WhatsApp, CRM), writes the next-call briefing. Stay in the moment. We handle the after.
```

* 247 / 255 chars, well over the 50-char minimum.
* Same copy as §3. Server currently empty — fill on Page 1.

### 17.3 `description` — [DECIDED]

> 1783 / 2000 chars (headroom 217). Hybrid structure: pitch paragraph
> → use-case paragraph → technical loop paragraph → stack/license
> line → USP + claim. Decided with the team on 2026-05-19 after
> rejecting (a) a longer narrative-only variant and (b) a
> tech-first variant.

```
A call ends. Something else begins. A booking to enter, a confirmation to send, an allergy to remember, a briefing for the next call. The current AI answer is to replace the human with a voice agent — but the reason a customer dials a small business is the human. Replace the human, kill the moat. We don't replace the call. We replace the after.

Afterglow is a drop-in phone app for booking-driven SMBs — restaurants, dental clinics, body shops, hair salons, dog groomers, garages, tutoring studios. The operator picks up live. The moment they hang up, an agentic loop runs in the background and lands a structured extraction + a one-sentence next-call briefing on the customer's record. The next time the same number calls, the operator's screen already knows the context — gluten-free, anniversary, Bichon Frisé, previous diagnosis — without anyone typing.

Under the hood: Speechmatics transcribes with diarization on; a Gemini 3 Flash agent in Google ADK runs up to 12 turns over the transcript, calling typed tools — re-read a segment, query the customer's prior-call memory through Vultr's Vector Store via Serverless Inference RAG, execute booking / WhatsApp / calendar / payment / CRM / review action tools whose payloads are validated against a per-template JSON Schema, flag for review, or finalize. Each action result feeds back into the next turn so the model can self-correct, capped at two attempts. The full reasoning trail is a first-class UI surface, auditable turn by turn.

Single-tenant. Deployed on Vultr (Cloud Compute + Managed Postgres + Vector Store + Serverless Inference) through Coolify, auto-deploy on push to main. MIT.

USP vs CallRail / Aircall / Dialpad AI: we don't replace the human. We replace the after. Stay in the moment. We handle the after.
```

Sign-off check before paste: re-count chars after any tweak, target
≤ 1990 so the form validator doesn't bite on a stray space.

### 17.4 `submissionType` — [DECIDED]

* **`Onsite`** — the team (4 people) is at Fiera Milano Rho today,
  2026-05-19.
* Server already has `ONSITE`. ✓ no change.

### 17.5 `categories` — [DECIDED]

> Multi-select, required (1+). All 7 entries below are verified
> verbatim against the 119-option catalog in §16.5.
> Decided 2026-05-19: functional-five plus the two seed verticals
> with the largest catalog match (dentist → Healthcare, restaurant
> → Food). Body shop has no direct match (`Automotive` would skew
> the read toward car-tech, not auto-repair SMBs) so we skip it.

| Pick | Why |
|---|---|
| `Customer Support` | Most accurate single label — post-call extract + follow-ups is exactly the customer-support workflow. |
| `Voice Assistant` | We ingest voice; the agent is invoked by a phone call. Different from "Assistant" because we are explicitly voice-led. |
| `Communication` | The phone is the communication channel; covers WhatsApp / email follow-ups too. |
| `Productivity` | The operator UX is a productivity surface (zero-typing, briefing-already-there). |
| `Business` | Generic SMB tag — helps discoverability on the lablab apps directory after the event. |
| `Healthcare` | Covers the dentist preset (one of the 3 seed templates). |
| `Food` | Covers the restaurant preset (one of the 3 seed templates). |

Deliberately **not picked**:

* `Automotive` — body shop preset would map here, but the label
  reads as "car-tech / self-driving" in this catalog and skews the
  read away from "SMB auto-repair".
* `Chatbot`, `Assistant` — Afterglow is not a chatbot; the
  operator-Customer conversation is a real human phone call.
* `*-Raise` / `Internet of Agents` / `Qubic*` / `Kraken*` — those
  are reserved for partner sub-tracks we don't compete in.

### 17.6 `tracks` — [DECIDED]

* Keep the 6 already selected: `Intelligent Reasoning`,
  `Agentic Workflows`, `Enterprise Utility`, `Vultr`, `Google Track`,
  `Speechmatics`.
* Do **not** add `Multimodal Intelligence` (we ingest audio but the
  agent operates on transcript text — overreach).
* Do **not** add `Collaborative Systems` (single agent, not
  multi-agent collaboration).

### 17.7 `technologies` — [DECIDED]

Final tag set (5 entries):

1. `Vultr` — already in server draft. ✓
2. `Speechmatics api` — already in server draft. ✓
3. **`Gemini 3 Flash`** — ADD. Primary Gemini tag, closest available
   label to the production model `Gemini 3.1 Flash Lite`.
4. **`Gemini AI`** — ADD. Secondary, generic-Gemini bucket — in case
   the Google judging filter looks for the umbrella label rather
   than the specific model.
5. **`AI Studio`** — ADD. Closest publicly Google-branded label for
   the ADK surface (no `Google ADK` exists in the catalog).

Rationale for the triple-Google approach: per Joan's Q&A on 2026-05-13,
untagged tech is not judged. Each of the three Google labels covers
a different judging-filter shape (specific model, family, surface)
so we maximize coverage at zero cost. Risk of "keyword stuffing"
read is low — three Google labels for a project that genuinely uses
Gemini-via-ADK is honest, not spammy.

Drop from previous wishlist (they are NOT in the lablab catalog and
cannot be tagged): `Google ADK`, `Vultr Vector Store`,
`Vultr Serverless Inference`, `PostgreSQL`, `Python`, `FastAPI`,
`React Native`, `Expo`, `TypeScript`, `MIT License`.

### 17.8 `imageLink` / `videoLink` / `presentationLink` — [DECIDED]

| Field | File | Status |
|---|---|---|
| `imageLink` | `submission/afterglow-cover.png` (1920×1080 PNG, 286 KB) | ready |
| `videoLink` | `submission/afterglow-pitch.mp4` | **in regeneration** — wait |
| `presentationLink` | `submission/afterglow-slides.pdf` (10 pages, 1.40 MB) | ready |

### 17.9 `repoLink` — [DECIDED]

```
https://github.com/Cleversoft-IT/afterglow
```

* Verified public + MIT + `main` is default branch + pushed today.

### 17.10 `demoPlatform` — [OPEN — depends on whether field is a free-text or a select]

* Preferred value (free-text):
  `Custom — Vultr Cloud Compute via Coolify`
* If the form forces a select (we'll see on Page 3): pick `Vultr`
  if present; otherwise `Custom` / `Other`.
* Server is currently `null`.

### 17.11 `demoUrl` — [DECIDED]

```
https://afterglow.cleversoft.it
```

* The landing page that iframes the operator app. Single canonical
  URL for judges.

### 17.12 `additionalInfo` — [DECIDED]

> Hybrid format: 2 lines of market sizing (Business Value criterion,
> 25%) + 2 lines of agentic proof-points (Application of Technology
> criterion, another 25%). Each half is one paragraph the judge can
> verify in 60 seconds without leaving the form.

```
Market: ~478k Italian booking-led SMBs, ~185k phone-led, €50/seat/mo → ~€110M Italian SAM/year baseline. Expansion: FR · DE · UK · ES · US service economy.

Agentic, verifiable in 60s: /admin/rag-probe returns non-zero input_tokens (Vultr billing); any completed-call audit log shows a validation_failed → re-emit → finalize turn chain; each ExecutedAction carries payload.agent_turn for deterministic correlation.
```

(414 chars.)

### 17.13 `social_media_post_link_1..5` — [DECIDED]

* Leave **all 5 empty.** We aren't competing in the Kraken Social
  Engagement track and we don't have a public X / LinkedIn launch
  thread that benefits us in the judging. (If a teammate posts a
  launch tweet later, we can paste the URL on Page 1 before the
  17:00 cut-off.)

### 17.14 `kraken_api_key_read_only` + `kraken_account_id_username` — [DECIDED]

* Leave **both empty.** We are not in the Kraken track.

### 17.15 Submit timing — [DECIDED]

1. Fill Pages 1 + 3 ASAP today **without waiting for the video**.
   The form supports `save draft` per Joan, so we get a green
   "submission visible" state on the public page even before the
   MP4 lands.
2. As soon as `afterglow-pitch.mp4` is ready, return to Page 2,
   upload, click Submit.
3. Sanity-check the public submission page before 16:50 CEST.

---

*End of bible. If you find anything stale, fix the code or fix this
file — whichever is wrong.*
