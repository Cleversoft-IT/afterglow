# Afterglow

> **The dialer that takes notes for you.**
>
> A drop-in replacement for the system Phone app: the operator handles every call, the AI runs silently after each one — extracting fields, executing actions, and writing a one-line briefing for the next call. Every action is revertible, every decision is traceable.

Built for the **AI Agent Olympics Hackathon @ Milan AI Week 2026** — targeting Best use of Vultr, Best use of Gemini, and bonus integration with Speechmatics.

## The problem

Small appointment-driven businesses (restaurants, dental clinics, body shops) still take bookings on the phone. Every call carries data that is easily lost: a name, a date, an allergy, a callback request. Post-its and memory don't scale. AI receptionists that talk *instead of* the human kill the relationship.

## The approach

Afterglow looks and feels like the system Phone app on a Pixel: a Drawer with Contacts/Templates/Settings, a 2-tab bottom bar (Home for recents, Keypad for dialing), and a full-screen incoming-call screen. The human keeps talking on every call; the AI listens in opt-in (the **AI button** during the ringing screen), transcribes with diarization, and **after** the call runs a Gemini pass that extracts the fields, classifies the call, plans the follow-up actions and writes a one-or-two-sentence "next-call briefing" for the operator who will pick up the next call. Every executed action lands on the post-call screen with an **Undo / Redo** button (only when the catalog says the action can be safely undone — sent messages do not get one). Every step is logged in a production-shape audit log.

The autonomy is the whole point: the hackathon brief calls for *autonomous decision-making systems*, not copilots. The undo + audit + confidence/evidence are the trust net that justifies the autonomy.

## Architecture

```
App (Expo + react-native-web)         ◄── embedded by ── Demo site (Vite)
       │ POST /api/v1/calls (audio + phone)
       ▼
FastAPI background task ─► Speechmatics batch (diarization + language auto-detect)
       │
       ├─► Vultr Vector Store /v1/chat/completions/RAG  (pre-fetch: prior_facts)
       │   └─► single collection, configured via VULTR_VECTOR_DEFAULT_COLLECTION
       │
       ├─► Gemini structured-output call  (single Gemini pass — see app/agents/call_analyzer.py)
       │       prompt: transcript + template fields_schema (confidence_threshold /
       │               extractor_hint / depends_on) + action_types (preconditions /
       │               confidence_threshold / evidence_required / payload_schema) +
       │               applicable prompt_hints rules + prior_facts
       │       Grounding rule: evidence MUST be a verbatim span from the current
       │       transcript; prior_facts only inform the briefing.
       │       response_schema = CallAnalysis (Pydantic):
       │         - fields[]  (key, value, confidence, evidence)
       │         - intent, sentiment, language, urgency
       │         - planned_actions[]  (subset of template auto-actions, typed payload)
       │         - next_call_briefing  (NL paragraph, detected language)
       │       Fail-fast: missing key / error / schema mismatch → Call.failed.
       │
       ├─► Action Planner (agentic ADK loop — see app/agents/action_planner.py)
       │       Each auto-mode action_type is exposed as an ADK tool with a
       │       Pydantic payload model built dynamically from payload_schema.
       │       Gemini emits a typed JSON payload; the executor revalidates.
       │       Fail-fast: ADK error → Call.failed (no fallback).
       │
       ├─► Action Executor (deterministic Python) ─► jsonschema.validate(payload),
       │       evidence_required gate, `mutates` flag read from action_catalog
       │       (single source of truth), routes the call to either MOCK_REGISTRY
       │       (integration_kind=mock_external, e.g. booking.create) or
       │       INTERNAL_HANDLERS (integration_kind=internal_real, e.g.
       │       customer.update_profile which actually writes Customer.tags +
       │       profile_facts on Postgres). Audit log records the integration_kind
       │       and mutates flag on every step.
       │
       └─► Memory write-back ─► customer.memory_summary (Postgres, operator-visible)
                                + bilingual chunk (native + EN summary) pushed to
                                  Vultr Vector Store
```

PII / privacy classification and the Speechmatics ASR custom dictionary
were removed from the template surface on 2026-05-17 (see
`.claude/memory/project_template_simplified_2026_05_17.md`). The template
now carries only the product-level shape (what to extract, what to do
after); system-level concerns (`mock_target`, `mutates`, integration
kind, undo semantics) live in `app/integrations/action_catalog.py`. As of
2026-05-18 the catalog ships **25 actions across 8 simulated buckets +
1 live bucket** (`customer_profile`), and the marketplace surface is
read-only browsable via the "Integrations" drawer item on the app.

