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

---

## 1. Identity card

| Field | Value |
|---|---|
| **Project name** | Afterglow |
| **Tagline (≤8 words)** | The dialer that takes notes for you |
| **One-liner (≤25 words)** | A phone app for small businesses where humans take calls and AI extracts data, executes follow-ups, and writes the next-call briefing. |
| **Repo** | `https://github.com/sepa85/hackaton-lablab` (public, MIT) |
| **Backend** | `https://api.95-179-245-107.sslip.io` |
| **Operator app (Expo web)** | `https://app.95-179-245-107.sslip.io` |
| **Landing + iframe demo** | `https://demo.95-179-245-107.sslip.io` |
| **Tracks (lablab.ai)** | Intelligent Reasoning · Agentic Workflows · Enterprise Utility · Multimodal Intelligence |
| **Partner tracks targeted** | **Vultr** · **Google (Gemini)** · **Speechmatics** |
| **Partner tracks NOT targeted** | Kraken (out-of-domain) · Featherless (we use Gemini, not Featherless catalog) |
| **License** | MIT (`afterglow/LICENSE`) |
| **Team size** | 4 |

The three live URLs above are the only "production" we have, and the
only one judges will see. There is no separate staging or marketing
environment.

---

## 2. The pitch narrative

### The problem (60 seconds)

Small booking-driven businesses — restaurants, dental clinics, body
shops — run their day on phone calls. A booking, an allergy, a callback
request, a complaint: the operational reality of the business is spoken
into a phone for 60 seconds and then has to be remembered, typed into
a CRM, and turned into a follow-up. Post-its and short-term memory
don't scale; the staff is in the room, talking to a customer in
front of them, and the next call is already ringing.

The "AI receptionist" wave answers this by replacing the human with a
voice agent. That solves the wrong problem. The reason customers call
a small business instead of clicking a form is **the human**. Replace
the human with a bot and you kill the only moat the small business has.

### The solution

Afterglow keeps the human on the phone and puts the AI **after** the
call. The operator picks up, talks, hangs up. Behind the scenes:

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
fighting it. The operator's UX is identical to the Pixel Phone app —
because we built it that way on purpose. The AI work is auditable
turn-by-turn in a side panel for anyone curious enough to look, and
invisible for anyone who isn't.

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

The judge's persona is **the operator of a small Italian restaurant**
running the default "Restaurant — Standard booking" template.

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

---

## 3. lablab.ai form — pre-filled fields

> Copy each block verbatim into the lablab.ai submission form. Character
> counts already verified.

### Project title (max 50 characters)

```
Afterglow — the dialer that takes notes for you
```

(47 chars, within the 50-char limit.)

### Short description (max 255 characters)

```
A drop-in phone for small businesses. The human handles every call live; an agentic AI loop runs after the call to extract fields, execute follow-ups (booking, WhatsApp, CRM), and write a next-call briefing so nothing said on the phone is ever lost.
```

(249 chars.)

### Long description (min 100 words)

