# Afterglow architecture

> What remains after the call.
> Drop-in replacement for the system Phone app: the operator handles every
> call; the AI runs silently after each one — extracting fields, executing
> actions, and writing a one-line briefing for the next call.

## User-facing navigation

The frontend is an Expo SDK 54 / react-native-web PWA shaped like the Google
Phone (Pixel) app. There is no single 5-tab bar; the structure is:

```
Stack root  (app/_layout.tsx)
└─ (drawer)/_layout.tsx                     Drawer navigator (@react-navigation/drawer v7)
    ├─ (tabs)/_layout.tsx                   BottomNavigation.Bar Paper, 2 entries
    │   ├─ index.tsx                        Home — Pixel Recents
    │   └─ keypad.tsx                       Keypad — 4×3 dialpad (Call FAB is UI-only)
    ├─ contacts.tsx                         Contacts — alphabetical, mock + customer
    ├─ templates.tsx                        Templates list
    ├─ audit.tsx                            Audit log
    └─ settings.tsx                         Settings

Stack siblings (outside the drawer)
├─ incoming-call.tsx                        Full-screen Pixel-inspired dialer
├─ call/[id].tsx                            Call detail (MD3 Card + Chip + Undo/Redo)
├─ customer/[id].tsx                        Contact detail (briefing on elevation.level2)
├─ templates/[id].tsx                       Template editor
├─ templates/wizard.tsx                     Wizard chat (MD3 Surface bubbles)
└─ simulator.tsx                            Test simulator (drawer entry → push)
```

**Home (Recents) layout** mirrors the Pixel call log: an `Appbar` pill
`Searchbar` with hamburger leading + voice trailing, a horizontal chip filter
row (**All / Missed / Bookings / Saved / Unsaved**), a `SectionList` with
sticky azure date headers (Today / Yesterday / `D Mon`), and a `CallRow` per
call with a hash-colored `Avatar.Text` (11-color Amadz palette, hash on
phone), first+last initials, a "Booking" `Chip` when the call has an
executed booking action, and a trailing `phone-outline` `IconButton` that
opens a `Snackbar` (the trailing icon deliberately does **not** navigate to
the dialer — would have required touching the `incoming-call` state machine,
which is locked).

**Booking chip filter** hides the phone number on each row and renders
`payload.booking_date · booking_time · party_size · customer_name` from the
matching `BookingListItem`. The Home screen fetches `listCalls` and
`listBookings` in parallel and joins them on `call_id` client-side; the
chip is not powered by a new endpoint.

**Search query** (the Searchbar text) filters across `caller.display_name`,
`call.phone_e164`, `booking.title`, and `payload.customer_name`. It is
ANDed with whichever chip is active.

**Contacts drawer entry** is a unified list of:
1. The `Customer` table (`GET /api/v1/customers?limit=50`), marked with a
   "Client" `Chip`.
2. Twenty client-side hardcoded UK/US `PersonalContact` entries from
   `app/lib/mockContacts.ts` — they have no backend representation. Their
   purpose is to make the "system phone replacement" pitch credible: even
   on a fresh install, the Contacts entry looks populated.
The two sources are deduped on phone (customer wins), sorted alphabetically,
and grouped by first-letter section header. `app/lib/callerResolver.ts`
provides the sync resolver used by every `CallRow`:
`customer.display_name > MOCK_CONTACTS[phone] > "Unknown caller"`.

**Incoming-call screen** is "Pixel-inspired, not 1:1": three FABs (Decline
red `#B3261E` / AI primary with `creation` icon / Accept green `#26B31E`)
during the ringing phase instead of the two-button Pixel layout; an
animated 160 dp green `Avatar.Text` (the avatar is hardcoded green because
"in-call" is a phone-app semantic state, not the brand color); during the
talking phase the layout becomes `Chip "Afterglow listening"` + timer in
`tabular-nums` + four `IconButton` controls (Keypad / Mute / Speaker /
More — all UI-only) + a big red pill hangup. The state machine
(`useEffect` / `useState` / `usePhoneAudio` calls) is **unchanged** from
the pre-Material-3 codebase; only the JSX was rewritten.

