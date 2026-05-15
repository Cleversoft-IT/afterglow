# Afterglow

> **What remains after the call.**
>
> Human-first AI dialer that turns booking phone calls into structured data, customer memory, and autonomously executed actions — every action is revertible, every decision is traceable.

Built for the **AI Agent Olympics Hackathon @ Milan AI Week 2026** — targeting Best use of Vultr, Best use of Gemini, and bonus integration with Speechmatics.

## The problem

Small appointment-driven businesses (restaurants, dental clinics, body shops) still take bookings on the phone. Every call carries data that is easily lost: a name, a date, an allergy, a callback request. Post-its and memory don't scale. AI receptionists that talk *instead of* the human kill the relationship.

## The approach

The human keeps talking. The AI listens (opt-in via the **blue phone button**), transcribes with diarization, and **after** the call runs a single Gemini pass that extracts the fields, classifies the call, plans the follow-up actions and writes a one-paragraph briefing for the next operator. Every executed action lands on the post-call screen with a **Revert** button. Every step is logged in a production-shape audit log.

The autonomy is the whole point: the hackathon brief calls for *autonomous decision-making systems*, not copilots. The revert button + audit + confidence/evidence are the trust net that justifies the autonomy.

## Architecture

```
App (Expo + react-native-web)         ◄── embedded by ── Demo site (Vite)
       │ POST /api/v1/calls (audio + phone)
       ▼
FastAPI background task ─► Speechmatics batch (diarization + lang detect + custom dict)
       │                   (skipped in DEMO_MODE, falls back to a canned transcript)
       │
       ├─► Vultr Vector Store /v1/chat/completions/RAG  (pre-fetch: prior_facts)
       │   └─► single collection, configured via VULTR_VECTOR_DEFAULT_COLLECTION
       │
       ├─► Gemini structured-output call  (single Gemini pass — see app/agents/call_analyzer.py)
       │       prompt: transcript + template fields_schema + action_types + prompt_hints + prior_facts
       │       response_schema = CallAnalysis (Pydantic):
       │         - fields[]  (key, value, confidence, evidence)
       │         - intent, sentiment, language, urgency
       │         - planned_actions[]  (subset of template auto-actions)
       │         - next_call_briefing  (NL paragraph, detected language)
       │
       ├─► Action Executor (deterministic Python) ─► mock registry + Postgres + audit_log
       │
       └─► Memory write-back ─► customer.memory_summary (Postgres, operator-visible)
                                + new chunk pushed to Vultr Vector Store (semantic memory for next call)
```

The pipeline runs **entirely after the call ends** — the human-facing latency is whatever Postgres takes to return `customer.memory_summary`. No AI in the live-call hot path. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full diagram and rationale.

System of record: **Vultr Managed Postgres**. Deploy: **Vultr Cloud Compute + Coolify**. IAM: Service User minimal-privilege + OIDC GitHub Actions.

## Award alignment

### Best use of Vultr
- `POST /v1/chat/completions/RAG` powers the pre-call memory lookup
- Vector Store collection per business, populated by every completed call's `next_call_briefing`
- Vultr Managed Postgres as the system of record (every call, customer, action, audit row)
- IAM Service User with resource-scoped policy + OIDC GitHub Actions deploy
- Coolify auto-deploy with HTTPS via Traefik + Let's Encrypt
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
- Falls back to `gemini-flash-latest` (verified free-tier) as the default model
- Multimodal-ready: the analyzer interface accepts an `audio_bytes` argument and
  the `Part.from_bytes` path is wired in `app/integrations/gemini_adk.py` for the
  forthcoming multimodal upgrade
- Template Wizard wired live on `gemini-3-flash-preview` with structured
  output (Pydantic `response_schema=TemplateWizardResponse`); falls back to
  `gemini-flash-latest` and then to a hand-crafted offline template if both
  fail. Originality bonus is real, not aspirational