```
Afterglow is a drop-in replacement for the system Phone app, designed for small booking-driven businesses (restaurants, dental clinics, body shops). The operator picks up every call live — humans are the moat for small businesses, and we deliberately do not replace them with a voice agent.

The intelligence runs AFTER the call. A Gemini 3.1 Flash Lite agent, hosted in Google ADK, runs a multi-turn loop (up to 12 turns) over the diarized Speechmatics transcript. It decides which tools to call: re-read transcript segments, query the customer's prior-call memory through Vultr's Vector Store and Serverless Inference RAG, execute one of the template's action tools (booking, WhatsApp, calendar, payment, CRM, review), flag for human review, or finalize. Each action runs inline with typed Pydantic payloads built dynamically from the template's JSON Schema; the result feeds back into the next turn so the model can self-correct, capped at two attempts per action.

The output is a structured extraction (fields, intent, sentiment, urgency, language) plus a one-sentence next-call briefing written to the Customer record. The next time the same phone number calls, the operator's screen already knows the context — gluten-free, anniversary, license plate, previous diagnosis — without the operator having to type anything.

Single-tenant by design. Deployed on Vultr (Cloud Compute + Managed Postgres + Vector Store + Serverless Inference) through Coolify with auto-deploy on push to main. The full agent reasoning trail is exposed as a first-class UI element on every call detail, so the AI work is auditable turn by turn.

Market focus: Italy first. Our reference sizing covers ~478k booking-led businesses across restaurants, hair salons, beauty centers, auto repair, dental practices and hotels. The more realistic phone-led subset is ~185k businesses that plausibly still manage bookings through the owner or staff's phone/WhatsApp, led by hair salons (~62k), restaurants (~58.6k), auto repair (~30.7k), beauty centers (~21.8k) and dental practices (~10.8k). At ~€50/month per seat, that is an initial Italian SAM of roughly €110M/year before expansion into other EU markets. USP vs incumbents (CallRail, Aircall, Dialpad AI): we don't try to replace the human, we augment them with persistent memory and audited automation. Roadmap (post-hackathon): SIP trunk integration, on-call WhatsApp suggestions, multi-language quality bar, real CRM connectors swapping the mock registry.
```

(370 words.)

### Market sizing notes for judges

Use this if the lablab form has an "Additional Information" field or if a
judge asks where the TAM/SAM numbers come from.

The market sizing above is derived from the internal deep-research report
`tmp/deep-research-report (2).md`. It uses Italian source categories such
as FIPE/InfoCamere, ISTAT, Federalberghi, Cosmetica Italia, FNOMCeO,
Key-Stone, Confartigianato/CNA, AGCOM and UPB.

Key point: we do **not** count every SMB as equally reachable. The hard
activity base is ~478k Italian booking-led businesses across restaurants
(195,471), hair salons (~100k), auto repair (73k), dental practices
(~38.5k, inferred from market value / average practice revenue), beauty
centers (~38.3k), and hotels (32,943). The more relevant serviceable
market is the **phone-led subset**: businesses likely still coordinating
appointments through personal phones, WhatsApp, or lightweight manual
processes. Using sector-specific midpoint estimates, that subset is
~185k businesses: hair salons ~62k, restaurants ~58.6k, auto repair
~30.7k, beauty centers ~21.8k, dental practices ~10.8k, hotels ~1.6k.

Commercial ranking from the research: hair salons first, then auto
repair, beauty centers, dentistry, restaurants, hotels. Restaurants are
the largest raw cluster, but the report treats them as a mixed-fit volume
market because walk-ins, fixed lines and booking platforms are common.
Hair and beauty are cleaner "personal phone + recurring appointment"
targets; dentistry has fewer logos but higher likely ARPU; auto repair
has strong phone friction around slots, emergencies and rescheduling.

### Technology tags (must tag every partner you want to be judged by)

* `Google Gemini`
* `Google ADK`
* `Vultr`
* `Vultr Serverless Inference`
* `Vultr Vector Store`
* `Speechmatics`
* `PostgreSQL`
* `Python`
* `FastAPI`
* `React Native`
* `Expo`
* `TypeScript`
* `MIT License`

### Tracks

Tag at minimum: **Intelligent Reasoning**, **Agentic Workflows**,
**Enterprise Utility**, **Multimodal Intelligence** (we ingest audio).

### Cover image spec

* Aspect ratio **16:9** (lablab recommendation).
* Source asset: a screenshot of the call detail with the Agent Reasoning
  Trail expanded on the right, customer card on the left, status chip
  `completed`. Captured on `https://app.95-179-245-107.sslip.io`.
* Add the wordmark "**afterglow**" bottom-left and "AI Agent Olympics
  2026 — Milan AI Week" bottom-right in a thin sans-serif.
* Export as PNG, target ≤500 KB.

### Participation type

* **Online** (no team member on-site at Fiera Milano Rho).

---

## 4. Video pitch script — 5 minutes scene-by-scene

**Constraints from lablab** (`hackathon-docs/06-what-to-submit.md`):

* MP4, ≤5 min, ≤300 MB. Upload **direct** on lablab (no YouTube, no
  Drive). Problem→solution must land in the first 60 seconds.