**Material 3 theme** is generated at startup from a single seed color
(`#3b82f6`) using `@material/material-color-utilities` — `paperLightTheme`
and `paperDarkTheme` in `app/lib/paperTheme.ts` carry the full MD3 palette
(`primaryContainer`, `secondaryContainer`, `surfaceVariant`, `outline`, the
tonal `elevation.level0..5`, etc.). `PaperProvider` is wired **inside**
`RootLayoutInner` because the Paper theme depends on the `useTheme()` hook
from our custom `ThemeContext` (the mode toggle in Settings flips Paper's
light/dark scheme via the same hook). Two colors are hardcoded outside the
generated palette and survive any brand-color change because they are
phone-app semantics, not branding: `callGreen = '#26B31E'` (accept / in-call
avatar) and `callRed = '#B3261E'` (decline / end).

## End-to-end shape

```
App (Expo + react-native-web)         ◄── embedded by ── Demo site (Vite)
       │ POST /api/v1/calls (audio + phone, X-Demo-Session header)
       ▼
FastAPI background task ─► Speechmatics batch (diarization + lang detect + custom dict)
       │
       ├─► Vultr Vector Store /v1/chat/completions/RAG  (pre-fetch: prior_facts)
       │   └─► single collection, configured via VULTR_VECTOR_DEFAULT_COLLECTION
       │       (skipped when the call carries a demo session_id — see below)
       │
       ├─► Gemini structured-output call  (call_analyzer.py — single Gemini pass)
       │       prompt: transcript + template fields_schema (incl. pii_class /
       │               confidence_threshold / extractor_hint / depends_on) +
       │               action_types (incl. preconditions / confidence_threshold /
       │               mutates / evidence_required / payload_schema) +
       │               applicable prompt_hints rules (when evaluated against
       │               prior_structured) + prior_facts
       │       response_schema = CallAnalysis (Pydantic):
       │         - fields[]  (key, value, confidence, evidence)
       │         - intent, sentiment, language, urgency
       │         - planned_actions[]  (subset of template auto-actions, typed payload)
       │         - next_call_briefing  (NL paragraph, detected language)
       │       Fail-fast: missing key / error / schema mismatch → Call.failed.
       │
       ├─► PII sanitizer (pii_sanitizer.py — pure Python, no LLM)
       │       applies the per-pii_class redaction policy to next_call_briefing
       │       and planned_action evidence; audit step `pii_policy_applied`
       │       records exactly what was redacted, with which threshold.
       │       Raw `fields` survive untouched for UI + executor.
       │
       ├─► Action Planner (action_planner.py — Google ADK agentic loop)
       │       reads the SANITIZED analysis, exposes the template's auto-mode
       │       action_types as ADK tools with TYPED payload parameters
       │       (Pydantic models built from payload_schema). Gemini emits a
       │       structured object that matches the schema; the executor revalidates.
       │       Fail-fast: ADK runner error → Call.failed (no fallback).
       │
       ├─► Action Executor (deterministic Python) ─► jsonschema.validate(payload),
       │       evidence_required gate, mutates flag, `mock: True` stamp on the
       │       result (renders a "Simulated" badge in the operator UI) →
       │       mock registry + Postgres + audit_log
       │
       └─► Memory write-back ─► customer.memory_summary (Postgres, operator-visible)
                                + extracted_fields.briefing_snapshot (sanitized per-call copy)
                                + bilingual chunk pushed to Vultr Vector Store
                                  (native briefing + EN summary; skipped when the
                                   call carries a demo session_id)
```

The pipeline runs **entirely after the call ends**. The human-facing latency
is whatever Postgres takes to return `customer.memory_summary`. No AI in the
live-call hot path.

System of record: **Vultr Managed Postgres**. Deploy: **Vultr Cloud Compute +
Coolify** with auto-deploy via GitHub App webhook on push to `main` (no
manual deploy step, no GitHub Actions in the critical path). IAM: Vultr
Service User with minimal-privilege ACL.