The pipeline runs **entirely after the call ends** — the human-facing latency is whatever Postgres takes to return `customer.memory_summary`. No AI in the live-call hot path. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full diagram and rationale.

System of record: **Vultr Managed Postgres**. Deploy: **Vultr Cloud Compute + Coolify**, auto-deploy on push to `main` via GitHub App webhook (no GitHub Actions in the deploy critical path). IAM: Vultr Service User with minimal-privilege ACL.

## Award alignment

### Best use of Vultr
- `POST /v1/chat/completions/RAG` powers the pre-call memory lookup (skipped in demo mode — see "Demo isolation policy")
- Single Vector Store collection (single-tenant), populated by every completed production call's `next_call_briefing`
- Vultr Managed Postgres as the system of record (every call, customer, action, audit row)
- Vultr IAM Service User with a minimal-privilege ACL (`subscriptions_view, subscriptions, provisioning, firewall`)
- Coolify auto-deploy from `main` via GitHub App webhook, with HTTPS via Traefik + Let's Encrypt
- Note: Kimi-K2 was originally planned as the Classification model. Day 2 we
  collapsed Classification into the same Gemini structured output to reduce
  failure surface, and switched the RAG model to `MiniMaxAI/MiniMax-M2.7`
  (the model Vultr actually serves on `/v1/chat/completions/RAG`).

#### Demo isolation policy

The public iframe at `demo.95-179-245-107.sslip.io` is a multi-visitor
sandbox: every browser that loads it is stamped with an opaque
`X-Demo-Session: <uuid>` and every write (calls, customers, audit log,
executed actions, wizard-generated templates) is scoped to that uuid.
Two judges browsing the demo at the same time will not see each other's
state. Sessions are wiped 24h after inactivity by a background task.

To keep concurrent visitors from polluting the shared semantic memory,
the **Vultr Vector Store write/read path is intentionally disabled in
demo mode**. The audit log makes this visible: the `memory_lookup` and
`memory_updater` rows surface `status=skipped reason=demo_session` so a
judge can see the wiring exists. Run the same backend without the
`X-Demo-Session` header (production single-tenant deploy, or the
`?bypass=<token>` pitch-day escape hatch) and the full
`/v1/chat/completions/RAG` loop fires — call → write chunk → next call
prefetches the chunk → briefing returns the memory.

### Best use of Gemini
- **Single multi-purpose structured-output call** with Pydantic `response_schema` —
  extracts fields, classifies, plans actions and writes the briefing in one shot
- Default model: `gemini-3.1-flash-lite`. We pin the explicit model instead of
  using moving aliases such as `gemini-flash-latest` / `gemini-latest-flash`,
  which can shift under us; this is also the value configured in Coolify for
  the backend.
- Multimodal-ready: the analyzer interface accepts an `audio_bytes` argument and
  the `Part.from_bytes` path is wired in `app/integrations/gemini_adk.py` for the
  forthcoming multimodal upgrade
- Template Wizard wired live on the same `gemini-3.1-flash-lite` with structured
  output (Pydantic `response_schema=TemplateWizardResponse`). Fail-fast: a
  missing key or a Gemini error bubbles up as HTTP 502 — no offline stub.

### Speechmatics
- `speechmatics-batch` SDK wired live (`AsyncClient.transcribe` with
  `diarization=speaker` + `language=auto`) — no offline fallback, missing
  key or unreadable audio raise. The template-level ASR custom dictionary
  was removed 2026-05-17; Speechmatics handles vocabulary auto-detection.
- The six demo MP3s bundled under `app/assets/audio/` (three domains ×
  two caller modes — `<domain>_existing.mp3` for returning callers,
  `<domain>_new.mp3` for first-time callers — plus a synthetic
  `ringtone.mp3` used by the incoming-call screen) are generated by
  **Speechmatics Text-to-Speech** (UK + US voices); see
  `afterglow/scripts/generate_demo_audio.py` to regenerate them
- Multilingual demo: language detection auto on every call

## Stack