> The script below uses verbatim narration in English. Adjust mouth-feel
> in delivery but keep claim-by-claim the same beats — the timing budget
> assumes ~140 words per spoken minute.

### Scene 1 — 0:00–0:15 · Hook

**Visual:** the Afterglow Home screen on the Expo web app, scrolling
the Recents list. A booking call comes in: the Pixel-style full-screen
incoming-call UI takes over.

**Narration (verbatim):**

> "This is the phone app on every restaurant counter in Italy. A call
> comes in. Someone books a table. Sixty seconds later, the call is
> over — and the only record of what was said is in the operator's
> head. Until the next post-it goes missing."

### Scene 2 — 0:15–0:45 · The problem

**Visual:** split screen. Left: a chaotic restaurant counter (stock
clip or live capture). Right: a competitor "AI receptionist" homepage,
hero "Replace your front desk with AI" — dim it.

**Narration:**

> "The current AI answer to this is to replace the human with a voice
> agent. That solves the wrong problem. The reason customers call a
> small business instead of clicking a form is the human. Replace the
> human with a bot, and you kill the only moat the business has.
>
> Afterglow takes the opposite bet. Keep the human on the phone. Put
> the AI after the call."

### Scene 3 — 0:45–1:30 · The product, in one sentence

**Visual:** zoom into the demo URL `demo.95-179-245-107.sslip.io`.
Scroll past the hero to the live iframe demo. Then click into the app.

**Narration:**

> "Afterglow is a drop-in phone app for small booking-driven businesses.
> The operator picks up every call live. The moment they hang up, an
> agentic AI loop runs in the background: it transcribes the call with
> Speechmatics, reads the diarized transcript turn by turn through
> Google ADK and Gemini, queries the customer's prior-call memory from
> Vultr's Vector Store, executes the follow-up actions — booking,
> WhatsApp, calendar, payment, CRM, review — and writes a one-sentence
> next-call briefing onto the customer's record."

### Scene 4 — 1:30–2:30 · Live end-to-end run (existing customer)

**Visual:** click **Drawer → Test simulator → Call from existing
customer**. The incoming-call screen takes over, audio plays (the
real Speechmatics-generated MP3). Hang up. The Home screen now shows
the new call with a progress chip. Watch it move through `transcribing
→ analyzing → completed`. Tap the call. The right-hand **Agent Reasoning
Trail** is open.

**Narration:**

> "Watch this. Mark Ross — a returning customer — is calling. The audio
> here is real, generated by Speechmatics TTS, so when it lands in the
> backend it gets transcribed by the real Speechmatics batch API, with
> diarization on.
>
> Now look at the trail on the right. Turn one: the agent reads the
> transcript header. Turn two: it queries the Vultr Vector Store —
> notice it asks a specific question, 'does Mark Ross have allergies
> on file?', not a generic catch-all. The RAG answer comes back: 'yes,
> gluten-free'. Turn three: the agent calls `booking.create` with a
> typed payload that's validated against the template's JSON Schema.
> Turn four: it calls `whatsapp.send_confirmation`. Turn five: it
> finalizes — emits the extracted fields, intent, sentiment, language,
> urgency, and the next-call briefing.
>
> Total: five turns, two thousand tokens, six seconds end-to-end."

### Scene 5 — 2:30–3:15 · Self-correction (the agentic claim)

**Visual:** open a different completed call where the trail shows an
action `validation_failed` followed by a re-emit. Hover the failed
attempt; the result panel expands.

**Narration:**

> "This is what makes it agentic instead of a single LLM call. Here
> the model tried to create a booking with party size zero, the
> deterministic validator rejected it — `validation_failed:
> party_size required`. The very next turn, the agent re-reads the
> transcript at the relevant span, finds 'four people', and re-emits
> the action with the corrected payload. We cap retries at two attempts
> per action, so the loop can never thrash. Mutating actions that
> already executed cannot be replayed."

### Scene 6 — 3:15–4:00 · Memory and the next call

