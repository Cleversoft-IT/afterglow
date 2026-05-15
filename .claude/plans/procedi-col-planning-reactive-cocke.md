# Afterglow — Implementation Plan

> **⚠️ HISTORICAL / SUPERSEDED — verificato 2026-05-16.**
>
> Questo è il piano-master del 14-15 maggio. È stato in larga parte eseguito;
> alcune sezioni sono state poi sostituite da decisioni successive. **Non
> usarlo come roadmap o come mappa del repo.** Sezioni note come obsolete:
>
> - "Layout repo" cita `afterglow/frontend/` (Next.js) — cancellata; il
>   frontend è oggi `afterglow/app/` (Expo) + `afterglow/demo-site/` (Vite).
>   Il refactor è documentato nel piano `revisione-architettura-single-tenant-app-demo.md`.
> - Schema `businesses` + `business_id`: **droppato** dalla migration
>   `0002_drop_business.py`. Niente `template_versions` table. Niente
>   endpoint `/businesses/*`.
> - "Stack: `google-genai (no ADK runner)`" + "`integrations/gemini_adk.py`
>   legacy, may be removed" — falso: ADK è di nuovo attivo, usato da
>   `agents/action_planner.py` (commit `1c86292`).
> - `DEMO_MODE` env / `_FAKE_TRANSCRIPTS` — rimosse il 2026-05-15 (commit
>   `3a6f038`). I 3 MP3 demo reali sono ora persistenti in `app/assets/audio/`.
> - Lista degli step audit "5 step name": ora sono 6+ (aggiunto `action_planner`).
> - Route Next.js (`/dialer/incoming/[callId]`, `/dashboard/calls`, ecc.) —
>   non esistono. Le route attuali stanno in `afterglow/app/app/`
>   (expo-router file-based).
>
> Stato attuale → vedi `.claude/memory/project_afterglow_decisions.md`,
> `afterglow/docs/ARCHITECTURE.md`, `afterglow/README.md`.
>
> ---

> "What remains after the call." PWA + multi-agent backend AI che trasforma telefonate di prenotazione in **dati strutturati + memoria cliente + azioni eseguite autonomamente** (revert manuale post-fatto, non approvazione preventiva).
>
> **Target award:** Best use of Vultr ($5K+$1K credit) · Best use of Gemini ($5K) · Speechmatics ($200 credit, NO cash).
> **Tracks:** Enterprise Utility · Multimodal Intelligence · Agentic Workflows.
> **Deadline:** 19 maggio 2026 17:00 CEST · oggi 15 maggio · ~4 giorni di build rimasti.

---

## Changelog

> Storia delle decisioni-pivot. Le sezioni successive del piano sono già allineate
> a queste decisioni: leggi tutto il piano linearmente, senza disclaimer.

### 2026-05-15 — Single-tenant friendly UI
L'hackathon premia *Enterprise Utility verticale + autonomia decisionale*, **non**
SaaS multi-tenant (vedi `hackathon-docs/07-judging-criteria.md` e `02-challenge.md`).
Riposizionamento: "engine agentico verticalizzabile, **1 installazione per cliente**".
I 3 business demo (ristorante/dentista/carrozziere) restano come *esempi di template
verticali*, non come tenant attivi. `Business` resta tabella nel DB (toglierla
costava più che lasciarla), ma in UI è pinned via env `AFTERGLOW_DEFAULT_BUSINESS_ID`
+ endpoint `GET /api/v1/businesses/current`. Rimosse `/dashboard/business`, voce nav
"Business", dropdown "Business" nel Template Wizard. Il dialer demo
`/dialer/incoming/[callId]` continua a usare `listBusinesses()` per il routing per
dominio (è lo show "3 verticali su 3 URL" del pitch).

### 2026-05-15 — Pipeline post-call collassata in 1 Gemini call
Il flusso "Memory Retrieval Agent prima di Extraction Agent" è inutile per il
nostro modello (human-first AI dialer): l'operatore vede il `customer.memory_summary`
istantaneamente da Postgres, e *tutta* l'analisi AI gira **post-call**. Cancellati
i sub-agent scaffolding (`agents/extraction.py`, `agents/action_planner.py`,
`agents/memory_updater.py`, `agents/classification.py`) più `tools/` e i prompt
associati. Sostituiti da **`agents/call_analyzer.py`** — una sola chiamata Gemini
con `response_mime_type=application/json` + `response_schema=CallAnalysis` (Pydantic).
Lo schema produce in un colpo: fields/confidence/evidence, intent/sentiment/
language/urgency, planned_actions e `next_call_briefing`. La RAG di Vultr è
**pre-fetch deterministico** prima dell'unico Gemini call (`memory_retrieval.py`
resta come step di lookup, non è più "agent"). Fallisce gracefully a "" se Vultr è
giù. `customer.memory_summary` ora ospita il `next_call_briefing` Gemini-generated
nella lingua detected. Etichetta UI in `CallerMemoryCard`: **"Next-call briefing"**.

### 2026-05-15 — Local development senza Docker
Su Fedora 43 usato **podman** (drop-in compatibile) per Postgres + venv/pip per
Python 3.11 + npm per il frontend. Tre fix one-off:
- `requirements.txt` aveva `speechmatics-batch>=1.0.0`, che non esiste su PyPI
  (max reale 0.4.8). Pinnato `>=0.4.0`.
- `next.config.mjs` ha `rewrites()` per `/api/v1/* → backend`. Le rewrites
  valgono **solo per fetch lato browser**: le pagine sono Server Components, la
  fetch parte da Node e ignora le rewrites. Fix in `frontend/src/lib/api.ts`:
  `BASE = typeof window === 'undefined' ? process.env.NEXT_PUBLIC_API_BASE : ''`.
