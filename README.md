<h1 align="center">Afterglow</h1>

<p align="center">
  <span>The dialer that takes notes for you.</span>
</p>

<p align="center">
  <a href="https://afterglow.cleversoft.it">Live demo</a>
  ·
  <a href="https://app.afterglow.cleversoft.it">Operator app</a>
  ·
  <a href="https://api.afterglow.cleversoft.it/health">API health</a>
  ·
  <a href="docs/ARCHITECTURE.md">Architecture</a>
</p>

<p align="center">
  <img alt="Expo" src="https://img.shields.io/badge/Expo-54-000020?style=flat-square&logo=expo" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi" />
  <img alt="Postgres" src="https://img.shields.io/badge/Postgres-Vultr%20Managed-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-111827?style=flat-square" />
</p>

Afterglow is a phone-app shaped operator assistant for booking-driven
businesses. The human still answers the call. After the call ends, an agent
transcribes it, extracts the important fields, decides which follow-up actions
to run, writes a briefing for the next call, and records an audit trail of what
happened.

It began during the **AI Agent Olympics @ Milan AI Week 2026**, but it is not
meant to stop at a hackathon demo. This repository is the first working slice
of a product for small teams that still run on phone calls, memory, and sticky
notes.

Built in the open over a few intense days by a small team. First commit:
**2026-05-14 17:21 CEST** (`a3dc6e8`). Public demo deadline:
**2026-05-19**.

## Contents