**Visual:** open Mark Ross's customer card. Point at the **briefing**
at the top. Then trigger a second simulated call from the same number
and show how the briefing surfaces on the operator's screen during
the call.

**Narration:**

> "Here's the briefing the agent wrote at the end of the last call.
> When the same number calls again, the operator sees it on the screen
> before picking up. The next call already has context — no typing,
> no second tab, no waiting on a CRM lookup. That's what 'after the
> call' was for: building memory that persists across calls."

### Scene 7 — 4:00–4:30 · Templates and adaptability

**Visual:** switch the active template via **Drawer → Templates →
pick Dentist**. Open the wizard and show that any small-business
operator can describe their domain in natural language and the wizard
produces a new template with action types, JSON Schema, and even two
fresh demo MP3s (existing + new caller) generated by Speechmatics TTS.

**Narration:**

> "Three preset templates ship with the demo: restaurant, dentist,
> body shop. Each defines its own field schema and action set, and
> Gemini reshapes the agent's tool surface accordingly. For any other
> small business, the wizard — itself an agent — interviews the user
> in two to five questions and produces a working template, plus two
> fresh demo audio scripts rendered through Speechmatics TTS Preview.
> Adapting the product to a new vertical is a thirty-second
> conversation, not a release."

### Scene 8 — 4:30–5:00 · Stack, deployment, close

**Visual:** open the README. Pan across the partner pills on the demo
landing. Close on the team photo.

**Narration:**

> "Built on Vultr — Cloud Compute, Managed Postgres, Vector Store,
> Serverless Inference RAG, all in the same audit trail — Google ADK
> with Gemini 3.1 Flash Lite, and Speechmatics for batch transcription
> and TTS. MIT-licensed, deployed in Coolify on a single Vultr VM with
> auto-deploy on push. Live demo at demo dot 95-179-245-107 dot sslip
> dot io. The repo is on GitHub.
>
> Afterglow. The dialer that takes notes for you."

**End screen** (still, 2 seconds): wordmark + demo URL + GitHub link.

### Recording tips

* Record at 1080×1920 portrait if you want the phone-frame iframe to
  fill the screen; or 1920×1080 landscape if you want browser chrome
  + dev panels in the shot. **Pick one and stay there.**
* Use the existing `afterglow/scripts/record-demo.cjs` (Playwright)
  for the scripted scenes; voiceover dubbed in post.
* Pre-warm the backend right before recording: hit
  `/api/v1/admin/rag-stats` to confirm preseed chunks count, then
  load Home so the cold start doesn't show.
* Resolution priority: **legibility of the Agent Reasoning Trail**
  text matters more than 4K. Bump font scale in Chrome if needed
  before recording.

---

## 5. Slide deck outline

**Constraint:** PDF, one-pager allowed, 2–3 sentences per slide max
(`hackathon-docs/06-what-to-submit.md`). 8 slides is the right size.

### Slide 1 — Title

* "**afterglow** — the dialer that takes notes for you."
* Subtitle: "AI Agent Olympics · Milan AI Week 2026 · MIT".
* Team logo strip (Vultr · Google ADK · Speechmatics).

### Slide 2 — The problem

* "Small businesses run on phone calls. The data spoken on those calls
  evaporates."
* "AI receptionists kill the only moat small businesses have: the
  human."

### Slide 3 — The product

* "Afterglow is a drop-in phone app. The human takes every call live.
  An agentic AI loop runs **after** the call."
* Three icons: extract · execute · remember.

### Slide 4 — How it works (architecture diagram)

* The ASCII diagram from §7 below, redrawn as a clean architecture
  diagram. Speechmatics → Postgres + Gemini/ADK loop → Vultr RAG &
  Vector Store → Customer briefing.

### Slide 5 — Why it's agentic

* "Multi-turn loop, typed tool surface, self-correction on tool errors,
  RAG-on-demand."
* Screenshot of an Agent Reasoning Trail with a `validation_failed`
  → re-emit → `executed` sequence.

### Slide 6 — Partner integration depth

