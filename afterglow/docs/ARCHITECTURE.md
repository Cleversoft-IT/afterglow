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

The drawer header is the `<Text>` wordmark `<Text>after</Text><Text color=primary>glow</Text>`
(font weight 800, letter-spacing -0.3, size 22) that mirrors the demo site
markup. The drawer voice list, top to bottom, is **Calls → Contacts →
Templates → Audit log → Test simulator → (divider) → Settings → Reset demo**.
"Calls" is a manual `<DrawerItem>` that routes to the hidden `(tabs)` group
so the user always has a path back to the Home feed from any other drawer
entry. Every icon uses `focused ? primary : (color ?? onSurface)` for the
color so the active highlight stays and dark mode never loses legibility.

**Simulator / incoming-call audio** reads the active template's
`simulation_config`. Seed templates ship bundled recordings under
`app/assets/audio/` (two MP3s per domain, one per `scenarios.existing` /
`scenarios.new`); wizard-generated templates can generate a single call
script + WAV through the backend's simulation endpoints
(`simulation_script.py` + Speechmatics TTS) or accept an uploaded recording.
Because wizard-built templates only produce a flat script (one
`caller_name`/`caller_phone_e164`, no per-mode scenarios) and that phone
doesn't match any seeded customer, the Simulator hides the "Call from
existing customer" button for them and exposes only "Call from new
customer". The selected recording is then submitted to `POST /api/v1/calls`
with the current `X-Demo-Session` header.

**Home (Recents) layout** mirrors the Pixel call log: an `Appbar` pill
`Searchbar` with hamburger leading + voice trailing, a horizontal chip filter
row (**All / Missed / Bookings / Clients / Saved / Unsaved**), a `SectionList`
with sticky azure date headers (locale-aware: `Oggi / Ieri / 15 mag` in IT,
`Today / Yesterday / May 15` in EN), and a `CallRow` per call with a
hash-colored `Avatar.Text` fallback (11-color Amadz palette, hash on phone) —
or, when the row resolves to a mock contact carrying `avatar_url`, a real
photo from `randomuser.me`. The row description is a **directional arrow
icon** (↙ for incoming/missed, `progress-clock` while analyzing,
`alert-circle-outline` for pipeline errors) + relative time — no text
labels like "Incoming" / "Missed" (Pixel system-dialer pattern, round 9).
Trailing area: a phone-outline **"ridial"** `IconButton` on every row pops a
`Calling {phone}… (demo)` `Snackbar`; rows whose call has a booking get a
compact icon-only `BookingMarker` pill (View + Paper Icon
`calendar-blank-outline`) next to the ridial button in all filters except
`bookings`, where the full `BookingBadge` (slot + party size) replaces the
marker. The IconButton is wrapped in a `Pressable` with `stopPropagation` as
a safety net so the row's onPress (open call detail) doesn't fire.

**Booking chip filter** sorts the calls by the booking slot, not by call
timestamp: upcoming slots come first (ascending), then past slots
(descending). The secondary sort chip row (`By call date` / `By booking
date`) shows a `swap-vertical` icon when inactive (Material standard "tap
to sort"), and flips between `arrow-up` (asc) / `arrow-down` (desc) when
active. The `BookingBadge` shown on each row renders
`${formatDayMonth} ${time} · party N` — no year — from `payload.booking_date`
and `payload.booking_time`. The Home screen fetches `listCalls` and
`listBookings` in parallel and joins them on `call_id` client-side; the
chip is not powered by a new endpoint.

**Clients chip filter** keeps only rows where `caller.is_customer` is true
(i.e. the phone matched a row in the `Customer` table). It is a subset of
"Saved", which also matches the local `MOCK_CONTACTS` phonebook entries.

**Search query** (the Searchbar text) filters across `caller.display_name`,
`call.phone_e164`, `booking.title`, and `payload.customer_name`. It is
ANDed with whichever chip is active.

**Contacts drawer entry** is a unified list of:
1. The `Customer` table (`GET /api/v1/customers?limit=50`), marked with a
   "Client" `Chip`.
2. Twenty client-side hardcoded UK/US `PersonalContact` entries from
   `app/lib/mockContacts.ts` — they have no backend representation. Their
   purpose is to make the "system phone replacement" pitch credible: even
   on a fresh install, the Contacts entry looks populated. About half of
   them carry an `avatar_url` pointing at `randomuser.me/api/portraits/
   {women,men}/N.jpg` — the gender of the photo is hand-picked to match
   the name, and the URLs are checked in at build time (no client-side
   randomization).
The two sources are deduped on phone (customer wins), sorted alphabetically,
grouped by first-letter section header, and shown above a chip filter
(`All / Clients / Personal`) that distinguishes the two sources visually.
`app/lib/callerResolver.ts` provides the sync resolver used by every
`CallRow`: `customer.display_name > MOCK_CONTACTS[phone] > "Unknown caller"`
and propagates `avatar_url` from `MOCK_CONTACTS` so the same portraits
show up on the Home feed.

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
tonal `elevation.level0..5`, etc.). The generator's `secondary` / `tertiary`
tracks lean pinkish off a blue seed, so on top of the generated scheme we:

- override `background` / `surface` / `surfaceVariant` / `outline` with
  flat neutrals (light = `#F7F8FA` / `#FFFFFF`, dark = `#0B0D12` /
  `#161922`) so the app reads as a clean Pixel-like dialer in both modes
  instead of inheriting the tinted greys the source-color generator
  produces;
- override `secondaryContainer` / `tertiaryContainer` and the entire
  `elevation.level0..5` object with cool-grey neutrals (light = `#E7EEFC`
  / `#EEF0F4` for the containers and `#F4F6FB → #D8E1EF` for elevation;
  dark = `#1B2944` / `#1F2330` and `#1A1F2B → #2D344A`). Without this,
  chips and elevated cards (the booking badge on the Home feed, the
  Audit log status chip, the simulator's Script Preview accordion, the
  Templates draft sidebar) inherit a faint lavender tint from the
  generator and the app reads as "Material You demo" rather than a
  Pixel-clean dialer;
- add a semantic **success palette** (`success`, `onSuccess`,
  `successContainer`, `onSuccessContainer`) — green in both light and
  dark — and export an `AppTheme` type that extends `MD3Theme` with
  those four keys. Screens that show "success" / "completed" status
  (audit log avatars, call-detail status chip, customer-detail call
  rows and template-editor chips) call
  `useTheme<AppTheme>()` and read `theme.colors.successContainer`
  instead of the generator's `tertiaryContainer` (which is pink in
  light and purple in dark — semantically wrong for success).

`PaperProvider` is wired **inside** `RootLayoutInner` because the Paper
theme depends on the resolved value from our lightweight
`ThemeContext`. That context stores only the appearance preference
(`auto | light | dark`) and its resolved mode; all visual colors,
typography and component state now come from Paper's MD3 theme. The
Settings screen flips Paper's light/dark scheme through that preference
context. Two colors are hardcoded outside the generated palette and
survive any brand-color change because they are phone-app semantics, not
branding: `callGreen = '#26B31E'` (accept / in-call avatar) and
`callRed = '#B3261E'` (decline / end).

**Template editor.** `app/templates/[id].tsx` is fully on
`react-native-paper` primitives. Cards, text fields, segmented buttons,
menus, checkboxes, chips, icon buttons and ripple headers are Paper
components wired to `AppTheme`; the old local UI wrappers
(`Button`, `Card`, `Input`, `Textarea`, `Select`, `Checkbox`,
`FormField`, `Badge`) and the pre-MD3 `app/lib/theme.ts` token file were
removed. The only custom theme context left is the appearance preference
provider described above.

**Drawer theme propagation.** `@react-navigation/drawer` does not pick
up the Paper theme on its own — it uses its own `DefaultTheme` (always
light) for the navigator chrome. `app/(drawer)/_layout.tsx` therefore
calls `useTheme()` from Paper and passes the bridge explicitly:
`drawerStyle.backgroundColor = theme.colors.surface`,
`sceneStyle.backgroundColor = theme.colors.background`,
`drawerActiveTintColor = theme.colors.primary`,
`drawerInactiveTintColor = theme.colors.onSurfaceVariant`,
`drawerActiveBackgroundColor = theme.colors.secondaryContainer`. Each
`DrawerItem` also receives `labelStyle={{ color: theme.colors.onSurface,
fontWeight: '500' }}` because the navigator otherwise paints labels with
its own tint that becomes invisible on the dark surface.