| Layer | Tech |
|---|---|
| App | Expo SDK 54 · React Native · react-native-web · expo-router · TypeScript |
| App UI kit | **react-native-paper v5.15 (Material 3)** · **@material/material-color-utilities** (palette generated from brand seed `#3b82f6`) · **@react-navigation/drawer v7** · **react-native-gesture-handler** · **react-native-reanimated v4** |
| Demo site | Vite 5 · React 18 · TypeScript (static landing that iframes the app) |
| Backend | Python 3.11 · FastAPI · google-genai · SQLAlchemy 2.0 async · Alembic |
| Speech | Speechmatics batch SDK |
| LLM | Gemini 3.1 Flash-Lite (default + template wizard) · MiniMax-M2.7 on Vultr (RAG) |
| Storage | Vultr Managed Postgres · Vultr Vector Store |
| Deploy | Podman / Docker Compose · Vultr Cloud Compute HP · Coolify |

> **Reanimated 4 caveat:** the app ships a `app/babel.config.js` with `'react-native-worklets/plugin'` (Reanimated 4 moved the plugin into the separate `react-native-worklets` package — the legacy `react-native-reanimated/plugin` is gone).

### User-facing navigation

The app does NOT use a single 5-tab bar. It is shaped like the Google Phone (Pixel) app:

- **Bottom Tabs (2):** **Home** (Pixel-style Recents — top-row with menu burger + search + Contacts icon, sticky locale-aware date headers, chip filter row, CallRow with semantic status labels `Incoming / Missed / Analyzing… / Pipeline error`, real photos or hash-colored fallback avatars, inline `BookingBadge` showing `DD/MM HH:mm · party N`) + **Keypad** (4×3 dialpad, Call FAB is UI-only and shows a Snackbar pointing to the Test simulator).
- **Drawer (hamburger top-left):** **Calls** (jumps back to Home — always at the top so any drawer screen has a path home), Templates, Audit log, ─── Test simulator, ─── Settings, [Reset demo] (demo mode only, Paper Dialog confirmation). Every drawer item lights up with `primary` on `secondaryContainer` when its screen is active (derived from `props.state.routes[props.state.index].name`). Contacts is reached from the Home top-right `account-multiple-outline` icon, not the drawer (Pixel Dialer pattern). Test simulator lives under the `(drawer)` group too, so it gets the hamburger header + active highlight like the other items.
- **Contacts screen:** chip filter `All / Clients / Personal` over an alphabetical list that mixes 20 client-side mock UK/US contacts with the server's `Customer` table — a "Client" chip marks customers; about half of the mock contacts carry a hand-picked `randomuser.me` portrait.
- **Stack screens (out of drawer):** Incoming call (Pixel-inspired full-screen with scrollable caller context), Call detail (header card with avatar + caller name — both tap-through to Customer when `customer_id != null`; flag emoji + phone; locale-formatted date; inline `customer.tags` chip row; status chip via `failure_kind`; no more separate "Open contact" button), Customer detail (mirror header layout; no `preferred_language` chip duplicating the flag; the "Calls (N)" list is divider-separated rows with `date · status chip`, no per-row phone icon), Template detail (editable name for non-seed, 409 on collision), Template wizard (editable name in draft preview, integration-discovery clarification on turn 1).
- **Home chip filters:** All / Missed / **Bookings** / **Clients** / Saved / Unsaved. **Bookings** shows a secondary chip row `By call date` (default) / `By booking date`; when sorting by booking date the upcoming slots come first (ASC) and past bookings sink. **Clients** keeps only rows linked to a `Customer`; **Saved** widens to include the local phonebook; **Unsaved** is the complement.
- **Fresh-install welcome:** on a fresh visit (or post `Reset demo`) the first navigation to **Templates** shows a Paper Dialog with two CTAs — `Pick a preset` (contained, recommended for demo) and `Build from prompt` (outlined, opens the wizard). One-shot per session.
- **Settings:** Appearance (theme) → Format (date/time locale, IT/EN — UI strings stay English) → [Demo controls if demo] → About. The Audit log is reached from the drawer; it's not duplicated in Settings.

## Local development

### Prerequisites
- **Python 3.11** (the project pins this — newer 3.12+/3.14 may not have wheels
  for `google-adk` / `asyncpg`)