* Vultr: Postgres + Vector Store + Serverless Inference RAG + Cloud
  Compute (4 surfaces, one audit log).
* Google: Gemini 3.1 Flash Lite via ADK 1.18 + structured output +
  dynamic typed tool surface.
* Speechmatics: batch STT with diarization on + TTS Preview for demo
  audio (real generated voices, not stock).

### Slide 7 — Business value

* Italy-first TAM/SAM: ~478k booking-led businesses across restaurants,
  hair, beauty, auto repair, dental and hotels; ~185k estimated
  phone-led subset; ~€110M/year initial SAM at €50/month.
* Beachhead ranking from research: hair salons → auto repair → beauty
  centers → dentistry → restaurants. Restaurants remain the volume
  wedge already shown in the demo.
* USP table vs CallRail / Aircall / Dialpad AI: "we augment the human,
  we don't replace them."
* Pricing: ~€50/seat/month target; higher-ARPU packaging for dentistry
  and multi-location service businesses.

### Slide 8 — Live demo + repo

* QR code to `https://demo.95-179-245-107.sslip.io`.
* QR code to GitHub repo.
* Big call-out: "Try it now — Drawer → Test simulator → Call from
  existing customer."

### Slide 9 (optional, one-pager OK) — Future work

* Real CRM connectors (swap mock registry).
* SIP trunk for full real-phone handling.
* Voice-aware operator suggestions during the call (read-only AI on
  the operator's screen, not on the line).
* Multi-language quality bar.

---

## 6. Judge cheat sheet — live demo

> Print or pin this section. This is the click-path a judge should
> follow if they open the demo cold.

### Three live URLs

1. **`https://demo.95-179-245-107.sslip.io`** — landing page, the
   marketing front door. Scroll to the **"Live demo"** section to see
   the operator app in an iframe (390×845 phone frame). On mobile the
   iframe collapses to a CTA — click it to open the app full-screen.
2. **`https://app.95-179-245-107.sslip.io`** — the operator app
   directly (Expo web build). This is where the work happens.
3. **`https://api.95-179-245-107.sslip.io`** — the API. Open
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

* `GET https://api.95-179-245-107.sslip.io/api/v1/admin/rag-stats` —
  returns `{preseed_chunks: N, runtime_chunks: M, collection: "..."}`.
  Confirms the Vultr Vector Store is live and pre-populated.
* `GET https://api.95-179-245-107.sslip.io/api/v1/admin/rag-probe?phone=+15552223344`
  — issues a real RAG query against the Vultr collection for Sophie
  Walker. Returns the RAG response **and** `input_tokens` from the
  Vultr Inference response. Non-zero tokens mean the call was billed
  to our Vultr account — not a stub; `hit=true` proves the preseeded
  memory store is returning customer facts.
* `GET https://api.95-179-245-107.sslip.io/api/v1/audit?call_id=<id>`
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

> Compact version. Full architecture lives in `afterglow/docs/ARCHITECTURE.md`
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
| **Cloud Compute + Coolify** | The VM hosting all 3 services. IP `95.179.245.107`. Auto-deploy on push to main. | `https://app.95-179-245-107.sslip.io` loads. |
| **Managed Postgres 16** | System of record. Schema mirrored locally by Alembic in `backend/entrypoint.sh`. | Any call detail renders DB-backed data. |
| **Vector Store** | `customer_memory_chunks` table mirrors Vultr items. Preseed task populates it at backend boot with `chunk_metadata.preseed=true`. | `GET /api/v1/admin/rag-stats` returns `{preseed_chunks: N, runtime_chunks: M}`. |
| **Serverless Inference RAG** | `POST /v1/chat/completions/RAG` against `MiniMaxAI/MiniMax-M2.7`. Exposed to the agent as the `lookup_customer_memory` tool. | `GET /api/v1/admin/rag-probe?phone=+15552223344` returns `hit=true`, the RAG response, and `input_tokens > 0`. |

**Code:** `afterglow/backend/app/integrations/vultr_inference.py`,
`afterglow/backend/app/tasks/vector_preseed.py`,
`afterglow/backend/app/agents/tools/memory_tool.py`.

### Google — **Gemini via ADK**

* **Model:** `gemini-3.1-flash-lite` (pinned in
  `afterglow/backend/app/config.py:34-35`).
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

**Code:** `afterglow/backend/app/integrations/gemini_adk.py`,
`afterglow/backend/app/agents/call_agent.py`,
`afterglow/backend/app/agents/wizard_chat.py`,
`afterglow/backend/app/agents/briefing_regenerator.py`.

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

**Code:** `afterglow/backend/app/integrations/speechmatics.py`,
`afterglow/backend/app/integrations/speechmatics_tts.py`,
`afterglow/scripts/generate_demo_audio.py`.

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

The four criteria from `hackathon-docs/07-judging-criteria.md` weight
equally (25% each). For each, this is our explicit evidence plus the
video timestamp where it lands.

### Application of Technology (25%)

| Evidence | Where in code | Where in video |
|---|---|---|
| Multi-turn agent loop with typed tool surface | `agents/call_agent.py` · `agents/tools/*.py` | Scene 4 (1:30–2:30) |
| Self-correction on tool errors | `agents/tools/action_tool.py:117-164` | Scene 5 (2:30–3:15) |
| RAG-on-demand as a tool decision | `agents/tools/memory_tool.py` | Scene 4 (RAG turn) |
| Vultr 4-surface integration (Compute · Postgres · Vector · Inference) | §8 above | Scene 8 (closing partner pills) + cheat-sheet `rag-probe` |
| Gemini structured output via ADK function calling | `integrations/gemini_adk.py` · `agents/tools/action_tool.py:107-115` | Scene 4 + Scene 5 |
| Speechmatics diarization fed into transcript tools | `integrations/speechmatics.py` · `agents/tools/transcript_tool.py` | Scene 4 |

### Originality (25%)

| Evidence | Where in code | Where in video |
|---|---|---|
| Counter-bet thesis: keep the human, run AI after the call | product design | Scene 2 (0:15–0:45) |
| Drop-in Pixel-style phone app aesthetic for an AI product | `afterglow/app/` Expo build | Scenes 4 + 6 |
| Agent reasoning trail as a first-class UI surface, not a buried log | `afterglow/app/components/AgentReasoningTrail.tsx` | Scene 4 |
| `needs_review` as terminal status, not silent fallback | `agents/orchestrator.py:397-411` | Cheat-sheet demonstration |
| Template wizard as a Gemini-driven 2-to-5-question interview | `agents/wizard_chat.py` | Scene 7 |
| Per-template Speechmatics TTS dual-scenario MP3 generation | `integrations/speechmatics_tts.py` | Scene 7 |

### Business Value (25%)

| Evidence | Where |
|---|---|
| Concrete persona (small-restaurant operator) with daily friction described in operator-language, not LLM-speak | §2 + Scene 2 |
| TAM/SAM with named markets, source methodology and pricing band | §3 Long Description + Market sizing notes + Slide 7 |
| USP table vs CallRail / Aircall / Dialpad AI ("we don't replace the human") | Slide 7 + Scene 2 |
| Concrete templates for three real verticals out of the box (restaurant · dentist · bodyshop) plus wizard-generated for any other | §8 + Scene 7 |
| Auditable AI work (every action undoable where the catalog allows) — addresses the small-business operator's #1 AI concern (control) | UI: call detail Undo button · `INTERNAL_REVERTERS` |
| Single-tenant model = clear sales motion, no multi-tenant complexity | architecture decision in `CLAUDE.md` constraint #1 |

### Presentation (25%)

| Evidence | Where |
|---|---|
| Problem → solution lands in the first 60 seconds (lablab tip) | Scene 1 (0:00–0:15) → Scene 2 (0:15–0:45) |
| Video ≤5 min, MP4, ≤300 MB, **uploaded directly to lablab** (not YouTube/Drive) | Submission checklist §13 |
| Slide PDF with 2–3 sentences per slide (lablab tip) | §5 outline |
| README reproducible from `afterglow/README.md` | repo root |
| Architecture diagram in the README and in the slides | §7 + Slide 4 |
| Live demo URL that works (cheat-sheet click path) | §6 |
| Public GitHub repo, MIT-licensed | repo root + `afterglow/LICENSE` |

### Speechmatics bonuses (non-quantified, but stated by Edgars)

* **Multilingual:** ✅ STT `language="auto"`, bilingual EN summarizer in `_persist_memory`.
* **Creative diarization:** ✅ speaker-aware transcript tools.
* **Voice SDK:** ✗ we use the batch SDK; trade-off declared honestly in the pitch.

---

## 11. Real-vs-mocked — the honest table

This is the table to **lead with** if anyone asks. Showing this matrix
proactively builds trust; trying to hide it backfires.

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
| Original work | ✅ All code written by the team during the build week. Single fork acknowledgement: the project structure was informed by the lablab official tutorial baseline (`hackathon-docs/14-tutorial-gemini-vultr-document-agent.md`) but no code is copied verbatim. |
| Open source | ✅ Public GitHub repo. |
| MIT License | ✅ `afterglow/LICENSE` from day 1. |
| No GPL/AGPL dependencies | ✅ Audited. Three notable frontend deps: `react-native-paper` (MIT), `@material/material-color-utilities` (Apache-2.0), `@react-navigation/drawer` (MIT). Backend: FastAPI (MIT), SQLAlchemy (MIT), `speechmatics-batch` (MIT), `google-genai` (Apache-2.0), `httpx` (BSD), `pydantic` (MIT). All permissive. |
| AI usage disclosure | Not required by lablab terms (`hackathon-docs/08-hackathon-details.md`). The repo contains AI-assistant config files openly. |
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
"Submit" (`hackathon-docs/06-what-to-submit.md` lines 60–67).
**Submit a complete draft ≥24h before the deadline** to insure
against last-second upload failures, then refine.

---

## 13. Pre-flight submission checklist

Run through this list in order. Do not check a box you haven't visually
verified.

### Artifacts to produce

* [ ] **Video pitch MP4** — ≤5:00, ≤300 MB, 1080p min. Filename:
      `afterglow-pitch.mp4`. Recorded per the §4 script.
* [ ] **Slide PDF** — ~9 slides per §5. Filename: `afterglow-slides.pdf`.
      Max 5 MB.
* [ ] **Cover image** — 16:9 PNG, per §3 spec. Filename:
      `afterglow-cover.png`. Max 500 KB.

### Live infrastructure

* [ ] `https://api.95-179-245-107.sslip.io/health` returns 200.
* [ ] `https://app.95-179-245-107.sslip.io` loads, Home renders with
      the busy-week seed data.
* [ ] `https://demo.95-179-245-107.sslip.io` loads, iframe shows the
      app, "How to get the most out of this demo" modal works.
* [ ] `GET /api/v1/admin/rag-stats` returns `preseed_chunks > 0`.
* [ ] `GET /api/v1/admin/rag-probe?phone=+15552223344` returns
      `hit=true` and `input_tokens > 0` (proves real Vultr billing
      and preseeded memory retrieval).
* [ ] Trigger a fresh simulated call — verify it lands `completed`
      within 15 seconds.

### Repo hygiene

* [ ] Repo is **public** on GitHub.
* [ ] `afterglow/LICENSE` is MIT.
* [ ] `afterglow/README.md` includes the architecture diagram, the
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
* [ ] Participation Type: **Online**.
* [ ] Cover Image: upload `afterglow-cover.png`.
* [ ] Video Presentation: upload `afterglow-pitch.mp4` **directly to
      lablab** (not YouTube/Drive).
* [ ] Slide Presentation: upload `afterglow-slides.pdf`.
* [ ] GitHub Repo URL: filled.
* [ ] Application URL: `https://demo.95-179-245-107.sslip.io`.
* [ ] Demo Application Platform: "Custom — Vultr Cloud Compute via
      Coolify".

### Submit ≥24h before deadline

* [ ] First **Submit** clicked by **2026-05-18 17:00 CEST**.
* [ ] Sanity-check the public submission page renders correctly.
* [ ] Edit until 2026-05-19 17:00 CEST as needed.

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
  `afterglow/docs/future-ideas.md`).