## Multi-visitor demo isolation

The public iframe at `demo.95-179-245-107.sslip.io` is reachable concurrently
by judges, hackathon attendees and crawlers. The product itself is
single-tenant (one installation = one customer); the demo is a sandbox bolted
on top of the same backend so visitors do not stomp on each other.

```
demo.95...                 app.95...                   api.95...
 (iframe)        ──────►   (Expo web)        ──────►   FastAPI
                            localStorage:                middleware:
                            demo_session_id              SessionContext(session_id | None)
                                  │
                                  ▼
                            X-Demo-Session: <uuid>       Postgres
                                                          calls.session_id
                                                          audit_log.session_id
                                                          executed_actions.session_id
                                                          customer_memory_chunks.session_id
                                                          templates.session_id   (wizard outputs)
                                                          customers.session_id   (clone-on-write)
                                                          demo_sessions(id, last_seen_at,
                                                                        active_template_id)
                                                          Vultr Vector Store
                                                          └─ skipped when session_id is not None
```

**Identity.** The first request from a new browser carries
`X-Demo-Session: new`. The backend mints a fresh `DemoSession` row and echoes
the freshly-generated uuid back on the response. The frontend persists it to
`localStorage` and stamps every subsequent request with it. No cookies, so
SameSite/Partitioned cookie behaviour inside an iframe is irrelevant.

**Visibility rule.** Every read filters
`WHERE session_id = me OR session_id IS NULL`. Seed rows (the three template
presets, the two known customers) live with `session_id IS NULL` and stay
shared and read-only.

**Clone-on-write customer.** When a call lands on a phone number that matches
a seed customer, the orchestrator clones the seed (`memory_summary`, `tags`,
`total_calls`, etc.) into a row stamped with the visitor's `session_id` and
writes back to the clone. Two judges who call Marco Rossi (`+393331112233`)
each get their own divergent timeline.

**Active template.** In demo mode the "currently active template" lives in
`demo_sessions.active_template_id`, not in `Template.is_active`. Production
single-tenant keeps the original `is_active` flag (rescoped to seed rows by a
partial unique index).

**Vultr Vector Store skip.** The wrapper to `/vector_store/{id}/items` and
`/chat/completions/RAG` does not expose per-item metadata filters, so we
cannot safely partition a shared collection by `session_id`. Rather than
provision one Vultr collection per visitor (cleanup is not guaranteed across
a 6-day judging window), demo mode skips both the chunk push and the RAG
prefetch. Postgres remains the source of truth: the briefing is still saved
on the visitor's clone customer and shown post-call. The audit log keeps the
wiring visible with explicit `status=skipped reason=demo_session` rows on the
`memory_lookup` and `memory_updater` steps.

The production single-tenant path (no `X-Demo-Session` header, or
`?bypass=<token>` for pitch-day) runs the full Vultr loop unchanged.

**Cleanup.** A background asyncio task running in the FastAPI lifespan event
sweeps `demo_sessions` every 30 minutes and deletes everything that has been
idle longer than 24 hours (calls, audit, executed actions, memory chunks,
wizard-generated templates, cloned customers, the session row itself). Vultr
is not touched because we never wrote to it for demo sessions.

**On-demand reset.** Visitors can also wipe their sandbox immediately from
the app's Drawer (the **Reset demo** entry, visible only in demo mode) or
from the Settings screen (drawer entry). `POST /api/v1/demo/reset` runs the same DELETE
sweep as the cron (`purge_session_data` in `app/tasks/session_cleanup.py`)
on the caller's `session_id`, but keeps the `demo_sessions` row alive and
clears `active_template_id` — so the visitor's localStorage uuid stays
valid and the next request lands on the cleaned-out sandbox without a fresh
handshake. The endpoint is 403 in production (`?bypass=<token>` / no demo
header). The web client follows with a hard reload, and the bootstrap gate
in `app/_layout.tsx` routes the visitor back to the Templates screen so
they pick a preset before doing anything else (same as a first-time
access).