### Speechmatics
- `speechmatics-batch` SDK wired live (`AsyncClient.transcribe` with
  `diarization=speaker` + `language=auto` + `additional_vocab` from the
  template's `custom_dictionary`)
- For demo robustness, audio files under 4 KB (e.g. the bundled `silence.wav`
  placeholder) bypass Speechmatics and use a canned Italian transcript so the
  pitch flow never burns credit on a 44-byte file
- `DEMO_MODE=true` is an explicit kill-switch that forces the canned transcript
  even on real audio (handy for offline pitch recording)
- Multilingual demo planned (IT, EN, ES) with language detection auto

## Stack

| Layer | Tech |
|---|---|
| App | Expo SDK 54 · React Native · react-native-web · expo-router · expo-av · TypeScript |
| Demo site | Vite 5 · React 18 · TypeScript (static landing that iframes the app) |
| Backend | Python 3.11 · FastAPI · google-genai · SQLAlchemy 2.0 async · Alembic |
| Speech | Speechmatics batch SDK |
| LLM | Gemini Flash (default) · Gemini 3 Flash Preview (template wizard) · MiniMax-M2.7 on Vultr (RAG) |
| Storage | Vultr Managed Postgres · Vultr Vector Store |
| Deploy | Podman / Docker Compose · Vultr Cloud Compute HP · Coolify |

## Local development

### Prerequisites
- **Python 3.11** (the project pins this — newer 3.12+/3.14 may not have wheels
  for `google-adk` / `asyncpg`)
- **Node 20+** with `npm`
- A container runtime for Postgres only — **Docker** or **Podman** (this project
  was bootstrapped on Fedora 43 using `podman` and it works as a drop-in)
- API keys: Google AI Studio (free tier OK), Speechmatics (only needed when you
  flip `DEMO_MODE=false` to call the real STT), and a **Vultr Serverless
  Inference** key (the *Inference* one — not a Vultr Cloud account key, which
  has the wrong scope and answers `"Invalid API key"` on the Inference base URL)

### One-time setup

```bash
# Postgres (one command, no compose needed)
podman run -d --name afterglow-pg \
  -e POSTGRES_USER=afterglow -e POSTGRES_PASSWORD=afterglow -e POSTGRES_DB=afterglow \
  -p 5432:5432 -v afterglow-pgdata:/var/lib/postgresql/data \
  docker.io/library/postgres:16-alpine

# Backend: env + venv + migrations + seed
cp .env.example .env       # fill API keys; for fully offline demos set DEMO_MODE=true
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
set -a && . ../.env && set +a
PYTHONPATH=. .venv/bin/alembic upgrade head
PYTHONPATH=. .venv/bin/python -m app.db.seed   # 3 template presets + 2 known customers

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
iframe. Activate a template from the Templates tab, then press the blue
button on the Simulator to run the full post-call pipeline.

### Demo mode vs live AI mode

- **`DEMO_MODE=false`** (production-shape): the real Speechmatics SDK runs
  against any uploaded audio. The 4 KB size guard transparently swaps in the
  canned transcript when you upload the bundled `silence.wav` placeholder, so
  the demo dialer keeps working without paying for empty jobs.
- **`DEMO_MODE=true`** is the hard offline switch — Speechmatics is bypassed
  for *every* audio, regardless of size. Useful when recording the pitch
  video offline.
- Gemini and Vultr stay live in both modes; missing keys degrade those agents
  gracefully (stub fields / skipped indexing) without breaking the pipeline.

### Known caveats

- `requirements.txt` pins `speechmatics-batch>=0.4.0` because there is no 1.x
  release on PyPI as of writing (the original `>=1.0.0` pin was aspirational).
- The Pydantic `response_schema` passed to Gemini cannot contain a
  `dict[str, Any]` field — Gemini rejects schemas with `additionalProperties`.
  We model action arguments as a JSON string (`payload_json`) and decode them
  in the orchestrator.

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

## License

MIT — see [LICENSE](LICENSE).

---

Built for [AI Agent Olympics @ Milan AI Week 2026](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon).