- [Live Demo](#live-demo)
- [What It Does](#what-it-does)
- [Why](#why)
- [Product Principles](#product-principles)
- [Local Development](#local-development)
- [Agent Pipeline](#agent-pipeline)
- [Production Deployment](#production-deployment)
- [Hackathon Context](#hackathon-context)

## Live Demo

| What | URL |
|---|---|
| Public demo | <https://afterglow.cleversoft.it> |
| Operator app | <https://app.afterglow.cleversoft.it> |
| Backend health | <https://api.afterglow.cleversoft.it/health> |

The public demo embeds the real Expo web app in a phone frame. On first visit,
open **Templates**, pick one of the seeded business presets, then open **Test
simulator** from the drawer and run an incoming call.

The demo is intentionally hands-on: it behaves like a small business phone app,
not a video walkthrough. You can inspect the audit log, review every tool call,
and reset your own sandbox session without affecting other visitors.

## What It Does

| Area | What works today |
|---|---|
| Phone surface | Recents, keypad, contacts, incoming-call screen, call detail, customer detail, templates, settings. |
| Capture | Operator opts in with the **AI** button on the ringing screen. |
| Processing | The pipeline runs **after** the call, so the live conversation is not in the latency path. |
| Transcription | Speechmatics diarized transcription with language auto-detect. |
| Agent loop | Gemini/ADK agent can inspect transcript spans, query memory, execute actions, retry validation failures, flag review, and finalize the result. |
| Trust | Every action and agent turn is written to an audit log. Undo/Redo appears only when the action catalog says undo is safe. |
| Memory | Postgres stores operational state; Vultr Vector Store stores long-term customer memory for next-call briefings. |
| Templates | Prompt-to-template wizard drafts fields, action schemas, and simulation scripts for new business types. |

## Why

Small booking-driven businesses still handle important work over the phone:
restaurants, dental clinics, body shops, salons, hotels, clinics, gyms, events,
and local service companies. Each call contains details that are easy to lose:
a name, date, allergy, quote, vehicle plate, callback, preference, complaint,
or promised follow-up.

Most receptionist automation tries to replace the human. Afterglow keeps the
human in the relationship and automates the work around the call: the notes,
the follow-ups, the audit trail, and the memory.

## Product Principles

- **Human first.** The operator owns the relationship; software handles the
  repetitive after-call work.
- **Fast when it matters.** Nothing model-driven blocks the live conversation.
- **Visible by default.** Extracted fields, actions, confidence, retries, and
  failures are inspectable.
- **Undo where possible.** Actions are reversible only when the integration
  contract makes that honest.
- **Useful before perfect.** The first version focuses on the full loop:
  answer, understand, act, remember.

## Local Development

### Prerequisites

- Python **3.11**
- Node **20+** and npm
- Docker or Podman for local Postgres
- API keys for:
  - Google AI Studio
  - Speechmatics
  - Vultr Serverless Inference

The backend can start without Vultr vector configuration, but RAG retrieval and
write-back are skipped. Speechmatics and Gemini failures are treated as real
pipeline failures; there is no fake offline transcription or model stub.

### 1. Start Postgres

```bash
podman run -d --name afterglow-pg \
  -e POSTGRES_USER=afterglow \
  -e POSTGRES_PASSWORD=afterglow \
  -e POSTGRES_DB=afterglow \
  -p 5432:5432 \
  -v afterglow-pgdata:/var/lib/postgresql/data \
  docker.io/library/postgres:16-alpine
```

Docker works too:

```bash
docker run -d --name afterglow-pg \
  -e POSTGRES_USER=afterglow \
  -e POSTGRES_PASSWORD=afterglow \
  -e POSTGRES_DB=afterglow \
  -p 5432:5432 \
  -v afterglow-pgdata:/var/lib/postgresql/data \
  postgres:16-alpine
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill at least:

```env
GOOGLE_API_KEY=...
SPEECHMATICS_API_KEY=...
VULTR_INFERENCE_API_KEY=...
```

For host-side local development, also change the database URL from the
compose service name to localhost:

```env
DATABASE_URL=postgresql+asyncpg://afterglow:afterglow@127.0.0.1:5432/afterglow
AUDIO_STORAGE_DIR=./data/audio
```

Optional, if you have a Vultr Vector Store collection:

```env
VULTR_VECTOR_DEFAULT_COLLECTION=...
```

### 3. Install and Seed the Backend

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

set -a
. ../.env
set +a

PYTHONPATH=. .venv/bin/alembic upgrade head
PYTHONPATH=. .venv/bin/python -m app.db.seed
```

The seed creates the demo templates, customers, call history, and simulation
fixtures used by the app.

### 4. Install the Frontends

```bash
cd ../app
npm ci
printf 'EXPO_PUBLIC_API_BASE=http://localhost:8000\n' > .env.local

cd ../demo-site
npm ci
printf 'VITE_APP_URL=http://localhost:8081\n' > .env.local
```

### 5. Run Everything

Terminal A:

```bash
cd backend
set -a
. ../.env
set +a
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal B:

```bash
cd app
npm run web
```

Terminal C:

```bash
cd demo-site
npm run dev
```

Open <http://localhost:5173>. The demo site embeds the app from
<http://localhost:8081>.

## Repository Layout

```text
backend/       FastAPI, SQLAlchemy, Alembic, Gemini/ADK agents, integrations
app/           Expo Router app, React Native Paper UI, web export
demo-site/     Vite landing page that embeds the app
scripts/       Demo audio generation and capture utilities
docs/          Architecture, submission notes, hackathon references
submission/    Slides and public submission assets
```

## Stack

| Layer | Tech |
|---|---|
| App | Expo SDK 54, React Native, react-native-web, expo-router, TypeScript |
| UI | react-native-paper Material 3, React Navigation Drawer, Reanimated |
| Demo site | Vite, React, TypeScript |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2 |
| Speech | Speechmatics Batch STT, Speechmatics TTS for bundled demo audio |
| Agents | Gemini 3.1 Flash-Lite, Google ADK, typed Pydantic tool schemas |
| Memory | Vultr Vector Store, Vultr Serverless Inference RAG endpoint |
| Storage | Vultr Managed Postgres |
| Deploy | Vultr Cloud Compute, Coolify, Traefik, Let's Encrypt |

## Typical Demo Flow

1. Open <http://localhost:5173>.
2. Open the drawer and go to **Templates**.
3. Pick a seeded preset: restaurant, dentist, or body shop.
4. Open **Test simulator**.
5. Start a call from an existing or new customer.
6. Accept the call with the **AI** button.
7. Hang up and open the call detail.
8. Review extracted fields, executed actions, next-call briefing, and the
   agent reasoning trail.
9. Open **Audit log** to inspect the pipeline step by step.

## Agent Pipeline

```text
Expo app / simulator
        │
        │ POST /api/v1/calls
        ▼
FastAPI background task
        │
        ├─ Speechmatics batch transcription
        │  diarization + language auto-detect
        │
        ├─ Structured customer facts from Postgres
        │
        ├─ Gemini/ADK call agent
        │     tools:
        │       lookup_customer_memory(query)
        │       search_transcript(keyword)
        │       read_transcript_segment(start, end)
        │       template action tools
        │       flag_for_review(reason, severity)
        │       finalize_call(payload)
        │
        ├─ Persist extracted fields, actions, status, audit rows
        │
        └─ Write next-call briefing to Postgres
           and, outside demo sandbox mode, Vultr Vector Store
```

The agent observes action results and can retry corrected payloads on
validation failures. Mutating actions are guarded against duplicate execution.
Every turn is recorded in the audit log and linked back to visible UI state.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Demo Isolation

The hosted public demo is multi-visitor even though the product is shaped as a
single-tenant installation. Each browser session gets an `X-Demo-Session`
identifier. Calls, customers, audit rows, actions, and wizard-built templates
are scoped to that session.

To avoid polluting shared semantic memory, demo sessions do not write new
chunks into the Vultr Vector Store. The read path still works for seeded
customers through a pre-seeded collection, so judges can see real RAG retrieval
in the audit log.

## Template Wizard

The wizard is a stateless conversation endpoint:

```text
POST /api/v1/templates/wizard/chat
```

The client owns the chat history and running draft. Gemini decides whether to
ask another focused question or produce a template draft. A deterministic
validator checks field keys, action keys, dependency cycles, JSON schema shape,
and action catalog compatibility before the template can be saved.

Wizard-generated templates can also generate simulation scripts and MP3s, so a
new business type can be tested through the same incoming-call flow as the
seeded presets.

## Useful API Checks

```bash
# Backend health
curl -s https://api.afterglow.cleversoft.it/health

# Vultr Vector Store stats
curl -s https://api.afterglow.cleversoft.it/api/v1/admin/rag-stats | jq

# Probe RAG retrieval for a seed phone number
curl -s "https://api.afterglow.cleversoft.it/api/v1/admin/rag-probe?phone=%2B15551112233" | jq

# Run the pipeline from a transcript without uploading audio
curl -s -X POST https://api.afterglow.cleversoft.it/api/v1/admin/dry-run-pipeline \
  -H 'Content-Type: application/json' \
  -d '{"transcript":"Operator: Hi.\nCaller: Hi, this is Mark. Friday eight thirty, party of four please.","phone_e164":"+15551112233"}'
```

## Production Deployment

Production deploys from `main` through Coolify on a Vultr VM. The three runtime
resources are separate Dockerfile builds:

```text
afterglow-backend  /backend    FastAPI + migrations + seed + uvicorn
afterglow-app      /app        Expo web export served by nginx
afterglow-demo     /demo-site  Vite build served by nginx
```

Public routes:

```text
https://api.afterglow.cleversoft.it
https://app.afterglow.cleversoft.it
https://afterglow.cleversoft.it
```

Environment variables and secrets live in Coolify, not in the repository.
Traefik handles routing and Let's Encrypt certificates. DNS is a wildcard A
record for `*.afterglow.cleversoft.it` pointing at the Vultr VM.

Coolify `watch_paths` are scoped per app:

| App | Watch path |
|---|---|
| `afterglow-backend` | `backend/**` |
| `afterglow-app` | `app/**` |
| `afterglow-demo` | `demo-site/**` |

If a future shared package, root script, or config file becomes a build input,
update the affected Coolify watch paths or the deploy will not trigger.

## Hackathon Context

Afterglow was built for the AI Agent Olympics hackathon and targets:

- Agentic workflows: one multi-turn agent, tool use, retries, auditability.
- Vultr: Cloud Compute, Managed Postgres, Vector Store, Serverless Inference.
- Gemini: Gemini/ADK agent and template wizard.
- Speechmatics: live STT and generated demo-call audio.

The hackathon constraint shaped the current product boundary: a public,
credible, end-to-end demo first; deeper production concerns such as persistent
audio volumes, real outbound integrations, and longer retention policies are
next steps.

## Known Caveats

- The app is production-shaped, but still a hackathon-era codebase.
- Some integrations are simulated action buckets. `customer_profile` is the
  live internal action bucket.
- Demo audio is generated and bundled for the seeded templates. Wizard-built
  templates can generate their own audio when the required keys are configured.
- `speechmatics-batch` is pinned to the available 0.x SDK line.
- The web app uses React Native Web; native iOS/Android work is structurally
  close but not the release target of this repository yet.
- The production VM is small. Build choices intentionally avoid heavyweight
  packages that can OOM the Coolify builder.

## License

MIT. See [LICENSE](LICENSE).