**Active-template signaling.** `GET /api/v1/templates/active` returns 204
for a demo visitor with no `active_template_id` — *no* fallback to the
seed preset marked `is_active=TRUE`, because the UX explicitly requires
the visitor to pick. Production keeps the seed fallback so a fresh install
ships with a working default until the admin chooses.

## Key tables

| Table                    | Carries `session_id`? | Purpose                                                |
|--------------------------|-----------------------|--------------------------------------------------------|
| `demo_sessions`          | (is the id)           | Per-visitor sandbox, plus the picked active template   |
| `templates`              | yes                   | Seed presets (`NULL`) + wizard-generated (per session) |
| `customers`              | yes                   | Seed customers (`NULL`) + clone-on-write per session   |
| `calls`                  | yes                   | Filtered on read and on cleanup                        |
| `audit_log`              | yes                   | Same; lets judges read their own audit trail           |
| `executed_actions`       | yes                   | Same                                                   |
| `customer_memory_chunks` | yes (always NULL today) | Demo mode skips the write; column exists for future   |
| `extracted_fields`       | no                    | Cascades via `calls`. Carries `briefing_snapshot` (mig `0005`): a frozen copy of the SANITIZED briefing emitted for this specific call, kept even after `customer.memory_summary` is later overwritten by a newer call. |

## PII handling

Every `FieldDefinition` carries a `pii_class` (`none|contact|health|
financial|identity`) and an optional per-field `confidence_threshold`
that overrides the class default. The defaults are encoded in
`backend/app/agents/pii_policy.py`:

| Class      | Default threshold | Redaction strategy (briefing / vector chunk / audit evidence) |
|------------|-------------------|---------------------------------------------------------------|
| `none`     | 0.0               | passthrough                                                   |
| `contact`  | 0.80              | `[redacted: contact]`                                         |
| `identity` | 0.85              | first2 + asterisks + last2 (e.g. `AB***CD`)                  |
| `financial`| 0.90              | `[hash:<sha256[:8]>]` deterministic per value                |
| `health`   | 0.90              | `[redacted: health]` — never inline                          |

The sanitizer (`backend/app/agents/pii_sanitizer.py`) runs **immediately
after** the call_analyzer and produces a `SanitizedAnalysis` that:

1. Redacts every occurrence of a PII field's raw value from
   `next_call_briefing` and from each `planned_action.evidence` span.
2. Leaves `analysis.fields` untouched — the operator UI and the action
   executor still need the original value (booking the right table, sending
   the right WhatsApp to the right customer).
3. Emits a `pii_policy_applied` audit row enumerating which fields
   triggered the policy, the class, the threshold, and the action taken
   (`flag` when confidence is below threshold, `redact` otherwise). The
   raw values never appear in the audit payload — only the field key.

The chunk that lands in the Vultr Vector Store metadata records
`pii_redactions_applied: list[pii_class]` so an auditor can answer "did
we leak any health data into the embedding?" without re-reading the
chunk text.

## Bilingual briefing

When `transcript.language != "en"` (and we are not in demo mode), the
orchestrator's `_persist_memory` makes one extra small Gemini call
(`_summarize_to_english`, ≤120 output tokens) to produce an English
restatement of the (already sanitized) briefing. Both copies are pushed
to the Vultr Vector Store chunk so semantic retrieval works across the
operator's spoken language and the embedding model's bias toward
English. Failure of the bilingual call lands as
`audit.memory_summarizer_bilingual.status=degraded` and the chunk falls
back to native-only — the briefing on Postgres is unaffected.

## Token accounting

Every LLM step on the post-call path writes the token counts it consumed
into `audit_log.input_tokens` / `audit_log.output_tokens`:

- `call_analyzer.llm_call` — Gemini `response.usage_metadata`
  (`prompt_token_count` / `candidates_token_count`).
- `memory_summarizer_bilingual.llm_call` — same source.
- `memory_lookup.rag_semantic` — Vultr RAG's `usage.prompt_tokens` /
  `usage.completion_tokens` from the JSON response body.

The wizard surface (`template_builder`, `template_validator`) is not in
the post-call path and is not audited per token today.