* **Multi-tenant SaaS shell** — explicitly out of scope (`CLAUDE.md`
  constraint #1 keeps single-tenant).
* **PII redaction** — designed and then deliberately removed
  2026-05-17 because it harms operator usefulness ("the customer is
  celiac" is the point, not a leak); see `afterglow/docs/future-ideas.md`
  §4 for the archived design.
* **Real-time Speechmatics Voice SDK** — only useful when we add
  on-call assistance; deferred until then.

---

## 15. Source-file reference index

If you need to verify any claim in this document, here is the
authoritative source for each topic.

### Architecture & pipeline

* `afterglow/docs/ARCHITECTURE.md` — 916 lines, the canonical
  architecture document.
* `afterglow/backend/app/agents/orchestrator.py` — the pipeline glue.
* `afterglow/backend/app/agents/call_agent.py` — the agent loop entry.
* `afterglow/backend/app/agents/tools/` — the typed tool surface
  (action_tool, control_tool, memory_tool, transcript_tool, turn).
* `afterglow/backend/app/executors/action_executor.py` — deterministic
  validator + MOCK/INTERNAL dispatcher.
* `afterglow/backend/app/integrations/gemini_adk.py` — ADK runner
  wrapper.
* `afterglow/backend/app/integrations/jsonschema_to_pydantic.py` —
  dynamic Pydantic from JSON Schema.

### Integrations

* `afterglow/backend/app/integrations/vultr_inference.py` — RAG +
  Vector Store.
* `afterglow/backend/app/integrations/speechmatics.py` — batch STT.
* `afterglow/backend/app/integrations/speechmatics_tts.py` — TTS preview.
* `afterglow/backend/app/integrations/action_catalog.py` — the
  authoritative catalog of 25 action keys across 8 mock buckets +
  1 internal real bucket.

### Data model + tasks

* `afterglow/backend/app/db/models.py` — SQLAlchemy models.
* `afterglow/backend/app/db/seed.py` — seed data (12 customers, 3
  templates, ~43 busy-week calls).
* `afterglow/backend/app/tasks/vector_preseed.py` — RAG preseed at
  boot.
* `afterglow/backend/app/tasks/seed_date_refresh.py` — anchor-date
  drift refresh.

### Market sizing

* `tmp/deep-research-report (2).md` — Italian TAM/SAM research for
  booking-led and phone-led businesses, with source-method notes and
  domain ranking.

### API + config + admin

* `afterglow/backend/app/api/calls.py` — `POST /calls` ingest +
  detail view.
* `afterglow/backend/app/api/admin.py` — `rag-stats`, `rag-probe`,
  `dry-run-pipeline`.
* `afterglow/backend/app/api/session_context.py` — demo session
  middleware.
* `afterglow/backend/app/config.py` — env-driven configuration.

### Frontend (the parts that matter for the pitch)

* `afterglow/app/components/AgentReasoningTrail.tsx` — the reasoning
  trail UI.
* `afterglow/app/app/(drawer)/(tabs)/index.tsx` — Home (Pixel Recents
  clone).
* `afterglow/app/app/call/[id].tsx` — call detail.
* `afterglow/app/app/(drawer)/simulator.tsx` — the demo simulator.
* `afterglow/app/app/templates/wizard.tsx` — wizard chat UI.
* `afterglow/demo-site/src/App.tsx` — the marketing landing.

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

### Hackathon reference (external, in `hackathon-docs/`)

* `02-challenge.md` — challenge thesis + 5 tracks.
* `06-what-to-submit.md` — submission form spec + MP4 rules.
* `07-judging-criteria.md` — the 4 criteria.
* `12-vultr-deep-dive.md` — Vultr award playbook.
* `13-gemini-deep-dive.md` — Gemini award playbook.

---

*End of bible. If you find anything stale, fix the code or fix this
file — whichever is wrong.*