- Aggiunto `frontend/.env.local` con `NEXT_PUBLIC_API_BASE=http://localhost:8000`
  (Next non legge l'`.env` della root del repo).

### 2026-05-15 — Gemini free tier verificato live
Tutti i modelli **Flash** sono utilizzabili gratis con una key Google AI Studio
generata da account Workspace. I **Pro** rispondono 429 (RESOURCE_EXHAUSTED) sul
free tier. Sorpresa: `gemini-3-flash-preview` **è gratis** sul free tier (la voce
"Gen 3 è paid-only" su molti blog è inesatta) — resta come
`GEMINI_TEMPLATE_BUILDER_MODEL`. Default scelto: `gemini-flash-latest` (alias
sempre puntato al Flash più recente, veloce nei test, output non vuoto su prompt
brevi a differenza di `gemini-2.5-flash` che consuma tutto il budget in "thinking").

### 2026-05-15 — Trappola Vultr API key documentata
La `VULTR_API_KEY` di account (Settings → API) non vale come `INFERENCE_API_KEY`.
L'endpoint inference risponde `"Invalid API key"` finché non usi una chiave
generata da *Serverless → Inference → <subscription> → API keys*. Warning box
aggiunto in `hackathon-docs/12-vultr-deep-dive.md`.

---

## Context

Stiamo costruendo Afterglow per l'AI Agent Olympics Hackathon @ Milan AI Week 2026. La sfida richiede *"autonomous AI agents that move beyond copilots — into real decision-making systems that create measurable enterprise value."*

Il problema reale: piccole attività appointment-driven (ristoranti, dentisti, carrozzieri) ricevono prenotazioni al telefono ma perdono i dati lungo il flusso quotidiano (post-it, memoria, distrazione). I copilot "AI receptionist" che parlano al posto dell'umano sono già diffusi e snaturano la relazione cliente.

**Afterglow inverte la prospettiva:** l'umano continua a parlare con il cliente; l'AI ascolta sotto-traccia (opt-in via "cornetta blu"), trascrive con diarization, struttura i dati, retrieve la memoria del cliente da chiamate precedenti, ed **esegue autonomamente le azioni** (booking, WhatsApp di conferma, update CRM). Ogni azione è revertibile manualmente dal post-call screen, ed è loggata in un audit production-shape.

L'autonomia full è una scelta consapevole: la challenge premia *autonomous decision-making systems*, non copilot. La revertibilità + audit + confidence/evidence visibili sono la trust net che giustifica l'autonomia.

Output atteso a fine sviluppo:
- Repo GitHub pubblico (MIT) con setup riproducibile e architecture diagram
- Demo URL pubblica HTTPS deployata su Vultr (Coolify)
- Video MP4 ≤5 min con storyboard pitch + multilingual demo + wow moment "prompt-to-template"
- Slide PDF
- Submission lablab con tag espliciti Vultr + Google + Speechmatics

---

## Decisioni già prese (non rinegoziare senza ridiscutere)

- **Nome:** Afterglow — "What remains after the call"
- **Autonomia full:** AI esegue, user reverte. Backend per-template-action può marcare `execution_mode: manual-only` come eccezione (es. cancellazioni).
- **Single-tenant per cliente** (revisione 15 maggio): 1 installazione = 1 attività cliente. `Business` resta nel DB ma in UI è pinned via env `AFTERGLOW_DEFAULT_BUSINESS_ID`. I 3 business demo sono *esempi di template verticali*, non tenant attivi.
- **Pipeline post-call single Gemini call** (revisione 15 maggio): zero AI durante la chiamata; un solo `genai.generate_content` con `response_schema=CallAnalysis` produce extraction + classification + planned actions + next-call briefing.
- **Speechmatics:** solo voice-in (no Voice-out / Flow API). Bonus diarization + multilingual + custom dictionary.
- **Forma mobile:** PWA, no APK. Demo con audio pre-registrati / upload.
- **Integrazioni esterne (booking, WhatsApp, email, CRM):** mock per hackathon.
- **Dataset audio:** generato con TTS Speechmatics consumando il credit $200.
- **Stack:** Python 3.11 · FastAPI · google-genai (no ADK runner) · speechmatics-batch · SQLAlchemy 2.0 async · podman/docker per Postgres locale · Vultr Cloud Compute + Coolify per deploy. Baseline `Stephen-Kimoi/gemini-multimodal-document-agent` come pattern di partenza, oggi divergente.
- **Scope:** prompt completo, sviluppo incrementale demo-ready a ogni checkpoint.

Memoria persistente (versionata, team-shared): `/.claude/memory/` nella root del repo.
Vedi `CLAUDE.md` in root per l'index.

---

## Architettura (cuore tecnico)

**Human-first, AI-post-call.** Durante la chiamata l'umano parla e l'operatore
vede il `customer.memory_summary` letto da Postgres in una SELECT (zero AI,
latenza trascurabile). Tutta l'analisi AI gira **dopo** la chiusura della call,
in un unico Gemini structured-output call grounded sul transcript completo + i
fatti retrieved dalla RAG di Vultr.

```
Frontend PWA (Next.js)
  │ Operator opens /dialer/incoming/[callId]
  │ → GET /api/v1/customers/by-phone/{e164}  →  customer.memory_summary
  │   (zero AI, just Postgres)
  │
  │ Human handles the call. Operator taps the blue button → upload audio.
  │ POST /api/v1/calls (multipart) → 202 + call_id
  ▼
FastAPI background task — backend/app/agents/orchestrator.py
  │
  ├─► 1) Speechmatics batch
  │     AsyncClient.transcribe(diarization='speaker', language='auto',
  │                            additional_vocab = template.custom_dictionary)
  │     Heuristic: size < 4 KB OR DEMO_MODE=true → use canned transcript.
  │
  ├─► 2) Customer match
  │     SELECT customers WHERE business_id=? AND phone_e164=?
  │
  ├─► 3) Vultr RAG pre-fetch  (vultr_inference.chat_completion_rag)
  │     "Return facts about phone {e164}" against business.vultr_collection_id
  │     Failure → prior_facts = "" (non-fatal).
  │
  ├─► 4) Single Gemini structured-output call (call_analyzer.analyze_call)
  │     model = GEMINI_DEFAULT_MODEL (gemini-flash-latest)
  │     response_schema = CallAnalysis (Pydantic):
  │       - fields[]  (key, value, confidence, evidence)
  │       - intent, sentiment, language, urgency
  │       - planned_actions[]  (subset of template.action_types where 'auto')
  │       - next_call_briefing  (NL paragraph, in detected_language)
  │
  ├─► 5) Persist ExtractedFields  (3 JSONB dicts: fields/confidence/evidence
  │                                + intent/sentiment/urgency)
  │
  ├─► 6) Deterministic Action Executor  (executors/action_executor.py)
  │     For each planned_action: lookup mock in MOCK_REGISTRY, run, write
  │     ExecutedAction with status executed | manual_required | failed.
  │
  └─► 7) Memory write-back
        customer.memory_summary = analysis.next_call_briefing (Postgres, UI-visible)
        Push briefing as a new chunk → Vultr Vector Store
        (failure → kept in Postgres, vector indexing skipped, warning logged)

Audit log row per step (agent_name, step_type, model, duration_ms, status).
System of record: Vultr Managed Postgres.
Deploy: Vultr Cloud Compute + Coolify, IAM Service User + OIDC GitHub Actions.

Separately — Template Builder (not part of the call pipeline):
  POST /api/v1/templates/wizard  →  template_builder.build_template()
  Single Gemini call with response_schema=TemplateWizardResponse.
  Tries GEMINI_TEMPLATE_BUILDER_MODEL (gemini-3-flash-preview), falls back to
  GEMINI_DEFAULT_MODEL, then to an offline barbershop stub.
```

**Modelli per task:**

| Task | Modello | Motivo |
|---|---|---|
| Call Analyzer (extract + classify + plan + briefing) | `gemini-flash-latest` (env: `GEMINI_DEFAULT_MODEL`) | Single structured-output call. Free tier, alias auto-aggiornato, non consuma tutto in "thinking" come `gemini-2.5-flash` |
| Memory Retrieval (RAG pre-fetch) | **Vultr `/v1/chat/completions/RAG`** con `kimi-k2-instruct` | Endpoint che combina retrieval + chat → unico signal Vultr "non decorativo". Pre-fetch deterministico, fallisce a "" |
| Memory write-back (vector indexing) | Vultr `/v1/vector_store/{id}/items` | Embedding auto-calcolato dal Vector Store, niente embedder esterno |
| Template Wizard | `gemini-3-flash-preview` (env: `GEMINI_TEMPLATE_BUILDER_MODEL`), fallback `gemini-flash-latest` | Wow moment del pitch. Structured output con Pydantic `response_schema` |

**Multimodal audio (target Day 4):** oggi passiamo solo il transcript text a
Gemini. Per la track Multimodal Intelligence vogliamo aggiungere
`Part.from_bytes(audio_bytes, "audio/wav")` parallelamente al transcript, così
Gemini grounding su lexicon Speechmatics + tono/pause dall'audio. Non bloccante
per il submission; bonus se entra Day 4.

---

## Layout repo

Monorepo `/afterglow/` sotto la root del progetto, 2 services Coolify su una VM.
Struttura attuale (le voci marcate ⏳ sono ancora da creare):

```
afterglow/
├── LICENSE                           # MIT
├── README.md                         # setup + architecture + 3 award sections
├── CLAUDE.md  (in repo root)         # team-shared Claude context, index su .claude/memory
├── .env  /  .env.example
├── docker-compose.yml                # podman/docker compatible (Postgres + backend + frontend)
├── .github/workflows/
│   ├── deploy.yml                    ⏳ OIDC → Vultr Service User → Coolify webhook
│   └── ci.yml                        ⏳
│
├── backend/                          # FastAPI + google-genai + speechmatics-batch + asyncpg
│   ├── Dockerfile                    # python:3.11-slim
│   ├── requirements.txt              # speechmatics-batch>=0.4.0 (NOT 1.x — non esiste su PyPI)
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                   # FastAPI lifespan + CORS + router include
│   │   ├── config.py                 # pydantic-settings, env-aliased AFTERGLOW_DEFAULT_BUSINESS_ID
│   │   ├── api/
│   │   │   ├── calls.py              # POST /calls (multipart audio), GET /calls/{id}, GET /calls
│   │   │   ├── customers.py          # GET /customers/by-phone, GET /customers/{id}
│   │   │   ├── templates.py          # CRUD + POST /templates/wizard
│   │   │   ├── actions.py            # POST /actions/{id}/revert
│   │   │   ├── audit.py              # GET /audit
│   │   │   └── business.py           # GET /businesses, /businesses/current, /businesses/{id}
│   │   ├── agents/                   # The whole post-call pipeline
│   │   │   ├── orchestrator.py       # run_pipeline() — drives the 7 steps end-to-end
│   │   │   ├── call_analyzer.py      # Single Gemini structured-output call (CallAnalysis Pydantic)
│   │   │   ├── memory_retrieval.py   # Vultr RAG pre-fetch (deterministic, non-fatal)
│   │   │   ├── template_builder.py   # Gemini structured-output for /templates/wizard
│   │   │   └── prompts/template_builder.md
│   │   ├── executors/
│   │   │   └── action_executor.py    # Deterministic; mock registry + revert
│   │   ├── integrations/
│   │   │   ├── speechmatics.py       # AsyncClient wrapper + size-guard fallback to canned transcript
│   │   │   ├── vultr_inference.py    # chat_completion(_rag), vector_store create/add
│   │   │   ├── gemini_adk.py         # ADK runner factory (legacy, may be removed)
│   │   │   └── mocks.py              # MOCK_REGISTRY: booking/whatsapp/sms/crm fake handlers
│   │   ├── db/
│   │   │   ├── engine.py             # asyncpg + SQLAlchemy 2.0 async
│   │   │   ├── models.py             # ORM: Business/Template/Customer/Call/ExtractedFields/ExecutedAction/AuditLog/CustomerMemoryChunk
│   │   │   └── seed.py               # 1 ristorante + 1 dentista + 1 carrozziere + 2 customer noti
│   │   ├── schemas/                  # Pydantic v2 (TemplateWizardResponse, CustomerCard, ...)
│   │   └── audit/logger.py
│   ├── alembic/versions/0001_initial_schema.py
│   ├── tests/
│   ├── sample_audio/                 ⏳ 6-12 file TTS Speechmatics
│   │   └── generate.py               ⏳ script per consumare il credit $200
│   └── sample_templates/             # YAML examples
│
├── frontend/                         # Next.js 14 App Router + PWA
│   ├── Dockerfile
│   ├── next.config.mjs               # rewrites /api/v1/* → backend (browser-only)
│   ├── .env.local                    # NEXT_PUBLIC_API_BASE=http://localhost:8000  (gitignored)
│   ├── public/
│   │   ├── manifest.webmanifest
│   │   ├── icons/
│   │   ├── audio-samples/silence.wav # 44-byte placeholder (size-guard triggers canned transcript)
│   │   └── og.png                    ⏳ cover 16:9 per submission
│   └── src/
│       ├── app/
│       │   ├── layout.tsx · page.tsx
│       │   ├── dialer/
│       │   │   ├── incoming/[callId]/page.tsx
│       │   │   └── post-call/[callId]/page.tsx
│       │   └── dashboard/
│       │       ├── layout.tsx
│       │       ├── calls/page.tsx
│       │       ├── customers/[id]/page.tsx
│       │       ├── templates/page.tsx
│       │       ├── templates/wizard/page.tsx
│       │       ├── audit/page.tsx
│       │       └── settings/privacy/page.tsx
│       ├── components/
│       │   ├── phone/                # BluePhoneButton, IncomingCallScreen, CallerMemoryCard, PostCallActions
│       │   └── ui/                   # shadcn/ui primitives
│       └── lib/
│           ├── api.ts                # SSR-aware BASE (typeof window === 'undefined' ? env : '')
│           ├── types.ts              # Mirror of Pydantic schemas
│           └── demoScenarios.ts      # 4 demo URLs by business_domain
│
├── docs/
│   ├── ARCHITECTURE.md               ⏳ diagram + rationale per i giudici
│   ├── DEMO_SCRIPT.md                ⏳ storyboard video
│   ├── SUBMISSION.md                 ⏳ testi pronti per il form
│   └── PITCH.pdf                     ⏳ generato day 5
│
└── infra/
    ├── coolify/{backend,frontend}.service.json   ⏳
    └── vultr/iam-policy.json                     ⏳
```

**Pattern riusati dal baseline `Stephen-Kimoi/gemini-multimodal-document-agent`:**
- `app/agent.py` baseline → spunto per `backend/app/integrations/gemini_adk.py`
  (ADK runner factory — di fatto non più usato dopo il pivot a single
  `genai.Client.aio.models.generate_content`; valutare se rimuoverlo Day 4)
- `app/main.py` baseline → `backend/app/main.py` (lifespan + CORS)
- `Dockerfile` baseline → riusato per il backend
- Pattern strutturato Pydantic + `response_schema` → `call_analyzer.py` e
  `template_builder.py` (entrambi usano lo schema Pydantic come contratto e
  parse `model_validate_json` sul `resp.text`)
- `docker-compose.yml` baseline → riusato (gira anche con `podman compose`)

---

## Schema database Postgres (Vultr Managed HP 1GB)

UUIDs v4. `created_at`/`updated_at` su ogni tabella. Schema `public`.

```sql
businesses (
  id uuid PK, name text, domain text, default_language text DEFAULT 'it',
  timezone text DEFAULT 'Europe/Rome', settings jsonb DEFAULT '{}'
)

templates (
  id uuid PK, business_id uuid FK, name text, version int DEFAULT 1,
  fields_schema jsonb,           -- {field_name, type, required, options[], sensitive}
  action_types jsonb,            -- [{key, label, execution_mode:'auto'|'manual-only', mock_target}]
  custom_dictionary text[],      -- per Speechmatics additional_vocab
  prompt_hints text, is_active boolean DEFAULT true,
  UNIQUE (business_id, name, version)
)

template_versions ( id, template_id FK, version int, snapshot jsonb )

customers (
  id uuid PK, business_id uuid FK, phone_e164 text, display_name text,
  preferred_language text, tags text[],
  memory_summary text,           -- short blurb mostrato in caller card
  total_calls int, last_call_at timestamptz,
  UNIQUE (business_id, phone_e164)
)
INDEX (business_id, phone_e164)

calls (
  id uuid PK, business_id FK, customer_id FK NULL, template_id FK,
  audio_url text, audio_duration_sec int, detected_language text,
  raw_transcript jsonb,          -- full Speechmatics output con diarization
  status text DEFAULT 'pending', -- pending|transcribing|analyzing|completed|failed
  started_at, completed_at
)

extracted_fields (
  id, call_id FK, fields jsonb, confidence jsonb, evidence jsonb,
  intent text, sentiment text, urgency text
)

executed_actions (
  id, call_id FK, customer_id FK, action_type text, payload jsonb, result jsonb,
  status text,                   -- executed|reverted|failed|manual_required
  reverted_at, reverted_by, reverted_audit_id FK
)

audit_log (
  id, call_id FK NULL, agent_name text, step_type text,
  -- step_type: tool_call|llm_call|action_exec|revert
  model text,                    -- 'gemini-2.5-flash'|'kimi-k2-instruct'|null
  input_tokens int, output_tokens int, duration_ms int,
  payload jsonb,                 -- redacted input/output
  status text, error text
)
INDEX (call_id, created_at), INDEX (agent_name, created_at DESC)

customer_memory_chunks (
  id, customer_id FK, call_id FK,
  vultr_collection_id text, vultr_item_id text,
  summary text, metadata jsonb,
  UNIQUE (vultr_collection_id, vultr_item_id)
)
```

**PII marker** (per privacy panel): `customers.phone_e164`, `customers.display_name`, `calls.audio_url`, `calls.raw_transcript`, `extracted_fields.fields`.

**Revert flow:** UPDATE `executed_actions.status='reverted'` + INSERT audit_log `step_type='revert'` + INSERT compensating action mock. Idempotente.

---

## Vector Store schema (Vultr)

**Una collection per `business_id`**. Filtri per phone fatti dal modello RAG
durante la query (la collection contiene chunk di tutti i customer del business).

**Cosa pushiamo oggi** (stato attuale, semplificato):
```json
{
  "content": "<analysis.next_call_briefing>",
  "description": "call_<uuid>"
}
```
La collection record `customer_memory_chunks` in Postgres mantiene il join
locale: `(customer_id, call_id, vultr_collection_id, vultr_item_id, summary,
chunk_metadata={intent, sentiment, language, urgency})`.

**Cosa potremmo pushare (target)** — se vogliamo metadata strutturati nel
content del chunk per query più mirate:
```json
{
  "content": "Customer Marco Rossi called on 2026-05-12 ... [briefing] ...
              [intent: booking_new] [tags: gluten_free] [party_size: 4]",
  "description": "call_<uuid>_<intent>"
}
```

Endpoint usati:
- `POST /v1/vector_store` con `{"name": "afterglow-<business_id>"}` per creare
  la collection on-demand (`vultr_inference.create_vector_collection`).
- `POST /v1/vector_store/{id}/items` con `{"content": briefing, "description":
  "call_<uuid>"}` (embedding auto-calcolato dal Vector Store, no charge —
  `12-vultr-deep-dive.md` r. 158-170).
- `POST /v1/chat/completions/RAG` con `{"collection": <id>, "model":
  "kimi-k2-instruct", "messages": [...]}` per il retrieval pre-call (vedi
  `agents/memory_retrieval.py`).

**Bootstrap demo:** seed Postgres ha già `memory_summary` italiani per Marco
Rossi + Giulia Bianchi. Al primo run Vultr-up, il flow `_persist_memory`
popolerà anche la collection cross-call. Se serve un kick-start più veloce per
il pitch, aggiungere uno script `seed_vector.py` che pre-pusha 2-3 chunk fake.

---

## Pipeline end-to-end (per chiamata)

1. **Frontend POST** `/api/v1/calls` multipart (`audio`, `business_id`,
   `template_id`, `phone_e164`) → 202 + `call_id`. Audio saved in
   `AUDIO_STORAGE_DIR`, INSERT `calls` (status `pending`).
2. **Background task** `orchestrator.run_pipeline(call_id)` parte qui. Status →
   `transcribing`.
3. **Speechmatics transcribe** (`integrations/speechmatics.transcribe_audio`).
   `AsyncClient.transcribe` con `diarization=speaker`, `language=auto`,
   `additional_vocab=template.custom_dictionary`. Heuristic: audio < 4 KB OR
   `DEMO_MODE=true` → canned IT transcript (zero crediti spesi sul placeholder).
   UPDATE `calls`: `raw_transcript`, `detected_language`, status `analyzing`.
4. **Customer matching:** SELECT by `(business_id, phone_e164)`. Se trovato,
   `calls.customer_id` settato.
5. **Vultr RAG pre-fetch** (`memory_retrieval.retrieve_customer_context`).
   `POST /v1/chat/completions/RAG` con `collection=business.vultr_collection_id`
   + prompt "Return facts about phone {e164}". Output → string `prior_facts`.
   Errore HTTP → log warning, `prior_facts = ""` (non-fatal).
6. **Single Gemini structured-output call** (`call_analyzer.analyze_call`).
   `genai.Client.aio.models.generate_content` con `response_schema=CallAnalysis`.
   Output: per-field extractions (key/value/confidence/evidence) +
   intent/sentiment/language/urgency + planned_actions[] (subset di
   `template.action_types` con `execution_mode=auto`) + `next_call_briefing`
   (paragrafo NL nella lingua detected).
7. **Persist `ExtractedFields`** (3 JSONB dicts ottenuti coercendo i field LLM
   ai tipi del template via `_cast_value`).
8. **Deterministic Action Executor** (`executors/action_executor`). Per ogni
   planned_action: lookup `MOCK_REGISTRY[action_type]` + INSERT `ExecutedAction`
   con `status=executed`. Se `execution_mode=manual-only` → `manual_required`
   (no auto-run). Audit log per ognuno.
9. **Memory write-back** (`orchestrator._persist_memory`):
   - `customer.memory_summary = analysis.next_call_briefing` (Postgres → UI)
   - `customer.total_calls += 1`, `last_call_at = now`
   - `vultr_inference.create_vector_collection` (lazy, se mancante) +
     `add_vector_item(content=briefing)` (failure → warning, skip indexing,
     Postgres-only briefing intatto)
   - INSERT `CustomerMemoryChunk` con metadata `{intent, sentiment, language, urgency}`
10. **UPDATE `calls`** status `completed`, `completed_at = now`.
11. **Frontend polling** GET `/api/v1/calls/{id}` → post-call screen con
    extracted fields, executed actions + Revert button, transcript diarizzato.

**FastAPI endpoints (current):**

| Method | Path | Scopo |
|---|---|---|
| POST | `/api/v1/calls` | Upload + start, returns 202 + call_id |
| GET | `/api/v1/calls/{id}` | Status + risultati |
| GET | `/api/v1/calls?business_id=&customer_id=&limit=` | Lista filtrabile |
| GET | `/api/v1/customers/by-phone/{e164}?business_id=` | Caller lookup (caller card) |
| GET | `/api/v1/customers/{id}` | Profile + history |
| GET | `/api/v1/templates?business_id=` | Lista template del business |
| GET | `/api/v1/templates/{id}` | Singolo template |
| POST | `/api/v1/templates/wizard` | Prompt-to-template (Gemini structured output) |
| POST | `/api/v1/actions/{id}/revert` | Revert idempotente |
| GET | `/api/v1/audit?call_id=` | Audit paginato |
| GET | `/api/v1/businesses` | Lista (usata solo dal demo dialer multi-dominio) |
| GET | `/api/v1/businesses/current` | Il business pinned per questa istanza (single-tenant) |
| GET | `/api/v1/businesses/{id}` | Singolo business |
| GET | `/health` | Coolify healthcheck |

---

## Frontend PWA — route map

| Route | Componente chiave | Note |
|---|---|---|
| `/` | landing + "Pick a number to call" + 4 demo URLs | Entry point del pitch |
| `/dialer/incoming/[callId]` | IncomingCallScreen + BluePhoneButton + CallerMemoryCard | Mobile chrome 375px. Customer noto → caller card pre-call con `next_call_briefing` |
| `/dialer/post-call/[callId]` | PostCallActions + TranscriptView + Revert | Extracted fields + executed actions con Revert. Transcript diarizzato |
| `/dashboard/calls` | CallList + filtri | Drawer dettaglio = stessa view post-call |
| `/dashboard/customers/[id]` | CustomerProfile + history | `memory_summary` editabile (override umano) — *target* |
| `/dashboard/templates` | TemplateLibrary | Lista template del business pinned, no business switcher |
| `/dashboard/templates/wizard` | TemplateWizard (prompt → generated template preview) | **WOW MOMENT** del pitch — wirato live su Gemini 3 Flash Preview |
| `/dashboard/audit` | AuditLogTable + filtri (agent, step, date) | Production-shape signal per giudici Vultr |
| `/dashboard/settings/privacy` | toggle PII visible + retention slider | Trust/GDPR signal |
| ~~`/dashboard/business`~~ | rimossa (refactor single-tenant 15 maggio) | Era listato per il multi-tenant SaaS, non più valido |

**PWA:** `manifest.webmanifest` (standalone, theme `#1d4ed8`), icone 192/512 + maskable, service worker precaches shell. Demo: i giudici useranno desktop → fornire "Phone preview" mode (CSS frame 375px).

---

## Plan giornaliero (deadline 19 maggio 17:00 CEST)

Regola: **alla fine di ogni giorno deve esistere uno scenario demo end-to-end funzionante** (anche mocked). Costruzione a strati.

> Le checkbox ✅/⏳/❌ riflettono lo stato al 2026-05-15. ⏳ = parzialmente fatto o in corso, ❌ = bloccato/da fare. Il piano originale era "oggi 14 maggio" → quindi Day 1 = giovedì 14, Day 5 = lunedì 18; oggi (15 maggio) siamo dentro Day 2.

### Day 1 — 14 maggio — "Skeleton end-to-end fake"
**Demo-ready target:** upload audio mock → transcript fake → "1 booking mock created" → revert. **Status: software OK, infra Vultr ferma.**

- ✅ `git init` + LICENSE MIT + README + repo locale. **❌ Push a GitHub pubblico (da verificare)**
- ✅ Backend skeleton (deriva dal pattern del baseline `Stephen-Kimoi/gemini-multimodal-document-agent`, divergente dopo il refactor)
- ❌ Vultr account + free trial $250 + provisioning HP 2vCPU/4GB + Coolify + Managed Postgres HP 1GB → account vergine, profilo personale vuoto, no carta/coupon, no Inference subscription
- ❌ Vultr IAM Service User + OIDC GitHub Actions
- ✅ Speechmatics API key + URL configurata (coupon $200 da verificare nel pannello)
- ✅ Google AI Studio API key Gemini (free tier verificato live su 9 modelli)
- ✅ Schema DB → Alembic 0001 applicato (su Postgres podman locale, non Vultr managed)
- ✅ Backend `/health` + `/api/v1/calls` (pipeline completa, non più stub)
- ✅ Frontend Next.js + Tailwind + tutte le route principali
- ❌ Coolify auto-deploy webhook
- ❌ Demo URL HTTPS pubblica

**Fallback (se Vultr stallato):** rimandare deploy a Day 3-4, continuare sviluppo software in local.

### Day 2 — 15 maggio (oggi) — "Real pipeline single template"
**Demo-ready target:** upload audio restaurant ITA → Speechmatics → Gemini estrae → mock booking eseguita → UI mostra fields + actions. **Status: ✅ raggiunto e superato.**

- ✅ Speechmatics SDK wirato (`AsyncClient.transcribe` diarization + lang detect + custom_dictionary). Heuristic anti-silence preserva la demo
- ⏳ **TTS Speechmatics dataset** (6 audio in 3 lingue) — non ancora generato; richiede `sample_audio/generate.py`
- ✅ Estrazione + classificazione + action planning collassati in `call_analyzer.py` (single Gemini structured-output call con `response_schema=CallAnalysis`)
- ⚠️ **Vultr Kimi-K2 non più usato come classificatore separato** — assorbito nel Gemini call. Resta Kimi-K2 nel RAG retrieval (`/v1/chat/completions/RAG`). Se serve un secondo signal Vultr per la checklist, valutare di aggiungere un mini-classifier su `chat_completion` Vultr (vedi sezione "Aperture")
- ✅ Action executor + 4 mocks (`booking.create`, `whatsapp.send_confirmation`, `customer.update_profile`, `sms.send_reminder`)
- ✅ Audit log scrive per ogni step (5 step name: speechmatics, memory_lookup, call_analyzer, action_executor, memory_updater)
- ✅ Frontend Dialer (incoming → post-call) con BluePhoneButton, TranscriptView, PostCallActions, Revert
- ✅ Seed DB: 3 business (restaurant + dentist + bodyshop) + 3 template + 2 customer noti (Marco Rossi, Giulia Bianchi)
- ✅ Refactor single-tenant UI (rimosso Business switcher; pinned via env)

### Day 3 — 16 maggio — "Memory cross-call + revert + multi-template"
**Demo-ready target:** seconda chiamata stesso customer → caller card pre-call → Gemini usa memoria → action eseguita → revert funzionante → Dentist e Bodyshop trascrivono.

- ⚠️ Vultr Vector Store collection + push briefing post-call — codice wirato, **sblocco appena arriva una `INFERENCE_API_KEY` valida**
- ⚠️ Memory Retrieval RAG → injection in Gemini prompt — codice wirato, **stesso sblocco**
- ✅ `CallerMemoryCard` UI: GET `/customers/by-phone` mostra display_name + tags + prior_calls + last_call + next_call_briefing (Gemini-generated)
- ✅ Revert button + audit log
- ✅ Template dentist + bodyshop (seed)
- ✅ Dashboard `/dashboard/calls` + drawer
- ✅ Dashboard `/dashboard/customers/[id]`
- ✅ Custom dictionary Speechmatics per template

**Fallback memory cross-call:** pre-popolare Vector Store via seed script con chunk fake per il customer demo (resta accettabile per pitch).

**Cosa resta concretamente al Day 3:**
- Compilare l'onboarding Vultr (profile + carta/coupon) e generare l'`INFERENCE_API_KEY` per sbloccare RAG + Vector Store cross-call
- Generare `sample_audio/*.mp3` con TTS Speechmatics (script `generate.py`)
- Iniziare deploy Vultr (VM + Coolify + Managed Postgres + IAM Service User)

### Day 4 — 17 maggio — "Wow + production polish"
**Demo-ready target:** prompt-to-template wizard funzionante + audit UI + privacy panel + 3 lingue demo + Coolify deploy stabile su dominio.

- ✅ **TemplateBuilderAgent (Gemini 3 Flash Preview)** wirato: prompt → structured output Pydantic. Verificato live con prompt veterinario in italiano
- ✅ `TemplateWizard` UI già esistente, senza dropdown business
- ⏳ Audit log viewer `/dashboard/audit` con filtri (pagina esiste, filtri da verificare)
- ⏳ Privacy panel `/dashboard/settings/privacy` (pagina esiste, contenuto da verificare)
- ⏳ Multilingual demo: 1 audio ITA + 1 ENG + 1 ES (accento forte) → richiede TTS dataset Day 3
- ⏳ Architecture diagram nel README (Mermaid) — `docs/ARCHITECTURE.md` da scrivere
- ⏳ **Multimodal audio Gemini** (bonus): passare `Part.from_bytes(audio)` in `call_analyzer` accanto al transcript
- ❌ Coolify deploy con dominio custom + Let's Encrypt HTTPS
- ❌ Backup DB + snapshot VM
- ⏳ *(opzionale)* migrare a Interactions API beta per bonus Originality
- ⏳ Test demo flow completo zero→fine

**Fallback wizard:** già coperto — c'è fallback `gemini-flash-latest` + offline stub.

### Day 5 — 18-19 maggio — "Submission day" (deadline 19 maggio 17:00 CEST)
**Mattina (4h):**
- Registrazione **demo video MP4 ≤5 min** (storyboard sotto)
- Slide PDF 8-10 slide
- Cover image 16:9 PNG

**Pomeriggio (3h):**
- README finale (già aggiornato 15 maggio, eventuali ritocchi)
- Test demo URL HTTPS finale
- Compilazione **submission form lablab** con TUTTI i tag (Vultr · Google · Speechmatics · Multimodal · Enterprise Utility · Agentic Workflows)
- Save draft → review a freddo → submit

**Buffer:** 16:30 → 17:00 = re-submit fix lampo (le submission sono editabili fino a 17:00 — `06-what-to-submit.md` r. 60-68).

---

## Aperture aperte da decidere

Cose che il refactor del 15 maggio ha lasciato sul tavolo, da chiudere prima del submit:

1. **Secondo signal Vultr non-decorativo.** La Classification ora gira dentro Gemini, quindi Kimi-K2 è chiamato solo dal RAG retrieval. Per il bando "Best use of Vultr non decorativo" potrebbe essere prudente aggiungere un mini-uso aggiuntivo: per esempio una `chat_completion` su Kimi per generare il `next_call_briefing` (invece che farlo Gemini), oppure un re-rank dei retrieval chunks. Decidere Day 3-4.
2. **Multimodal audio raw a Gemini.** Oggi `call_analyzer` riceve solo il transcript text. Aggiungere il `Part.from_bytes(audio_bytes, "audio/wav")` apre la track Multimodal Intelligence + bonus tono/pause. Day 4.
3. **Audit log UI filtri.** La pagina esiste ma non l'ho verificata in dettaglio (filtri agent/step/date). Day 4 review.
4. **Privacy panel.** Stessa cosa — pagina esiste, contenuto da verificare.
5. **`integrations/gemini_adk.py` residuo.** Era previsto per ADK multi-agent. Dopo il refactor non viene chiamato. Valutare se rimuoverlo per pulizia o tenerlo come "fallback ADK runner" documentato.

---

## Best use of Vultr — checklist dimostrabile

| Item | Stato | Come dimostrarlo |
|---|---|---|
| `/v1/chat/completions/RAG` endpoint usato | ⚠️ wirato, key fix pending | `memory_retrieval.retrieve_customer_context` chiama l'endpoint. Audit log mostra `agent_name=memory_lookup`, `model=vultr-rag`. Sblocco appena arriva una `INFERENCE_API_KEY` valida |
| Vector Store popolato cross-call | ⚠️ idem | `_persist_memory` crea la collection per business + pusha il `next_call_briefing` di ogni call come nuovo chunk. Demo target: chiamata 1 → chiamata 2 stesso customer → caller card piena |
| Kimi-K2 non decorativo | ⚠️ ridotto a 1 agent | Solo `memory_retrieval` ora usa Kimi-K2 via `/RAG` (classification è stata assorbita nel single Gemini call). Se serve un secondo signal Vultr, considerare di mantenere un mini-classifier su `chat_completion` (no `/RAG`) — vedi sezione "Aperture" |
| Managed Postgres = system of record | ⏳ deploy | Tutte le tabelle (calls/customers/templates/extracted_fields/executed_actions/audit_log/customer_memory_chunks) visibili. Sul deploy passa da Postgres podman locale a Vultr Managed |
| IAM Service User + policy resource-scoped | ⏳ todo | `infra/vultr/iam-policy.json` da committare + screenshot nella slide |
| OIDC GitHub Actions | ⏳ todo | `.github/workflows/deploy.yml` con `id-token: write` |
| Coolify deploy + HTTPS auto | ⏳ todo | Demo URL pubblica + screenshot Coolify dashboard |
| Audit log production-grade | ✅ live | Tabella `audit_log` popolata da `audit/logger.py` per ogni step (speechmatics, memory_lookup, call_analyzer, action_executor, memory_updater). UI `/dashboard/audit` visualizza |

> Riferimenti: `12-vultr-deep-dive.md` r. 144-198 (RAG), r. 409-434 (IAM), r. 469-475 (tips), warning box su `VULTR_API_KEY` vs `INFERENCE_API_KEY`.

---

## Best use of Gemini — checklist dimostrabile

| Item | Stato | Come dimostrarlo |
|---|---|---|
| Structured Output Pydantic come contratto | ✅ live | Sia `call_analyzer.analyze_call` (response_schema `CallAnalysis`) sia `template_builder.build_template` (response_schema `TemplateWizardResponse`). Niente JSON prompt-engineering tricks |
| Single multi-purpose call | ✅ live | Una sola Gemini call produce: fields + classification + planned_actions + next_call_briefing. Costo basso, latency bassa, contratto enforced |
| Upgrade Gemini 3 selettivo | ✅ live | Template Wizard su `gemini-3-flash-preview`. Verificato funzionante sul free tier (a smentita di alcuni blog) |
| Fallback robusto | ✅ live | Template Wizard: `gemini-3-flash-preview` → `gemini-flash-latest` → offline barbershop stub. Call Analyzer: Gemini → offline canned analysis |
| Caveats schema gestiti | ✅ live | Gemini rigetta `additionalProperties` → `PlannedAction.payload` modellato come `payload_json: str` e decodificato nell'orchestrator |
| Multimodal audio nativo | ⏳ Day 4 | Aggiungere `Part.from_bytes(audio_bytes, 'audio/wav')` parallelamente al transcript text in `call_analyzer`. Bonus Multimodal Intelligence track |
| (opzionale) Interactions API beta | ⏳ Day 4-5 | Orchestrator migrato a Interactions per passi tipizzati osservabili — bonus Originality dichiarato in `13-gemini-deep-dive.md` r. 326. Rischio: poco testato, isolare in branch |

> Riferimenti: `13-gemini-deep-dive.md` r. 23-107 (Function Calling), r. 158-218 (Structured Output), r. 272-328 (Interactions API).

---

## Speechmatics — checklist bonus

| Item | Stato | Come dimostrarlo |
|---|---|---|
| Voice SDK Python diretto | ✅ live | `speechmatics-batch.AsyncClient.transcribe` in `integrations/speechmatics.py` — bonus dichiarato (`03-technology-partners.md` r. 610) |
| Diarization sempre attiva | ✅ live | `TranscriptionConfig(diarization='speaker')`. `_diarized_text` produce "S1: ... S2: ..." dal `results[]`. Mostrato in TranscriptView post-call — massive bonus (r. 613) |
| Custom dictionary per template | ✅ live | `template.custom_dictionary` → `additional_vocab=[{"content": t}, ...]`. Demo restaurant ha già 11 termini food (`celiachia`, `Nebbiolo`, ...) |
| Language detection auto | ✅ live | `TranscriptionConfig(language='auto')`. `_detect_language` legge `metadata.language_identification` → `calls.detected_language` |
| Multilingual demo | ⏳ Day 3-4 | 3 audio in 3 lingue (IT, EN, ES) — massive bonus (r. 612). Servono i sample audio TTS |
| Dataset generato con TTS Speechmatics | ⏳ Day 3-4 | Script `backend/sample_audio/generate.py` consuma il credit $200 = bonus engagement |
| Size-guard fallback | ✅ live | File <4 KB (silence.wav placeholder) → canned IT transcript, no crediti spesi sul flusso demo |

> Riferimenti: `03-technology-partners.md` r. 601-613 (pro tips Edgars), r. 656-672 (SDK).

---

## Demo video pitch — storyboard ≤5 min

| Scena | Durata | Contenuto |
|---|---|---|
| 1. Hook problema | 0:00 – 0:25 | "Ogni telefonata di prenotazione è un cliente che vince o perde. Oggi finisce su un post-it." |
| 2. Soluzione Afterglow + cornetta blu | 0:25 – 0:55 | Logo + tagline "What remains after the call". Animazione UI mobile: pulsante blu pulsing, "memory mode on" |
| 3. Chiamata #1 (nuovo cliente ITA) | 0:55 – 1:55 | Upload audio ITA → Speechmatics trascrive con diarization → Gemini extracts → mock booking + WhatsApp Done → revert button |
| 4. Chiamata #2 (stesso cliente) | 1:55 – 2:45 | Caller memory card PRIMA della call → Gemini usa la memoria → action eseguita autonoma. **Highlight Vector Store Vultr `/RAG` cross-call** |
| 5. Multilingual + autonomia | 2:45 – 3:15 | Audio ENG con accento → Speechmatics + lang detect → action eseguita (no approve, solo revert) |
| 6. Prompt-to-template wow | 3:15 – 4:00 | "Apro un barber shop, voglio data + servizio + barbiere + SMS" → TemplateBuilderAgent → template generato → caricato → testato |
| 7. Architettura partner | 4:00 – 4:40 | Diagramma: Speechmatics in · Gemini ADK orchestrator · Vultr Kimi-K2 + RAG · Postgres audit · Coolify. 3 award targets |
| 8. CTA + impatto | 4:40 – 5:00 | "Turns every call into structured memory + executed action. Live demo: afterglow.<domain>" |

---

## Submission checklist (ultime 4h del day 5)

Pre-compilati in `docs/SUBMISSION.md` durante day 4:

- **Title (≤50 char):** `Afterglow — Memory & Action from Every Call`
- **Short description (≤255):** "Afterglow turns booking phone calls into structured data, customer memory, and autonomously executed actions (booking, WhatsApp, CRM). Multi-agent AI on Vultr + Gemini + Speechmatics. Revert anytime."
- **Long description (≥100 parole):** problema → soluzione → multi-agent architecture → demo flow → TAM/SAM (15M SMB EU × €30/mese ≈ €5.4B) → USP "human talks, AI remembers and acts" → roadmap (CRM connectors reali, Voice-out Live API, Speechmatics on-prem)
- **Main Tracks:** Enterprise Utility · Multimodal Intelligence · Agentic Workflows
- **Technologies tagged (CRITICAL):** Vultr · Google (Gemini) · Speechmatics
- **Partners tagged:** Vultr · Google · Speechmatics
- **Participation Type:** Hybrid o On-site
- **Cover image 16:9 PNG**
- **Video MP4 ≤300MB ≤5 min upload diretto** (no YouTube/Drive)
- **Slide PDF 8-10 slide**
- **Repo GitHub PUBLIC con LICENSE MIT + README + diagram**
- **Demo URL HTTPS** funzionante in incognito

**Re-read a freddo (3 min prima Submit):**
- [ ] Vultr · Google · Speechmatics tutti flaggati?
- [ ] Repo public in incognito?
- [ ] Demo URL si apre in incognito?
- [ ] Video MP4 caricato (non link)?
- [ ] LICENSE MIT in root commit?
- [ ] README ha architecture diagram?

---

## Rischi + mitigazione

| # | Rischio | Impatto | Mitigazione |
|---|---|---|---|
| 1 | Speechmatics batch queue >2 min sui sample lunghi | Demo lenta | (a) Audio brevi 30-60s; (b) `DEMO_MODE=true` skippa Speechmatics e usa transcript canned IT (già implementato); (c) size-guard <4 KB già protegge il `silence.wav` placeholder |
| 2 | Vultr Inference key non disponibile per Day 5 | RAG + Vector Store down | (a) Pipeline degrada gracefully a warning + skip indexing (già implementato); (b) Postgres `customer.memory_summary` resta intatto come fallback caller card; (c) Worst-case pitch su Postgres-only memoria + spiegare il Vector Store come "wirato, in attesa di Inference subscription" |
| 3 | Gemini schema rifiuta `additionalProperties` | Call analyzer rotto | ✅ Risolto: `payload` modellato come stringa JSON (`payload_json`) e decodificato nell'orchestrator |
| 4 | Coolify/DNS/HTTPS non chiude prima della demo | No demo URL pubblica | (a) Setup non oltre Day 3; (b) fallback `<id>.sslip.io` + Cloudflare proxy HTTPS gratis; (c) ngrok tunnel in last resort; (d) `DEMO_MODE=true` + screen recording da localhost se il deploy è bloccato |
| 5 | Vultr trial $250 esaurito o carta non aggiunta | Inference/DB/VM down | (a) Profile + carta/coupon ASAP (oggi 15 maggio, bloccante per Day 3+); (b) monitor billing daily; (c) stima totale ~$15-18 (`12-vultr-deep-dive.md` r. 483-490); (d) fallback Postgres locale + Gemini diretto documentato nel README |
| 6 | Gemini Pro response 429 sul free tier (verificato 15 maggio) | Wizard/Analyzer cade su modello sbagliato | Default e fallback su `gemini-flash-latest` (free, verificato). Niente call Pro sul free tier |

**Bonus risk — time-boxing demo video:** se day 5 mattina deploy ha bug bloccante, registra video da localhost (giudici valutano *Presentation* dal video). Plan B: tieni demo URL pubblico anche solo come `/health`.

---

## File critici da leggere/riusare durante l'esecuzione

**Project memory (team-shared, versioned):**
- `/.claude/memory/MEMORY.md` — index delle memorie
- `/.claude/memory/project_afterglow_hackathon.md` — coordinate hackathon
- `/.claude/memory/project_afterglow_decisions.md` — pivot decisions lockati
- `/.claude/memory/feedback_code_language.md` — code in inglese, conversazione in italiano
- `/CLAUDE.md` (repo root) — auto-loaded da Claude Code, index su `.claude/memory/`

**Hackathon docs (read-only reference):**
- `/hackathon-docs/14-tutorial-gemini-vultr-document-agent.md` — baseline pattern
- `/hackathon-docs/12-vultr-deep-dive.md` — Serverless Inference, Vector Store, IAM, Coolify. **Warning box** sulla differenza `VULTR_API_KEY` vs `INFERENCE_API_KEY` (aggiunto 15 maggio)
- `/hackathon-docs/13-gemini-deep-dive.md` — function calling, structured output, Interactions API, Live API
- `/hackathon-docs/03-technology-partners.md` r. 560-680 — Speechmatics bonus pattern
- `/hackathon-docs/06-what-to-submit.md` — submission form e tag tagging
- `/hackathon-docs/07-judging-criteria.md` — 4 criteri ufficiali

**Baseline upstream (pattern di partenza, oggi divergente):**
- https://github.com/Stephen-Kimoi/gemini-multimodal-document-agent

**File chiave del repo (stato attuale + da creare):**
- ✅ `afterglow/backend/app/main.py` — FastAPI lifespan + router
- ✅ `afterglow/backend/app/agents/orchestrator.py` — drives the 7-step post-call pipeline
- ✅ `afterglow/backend/app/agents/call_analyzer.py` — single Gemini structured-output call
- ✅ `afterglow/backend/app/agents/memory_retrieval.py` — Vultr RAG pre-fetch (non-fatal)
- ✅ `afterglow/backend/app/agents/template_builder.py` — Gemini structured-output wizard
- ✅ `afterglow/backend/app/integrations/vultr_inference.py` — RAG + Vector Store client
- ✅ `afterglow/backend/app/integrations/speechmatics.py` — AsyncClient + size-guard fallback
- ✅ `afterglow/backend/app/db/models.py` — schema
- ✅ `afterglow/frontend/src/app/dialer/incoming/[callId]/page.tsx`
- ✅ `afterglow/frontend/src/components/phone/CallerMemoryCard.tsx`
- ✅ `afterglow/CLAUDE.md` (in repo root) + `.claude/memory/` versioned project memory
- ⏳ `afterglow/docs/ARCHITECTURE.md` — diagramma Mermaid per i giudici (Day 4)
- ⏳ `afterglow/docs/DEMO_SCRIPT.md` — storyboard video (Day 5)
- ⏳ `afterglow/docs/SUBMISSION.md` — testi pre-compilati form lablab (Day 4)
- ⏳ `afterglow/backend/sample_audio/generate.py` — TTS Speechmatics dataset (Day 3-4)
- ⏳ `afterglow/infra/vultr/iam-policy.json` (Day 3-4)
- ⏳ `afterglow/.github/workflows/deploy.yml` con OIDC (Day 3-4)

---

## Verification (come testare end-to-end)

### Smoke test locale (Day 1-2)
```bash
# Postgres
podman run -d --name afterglow-pg \
  -e POSTGRES_USER=afterglow -e POSTGRES_PASSWORD=afterglow -e POSTGRES_DB=afterglow \
  -p 5432:5432 -v afterglow-pgdata:/var/lib/postgresql/data \
  docker.io/library/postgres:16-alpine

# Backend
cd afterglow/backend
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
set -a && . ../.env && set +a
PYTHONPATH=. .venv/bin/alembic upgrade head
PYTHONPATH=. .venv/bin/python -m app.db.seed
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# In another shell — frontend
cd afterglow/frontend
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
npm install && npm run dev

# Smoke test (browser): http://localhost:3000/dialer/incoming/demo-restaurant-known
# → click "Answer with AI memory" → post-call screen with executed actions
```
Atteso: status `completed`, executed_actions ≥1, audit_log con step
`speechmatics` / `memory_lookup` / `call_analyzer` / `action_executor` /
`memory_updater`.

### Verifica audit pipeline (Day 2-3)
- `GET /api/v1/audit?call_id=<id>` mostra 5 step:
  - `speechmatics` (`tool_call`)
  - `memory_lookup` (`tool_call`, `model=vultr-rag`)
  - `call_analyzer` (`llm_call`, `model=gemini-flash-latest`)
  - `action_executor` (`action_exec`)
  - `memory_updater` (`tool_call`, `model=vultr-vector-store`)
- Ogni step con `duration_ms` non-null. Token counts disponibili solo quando il
  modello li ritorna (Gemini sì, le chiamate Vultr no).

### Verifica cross-call memory (Day 3, richiede Vultr `INFERENCE_API_KEY`)
- Chiamata #1 nuovo customer → INSERT `customers` + `customer_memory_chunks`
- Chiamata #2 stesso phone → `GET /api/v1/customers/by-phone/...` ritorna
  `memory_summary` popolato (briefing Gemini-generated) → caller card pre-call
  mostra dati
- `SELECT * FROM customer_memory_chunks WHERE customer_id=...` → ≥1 row

### Verifica revert (Day 3)
```bash
curl -X POST http://localhost:8000/api/v1/actions/<id>/revert
```
- `executed_actions.status='reverted'`, `reverted_at` settato
- `audit_log` nuovo step `revert`
- UI post-call mostra azione barrata (idempotente: secondo POST = no-op)

### Verifica prompt-to-template (Day 4)
```bash
curl -X POST http://localhost:8000/api/v1/templates/wizard \
  -H 'content-type: application/json' \
  -d '{
    "business_id": "<UUID>",
    "description": "I run a barbershop, extract date+service+barber, send SMS",
    "language": "en"
  }'
```
Atteso: JSON con `name` + `description` + `fields_schema` (4-10 elementi) +
`action_types` (2-5 con `execution_mode` esplicito) + `custom_dictionary` (8-20
termini) + `prompt_hints`. Validabile `TemplateWizardResponse.model_validate_json`.

### Verifica deploy pubblico (Day 4-5)
- `https://<demo-url>/health` → 200
- Apri demo URL in incognito → landing carica → demo scenario completo eseguibile
- Lighthouse PWA installability check (target ≥85)

### Verifica submission readiness (Day 5)
- Repo public in incognito
- LICENSE MIT in root commit
- Architecture diagram in README (sezione "Architecture" già presente)
- Video MP4 ≤300MB ≤5 min playabile
- Submission form: tutti i 3 partner taggati