- **Node 20+** with `npm`
- A container runtime for Postgres only — **Docker** or **Podman** (this project
  was bootstrapped on Fedora 43 using `podman` and it works as a drop-in)
- API keys: Google AI Studio (free tier OK), Speechmatics (required — STT is
  always live), and a **Vultr Serverless Inference** key (the *Inference* one
  — not a Vultr Cloud account key, which has the wrong scope and answers
  `"Invalid API key"` on the Inference base URL)

### One-time setup

```bash
# Postgres (one command, no compose needed)
podman run -d --name afterglow-pg \
  -e POSTGRES_USER=afterglow -e POSTGRES_PASSWORD=afterglow -e POSTGRES_DB=afterglow \
  -p 5432:5432 -v afterglow-pgdata:/var/lib/postgresql/data \
  docker.io/library/postgres:16-alpine

# Backend: env + venv + migrations + seed
cp .env.example .env       # fill API keys (Google, Speechmatics, Vultr)
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
set -a && . ../.env && set +a
PYTHONPATH=. .venv/bin/alembic upgrade head
PYTHONPATH=. .venv/bin/python -m app.db.seed   # 3 template presets + 4 known customers + 5 seeded calls

# App (Expo) — installs once, then runs the web bundle
cd ../app
npm install
echo "EXPO_PUBLIC_API_BASE=http://localhost:8000" > .env.local

# Demo site (Vite) — landing that iframes the app
cd ../demo-site
npm install
echo "VITE_APP_URL=http://localhost:8081" > .env.local
```

### Run

```bash
# Terminal A — backend
cd backend
set -a && . ../.env && set +a
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal B — app (Expo web on :8081)
cd app
npm run web

# Terminal C — demo site (Vite on :5173)
cd demo-site
npm run dev
```

Open the demo site at <http://localhost:5173> → the app is embedded as an
iframe. Open the **Drawer** (hamburger top-left) → tap **Templates**, activate
one of the seeded presets, then open the Drawer again → **Test simulator** →
tap **"Call from existing customer"** and accept the call with the **AI**
button on the ringing screen to run the full post-call pipeline.

### Live-AI behaviour

Speechmatics, Gemini and Vultr are all called for real on every submitted
call. Missing Speechmatics key or unreadable audio fails the call loudly.
**Missing GOOGLE_API_KEY, Gemini errors, ADK runner errors, or schema
mismatches fail the call loudly too** — the orchestrator marks the row as
`Call.status="failed"` with a human-readable `error` (the UI shows a red
banner). There is no offline stub: a demo that hallucinates structure on
every audio is a worse story than an honest failure. Missing Vultr key
skips RAG retrieval and write-back (the Postgres briefing is still saved).
The six demo MP3s under `app/assets/audio/` are pre-built EN UK/US
recordings generated by Speechmatics TTS (two per template — one for the
"Call from existing customer" Simulator button and one for the "Call
from new customer" button, so the audio always matches the operator's
expectation). Regenerate them with
`python afterglow/scripts/generate_demo_audio.py`.

Wizard-built templates instead produce a single flat script + WAV via
`POST /templates/{id}/simulation/{script,generate-audio,upload-audio}`,
so the Simulator only shows **"Call from new customer"** for them (the
generated phone has no matching customer in the demo DB). The WAV is
served from a session-scoped endpoint — `<audio src=URL>` cannot carry
the `X-Demo-Session` header cross-origin, so the app fetches the bytes
as a `Blob` and feeds the audio element an
`URL.createObjectURL(blob)`.

### Prompt-to-template wizard

`POST /api/v1/templates/wizard/chat` (`agents/wizard_chat.py`) drives a
**stateless, agentic, draft-first conversation**. The client owns the
message history + running draft; each turn the server returns the next
assistant message, an optional running `slots_filled`, a candidate
`TemplateWizardResponse` and a `ValidationReport`. The validator
(`agents/template_validator.py`) is a synchronous deterministic guardrail
— snake_case keys, duplicate keys, depends_on cycles, dot.namespaced
action keys, actions missing from the action catalog, invalid
JSONSchema in `payload_schema`, and `prompt_hints[].when` outside the
runtime mini-grammar. No LLM call, no `proposed_mocks`: hallucinated
action keys are stripped server-side in `wizard_chat` itself and
surfaced via `proposed_actions_from_catalog` on the wizard response.