**Incoming-call layout.** The avatar sits in a `flex: 1` zone underneath
a header zone (caption / display name / phone subtitle). To keep the
green pulse from clipping into the name when the viewport is short
(landscape web, demo iframe), the header reserves `paddingBottom: 24`
and the ringing-phase avatar shrinks from 160 to **128 dp** while
pulsing; the talking-phase avatar stays at 160 dp.

**Hangup audio.** Browsers reject `Audio.play()` with `AbortError`
("interrupted by a call to pause()") when the operator hangs up
mid-MP3. `app/lib/usePhoneAudio.ts` catches that specific case and
returns silently — it is a graceful stop, not an error. The hangup
handler in `app/incoming-call.tsx` also falls back to
`router.replace('/(drawer)/(tabs)')` when `router.canGoBack()` is
false, so a deep-link / cold-load hangup no longer leaves a black
screen behind a stale `play()` rejection toast.

**Custom-template audio via blob URL.** The
`/api/v1/templates/{id}/simulation/audio` endpoint is session-scoped
(`X-Demo-Session` + `visibility_filter_seedable`), but
`<audio src="…">` cannot carry custom headers and the app + backend live
on different sslip.io subdomains. Pointing the audio element at the bare
backend URL therefore 404s for wizard-built templates (session-owned,
not visible to a header-less request) and the browser reports the
generic "Failed to load because no supported source was found". The fix
is in `api.fetchSimulationAudio(id, mode)`: it pulls the WAV as a
`Blob` through the session-aware fetch wrapper, and
`usePhoneAudio.prefetchBlob(key, blob)` wraps it in
`URL.createObjectURL(blob)` before handing the URL to `<audio>` —
object URLs need no auth. Owned object URLs are revoked on unmount.

**Locale (date/time only).** `app/lib/LocaleContext.tsx` carries a binary
`it | en` preference (default `it`, persisted in `localStorage` under
`afterglow.locale`). The Settings screen toggles it via Paper
`SegmentedButtons`. `app/lib/dateFormat.ts` wraps `Intl.DateTimeFormat`
(cached per locale × options) and produces the formats every screen
consumes: full datetime (`DD/MM/YYYY HH:mm` vs `MM/DD/YYYY h:mm a`), day-
month (`DD/MM` vs `M/D`), relative time (`21 h fa` vs `21h ago`), and the
"Today / Yesterday / D Mon" relative-day grouper. The toggle reflows the
entire app on the next render. **This is not UI i18n** — strings stay in
English per `feedback_code_language`; only dates and times localize.