**Agentic behaviour.** Gemini decides at every turn whether the available
context is rich enough to draft, or whether one more focused question
would materially improve the result. Conversation budget: 2-5 questions
(hard ceiling 5). The server injects an `AGENT STATE` meta-block into the
user prompt telling the model how many questions it has already asked,
and forces a draft once the budget is exhausted. `ready=True` can fire on
the very first turn if the user's first message already covers business
type + call flow. The wizard never asks for the template name (inferred
from context) and never asks about technical internals (schemas, ASR
dictionaries, payload shape, mock targets, privacy classes, confidence
thresholds). Hallucinated action keys are stripped post-response.

When `ready=true` the Expo screen `app/templates/wizard.tsx` lets the
operator refine inline and re-trigger `POST /api/v1/templates/validate`
if needed, then persist via `POST /api/v1/templates` (writes the draft
with `session_id=ctx.session_id` for demo or `NULL` for prod;
`version` is auto-bumped per `(name, session_id)`; `set_active=true`
switches the active template in the same transaction).

Fail-fast on missing key / Gemini error → HTTP 502. The legacy one-shot
endpoint `POST /api/v1/templates/wizard` was removed on 2026-05-17.

### Known caveats

- `requirements.txt` pins `speechmatics-batch>=0.4.8` because there is no 1.x
  release on PyPI as of writing (the original `>=1.0.0` pin was aspirational).
- `Template.payload_schema` (per action) is the JSONSchema the executor
  validates against. The Action Planner converts it to a Pydantic model
  at runtime (`integrations/jsonschema_to_pydantic.py`) and exposes the
  tool to Google ADK with typed parameters; the model accepts arbitrary
  JSONSchema only up to the dialect we actually use (`type: object` at
  top level, scalar / array / object properties, no `$ref` / `oneOf` /
  `anyOf`). Schemas outside the dialect fall back to a `dict` annotation
  and still pass through `jsonschema.validate` on the executor side.
- **Icon set:** Paper uses `MaterialCommunityIcons` (via `@expo/vector-icons`)
  by default. The Material Symbols icon `auto-awesome` is **not** available
  there; the AI-state indicators (ringing-phase AI FAB, "Afterglow listening"
  chip during the talking phase) use `creation` instead (thematically
  equivalent sparkle icon).
- **`PaperProvider` placement:** it lives **inside** `RootLayoutInner` (wrapped
  in `<GestureHandlerRootView>`) because the Paper theme depends on the
  `useTheme()` hook from our custom `ThemeContext`. Moving it above
  `ThemeProvider` breaks dark-mode toggling.
- **Tonal surfaces:** Paper v5 does **not** expose MD3's `surfaceContainerHigh`
  in the `MD3Colors` type. We use `theme.colors.elevation.level1 / level2 /
  level3` instead (e.g. briefing card on the Customer detail and Incoming
  call screens uses `level2`).
- **`AppTheme` + success palette:** the source-color generator
  (`@material/material-color-utilities`) leans pink on a blue seed, so
  `lib/paperTheme.ts` overrides `background` / `surface` / `surfaceVariant`
  / `outline` with flat neutrals and exports an `AppTheme` type that adds
  a semantic `success` / `onSuccess` / `successContainer` /
  `onSuccessContainer` palette (green in both modes). Screens that show
  a "success" / "completed" state (Audit log, Call detail, Customer
  detail, `Badge tone="success"`) call `useTheme<AppTheme>()` and read
  `theme.colors.successContainer` instead of `tertiaryContainer`
  (which is pink in light, purple in dark — semantically wrong).
- **Drawer theme propagation:** `@react-navigation/drawer` ignores the
  Paper theme by default. `app/(drawer)/_layout.tsx` reads
  `useTheme()` from Paper and passes the bridge explicitly via
  `drawerStyle.backgroundColor`, `sceneStyle.backgroundColor`,
  `drawerActiveTintColor`, `drawerInactiveTintColor`,
  `drawerActiveBackgroundColor`. Each `DrawerItem` also takes an
  explicit `labelStyle={{ color: theme.colors.onSurface, fontWeight:
  '500' }}` — without it the labels are unreadable in dark mode.