**Transcript split.** `app/components/TranscriptList.tsx` parses
`raw_transcript.text` on the `^(Operator|Caller|Operatore|Chiamante):`
line prefix, then renders the turns inside a `<Card> + <List.Accordion>`
"View turns" — same Material 3 pattern as the simulator's `ScriptPreview`
(not the wizard's chat bubbles). Operator labels render in `primary`,
caller labels in `success`; the body of each turn is `bodyMedium`.

**Call detail polish.** `app/app/call/[id].tsx` hides the
`integration_kind="mock_external"` "Simulated" badge for actions whose
side effect lives on the operator's own device — the whitelist is
`REAL_ON_DEVICE = {"booking.create"}` (round 8 unified the action
namespace to `booking.*` across all verticals — the `appointment.*` keys
are gone). This is a **UI-only** choice; the backend catalog and audit
log still classify those actions as `mock_external`. Status chips are now Capitalize'd with an icon
(`check-circle-outline` / `alert-circle-outline` / `progress-clock`),
and the phone subtitle prefixes a country flag emoji from
`app/lib/flagFromE164.ts` (small table, no external library). The
machine-key monospace lines under field labels and action types — a
pleonasm with the operator-facing label — were removed.

**Fresh-session redirect.** When the bootstrap gate in `app/_layout.tsx`
sees `getActiveTemplate()` return `null` (fresh visit or after Reset
demo) and redirects to `/(drawer)/templates`, it also calls
`markFreshSession()` (`app/lib/freshSession.ts`, one-shot flag in
`sessionStorage`). The Templates screen calls `consumeFreshSession()`
right after a successful `setActiveTemplate(id)` and, if the flag was
set, shows a Paper `<Dialog>` asking the visitor whether they want to
jump to the Calls feed or stay on Templates. The flag is cleared on
read; subsequent template activations don't re-prompt.

**Reset demo.** Both the Settings entry **and** the Drawer entry use the
same Paper `<Portal><Dialog>` confirmation pattern. The drawer entry used
to call `window.confirm`, which raced with the drawer auto-close and left
the button stuck on "Resetting…" — see [[feedback-drawer-window-confirm]].
The post-reset hard reload re-enters the bootstrap gate, which sets
`markFreshSession()` again because the active template was cleared, so
the visitor is offered the "Go to Calls" dialog after they pick a new
template.

**Web first-paint sync.** `app/app/_layout.tsx` runs a module-level
block on `Platform.OS === 'web'` that reads the stored theme preference
(or the OS `prefers-color-scheme` if `auto`) and stamps
`document.documentElement.style.colorScheme` and
`document.body.style.backgroundColor` *before* the first React render.
This minimizes the flash of browser-default background at cold load,
but it does not eliminate it — a true pre-paint would need a custom
Expo web `index.html` template. A `useEffect` re-applies on runtime
theme changes.

## Demo site shell

The public demo site is a Vite/React marketing shell that embeds the real
Expo web app via `APP_URL` (`VITE_APP_URL`, defaulting to the production
`app.95-179-245-107.sslip.io` URL). On desktop/tablet widths it renders the
app inside a fixed logical 390×845 phone viewport, wrapped by `.phone-stage`:
the app keeps a stable viewport while the wrapper applies a viewport-aware
CSS transform scale (`0.55..1.0`) so the full device fits below the demo
section copy. A subtle "Click anywhere on the screen to interact" hint sits
below the frame. On mobile, the iframe preview is hidden and the site shows
a single CTA to open the live app full-screen.

## End-to-end shape

```
App (Expo + react-native-web)         ◄── embedded by ── Demo site (Vite)
       │ POST /api/v1/calls (audio + phone, X-Demo-Session header)
       ▼
FastAPI                ─► eager Customer lookup by phone (clone-first/seed-fallback
                          in demo, session-scoped in prod) — sets call.customer_id
                          BEFORE the commit so the calls list shows the name
                          immediately instead of "Unknown caller" during the pipeline.
                          The pipeline's _resolve_customer may rewrite the FK later
                          if the lookup landed on a seed row.
       │
       ▼
FastAPI background task ─► Speechmatics batch (diarization + lang detect)
       │
       ├─► Memory lookup
       │   ├─► structured SQL history (demo, or customers with <=10 prior calls)
       │   └─► Vultr Vector Store /v1/chat/completions/RAG
       │       (production customers with >10 prior calls, single collection
       │        configured via VULTR_VECTOR_DEFAULT_COLLECTION)
       │
       ├─► Gemini structured-output call  (call_analyzer.py — single Gemini pass)
       │       prompt: transcript + template fields_schema (confidence_threshold /
       │               extractor_hint / depends_on) + action_types (preconditions /
       │               confidence_threshold / evidence_required / payload_schema) +
       │               applicable prompt_hints rules (when evaluated against
       │               prior_structured) + prior_facts
       │       Grounding rule (enforced in the system instruction):
       │         prior_facts can only inform next_call_briefing — they MUST NOT
       │         be used as `evidence` for field extractions and MUST NOT fill
       │         action `payload` fields unless the current transcript confirms
       │         them. evidence must always be a verbatim span FROM the
       │         current transcript.
       │       response_schema = CallAnalysis (Pydantic):
       │         - fields[]  (key, value, confidence, evidence)
       │         - intent, sentiment, language, urgency
       │         - planned_actions[]  (subset of template auto-actions, typed payload)
       │         - next_call_briefing  (NL paragraph, detected language)
       │       Fail-fast: missing key / error / schema mismatch → Call.failed.
       │
       ├─► Action Planner (action_planner.py — Google ADK agentic loop)
       │       reads the analysis, exposes the template's auto-mode
       │       action_types as ADK tools with TYPED payload parameters
       │       (Pydantic models built from payload_schema). Each tool's
       │       docstring surfaces `mutates` from the action catalog (single
       │       source of truth). Gemini emits a structured object that
       │       matches the schema; the executor revalidates.
       │       Fail-fast: ADK runner error → Call.failed (no fallback).
       │
       ├─► Action Executor (deterministic Python) ─► jsonschema.validate(payload),
       │       evidence_required gate, `mutates` flag read from action_catalog,
       │       catalog dispatch: `mock_external` actions are stamped
       │       `mock: True`; `internal_real` actions mutate Postgres and are
       │       stamped `mock: False`. All executions/refusals write
       │       executed_actions + audit_log.
       │
       └─► Memory write-back ─► customer.memory_summary (Postgres, operator-visible)
                                + extracted_fields.briefing_snapshot (per-call copy)
                                + customer.profile_facts / tags when internal profile
                                  actions run
                                + bilingual chunk pushed to Vultr Vector Store
                                  (native briefing + EN summary; skipped when the
                                   call carries a demo session_id)
```

The pipeline runs **entirely after the call ends**. The human-facing latency
is whatever Postgres takes to return `customer.memory_summary`. No AI in the
live-call hot path.

**Startup recovery.** FastAPI lifespan startup also runs `orphan_recovery`:
any call stuck in `transcribing` or `analyzing` for more than 10 minutes is
marked `failed` with `error="orphaned_after_restart"` and an audit row. This
keeps the UI from polling forever after a deploy, crash, or container restart
that interrupted a background task.

**Action catalog.** `backend/app/integrations/action_catalog.py` is the source
of truth for action execution kind. External integrations are simulated
through `MOCK_REGISTRY` (`mock_external`); internal profile updates run
against Postgres (`internal_real`) through `customer_profile.apply_update`.
The profile handler can backfill `display_name`, merge `tags`, store
allergies and other free-form facts in `customers.profile_facts`, and keeps a
`previous_state` snapshot so undo can replay the prior customer row state.

As of 2026-05-18 the catalog ships **25 actions** spread across **8 mock
buckets** (`booking`, `whatsapp`, `sms`, `email`, `crm`, `calendar`,
`payment`, `review`) plus **1 internal_real bucket** (`customer_profile`).
The `sms.*` actions now dispatch to their own dedicated mock handler
(previously they piggybacked on the `whatsapp` mock — a semantic bug fixed
in the same change). `action_catalog.aggregate_integrations()` is a pure
function that groups the catalog by bucket and powers `GET /api/v1/integrations`
+ the read-only "Integrations" drawer screen on the app. The same file
exports `KNOWN_DOMAINS` — 11 verticals the wizard can assign as
`domain_hint` (restaurant, dentist, bodyshop, hotel, salon, clinic, legal,
realestate, gym, events, generic).

The Call detail screen further refines the user-facing "Simulated" badge with
a UI-only whitelist: actions in `REAL_ON_DEVICE = {"booking.create"}` never
show the badge even though the catalog classifies them as `mock_external`.
The rationale is that those actions are conceptually "the operator wrote
the booking on their own device", not "a remote CRM call". Round 8 unified
the action namespace (`appointment.*` removed everywhere — dentist and
bodyshop now also emit `booking.create`), so the whitelist has a single
entry. The backend, audit log, and `result.mock` are unchanged.

**Personal phonebook calls in the seed.** `backend/app/db/seed.py` exposes
`_ensure_personal_calls(session)` that runs every seed pass (it lives
*outside* the "templates already present, skipping" early-return). It
calls `_ensure_seed_customers(session)` at the top — an idempotent upsert
that inserts any of the **six** `SEED_CUSTOMERS` (Mark Ross, Julia White,
Laura Bennett, Andrew Green, Sophie Walker, Tom Hughes) missing from the
DB by phone, so a round-8-clean DB picks up the round-9 additions (Sophie,
Tom) without a wipe. Then it idempotently inserts the base personal
fixtures (3 missed + 2 unsaved + 2 human-handled mock-contact calls)
plus a "busy week" 9–17 May densification that yields ~43 entries; combined
with the 7 base fixtures the Home `limit=50` page lands fully populated.
The busy-week plan emits **9 `ai_booking` calls** distributed across all
6 customers (Mark×2, Julia×1, Laura×1, Andrew×2, Sophie×2, Tom×1, never
more than one same-customer ai_booking per day) so the Bookings sort
doesn't show monotonous customer streaks. AI booking blueprints live in
`_AI_BOOKING_BLUEPRINTS` (one entry per `SEED_CUSTOMERS` name); the three
dicts `SEED_CUSTOMERS` / `_AI_BOOKING_BLUEPRINTS` / `_CUSTOMER_PHONES_BY_NAME`
must stay isomorphic — `backend/tests/test_seed_templates.py` enforces it.

The fixtures duplicate phone/name literals from `MOCK_CONTACTS` because
the backend cannot import client-side code; the list has a comment
pointing at the matching `pc_xxx` entries and the two must be kept in
sync. Visibility is guaranteed by `visibility_filter_seedable`, which is
the filter the `calls` endpoint applies (the table has `is_seed` even
though most activity tables don't — these rows look like seeds for the
purposes of demo isolation).

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

**Visibility rule.** Activity tables (`calls`, `audit_log`,
`executed_actions`, etc.) are not seedable: production reads
`session_id IS NULL`, while demo reads strictly `session_id = me`.
Seedable tables (`templates`, `customers`) use a different filter: production
reads `session_id IS NULL`, while demo reads `session_id = me OR is_seed =
TRUE`. Seed rows (the template presets, the known demo customers) live with
`session_id IS NULL AND is_seed = TRUE` and stay shared and read-only.

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
on the visitor's clone customer and shown post-call. Demo memory lookup uses
the session-isolated SQL structured-history path and writes a
`memory_lookup.structured_history` audit row with `demo=true`; the vector
write-back path writes a `memory_updater` audit row with `status=skipped`
and reason `demo_sandbox_vector_store_disabled`.

The production single-tenant path (no `X-Demo-Session` header, or
`?bypass=<token>` for pitch-day) keeps Vultr enabled: memory write-back pushes
chunks to the configured collection, and semantic RAG is used once the
customer has enough history (`total_calls > 10`). For shorter histories,
production also uses the exact SQL structured-history path.

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
| `templates`              | yes                   | Seed presets (`NULL`) + wizard-generated templates, including optional `simulation_config` |
| `customers`              | yes                   | Seed customers (`NULL`) + clone-on-write per session; profile facts live in `profile_facts` |
| `calls`                  | yes                   | Filtered on read and on cleanup                        |
| `audit_log`              | yes                   | Same; lets judges read their own audit trail           |
| `executed_actions`       | yes                   | Same                                                   |
| `customer_memory_chunks` | yes (NULL in production rows; demo writes are skipped today) | Vector-store write index for production memory chunks |
| `extracted_fields`       | no                    | Cascades via `calls`. Carries `briefing_snapshot` (mig `0005`): a frozen copy of the operator-visible briefing emitted for this specific call, kept even after `customer.memory_summary` is later overwritten by a newer call. |

## PII handling

PII/privacy classification is **out of scope for the hackathon demo** —
`FieldDefinition` carries no privacy metadata and the post-call pipeline
runs four steps (`call_analyzer` → `action_planner` → `action_executor`
→ `_persist_memory`) with no sanitizer or redaction step. The original
design and the rationale for removal live in `afterglow/docs/future-ideas.md` §4.

`FieldDefinition.confidence_threshold` (per-field, 0.0–1.0) is kept and
gates `depends_on` propagation in `orchestrator._coerce_extractions`.

## Bilingual briefing

When `transcript.language != "en"` (and we are not in demo mode), the
orchestrator's `_persist_memory` makes one extra small Gemini call
(`_summarize_to_english`, ≤120 output tokens) to produce an English
restatement of the operator-visible briefing. Both copies are pushed to the
Vultr Vector Store chunk so semantic retrieval works across the operator's
spoken language and the embedding model's bias toward English. Failure of
the bilingual call lands as
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

The wizard surface (`wizard_chat`, `template_validator`) is not in the
post-call path and is not audited per token today.