- **`Audio.play()` AbortError:** `lib/usePhoneAudio.ts` swallows the
  `AbortError "interrupted by a call to pause()"` that browsers emit
  when the operator hangs up mid-MP3. Hangup also uses
  `router.canGoBack() ? router.back() : router.replace('/(drawer)/(tabs)')`
  so a cold-loaded `/incoming-call` deep link doesn't leave a black
  screen behind a stale rejection toast.
- **Mock personal contacts:** the Contacts drawer entry mixes 20 hardcoded
  UK/US contacts from `app/lib/mockContacts.ts` with the server's `Customer`
  table. Resolution priority is *customer > mock > "Unknown caller"* (see
  `app/lib/callerResolver.ts`); contacts have no backend representation and
  no API — they exist purely client-side to make the "system phone app
  replacement" pitch credible.

## Demo

| What | Where |
|---|---|
| Demo site | https://demo.95-179-245-107.sslip.io |
| App (Expo web) | https://app.95-179-245-107.sslip.io |
| Backend API | https://api.95-179-245-107.sslip.io · `/health` returns `{"status":"ok"}` |
| Coolify admin | http://95.179.245.107:8000 (plain HTTP; team-only) |

## Production stack — auto-deploy from `main`

The only path to production is `git push origin main` against
[`Cleversoft-IT/hackaton-lablab`](https://github.com/Cleversoft-IT/hackaton-lablab).
A GitHub App webhook reaches Coolify on the Vultr VM, which rebuilds the two
Docker images and rolls them in. There is no manual deploy step.

```
local podman                git push                   Coolify (Vultr VM, FRA, vhf-2c-4gb)
─────────────              ─────────▶                  ───────────────────────────────────
 Postgres podman             main branch                 ┌─ afterglow-backend  (Dockerfile)
 .venv uvicorn          GitHub App webhook               │   entrypoint.sh: alembic + seed + uvicorn
 expo web :8081                                          │   :8000 → api.95-179-245-107.sslip.io
 vite :5173                                              │
                                                         ├─ afterglow-app      (Dockerfile, expo export -p web + nginx)
                                                         │   :3000 → app.95-179-245-107.sslip.io
                                                         │
                                                         └─ afterglow-demo     (Dockerfile, vite build + nginx)
                                                             :3000 → demo.95-179-245-107.sslip.io
                                                                  │
                                                         Vultr Managed Postgres 16 (hobbyist 1GB, FRA)
                                                         trusted-ips: VM /32 + dev IP /32
```

Environment variables (DB connection string, API keys, CORS allow-list) are
stored encrypted inside Coolify per Resource. They are **not** in the repo —
see [`reference_devops_pipeline.md`](../.claude/memory/reference_devops_pipeline.md)
for the source of truth. User-local credentials (Coolify API token etc.) live
outside the repo in `~/.config/afterglow/`.

Traefik on Coolify auto-issues a Let's Encrypt cert for each app domain.
[sslip.io](https://sslip.io) resolves `<ip-with-dashes>.sslip.io` to the
matching IP, so we get an HTTPS-ready domain with zero DNS setup.

### Per-app `watch_paths` (operational contract)

Coolify rebuilds a given application **only if the commit touches files
inside its `watch_paths`**. The current mapping is:

| App | `watch_paths` |
|---|---|
| `afterglow-backend` | `afterglow/backend/**` |
| `afterglow-app`     | `afterglow/app/**` |
| `afterglow-demo`    | `afterglow/demo-site/**` |

Consequence: **any new build input that lives outside one of those
sub-directories must be added explicitly to the `watch_paths` of every
app that depends on it** (root-level scripts, a future `shared/`
directory, a CI workflow file that influences the deploy, etc.) — or the
deploy simply will not fire. Same applies if a top-level directory is
ever renamed. The values are stored on the Coolify side via the API
(`PATCH /api/v1/applications/{uuid}`); see the snippet in
[`.claude/memory/reference_coolify_api.md`](../.claude/memory/reference_coolify_api.md).

The three Dockerfiles also enable a BuildKit cache mount for `pip` and
`npm` (`# syntax=docker/dockerfile:1.7` + `RUN --mount=type=cache,...`).
That keeps the package wheel cache across rebuilds of the same image,
shaving the dominant slice of build time when only application code
changes but the dependency layer is invalidated.

## License

MIT — see [LICENSE](LICENSE).

---

Built for [AI Agent Olympics @ Milan AI Week 2026](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon).
