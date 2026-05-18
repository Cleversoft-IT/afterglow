---
name: project-afterglow-decisions
description: Decisioni di prodotto/architettura di Afterglow. Pivot da non rinegoziare senza ridiscutere. Aggiornato 2026-05-18 notte (round 10 polish — formatRelativeTime calendar-day-first per coerenza col section header; DENTIST_TEMPLATE rinominato "Patient booking" + booking_time label cleanup; helper idempotente _ensure_seed_templates_fresh per applicare il rename al DB già seedato; Wizard Stack.Screen Appbar.BackAction; initialsFromName(phone) revert §R round 3 a "+"/"#" hash-color; admin.py docstring "Three endpoints" incl. dry-run-pipeline non read-only; README sub-section "What to look at in the live demo" sotto Speechmatics con 7 bullet pitch-UX). 2026-05-18 (round 9 parte 2 — seed expansion 6→12 customer + ~20 historical AI booking call 6-8 settimane indietro, day_offset relativo a Setting[seed_anchor_date] + BULK UPDATE shift al boot, Vultr Vector Store **read-only attivo** su collection pre-seedata via lifespan task con idempotency per-call, RAG demo unskip via preseed_available + _seed_exists_for_phone, briefing esposto end-to-end su CallExtractedView + endpoint Regenerate summary con modulo dedicato briefing_regenerator, audit drawer overview-first ScrollView+Accordion call→agent→step→payload via LEFT JOIN Customer + listAudit limit=500). 2026-05-18 sera (round 9 parte 1 — Pixel CallRow pattern: BookingMarker icon-only nei filtri non-booking, RidialButton phone-outline su ogni row, status come freccia direzionale, sort chip swap-vertical inattivo; seed varietà: 6 seed customer via SEED_CUSTOMERS single source of truth + Sophie/Tom + busy-week ridistribuito Mark×2/Julia×1/Andrew×2/Laura×1/Sophie×2/Tom×1; upsert idempotente _ensure_seed_customers per DB round-8-clean). 2026-05-18 (round 8 — avatar tonal ring + appointment unification + 5 UX fix) — ContactAvatar usa tonal ring pattern (no border, no gap); `appointment.*` rimosso del tutto in favore di `booking.create` unificato per tutti i verticali con `booking_date`+`booking_time` in preconditions+required; formatRelativeTime estesa a giorni/settimane/mesi; bookings sort con dir asc/desc toggle + group-by booking_date; Contacts Clients chip parità Home; ringing screen microcopy "12h ago" senza prefix "last". 2026-05-18 (round 7 UI polish + seed credibility) — avatar legend brand (primary border per customer), CallListItem.customer_tags additivo, no-op tap su call non-client, Home chip primaryContainer, wizard ProgressBar, simulator card multilinea, prettyValue helper, template badge wrap, seed densification ~50 personal calls 9-17 mag con 1 pipeline_error e Customer.total_calls ricomputato. 2026-05-18 (round 6 UI consistency) — drawer active highlight uniforme, Test simulator dentro (drawer), call/customer detail con Card.Content + Pressable + tags inline, calls list senza icone phone-incoming. 2026-05-17 (round 5 fix cluster) — failure_kind computed, default_payload_schema arricchito al persistence boundary, Integration discovery HARD RULE nel wizard, template rename end-to-end, validator source-based filter, sidebar pulito + Contacts top-right Home + welcome dialog fresh install. 2026-05-17 (legacy cleanup) — wizard one-shot rimosso, conversational wizard chat unica via; residui PII/sanitizer ripuliti da docstring/prompts. 2026-05-17 (template simplification) — schema Template ridotto al solo product surface; mock_target/mutates spostati nel catalog. 2026-05-17 (notte) — simulator dei custom template wizard-built: solo bottone "new" + audio cross-origin via blob URL. 2026-05-17 (sera) — round 3 UI audit (drawer "Calls" voice, locale IT/EN via Intl.DateTimeFormat, BookingBadge inline, TranscriptList accordion, REAL_ON_DEVICE whitelist UI-only, randomuser.me portraits hard-coded, web first-paint sync, drawer reset via Paper Dialog, eager customer FK al submit). 2026-05-17 — frontend Material 3 rewrite + UI bug cluster post-rewrite. 2026-05-16 — feedback round 2 (action catalog, dialer non bloccante, Undo/Redo flip-only, simulator 2-mode con MP3 distinti existing/new e 4 customer seedati).
metadata:
  type: project
---

Decisioni iniziali del **2026-05-14** + revisioni del **2026-05-15** e **2026-05-16** (incluso il **feedback round 2** del pomeriggio). Ridiscutere solo con motivazione esplicita.

### 1. Autonomia agent — FULL
L'AI esegue **autonomamente** anche le azioni esterne (booking, WhatsApp, email, follow-up). Nel dialer le ex "pending actions" diventano **"executed actions con revert manuale"**. Eccezioni: nel backend l'utente può marcare alcune azioni specifiche come "manual-only" (no auto-execute).

**Why:** la sfida hackathon chiede esplicitamente *"autonomous decision-making systems, not copilots"*. Tenere human-in-the-loop su ogni azione classifica come copilot e perde punti su Originality + Application of Technology.

**How to apply:** UI dialer post-call mostra "executed / Revert" (non "Approve / Dismiss"). Backend ha `template.action_types[].execution_mode: auto | manual-only`. Default = auto. Tutto loggato in audit. Confidence/evidence visibili per giustificare l'esecuzione automatica.

### 1.bis. Single-tenant deployment (revisione 2026-05-15, completata 2026-05-16)
**1 installazione = 1 cliente.** I 3 business demo (ristorante/dentista/carrozziere) restano nel seed come *esempi di template verticali*, **non** come tenant attivi multi-SaaS.

La tabella `Business` è stata **droppata** (migration `alembic/versions/0002_drop_business.py`); single-tenant è ora enforced a livello di schema. Niente più `business_id` su nessuna tabella, niente più endpoint `/businesses/*`, niente env `AFTERGLOW_DEFAULT_BUSINESS_ID`, niente `listBusinesses()` / `getCurrentBusiness()` sul client. Il "verticale attivo" è espresso esclusivamente come `Template` con `is_active=True` (in produzione) oppure `demo_sessions.active_template_id` (in demo via iframe).

Lo show "3 verticali su 3 URL" continua nella demo, ma è il visitatore a scegliere il template attivo dalla tab Templates (`PUT /templates/active`); l'incoming-call dialer (`app/app/incoming-call.tsx`) parte dal template attivo, non da una lista di business.

**Why:** l'hackathon premia *Enterprise Utility verticale + autonomia decisionale*, non SaaS multi-tenant (vedi `hackathon-docs/07-judging-criteria.md` e `02-challenge.md`).

**How to apply:** se rivedi una sezione di codice o doc e trovi `business`, `business_id`, `getCurrentBusiness`, `listBusinesses`, `/businesses/current`, è un retaggio: va rimosso. Per il "template attivo" usa gli endpoint `/templates/active` e (in demo) lo state della `DemoSession`.

### 1.quater. Demo iframe isolation via `session_id` (2026-05-15)

L'app è caricata in iframe da `demo.95...` durante la judging window; più giudici cliccano contemporaneamente. Soluzione: ogni visitatore riceve un `X-Demo-Session: <uuid>` (server-minted, persistito su `localStorage`) e tutte le scritture sandbox sono scopate via `session_id` su 6 tabelle (`calls`, `audit_log`, `executed_actions`, `customer_memory_chunks`, `templates`, `customers`) + tabella `demo_sessions`. Letture: `WHERE session_id = me OR session_id IS NULL` — i seed sono shared read-only. Customer matchato dai seed → clone-on-write nella sessione. Pitch live via `?bypass=<token>` evita la sandbox e usa il tenant produzione.

**Vultr Vector Store read-only attivo in demo mode su collection pre-seedata** (round-9, 2026-05-18): la decisione iniziale era skippare sia RAG read che chunk write per 3 ragioni storiche — (a) l'SDK Vultr (`vultr_inference.py`) non espone metadata filter né su `/vector_store/{id}/items` né su `/chat/completions/RAG`, (b) una collection-per-sessione moltiplicherebbe risorse Vultr senza garanzia di cleanup, (c) il valore della RAG nella demo era marginale (1-2 call per giudice, niente "seconda chiamata stesso chiamante"). I 3 vincoli restano veri, ma il valore "marginale" è stato mitigato pre-seedando la collection condivisa al boot: il giudice vede il retrieval reale al **primo** ring di un seed customer, senza aspettare la seconda chiamata. Il preseed è un task lifespan (`backend/app/tasks/vector_preseed.py`) con **idempotency per-call**: marker `chunk_metadata @> '{"preseed": true}'::jsonb`, expected set = `SELECT id FROM calls WHERE is_seed AND raw_transcript IS NOT NULL`, diff su `call_id` → insert solo i mancanti. Sopravvive a partial failures (es. Vultr 500 a metà push) e a cambio dataset (aggiungere una seed Call inserisce automaticamente il chunk al prossimo boot; rimuovere richiede cleanup manuale via script o `DELETE FROM customer_memory_chunks WHERE chunk_metadata @> '{"preseed":true}'`). Le chunk preseed hanno `session_id=NULL` (analogo template/customer seed) e sono read-only da tutti i visitatori. **Il write-back resta skipped** in demo: `_persist_memory` continua a emettere `memory_updater status=skipped reason=demo_sandbox_vector_store_disabled` così la wiring "non inquino la collection con la tua call" resta esplicita al giudice. La logica di unskip read è centralizzata in `memory_retrieval.retrieve_customer_context(preseed_available: bool)` + `orchestrator._seed_exists_for_phone`. Production single-tenant continua a usare Vultr Vector Store a piena banda (read + write). Pitch Vultr Award è ora coperto da: preseed visibile nei boot log, audit row `rag_semantic` con `prior_facts_preview` non vuoto al primo ring, landing/README/ARCHITECTURE allineati. Dettagli e cleanup playbook: [[project-rag-demo-read-only]].

**Cleanup:** asyncio task in lifespan FastAPI sweep ogni 30 min sessioni con `last_seen_at < now-24h`, cascade delete di tutto il sub-tree.

**Reset on-demand (2026-05-16):** `POST /api/v1/demo/reset` (`app/api/demo.py`) chiama la stessa `purge_session_data` del cron sul `session_id` corrente con `drop_session_row=False`, poi azzera `active_template_id` e bumpa `last_seen_at`. La row `DemoSession` resta viva → il client mantiene la stessa uuid in `localStorage`, niente nuovo handshake. 403 in production. Pulsante "Reset demo" nella tab Settings dell'app (`app/(tabs)/settings.tsx`), visibile solo se `isDemoMode()`. Dopo il reset il client fa hard reload (web) / `router.replace('/')` (native); il gate `ActiveTemplateBootstrap` in `app/_layout.tsx` redirige a `/(drawer)/templates` se `getActiveTemplate()` ritorna 204. Il modal "soft warning" in `app/(drawer)/templates.tsx` intercetta `tabPress` sul parent navigator e avverte se l'utente lascia la pagina senza aver scelto un template. `GET /api/v1/templates/active` ritorna **204** per demo senza `active_template_id` (no fallback al seed `is_active=TRUE`, che resta solo per production).

**Why:** la decisione 1.bis (single-tenant in produzione) resta vincolata. La sandbox è layer opzionale che si attiva solo quando l'header è presente; production senza header = comportamento single-tenant immutato. Aderiscere al vincolo di prodotto + non bruciare Presentation per concorrenza demo.

**How to apply:** ogni nuovo endpoint deve aggiungere `ctx: SessionContext = Depends(get_session_context)` e usare `visibility_filter(Model.session_id, ctx)` per le letture, e impostare `session_id=ctx.session_id` sulle scritture. Ogni `audit_step(...)` deve ricevere `session_id=call.session_id` (o l'equivalente). Schema/migration: `0003_demo_sandbox_session.py`. Coordinate vive: `afterglow/backend/app/api/session_context.py`, `afterglow/backend/app/tasks/session_cleanup.py`.

### 1.ter. Pipeline post-call: Gemini analyzer + ADK action planner — **SUPERSEDED 2026-05-18 dal round-10 agentic single-agent (vedi sezione 1.quindici sotto)**
> ⚠️ Storico — la descrizione qui sotto del flusso a 3 step `call_analyzer` → `action_planner` → `action_executor` non è più la pipeline live. Il round-10 (2026-05-18) ha collassato tutto in un singolo agente ADK multi-turn (`agents/call_agent.py`), `action_planner.py` è stato eliminato, `call_analyzer.py` ridotto a soli schemi. Cerca **sezione 1.quindici** e [[project-agentic-pipeline]] per la forma attuale. Il testo qui sotto è preservato per archeologia (audit_log/storia commit).
>
> Cosa resta valido dalla 1.ter: l'invariante "AI runs **after** the call, never during", il fail-fast esplicito (no stub / no `_fallback_planner` / no deterministic fallback), il token accounting (`usage_metadata` Gemini + Vultr usage block scritti in `audit_log.input_tokens`/`output_tokens`).

**Architettura precedente (storica):** zero AI durante la chiamata; tutta l'analisi gira **dopo** la fine call. La pipeline post-call era **4 step**: `call_analyzer` → `action_planner` → `action_executor` → `_persist_memory`. Tutti loggati nello stesso `audit_log`:

1. **`agents/call_analyzer.py`** — singolo Gemini structured-output call. Lo schema Pydantic `CallAnalysis` produce in un colpo: fields/confidence/evidence, intent/sentiment/language/urgency, `planned_actions[]` (con `payload: dict[str, Any]` tipato, niente più `payload_json: str`) e `next_call_briefing` (paragrafo in linguaggio naturale per l'operatore della prossima call). Il prompt cita i `depends_on` per-field, e le `preconditions` / `confidence_threshold` / `evidence_required` per-action. Le `prompt_hints` (struttura `list[{when, then}]` dopo migration 0006) vengono valutate deterministicamente in Python contro `memory_retrieval.retrieve_structured_facts` PRIMA di costruire il prompt e prependute al system instruction quando matchano.
2. **`agents/action_planner.py`** — agentic loop via Google ADK (`integrations/gemini_adk.py`) che rilegge l'analisi del passo 1 e emette le tool call per le sole azioni `execution_mode=auto`. Ogni tool ha un parametro `payload` con annotation Pydantic dinamica costruita da `ActionDefinition.payload_schema` via `integrations/jsonschema_to_pydantic.py` (FunctionDeclaration tipizzata per Gemini). L'`executors/action_executor.py` ri-valida il payload con `jsonschema.validate` prima di MOCK_REGISTRY, rifiuta azioni con `evidence_required=True` ed evidence vuota, e legge `mutates` dal `action_catalog` propagandolo nell'audit + `ExecutedAction.result`. `_summarize_to_english` è un piccolo Gemini call extra (~120 token, dentro `orchestrator._persist_memory`) che genera l'EN summary del briefing quando la lingua detected non è EN (solo in prod), poi il chunk del Vector Store contiene native + EN.

PII/privacy classification e sanitizer sono **out of scope** (vedi `afterglow/docs/future-ideas.md` §4 + sezione 1.nove qui sotto).

**Fail-fast esplicito, niente fallback silenziosi (deciso 2026-05-16):** se manca `GOOGLE_API_KEY`, se Gemini fa raise/empty/JSON malformato, se l'ADK runner fallisce, la `Call` va in stato `failed` con `failure_reason` leggibile + audit row con `status="error"`. La UI mostra un banner rosso con la ragione. **Nessun stub deterministico, nessun "_fallback_planner".** Un demo che inventa "Marco in 4 alle 20:30" per ogni MP3 è una bugia che inquina la judging window; meglio mostrare l'errore vero e dimostrare che la pipeline è davvero AI-driven.

La RAG di Vultr è **pre-fetch deterministico** prima del Gemini call (`memory_retrieval.retrieve_customer_context`) e fallisce gracefully a stringa vuota — è degrado tollerabile perché "no prior facts" è uno stato semantico valido (cliente nuovo). Non confondere con un fallback AI.

**Storia del rientro di `action_planner.py`:** nella prima revisione del 2026-05-15 era stato cancellato per collassare tutto in una sola Gemini call. È stato re-introdotto con ADK il 2026-05-16 (commit `1c86292`) per allinearsi al criterio judging "Agentic Workflows / decision-making systems, not copilots". Resta **un solo** sub-agent post-`call_analyzer`, nessuno scaffolding ulteriore.

Cancellati (e tuttora assenti): `agents/extraction.py`, `agents/classification.py`, `agents/memory_updater.py`, l'intera cartella `app/tools/` e `app/pipeline/`. Cancellati il 2026-05-16: `_stub_analysis` in `call_analyzer.py` e `_fallback_planner` in `action_planner.py` (~115 LOC totali) — vedi sopra "Fail-fast esplicito".

**Token accounting (2026-05-16):** `audit_log.input_tokens` / `output_tokens` vengono popolate da `resp.usage_metadata` (Gemini) e dall'equivalente Vultr. Erano già a schema ma mai scritte; ora le scriviamo davvero per dare ai giudici la visibilità "trustworthy AI / cost-per-call audit".

**Why:** AI a fine call è il modello giusto per *human-first AI dialer*. L'operatore vede il `customer.memory_summary` da Postgres istantaneamente. Il double-step (analizzatore structured + planner agentico) tiene il pitch agentic; il fail-fast esplicito sostituisce la falsa robustezza del fallback con audit reale e UI onesta.

**How to apply:** `customer.memory_summary` è il "next-call briefing" Gemini-generated nella lingua detected. La tabella `extracted_fields.briefing_snapshot` (migration 0005) preserva la briefing storica per-call anche dopo overwrite di `memory_summary`. Quando si tocca la pipeline modifica `call_analyzer.py` per scope/prompt, `action_planner.py` per il tool registry / loop ADK, `action_executor.py` per la validation deterministica, `orchestrator.py` per glue/persistence + error state — non aggiungere altri sub-agent, non re-introdurre fallback "per sicurezza". Il `template_validator.py` vive in `agents/` per ragioni storiche ma dal 2026-05-17 è un guardrail deterministico puro (zero LLM call); vedi [[project_template_validator_deterministic]].

### 1.cinque. Templates v2 — schema strutturato + wizard 4-step (2026-05-16)
Estensione completa del `Template` landata con migration `0006_templates_v2.py`. Tutta v2 è additive a livello di codice ma cancella i dati esistenti (vedi [[feedback-db-disposable]]) per riallineare la shape.

**Schema esteso (vedi 1.nove per la simplification 2026-05-17):**
- `FieldDefinition` ha `confidence_threshold` opzionale per-field, `extractor_hint` (`regex|freeform|enum|llm_only`), `depends_on: list[str]`, `options`, `required`.
- `ActionDefinition` ha `preconditions: list[str]`, `confidence_threshold: float`, `evidence_required: bool`, `payload_schema: dict | None` (JSONSchema). Il payload_schema serve sia al planner (FunctionDeclaration tipizzata) sia all'executor (`jsonschema.validate`).
- `Template.prompt_hints` da `Text` a `JSONB` (`list[PromptHintRule]` con grammatica `always | field.<key> == '<value>' | field.<key> is [not] null`).
- Unique `(name, version)` espressa come **due partial unique index** (`session_id IS NULL` vs `IS NOT NULL`) per evitare la trappola Postgres "NULL distinct". POST `/templates` auto-bumpa la `version` per `(name, session_id)`.

**Wizard conversazionale (revisione 2026-05-17):** `POST /api/v1/templates/wizard/chat` (`agents/wizard_chat.py`) gestisce un dialogo stateless multi-turn. Il client tiene history + `slots_filled` + `draft_partial`; il server ritorna il prossimo turno + draft aggiornato + `ValidationReport` (deterministico — `agents/template_validator.py`, vedi [[project_template_validator_deterministic]]). Action keys allucinate vengono droppate dal draft direttamente in `wizard_chat.run_wizard_chat` e restituite via `proposed_actions_from_catalog`. Quando `ready=true`, UI Expo `app/templates/wizard.tsx` espone "Save draft / Save & activate" → `POST /api/v1/templates` (scrive con `session_id=ctx.session_id` in demo o `NULL` in prod, `set_active` opzionale nella stessa transazione). Il vecchio endpoint one-shot `POST /api/v1/templates/wizard` + `template_builder.py` sono stati **rimossi il 2026-05-17**.

**PII/privacy gating:** rimosso 2026-05-17 — vedi 1.nove + `afterglow/docs/future-ideas.md` §4.

**Bilingual briefing:** in prod, se `transcript.language != "en"`, `_summarize_to_english` produce un EN summary del briefing; il chunk del Vector Store contiene `native\n\n[EN] <en>` + metadata `language` + `briefing_en`. In demo è skipped.

**Why:** la sfida judging "Application of Technology" + "Agentic Workflows" premia template tipati end-to-end (FunctionDeclaration → executor validation) + un wizard che si valida da sé più di quanto premi un'UI di tuning. Le 3 idee scartate (parent_id lineage, status tri-state, learning loop) sono documentate in [`afterglow/docs/future-ideas.md`](../../afterglow/docs/future-ideas.md) come material per la slide "future work".

**How to apply:** quando un nuovo `FieldDefinition` / `ActionDefinition` arriva (seed o wizard), assume tutti i campi v2 abbiano un default — non patchare codice consumer per "tollerare" shape v1. Quando aggiungi un nuovo `mock_target` a `MOCK_REGISTRY`, ricordati che `available_keys()` è letto dal validator (un'action key sconosciuta viene segnata come warning automaticamente).

### 2. Speechmatics — voice-in + TTS per gli MP3 demo
Non puntiamo al cash Award Speechmatics (sfida ridefinita kick-off = voice-in→reasoning→voice-out). Usiamo i $200 credit per: trascrizione, language detection, diarization, multilingual, custom dictionary, **e** generazione TTS dei 6 MP3 demo. "Massive bonus love" dichiarati al kick-off → migliorano lo score Application of Technology su Vultr/Google Award.

**Why:** voice-out come prodotto runtime sarebbe scope-creep, ma usare Speechmatics TTS *offline* per generare gli audio della demo costa zero in complessità e raddoppia visivamente la dipendenza dal partner nel pitch ("STT + TTS, entrambi Speechmatics").

**How to apply:**
- STT runtime: `speechmatics-batch` SDK wirato live (`AsyncClient.transcribe` con `diarization=speaker`, `language=auto`, `additional_vocab` dal `custom_dictionary` del template). **Nessun fallback offline**: missing key o audio illeggibile sollevano e fanno fallire la call (vedi `backend/app/integrations/speechmatics.py`). Niente più `_FAKE_TRANSCRIPTS`, niente più flag `DEMO_MODE` (rimosso il 2026-05-15).
- TTS offline: dal 2026-05-16 sono **6 MP3 demo** — uno per ogni combinazione `(domain, caller_mode)`: `{restaurant,dentist,bodyshop}_{existing,new}.mp3` in `afterglow/app/assets/audio/` e mirror in `backend/sample_audio/`. Esistono per evitare che il caller "new" si presenti col nome del cliente seedato o che il caller "existing" rifaccia tutta la presentazione a un operatore che lo conosce già dal numero. Voce **operator costante per dominio** (sarah/jack/megan), voce **caller diversa fra existing e new** così suonano persone distinte. Generati da Speechmatics TTS preview (`https://preview.tts.speechmatics.com/generate/<voice>`) via `afterglow/scripts/generate_demo_audio.py`. Le voci preview supportano solo EN UK/US (`sarah`/`theo`/`megan`/`jack`), quindi i copioni demo sono in inglese. **Anche il resto del seed (nomi business, customer profiles, transcript stubs) è in inglese** dal 2026-05-16 — vedi [[feedback-code-language]]. Per rigenerare gli audio: `python afterglow/scripts/generate_demo_audio.py`. Stessa cartella contiene anche `ringtone.mp3` (synth ITU-T 425Hz · 1 s on / 4 s off) usato dall'incoming-call screen — non parte della pipeline AI.

### 3. Forma mobile — PWA, non APK
Web app responsive mobile-style installabile come PWA da URL pubblica. Niente APK distribuito, niente vero dialer Android.

**Why:** vincoli OS Android + permission + tempo. La submission richiede "Public demo URL" → PWA copre.

**How to apply:** stack frontend mobile-first. Demo con audio pre-registrati o upload audio file. Nel video pitch dichiarare onestamente: *"prototipo PWA dimostra la pipeline, produzione Android dialer fuori scope hackathon"*.

### 4. Scope — pieno prompt, sviluppo incrementale
Target: tutte le feature del prompt originale. Strategia: sviluppo a priorità tale che a OGNI punto del processo l'MVP sia funzionante e dimostrabile.

**Priorità (alta → bassa):**
1. PWA dialer con cornetta blu + incoming-call UI ✅
2. Pipeline reale: audio → Speechmatics → Gemini analisi → executed actions ⚠️ (Gemini live, Speechmatics ancora stub)
3. Caller memory card alla seconda chiamata ✅ (briefing Gemini-generated)
4. Dashboard web: call log + action history (con revert) + customer profile ✅
5. Prompt-to-template wizard conversazionale (`POST /api/v1/templates/wizard/chat`) ✅ — `wizard_chat.py` chiama `gemini-3.1-flash-lite` multi-turn, `template_validator.py` runs deterministic-only (Gemini semantic pass rimosso 2026-05-17), UI `app/templates/wizard.tsx` espone chat + draft sidebar e POST `/templates` persiste con session_id corretto + version auto-bump. Vedi sub-decisione 1.cinque.
6. Template library con 3 voci ✅ (seed)
7. Test/simulator template (nice-to-have)
8. Manual template builder pieno (nice-to-have)
9. Audit log avanzato e retention policy (nice-to-have)

**Why:** 6 giorni di build + 1 persona/piccolo team. Garantire demo funzionante > feature complete.

**How to apply:** ogni feature deve essere "deployabile" prima di passare alla successiva. Niente lavoro a metà su due cose in parallelo.

### 5. Stack baseline — partire dal tutorial ufficiale lablab
Baseline: **Stephen-Kimoi/gemini-multimodal-document-agent** (FastAPI + Google ADK 1.18 + Gemini 2.5 Flash + Docker + Vultr). Pubblicato 8 maggio 2026 da lablab.ai → segnale forte di "pattern raccomandato".

**Why:** doppia eligibility Vultr+Google con stack già provato + GitHub repo riusabile.

**How to apply:** forkare repo, adattare. *Nota 2026-05-15: il fork era day-1; ora il codice è divergente abbastanza che il riferimento al baseline serve solo come pattern ADK, non come repo upstream da rebasare.*

### 6. Vultr come system-of-record visibile
Non basta deployare. Vultr deve essere usato in profondità per il "Best use of Vultr" Award:
- **Vultr Managed Postgres** per call log, customer profile, action history, audit log, template store ✅
- **Vultr Vector Store** per customer memory RAG ✅ (wirato; skippato esplicitamente in demo mode, vedi 1.quater)
- **Vultr Serverless Inference (MiniMaxAI/MiniMax-M2.7)** ✅ — wirato nel solo endpoint `/v1/chat/completions/RAG` per il memory retrieval pre-fetch. Il modello è stato cambiato da Kimi-K2 a MiniMax-M2.7 (commit `d08912f`) perché è quello che Vultr serve realmente sull'endpoint RAG. Se servisse un secondo uso non-RAG dell'inference Vultr per pitch, va aggiunto un mini-agente dedicato.
- **IAM Service User** per credenziali API-only minimal-privilege

**Why:** il requisito Vultr è *"system of record per planning, coordination, execution"* — non solo hosting.

**How to apply:** se devi scegliere tra "feature in più nella UI" e "uso Vultr più profondo", scegli il secondo nelle prime fasi.

⚠️ **Trappola key Vultr:** la `VULTR_API_KEY` di account (Settings → API) non vale come `INFERENCE_API_KEY`. L'endpoint inference risponde `"Invalid API key"` o 422 finché non usi una chiave generata dal pannello *Serverless → Inference → <subscription> → API keys*. Documentato in `hackathon-docs/12-vultr-deep-dive.md` warning box.

### 7. Licenza MIT day-1
File `LICENSE` MIT nel repo dal primo commit.

**Why:** vincolo legale submission lablab.ai (Sez. 16 Terms of Use).

**How to apply:** non aggiungere mai dipendenze GPL/AGPL nel progetto.

### 8.bis. Pipeline DevOps — local → GitHub → Coolify autodeploy (2026-05-15)
**Una sola via verso produzione:** `git push origin main` su `Cleversoft-IT/hackaton-lablab` → webhook GitHub App → Coolify ricostruisce le due Application e fa rolling update. NESSUN deploy manuale via SSH; nessun `docker-compose up` sulla VM; nessun upload di artifact a mano.

**Why:** garantisce che la demo URL pubblica rifletta sempre `main`, evita drift fra workstation. Riduce il "blast radius" del service user IAM (è limitato + audit trail GitHub).

**How to apply:**
- DB: in produzione gira **Vultr Managed Postgres** (`221ca284-…`). Il service `postgres` del `docker-compose.yml` resta SOLO come comodità dev locale; **non va mai deployato** in Coolify.
- Audio: oggi è dentro il container (`/var/data/audio` no volume). Persistent volume è in roadmap; nel frattempo i file audio sono ephemeral fra i redeploy.
- Env vars: gestite in Coolify (Resource → Environment Variables, criptate at-rest). NIENTE secret committato. Il `.env` locale ha valori dev (Postgres podman su localhost, audio in `./data/audio`).
- HTTPS: Traefik + Let's Encrypt sul dominio `*.95-179-245-107.sslip.io`. Sslip.io risolve `<dashes>.sslip.io` → IP corrispondente senza configurazione DNS aggiuntiva.
- Coordinate complete in [[reference-devops-pipeline]]. Credenziali fuori dalla repo (Coolify env vars + `~/.config/afterglow/`).

### 8.ter. Gemini default model — `gemini-3.1-flash-lite` (aggiornato 2026-05-16)
Default esplicito per backend e wizard: `GEMINI_DEFAULT_MODEL=gemini-3.1-flash-lite` e `GEMINI_TEMPLATE_BUILDER_MODEL=gemini-3.1-flash-lite`. Coolify è già stato aggiornato lato backend; il codice tiene lo stesso default per local dev e deploy freschi. Evitare alias mobili come `gemini-flash-latest` / `gemini-latest-flash` e vecchi pin `gemini-2.5-flash` o `gemini-3-flash`, perché cambiano quota/comportamento o puntano a generazioni non allineate alla demo.

**How to apply:** se serve un modello reasoning Pro, sappi che il free-tier non lo serve. Per la demo restiamo su Flash-Lite, dove latenza e costo sono più importanti del massimo reasoning.

### 1.sei. Feedback round 2 — UX & action catalog (2026-05-16 pomeriggio)

Dopo il primo giro di test su installazione fresh (Mark Ross / Julia White) sono emerse 7 famiglie di problemi che alterano la forma del prodotto. Decisioni bloccate qui per non ridiscuterle:

**A. PII redaction → out of scope** (decisa qui, completata 2026-05-17 con la cancellazione di `pii_sanitizer.py` / `pii_policy.py`). Motivo originale: l'operatore deve sapere che il cliente è celiaco; redazioni `[redacted: health]` sono inutili. Vedi sezione 1.nove + `afterglow/docs/future-ideas.md` §4 per il design archiviato.

**B. Dialer fire-and-forget.** `app/app/incoming-call.tsx` non polla più la pipeline: dopo che l'audio finisce, submit + `router.replace('/(tabs)')` + toast pubblicato via `app/lib/pipelineToast.ts`. La tab Calls (`app/app/(tabs)/index.tsx`) ha un banner "Analysis in progress" e auto-refresh ogni 2s finché ci sono call non-terminali. NESSUN auto-redirect a Card Detail quando la call completa: l'utente può cliccare quando vuole. Sostituisce la vecchia logica `phase='analyzing'` con polling bloccante (rimossa).

**C. Simulator a due bottoni con MP3 distinti per modalità.** `app/app/simulator.tsx` espone "Call from existing customer" (phone seedato per il domain) e "Call from new customer" (phone random `+1 555 0XX XXXX` generato lato client). `incoming-call.tsx` legge `?caller=existing|new` e salta il customer lookup quando `new` per dimostrare la creazione del Customer durante la pipeline. **Dal 2026-05-16 ogni template ha DUE MP3** (`<domain>_existing.mp3` / `<domain>_new.mp3`): lo script "existing" presume il caller già noto dal numero ("Hi Sarah, it's Mark") e fa riferimento a interazioni passate; lo script "new" è un primo contatto ("Hi, I've never booked with you before. It's Hannah Clarke"). La shape `simulation_config` è cambiata: ora ha `scenarios.{existing,new}.{caller_name,caller_phone_e164,script_turns,audio_url,audio_status,audio_generated_at,audio_source}` — i template seed lo popolano via `_bundled_simulation_configs()` in `seed.py`; i template custom del wizard mantengono lo shape flat legacy e ne riusano l'unico MP3 in entrambi i modi (graceful fallback nell'endpoint `GET /templates/{id}/simulation/audio?mode=`). **Dal 2026-05-17 il Simulator nasconde il bottone "Call from existing customer" per i template wizard-built** (quelli senza `scenarios.{existing,new}`): il telefono fabbricato dallo script generator non matcha nessun customer seedato, quindi l'esistente regrediva sempre in "New caller" — confondente, vedi [[project-wizard-template-new-only]]. L'estensione del wizard a due script + customer seeded è tracciata come follow-up in `afterglow/docs/templates-roadmap.md`. **Audio dei custom template servito via blob URL**: l'endpoint `GET /templates/{id}/simulation/audio` è session-scoped e gli HTMLAudioElement cross-origin non possono mandare header custom, quindi `api.fetchSimulationAudio()` scarica il WAV come `Blob` attraverso il fetch session-aware e `usePhoneAudio.prefetchBlob()` espone un `URL.createObjectURL(blob)` al `<audio>`. Vedi [[feedback-audio-blob-url-for-session-endpoints]].

**D. Seed Call rows visibili.** `db/seed.py` ora inserisce ANCHE Call rows fittizie per i clienti seedati con transcript EN, ExtractedFields completi, briefing_snapshot, ExecutedAction e audit_log entries. Dal 2026-05-16 i customer seedati sono **quattro** (uno per ogni `existing` button così la card "Recent calls" non resta vuota su 2/3 template): Mark Ross +15551112233 (restaurant · 2 call: 20 Apr + 7 Mag), Julia White +15554445566 (restaurant · 1 call: 15 Apr), Laura Bennett +15559991122 (dentist · 1 call: 8 Apr, crown fitting on file), Andrew Green +15558883344 (bodyshop · 1 call: 3 Mag, returning Fiat Panda owner). Migration `0008_call_executedaction_is_seed.py` aggiunge il flag `is_seed` su `calls` e `executed_actions`. Le seed sono **visibili anche nella lista globale Calls** (no filter): l'utente ha esplicitamente chiesto di vederle al fresh install per dare contesto.

**E. Action catalog server-side (`integrations/action_catalog.py`).** Single source of truth per ogni action key Afterglow conosce: `integration_kind` (`mock_external` | `internal_real`), `mock_target` o `internal_handler`, `can_undo`, `compatible_domains`. L'`action_executor` consulta il catalog per scegliere il path (MOCK_REGISTRY vs `INTERNAL_HANDLERS`), e `CallActionView.is_simulated` / `can_undo` sono **server-computed dal catalog** (non più derivati da `result.mock` o da euristiche client). Il `template_validator` ora flagga template che citano action keys non nel catalog (sostituisce il vecchio import da `app.integrations.mocks.available_keys`).

**Marketplace expansion (2026-05-18):** catalog passato da 11 a **25 action keys** su **8 mock bucket** + 1 internal_real bucket. Nuovi bucket: `sms` (dedicato — prima `sms.send_reminder` puntava per errore al mock `whatsapp`), `calendar`, `payment`, `review`. Nuove key in bucket esistenti: `booking.reschedule`, `crm.create_lead`, `crm.create_ticket`, `email.send_quote`. `KNOWN_DOMAINS` estesa da 4 a 11 (aggiunti hotel, salon, clinic, legal, realestate, gym, events). Wizard prompt (`_system_instruction`) ora riceve il catalog ricco (key + label + description + integration_kind + compatible_domains) e ha HARD RULE Integration discovery estesa ai nuovi bucket channel-dependent (calendar/payment/review). Nuovo endpoint `GET /api/v1/integrations` (funzione pura `aggregate_integrations(CATALOG)`) + drawer screen consultativo `app/(drawer)/integrations.tsx`. Gli `action_types` dei 3 seed template (restaurant/dentist/bodyshop) sono stati aggiornati per includere le nuove action che i loro 6 script demo esercitano (booking.reschedule + review per restaurant, calendar.send_invite + calendar.block_slot + email.send per dentist, payment.request_deposit + payment.send_invoice per bodyshop). Generator `simulation_script.py` portato allo stesso standard: vede catalog ricco, genera ENTRAMBI `scenarios.{existing,new}` (era solo `new`), ha quality directives nel SYSTEM_INSTRUCTION. `speechmatics_tts.template_audio_path(template_id, mode)` supporta path per-mode (`<id>_existing.wav` / `<id>_new.wav`); `POST /simulation/generate-audio` esegue il render su entrambe le mode. Vedi [[feedback-demo-scripts-quality]].

**F. `customer.update_profile` è `internal_real`.** Nuovo modulo `integrations/internal/customer_profile.py`: muta davvero `customer.display_name` (solo se vuoto), `customer.tags` (deduped merge), `customer.profile_facts` (JSONB, migration `0009_customer_profile_facts.py`). Cattura `previous_state` nel `result` per abilitare l'undo che ripristina lo stato. Il `result.mock = False` significa "niente badge Simulated" nella UI: questa è un'azione interna REALE.

**G. Undo / Redo flip-only.** Endpoint `POST /actions/{id}/undo` (status `executed → undone`, replay del `previous_state` per internal_real) e `POST /actions/{id}/redo` (flip `undone → executed`, niente nuovo mock call — scelta esplicita). `POST /actions/{id}/revert` resta come alias retro-compat. La UI mostra il bottone Undo solo quando `action.can_undo === true` (sent messages → niente Undo). Niente bottone "Revert" dappertutto come prima.

**H. Endpoint nuovo `GET /api/v1/actions/catalog`.** Restituisce ogni entry per il wizard chat (Fase 8 in arrivo) e per il template editor (Fase 7). Sostituirà l'attuale `Template.action_types[].mock_target` come fonte di verità nel template builder.

**I. UI label.** "Memory summary" → "Next-call briefing" in customer profile + dialer caller card. "Re-validate" → "Check draft" nel wizard. Field UI in Call Detail mostra `FieldDefinition.label` come primario e `key` come stringa monospace piccola sotto (`CallExtractedView.field_definitions` espone label server-side). Settings tab non mostra più l'API base.

**J. Prompt analyzer briefing style.** `agents/call_analyzer.py` ora chiede esplicitamente "1-2 short sentences, operator-actionable" invece di "1-3 sentences" generici. Esempio target: *"Mark prefers a quiet table and is gluten-intolerant. Last booked party of 4 on 9 May — confirm the same setup if he calls again."*

**Why:** il primo test reale ha mostrato che la pipeline e l'UI sono corrette ma vivono in mondi separati: l'operatore non sapeva interpretare placeholder di redazione, vedeva il dialer bloccato in `preparing/processing` mentre la pipeline girava, vedeva action senza badge Simulated e senza poter undo, e si trovava in Card Detail teletrasportato senza averlo chiesto. Queste decisioni allineano l'UX al modello mentale dell'operatore.

**How to apply:**
- Quando aggiungi una nuova action key, **deve** apparire in `action_catalog.CATALOG` con `integration_kind` esplicito. Se è `internal_real`, registra anche un handler in `INTERNAL_HANDLERS` e (se è undoable) un reverter in `INTERNAL_REVERTERS`. Aggiorna `tests/test_action_catalog.py` se serve.
- NON ri-introdurre PII redaction/sanitizer senza ridiscutere — la pipeline runtime è 4-step volutamente senza policy gate (vedi 1.nove + `future-ideas.md` §4).
- NON toccare il polling bloccante dentro al dialer: la fase `analyzing` locale è morta apposta.
- Quando aggiungi un campo a `ExecutedAction.result`, valutare se modificarne anche la shape che la UI usa per `is_simulated` / `can_undo` (ora vengono SERVER-side dal catalog, non dal result).

### 1.sette. Frontend Material 3 rewrite — sostituto del dialer di sistema (2026-05-17)

Riscrittura end-to-end del frontend Expo PWA. **Pitch narrative riformulato**: Afterglow non è "un AI dialer demo per booking telefonici", è il **sostituto dell'app Phone di sistema** (Pixel-inspired). L'operatore lo usa per tutte le chiamate; l'AI lavora silenziosamente dopo ogni chiamata.

**Why:** la prima incarnazione "5 tab generiche (Calls / Customers / Bookings / Templates / Settings)" sembrava un'app web demo. Il pitch hackathon premia "enterprise-grade verticale" — un sostituto del dialer è enterprise-grade visibility, non un demo player. Reference visiva = screenshot Google Phone (AOSP/Pixel) condivisi dall'utente in `tmp/WhatsApp Unknown 2026-05-17 at 02.26.39/` + pattern Material 3 specifici da Amadz (`tmp/Amadz/`, Apache-2.0) per avatar palette e KeyPad.

**Nuova architettura navigation:**

- Top-level `Drawer` (hamburger sx, custom DrawerContent in `app/(drawer)/_layout.tsx`):
  - **Contacts** (nuova screen) — lista alfabetica unica che fonde 20 mock UK/US (`app/lib/mockContacts.ts`, client-side hardcoded JSON) con il `Customer` table; Chip "Client" distingue i customer. Resolution priority `customer > mock > "Unknown caller"` in `app/lib/callerResolver.ts`.
  - **Templates** (spostato da `(tabs)/`)
  - **Audit log** (spostato da `app/audit.tsx`)
  - **Test simulator** (escape hatch — la tab Calls non esiste più, il simulatore è raggiungibile solo dal drawer)
  - **Settings** (spostato)
  - **Reset demo** (conditional `isDemoMode()`)
- Bottom `BottomNavigation.Bar` Paper 2 tab dentro al drawer (`(drawer)/(tabs)/`):
  - **Home** = Pixel Recents (`(drawer)/(tabs)/index.tsx`)
  - **Keypad** = 4×3 dialpad con Call FAB UI-only (Snackbar "Use the Simulator…")
- Stack screen fuori drawer: `incoming-call`, `call/[id]`, `customer/[id]`, `templates/[id]`, `templates/wizard`, `simulator`.

**Eliminati dal codice (3 route):** `(tabs)/bookings.tsx` (diventa chip filter "Bookings" su Home), `(tabs)/customers.tsx` (confluito in Contacts drawer), vecchio `(tabs)/_layout.tsx`. **Deprecati componenti:** `components/ListRow.tsx` (screen consumano `List.Item` Paper direttamente), `components/CallButton.tsx` (incoming-call usa `<FAB>` Paper). `components/FormField.tsx` tenuto temporaneamente (usato dal Template Detail editor).

**Home (Recents) Pixel-style:**
- AppBar pill `Searchbar` con `icon="menu"` (hamburger → openDrawer) + `traileringIcon="microphone"`.
- Chip filter row scrollabile (5 chip, **niente "AI" chip**): All / Missed / **Bookings** / Saved / Unsaved. Audit esterno finding #1: `CallListItem` (`/api/v1/calls`) NON espone `executed_actions`, quindi un chip "AI" richiederebbe N+1 fetch. Il chip "Bookings" usa fetch parallelo `api.listBookings({limit:100})` + Map `bookingByCallId` per filtrare e arricchire visivamente la riga.
- `SectionList` con sticky date headers azzurri (`color: theme.colors.primary`) — Today / Yesterday / `D Mon`.
- `CallRow` (nuovo componente `app/components/CallRow.tsx`): `Avatar.Text` 48dp con bg hash-derived (11 colori Amadz `Contact.kt`: `#EF5350 #EC407A #AB47BC #7E57C2 #5C6BC0 #42A5F5 #26A69A #66BB6A #FFA726 #8D6E63 #78909C`, `Math.abs(hashCode(phone)) % 11`), iniziali first+last via `initialsFromName`; Chip "Booking" inline accanto al name quando la call ha un booking action; `direction icon` (phone-missed/incoming) + label + `formatRelativeTime`.
- Quando filter=`bookings` la riga **nasconde il phone** e mostra `booking.title · payload.booking_date · payload.booking_time · party of N` dal `payload` del `BookingListItem` (audit finding #5: campi in `payload`, non al top level).
- Trailing `phone-outline` `IconButton` → **Snackbar** "Use the Simulator from the drawer to test the AI pipeline" (audit finding #4: **non** apre incoming-call, la state machine accetta solo `caller=existing|new` e non un `phone=` arbitrario).

**Incoming Call — "Pixel-inspired" (NOT exact match):** rewrite **solo visivo**, la state machine (`useState`/`useEffect`/`usePhoneAudio`/parsing param `caller=existing|new`/`submitAndClose`) è copiata 1:1 dal pre-rewrite (audit finding #7). Tre divergenze esplicite dal Pixel originale documentate per il pitch: (a) avatar `Avatar.Text` 160dp verde fisso `#26B31E` con iniziali bianche e pulse animation durante `ringing`, (b) 3 FAB invece di 2 (Decline rosso / **AI** primary con icon `creation` / Accept verde, rounded 20dp) per esporre il pulsante AI, (c) Chip "Afterglow listening" con icon `creation` durante `talking`. In-call: timer in `tabular-nums`, 4 `IconButton` `mode="contained-tonal"` (Keypad/Mute/Speaker/More) sotto, big red pill hangup centrato. Submit dopo audio: `router.replace('/(drawer)/(tabs)' as never)`.

**Stack frontend (nuove dep, Expo SDK 54):**
- `react-native-paper@^5.15` (MIT) — componenti MD3.
- `@material/material-color-utilities@^0.4` (Apache-2.0) — generazione palette MD3 dal seed `#3b82f6` via `themeFromSourceColor`; output spreado dentro `MD3LightTheme.colors` / `MD3DarkTheme.colors` (audit finding #3: senza lo spread restano i token viola baseline su `surfaceDisabled`/`onSurfaceDisabled`).
- `@react-navigation/drawer@^7.10` (MIT) — Drawer navigator.
- `react-native-gesture-handler@~2.28` — peer dep del drawer.
- `react-native-reanimated@~4.1` — animazioni. **Attenzione:** Reanimated 4 ha spostato il Babel plugin in `react-native-worklets/plugin` (NON più `react-native-reanimated/plugin`). Aggiunto `app/babel.config.js` con `presets: ['babel-preset-expo'], plugins: ['react-native-worklets/plugin']` + dep `babel-preset-expo` come devDep esplicita.

**Token MD3 — convenzione tonal surfaces:** Paper v5 non espone `surfaceContainerHigh` nel tipo `MD3Colors`. Per le superfici tonali (briefing card, draft sidebar wizard, in-call footer) usare `theme.colors.elevation.level1` / `level2` / `level3` (Paper genera questi shading da MD3). Non re-introdurre `surfaceContainerHigh` finché Paper non lo tipa.

**`PaperProvider` posizione:** **dentro** `RootLayoutInner`, **dopo** `useTheme()` del nostro `ThemeContext`, wrapped in `<GestureHandlerRootView style={{flex:1}}>` (richiesto da `react-native-gesture-handler`). Sopra al `PaperProvider` resta `<ThemeProvider>` esterno. Audit finding #3: spostarlo fuori da `RootLayoutInner` rompe il binding mode light/dark del SegmentedButtons in Settings.

**Bug fix runtime (smoke test Chrome):** l'icon name `auto-awesome` (Material Symbols) **non esiste** in `MaterialCommunityIcons` (il set di default di Paper via `@expo/vector-icons`). Sostituito ovunque con `creation` (scintilla MD Community) — FAB AI in `incoming-call.tsx` + Chip "Afterglow listening" durante `talking`. NON re-introdurre `auto-awesome` né `sparkles`: nessuno dei due esiste in MaterialCommunityIcons.

**Routing pivot:** path hardcoded migrati nello stesso commit della creazione del drawer (audit finding #5):
- `app/_layout.tsx` gate redirect → `/(drawer)/templates` (era `/(tabs)/templates`)
- `app/incoming-call.tsx` post-submit → `/(drawer)/(tabs)` (era `/(tabs)`)
- `(drawer)/settings.tsx` audit log link → `/(drawer)/audit` (era `/audit`)
- `Stack.Screen name="(tabs)"` → `name="(drawer)"` nel root `_layout.tsx`
- `Stack.Screen name="audit"` rimosso dal root (audit è dentro drawer)

**Audit log spostamento:** `app/audit.tsx` → `app/(drawer)/audit.tsx` (refactor MD3: `List.Item` con `Avatar.Icon` colorato per `status`, `Chip` per `step_type`/model, monospace per token count).

**How to apply:**
- Quando aggiungi un nuovo schermo full-rewrite MD3, usa Paper widgets diretti (`<Card mode="elevated">`, `<List.Item>`, `<Chip>`, `<Surface elevation={N}>`), non i wrapper legacy in `components/`. I wrapper `Button/Card/Badge/Input/Textarea/Select/Checkbox` di Paper sono compat-API per gli schermi non rifatti (es. Template Detail editor); per il nuovo screen vai diretto.
- Quando devi una superficie tonale, leggi `theme.colors.elevation.levelN` (mai `surfaceContainerHigh`).
- Quando aggiungi un icon nell'UI, verifica che esista in MaterialCommunityIcons (https://pictogrammers.com/library/mdi/) — se non esiste cerca un equivalente prima di usare un nome Material Symbols.
- Quando aggiungi un mock contact, **client-side only**, modifica `app/lib/mockContacts.ts` (nessun backend touch).
- Quando aggiungi una nuova entry nel drawer, modifica `app/(drawer)/_layout.tsx` `CustomDrawerContent` + (se serve uno screen nuovo) crea il file in `(drawer)/`.
- La state machine di `incoming-call.tsx` è LOCKED. Cambia solo JSX. Se serve mutare `phase` / `audio.*` ridiscuti.

### 1.sette-bis. UI bug cluster post-rewrite (2026-05-17 pomeriggio)

Dopo il commit del rewrite MD3, smoke test in Chrome (deployato e locale) ha esposto 7 famiglie di bug che ho risolto in `032d3a5`. Le decisioni sotto sono permanenti — non re-introdurre i pattern vecchi senza ridiscutere.

**A. `AppTheme` + palette `successContainer` custom.** `material-color-utilities` da seed `#3b82f6` (blu) produce un secondary/tertiary track **rosa in light / viola in dark**: i chip e gli avatar status "success" / "completed" finivano rosa/viola, semanticamente sbagliato. `lib/paperTheme.ts` ora esporta un tipo `AppTheme` che estende `MD3Theme` con `success` / `onSuccess` / `successContainer` / `onSuccessContainer` (verde in entrambi i mode), più due hash override per `successLight` (`#1F7A3D` / `#B7E7C5`) e `successDark` (`#86D8A2` / `#1F5230`). Consumer pattern: `const theme = useTheme<AppTheme>()` poi `theme.colors.successContainer`. Già migrati: `(drawer)/audit.tsx`, `call/[id].tsx`, `customer/[id].tsx`, `components/Badge.tsx`. **Non re-introdurre `tertiaryContainer` per stati success** — i test smoke locks lockano la palette.

**B. Override `background` / `surface` / `surfaceVariant` / `outline` in `paperTheme.ts`.** Lo stesso source-color generator produce `scheme.background` con tinta pinkish-grey, e `surfaceVariant` ancora più tinto: l'app sembra "viola sporca" in light e "marsh" in dark. `paperTheme.ts` ora ha due record `surfacesLight` / `surfacesDark` (light: `#F7F8FA` / `#FFFFFF`, dark: `#0B0D12` / `#161922`, plus `outline` / `outlineVariant` neutri) che vengono spreadati DOPO i token generati dentro `buildSchemeColors`. Il risultato è un Pixel-feel pulito in entrambi i mode. Se rivedi tokens generati e vedi sfondo nero in light → sicuro che lo screen sta consumando `theme.colors.background` di Paper, NON un `colors.bg` hardcoded di `lib/theme.ts`.

**C. Drawer theme propagation manuale.** `@react-navigation/drawer` ignora il tema di Paper e usa il proprio `DefaultTheme` (sempre light). Risultato: drawer bianco anche con app in dark = inconsistenza grave. Fix in `(drawer)/_layout.tsx`: chiamare `useTheme()` (Paper) nel `DrawerLayout` e passare esplicitamente `drawerStyle.backgroundColor = theme.colors.surface`, `sceneStyle.backgroundColor = theme.colors.background`, `drawerActiveTintColor`, `drawerInactiveTintColor`, `drawerActiveBackgroundColor = theme.colors.secondaryContainer`. **Inoltre** ogni `DrawerItem` deve ricevere `labelStyle={{ color: theme.colors.onSurface, fontWeight: '500' }}` — senza questo, in dark le label sono quasi invisibili (il navigator ha un tint default che cade su `outline`).

**D. Listener Templates rimosso (renderer freeze).** `(drawer)/templates.tsx` aveva un `useEffect` con `parent.addListener('state', ...)` che mostrava un Dialog "Pick a template first" ogni volta che il parent drawer cambiava state. In pratica firing continuo sui transition state del drawer → renderer pegged → `Page.captureScreenshot` timeout → la screen `/templates` era unscreenshottabile. Risolto rimuovendo l'intero listener + relativo `<Portal><Dialog>` + state `warningVisible` / `pendingRoute`. Il bootstrap gate in `app/_layout.tsx` già fa il redirect a Templates quando manca l'active template; il soft-warning era ridondante *e* rotto. **Non re-introdurre listener `parent.addListener('state', …)`** — se serve un soft-warning, usare `useFocusEffect` + `beforeRemove` event, non lo state listener globale.

**E. Chip filter row Home: `flexGrow: 0` + `compact`.** `(drawer)/(tabs)/index.tsx` la `<ScrollView horizontal>` ereditava altezza dal flex parent → i chip diventavano box rettangolari ~120 dp alti. Fix: `style={{ flexGrow: 0, flexShrink: 0 }}` sulla ScrollView + `contentContainerStyle.alignItems: 'center'` + `<Chip compact mode="flat" selected={...}>` con `style` esplicito condizionale (`secondaryContainer` se selected, `surfaceVariant` altrimenti). Adesso pill 32 dp standard MD3.

**F. Searchbar opaca + sticky.** Sempre in Home: `<Searchbar elevation={0}>` lasciava i contatti scorrere visibili dietro il bordo inferiore della pill. Fix: `style={{ backgroundColor: theme.colors.surfaceVariant }}` esplicito sulla Searchbar così la superficie è opaca.

**G. Hangup audio AbortError + fallback navigation.** `lib/usePhoneAudio.ts` ora intercetta nel `.catch()` di `el.play()` la rejection `AbortError "interrupted by a call to pause()"` (browser quando l'utente fa hangup mid-MP3) e ritorna silenziosamente — è uno stop volontario, non un errore. Inoltre `incoming-call.tsx` `hangUp` ora fa `router.canGoBack() ? router.back() : router.replace('/(drawer)/(tabs)')` invece di solo `router.back()`: un deep-link / cold load su `/incoming-call` non ha back history, e prima lasciava schermo nero. **Non aggiungere altre rejection silenziate** — solo questa specifica è "graceful stop".

**H. Avatar incoming-call ringing 128 dp (era 160).** Il pulse animation faceva scale 1→1.15, e con avatar 160 dp + viewport short (web landscape, demo iframe) la testa dell'avatar copriva "Mark Ross" + phone subtitle. Fix in `incoming-call.tsx`: `size={phase === 'ringing' ? 128 : 160}` + `paddingBottom: 24` allo `styles.header`. La fase talking resta 160 dp.

**Why:** la pipeline e l'UI MD3 erano logicamente corrette ma la palette generata + il drawer mancante + i listener legacy + lo state machine audio rendevano la demo inguardabile in alcuni scenari. Tutti fix sono in `032d3a5` ed entrambi i mode (light/dark) ora sono visivamente coerenti.

**How to apply:**
- Quando aggiungi una nuova screen che mostra status "success/completed", usa `useTheme<AppTheme>()` + `theme.colors.successContainer` / `onSuccessContainer`. **Mai più `tertiaryContainer`** per success.
- Quando aggiungi un Drawer entry, propaga `labelStyle` con `theme.colors.onSurface`.
- Quando aggiungi un container "fullscreen", usa `theme.colors.background` (mai hardcoded `#000` / `#fff`). Se vedi sfondo bizzarro in uno dei due mode → controlla `paperTheme.ts surfacesLight` / `surfacesDark`.
- Quando aggiungi un audio asset al dialer, gestisci il caso "hangup durante play" con la stessa AbortError pattern in `usePhoneAudio.ts`.
- Quando aggiungi un soft-warning "non hai fatto X" su uno screen, **non** usare `parent.addListener('state')` — usa `useFocusEffect` + navigation `beforeRemove`.

### 1.otto. Round 3 UI audit — drawer Calls, locale IT/EN, booking badge, transcript split (2026-05-17 sera)

Secondo giro di test su `app.95-179-245-107.sslip.io` post-rewrite ha esposto bug bloccanti di navigazione + gap di forma rispetto al pitch "sostituto del dialer Pixel". Cluster di 8 stage chiusi in due commit (`d155c52` + `6823f1d`). Le decisioni qui sono permanenti.

**A. Drawer ha SEMPRE una voce "Calls" in cima.** `app/app/(drawer)/_layout.tsx` espone manualmente la rotta `(tabs)` come `<DrawerItem label="Calls" icon="phone-outline">` (con `focused ? primary : onSurface` per il colore), mentre `<Drawer.Screen name="(tabs)">` resta nascosta via `drawerItemStyle: { display: 'none' }`. Senza questa voce, una volta navigato a Contacts/Templates/Settings non c'era percorso UI per tornare alla Home — l'utente doveva editare l'URL. **Non rimuovere mai questa voce.** Se aggiungi screen sotto al drawer, segui lo stesso pattern `focused ? primary : (color ?? onSurface)` per le icone così l'highlight active resta e dark mode non perde leggibilità.

**B. Drawer wordmark `afterglow`.** L'header del DrawerContent è il `<Text>` styled `<Text>after</Text><Text color=primary>glow</Text>` (font weight 800, letter-spacing -0.3, size 22) replicando il markup demo (`afterglow/demo-site/src/App.tsx:129-130`). Sostituisce il vecchio `<Text variant="headlineSmall">Afterglow</Text>` plain. **Non passare a un asset/logo image** — è solo tipografia.

**C. Drawer Reset demo via Paper Dialog (non `window.confirm`).** `window.confirm` dentro un DrawerItem fa race con l'auto-close del drawer: il `setBusy(true)` parte ma il `await api.resetDemo()` non risolve mai (modal blur), e il bottone resta bloccato su "Resetting…". Dal round 3, `DrawerContent` usa lo stesso `<Portal><Dialog>` pattern di `(drawer)/settings.tsx` — `setResetDialogVisible(true)` apre il dialog, `runReset()` esegue + reload. **Non re-introdurre `window.confirm` in nessun DrawerItem.** Vedi [[feedback-drawer-window-confirm]].

**D. Fresh-session flag + "Go to Calls" dialog dopo activate.** Quando `app/_layout.tsx` rileva al boot che `getActiveTemplate()` ritorna null (fresh visit o post-reset), chiama `markFreshSession()` prima del `router.replace('/(drawer)/templates')`. La Templates screen, alla prima `setActiveTemplate(id)` successo, fa `consumeFreshSession()` e se è true mostra un Paper Dialog "Template activated — Go to Calls / Stay on Templates". Il flag vive in `app/lib/freshSession.ts` (sessionStorage + in-memory), one-shot, scope sessione browser. **Non riusarlo per altri flussi** — è cucito addosso al gate del bootstrap.

**E. Filter chips Home: aggiunto "Clients".** Set definitivo: `All / Missed / Bookings / Clients / Saved / Unsaved` (era 5 chip senza Clients). Semantica: `Clients = caller.is_customer` (solo righe linkate a un `Customer`), `Saved = is_customer || mockContact`, `Unsaved = nessuno dei due`. Il chip "Clients" è la richiesta operatore "fammi vedere solo i call dei clienti veri, no rubrica personale". Sort bookings resta ASC future-first + DESC past-after.

**F. Filter chips Contacts: aggiunto kind filter.** `(drawer)/contacts.tsx` ora ha sopra la Searchbar i chip `All / Clients / Personal` per separare visualmente i customer linkati ai dati AI dalla rubrica mock fittizia. Lo `ContactEntry` propaga `avatar_url` da `MOCK_CONTACTS` così la pagina Contacts mostra le stesse foto della Home.

**G. Locale IT/EN binary toggle.** `app/lib/dateFormat.ts` (Intl.DateTimeFormat-based, no librerie nuove) + `app/lib/LocaleContext.tsx` (persist `afterglow.locale` in localStorage, default `'it'`) + Settings ha una sezione `Format` con SegmentedButtons IT/EN. Il toggle aggiorna IMMEDIATAMENTE tutte le date/orari: Home section headers (`Oggi/Ieri/15 mag` vs `Today/Yesterday/May 15`), CallRow relative time (`21 h fa` vs `21h ago`), Call/Customer detail full datetime (`DD/MM/YYYY HH:mm` vs `MM/DD/YYYY h:mm a`), BookingBadge slot (`DD/MM HH:mm · party N` vs `M/D h:mm a · party N`). **NON è i18n delle UI strings** — quelle restano inglesi per [[feedback-code-language]]; il toggle riguarda solo i formati di data/ora. `dateGrouping.ts` resta export ma delega a `dateFormat.ts` (ha solo `groupByDay`).

**H. BookingBadge inline a destra della riga.** `app/components/CallRow.tsx` ha un sub-componente `BookingBadge` che rimpiazza il vecchio `Chip "Booking"` inline al titolo. Mostra `${formatDayMonth} ${time} · party N` (no anno, no titolo) con `icon="calendar-blank-outline"`, sfondo `secondaryContainer`. Il `phone-outline IconButton` destro è stato **rimosso** insieme al prop `onCallIconPress` (era dead API che apriva un Snackbar). La riga ora ha solo: avatar (con foto se mock contact ha `avatar_url`) | nome+descrizione | booking badge.

**I. TranscriptList component (Card + List.Accordion).** `app/components/TranscriptList.tsx` parsa `raw_transcript.text` su pattern `^(Operator|Caller|Operatore|Chiamante):` e renderizza i turni dentro un `List.Accordion` "View turns" — speaker label in `labelSmall` bold (Operator = primary, Caller = success), testo in `bodyMedium`. Sostituisce il vecchio single `<Text>` one-line. Il pattern visivo replica lo `ScriptPreview` di `simulator.tsx` (Card+Accordion+Text), **NON i bubble del wizard chat**.

**J. `REAL_ON_DEVICE` whitelist UI-only.** `app/app/call/[id].tsx` ha `const REAL_ON_DEVICE = new Set(['booking.create'])`; le azioni in questo set NON mostrano il badge `Simulated` anche se il backend le classifica come `integration_kind="mock_external"` in `action_catalog.py`. Razionale: il pitch è "il booking succede sul dispositivo dell'operatore", non su un sistema esterno simulato — il badge confondeva i giudici. **È SOLO una scelta UI**: backend, audit_log e `result.mock` restano invariati. Non documentare come "real backend execution". (Round 8: ridotto a una sola key dopo aver unificato `appointment.*` in `booking.*`.)

**K. Status chip capitalize + icona.** Status `completed/failed/pending` in `app/app/call/[id].tsx` ora capitalize'd (`Completed/Failed/Pending`) + icona (`check-circle-outline / alert-circle-outline / progress-clock`). Eliminato il pleonasmo machine-key sotto label nei field e action: `<Text fontFamily="monospace">{k}</Text>` rimosso, resta solo `def?.label ?? k`.

**L. Flag emoji nel Call Detail subtitle.** `app/lib/flagFromE164.ts` (tabella prefisso → emoji bandiera, no libreria) → subtitle del Card.Title diventa `🇺🇸 +15551112233 · en`. Tabella copre IT/UK/US/DE/FR/ES/AT/CH/PT/NL/BE/IE/GR/DK/SE/NO/FI/PL + fallback `🌐`.

**M. paperTheme accent/elevation override.** `lib/paperTheme.ts` ora estende ulteriormente la palette MD3 con `accentsLight`/`accentsDark` che spreadano DOPO `buildSchemeColors`: override esplicito di `secondaryContainer` (light `#E7EEFC`, dark `#1B2944`), `tertiaryContainer`, e tutto l'oggetto `elevation.level0..5`. Il generator `themeFromSourceColor('#3b82f6')` produceva surface tonal lavanda/rosa che si vedeva nei Chip, Accordion e Card elevati; ora sono neutri cool-grey. **Non re-introdurre tinte rosa per success/info** — i test smoke lockano la palette.

**N. Web first-paint sync + SPA shell output (2026-05-17 sera).** Tre meccanismi cooperanti, dopo il fix React error #418:

1. **`app.json` `web.output: "single"`** (cambio 2026-05-17 sera): Expo serve un thin HTML shell che bootstrappa il bundle React, niente prerender statico per-route. Cambio motivato dal fix di **React error #418**: con `"static"` Expo prerenderizzava ogni route in Node senza `localStorage`/`matchMedia`/`window`; il client poi risolveva theme/locale/safe-area-insets/demo-session diversamente e React loggava `Hydration failed` al primo render. Un hydration guard in-component non era sufficiente — troppe sorgenti di divergenza nel context tree (theme, locale, gate). Per un dialer SPA la SEO è irrilevante e il bundle è abbastanza grande che l'HTML statico non accelera il first-paint visibile. `"single"` è la scelta corretta. **Non flippare di nuovo a `"static"` senza un audit SSR-safety completo.**

2. **Module-level theme sync** (fuori dal componente, file top in `_layout.tsx`): su `Platform.OS === 'web'` legge `readStoredThemePreference()` + `prefers-color-scheme` e setta `document.documentElement.style.colorScheme` + `document.body.style.backgroundColor` PRIMA del primo render React. Minimizza il flash di sfondo bianco al cold load (tra HTML shell vuoto e primo paint React). Tocca solo nodi DOM che React non controlla via JSX. **Wording onesto**: "earliest possible from JS", non "pre-paint".

3. **Hydration guard in-component** (`const [hydrated, setHydrated] = useState(false)` + `useEffect(() => setHydrated(true), [])`): oggi è dead-equivalent in modalità `"single"` (no hydration step), ma resta come **defensive scaffolding** che documenta il pattern. Se domani qualcuno riprovasse `"static"`, il guard è già pronto e maschera `isDark` / `gateChecked` correttamente al primo render.

Vedi [[feedback-web-first-paint]] per dettagli e regole su cosa fare prima di tornare a `"static"`.

**O. Drawer icons usano `focused ? primary : (color ?? onSurface)`.** Tutti i `DrawerItem.icon` passano questa funzione di colore esplicita per icone visibili in entrambi i temi senza perdere l'highlight active. Il `drawerInactiveTintColor` passa a `onSurface` (era `onSurfaceVariant` che in dark scompariva su alcuni rendering).

**P. Eager customer FK al submit.** `backend/app/api/calls.py` `submit_audio_call` ora cerca il `Customer` per `phone_e164` PRIMA del commit (clone-first/seed-fallback in demo via stesso pattern di `customers.py:74-91` `get_customer_by_phone`, session-scoped in prod) e valorizza `call.customer_id`. Lista chiamate vede subito il nome "Mark Ross" invece di "Unknown" durante l'analysis (era 5-30 secondi di gap). Caveat: se la FK punta a una seed row, il pipeline successivo `_resolve_customer` clonerà la seed in row session-scoped e POTREBBE riscrivere la FK del Call — è accettabile per "nome subito", non è una FK stabile finale.

**Q. Personal calls visibili sempre nel feed.** `backend/app/db/seed.py` ha `_ensure_personal_calls(session)` che gira FUORI dalla guardia `if existing templates: return`. Idempotente via UUID fissi (`22222222-...`). Inserisce: 3 missed (`status='failed'` su numeri di `MOCK_CONTACTS`), 2 unsaved (`status='completed'` su numeri sconosciuti), 2 human-handled (`status='completed'` su contatti mock con `raw_transcript=None, extracted=None, actions=[]`). Tutti con `is_seed=True, session_id=None, template_id=<first seed template>` (non-nullable). Visibilità garantita dal `visibility_filter_seedable` che `api/calls.py` applica anche sulle `calls`. **Le fixture duplicano phone/name letterali da `MOCK_CONTACTS`** — backend non importa frontend; commento `must stay in sync with app/lib/mockContacts.ts entries pc_001/pc_003/pc_004/pc_008/pc_009` sopra la lista.

**R. Mock contacts: foto reali da `randomuser.me`, hard-coded.** `app/lib/mockContacts.ts` ha optional `avatar_url` su `PersonalContact`. URL puntano a `https://randomuser.me/api/portraits/{women,men}/N.jpg` (pool curated di foto reali). Scelti uno per uno per matchare il gender del nome. Prima provato `DiceBear avataaars` con `top=` filter ma anche con `facialHairProbability=0` il seed RNG di alcuni nomi (Amelia → unibrow + hoodie) renderizzava ambiguo. ~Metà dei contatti hanno `avatar_url`, metà no (per mostrare anche il fallback iniziali colorate). `ContactAvatar` riceve `avatarUrl` prop opzionale, mostra `<Avatar.Image>` con `onError` che fallback alle iniziali se la URL fallisce (anti-CSP/anti-network blip). `initialsFromName` ora ritorna `''` per stringhe phone-like (`/^\+?[\d\s().-]+$/`) così i numeri sconosciuti non mostrano "+" come iniziale ma il person icon generico. **(round 10 polish: revert — `initialsFromName(phone)` torna a `"+"` o `"#"` per parità visiva avatar; vedi sub-decisione 1.diciassette)**

**Why:** il primo audit visivo mobile post-rewrite (Chrome 412×900) ha mostrato che la UI Material 3 era completa ma alcuni dettagli — drawer senza Calls voice, locale solo EN, badge booking minimale, transcript one-line, "+" iniziali brutti, avatar mock gender-ambigui, reset demo che hang — facevano sembrare la demo "quasi finita" invece di "pulita". Round 3 chiude tutti i gap che un giudice noterebbe in 30 secondi di scroll.

**How to apply:**
- Quando aggiungi una nuova sezione del Drawer, segui il pattern `focused ? primary : (color ?? onSurface)` per le icone.
- Quando aggiungi un format di data/ora, **passa attraverso** `app/lib/dateFormat.ts` (mai `toLocaleString()` raw, mai `MONTHS` array hardcoded).
- Quando aggiungi una mock contact, hardcoda `avatar_url` (donna/uomo a mano), non delegare a generatori RNG.
- Quando aggiungi un'azione che vive sul device dell'operatore, aggiungila a `REAL_ON_DEVICE` in `app/app/call/[id].tsx` per nascondere il badge Simulated (UI-only, non toccare il backend).
- Quando aggiungi una guardia di "primo accesso", usa `markFreshSession()`/`consumeFreshSession()` da `app/lib/freshSession.ts` — non re-implementare flag custom.
- Quando devi un Dialog di conferma da un DrawerItem, usa **sempre** Paper `<Portal><Dialog>`, mai `window.confirm`.

### 1.nove. Template simplification + legacy wizard cleanup (2026-05-17)

Sfoltimento del `Template` model + del wizard surface. La prima ondata (mattino 2026-05-17) ha tolto governance/routing dal template; la seconda (sera 2026-05-17, ticket `ticket-remove-legacy-compressed-pie`) ha completato la pulizia rimuovendo il wizard one-shot e i residui PII testuali. Solo il "product surface" e il wizard conversazionale sopravvivono. Decisione e dettagli di esecuzione in [[project-template-simplified-2026-05-17]].

**Cosa è cambiato (riferimento veloce — la memory dedicata ha la mappa file completa):**

- `FieldDefinition` non porta più `pii_class` / `sensitive`. Restano `confidence_threshold`, `extractor_hint`, `depends_on`, `options`, `required`.
- `ActionDefinition` non porta più `mock_target` / `mutates`. Restano `preconditions`, `confidence_threshold`, `evidence_required`, `payload_schema`.
- `mock_target` (era già nel catalog) e **`mutates`** (campo nuovo di `ActionCatalogEntry`) sono ora source-of-truth in `app/integrations/action_catalog.py`. `action_executor` e `action_planner` fanno lookup-by-key (`action_catalog.mutates(key)`).
- `pii_sanitizer.py` e `pii_policy.py` **cancellati**. La pipeline non emette più audit step `pii_policy_applied`. Pipeline post-call ora 4 step: `call_analyzer` → `action_planner` → `action_executor` → `_persist_memory`.
- `Template.custom_dictionary` **droppato** (migration `0012_drop_template_custom_dictionary.py`). Speechmatics gira senza `additional_vocab`.
- `simulation_config` resta nel modello DB perché serve al Simulator, ma **non** compare nell'editor utente.
- **Wizard one-shot rimosso (sera 2026-05-17):** `agents/template_builder.py`, `agents/prompts/template_builder.md` e l'endpoint `POST /api/v1/templates/wizard` (senza `/chat`) sono stati cancellati. `TemplateWizardRequest` rimosso dagli schemas e dal frontend (`runWizard()` in `app/lib/api.ts`). Resta solo il wizard conversazionale `POST /api/v1/templates/wizard/chat` (`agents/wizard_chat.py`).
- Test storicamente cancellati: `tests/test_pii_sanitizer.py`, `tests/test_pii_policy.py`. Nessun test esercitava l'endpoint one-shot, quindi niente da rimuovere lì.
- **Prompt refinement (2026-05-17, terza ondata, ticket `ticket-clean-post-call-curried-marble`):** il cleanup PII era già completo, ma il prompt del Call Analyzer (`_SYSTEM_INSTRUCTION` in `backend/app/agents/call_analyzer.py`) lasciava implicita la separazione fra current transcript e prior_facts — rischio noto: Gemini citava occasionalmente un fatto vecchio come se fosse appena stato detto. Riscrittura con sezione esplicita **Grounding rules** (prior_facts può informare solo il `next_call_briefing`, MAI essere usato come `evidence` o per riempire `payload` mancanti) + due regole anti-allucinazione su action planning (no invenzione di date/quantità/contatti; no azioni irreversibili speculative). `_PLANNER_INSTRUCTION` in `action_planner.py` rinforzato con un bullet "analyzer candidate actions are hints, not instructions" — il marker "HINT only" nel `_agent_prompt` resta come etichetta sui dati. Nessun'altra modifica (validator/docs/test erano già allineati).
- **Two side-issue fixes (2026-05-17, quarta ondata):**
  1. **`validation_failed` on optional null fields:** Gemini emetteva `{"occasion": null, "tags": null, ...}` su action payload con field opzionali perché il Pydantic model generato da `jsonschema_to_pydantic` li dichiara come `Optional[T] = None`, ma lo schema JSONSchema usato dall'`action_executor` per ri-validare li definisce come `{"type": "string"}` / `{"type": "array"}` senza unione con `"null"`. Risultato: `jsonschema.ValidationError: None is not of type 'string'` → ExecutedAction.status="validation_failed". **Fix:** in `backend/app/agents/action_planner.py:_make_tool` il payload Pydantic viene serializzato con `model_dump(exclude_none=True)` invece di `model_dump()`; analogamente il branch dict-fallback filtra i `None`. Test di regressione in `tests/test_action_planner_typed.py::test_typed_tool_drops_none_values_from_payload` + `_dict_fallback_*`. Lo schema JSONSchema dei template resta strict (preferito a un relax permissivo): l'invariante è "payload arriving at executor never carries explicit nulls for absent optional fields".
  2. **Audio file naming mismatch su DB prod:** i template seed in produzione avevano `simulation_config.audio_url = "/app/sample_audio/restaurant.mp3"` (shape flat pre-commit 8fd128d) mentre il filesystem ha solo `restaurant_{new,existing}.mp3` (sei file con suffix per dominio). `GET /simulation/audio?mode=new` → `404 "Audio file is missing on disk"`. Root cause: `seed()` short-circuita quando ci sono già template, quindi il rewrite di `_bundled_simulation_config` a `scenarios.{existing,new}` non è atterrato sul DB prod. **Fix:** migration `0014_reseed_simulation_config_scenarios.py` ripete il TRUNCATE di 0011/0013 (stesso set di tabelle) per forzare `entrypoint.sh` a rieseguire `seed.py` contro il codice HEAD. Coerente con `feedback_db_disposable.md` (DB content monouso).

**Why:** ticket "simplify template model" + follow-up `ticket-remove-legacy-compressed-pie` — l'editor era diventato un wizard "PII + ASR + mock routing" mentre il valore di hackathon è la pipeline post-call + esecuzione tipata. Il flusso conversazionale è anche il pitch agentico (più Gemini interaction visibile al giudice). Piani originari: `ticket-simplify-template-fuzzy-forest` (mattino) + `ticket-remove-legacy-compressed-pie` (sera) + `ticket-clean-post-call-curried-marble` (notte, prompt refinement).

**How to apply:** prima di rimettere un campo cancellato nel template Pydantic, leggere il ticket: il piano corretto è arricchire il catalog (o aggiungere uno step di policy esterno al template), non il template. Per nuovi campi di runtime safety (es. retry policy, rate limit), il posto è `ActionCatalogEntry`, non `ActionDefinition`. Per cambiare il flusso wizard, lavorare in `agents/wizard_chat.py` (system instruction, slot model) e nel frontend `app/templates/wizard.tsx`; **non** ri-introdurre un endpoint one-shot stateless — la conversazione è feature.

### 1.dieci. Round 5 UI/agent feedback cluster (2026-05-17, pomeriggio)

Cluster di fix dopo che l'utente ha fatto un giro completo dell'app demo e segnalato 7 macro-aree di problemi. Plan in `.claude/plans/il-tuo-obiettivo-curried-lemur.md`; audit esterno di un collaboratore applicato prima dell'esecuzione (vedi [[feedback-external-audit]]).

**Nuove decisioni durature:**

1. **`Call.failure_kind` computed lato BE.** `Call.status="failed"` da solo non distingue "missed call reale" da "pipeline crash tecnico" — l'orchestrator setta `Call.error="empty_or_noise_audio"` per le missed e `Call.error="call_analyzer: …"` / `"action_planner: …"` per i crash. Soluzione: `CallListItem` + `CallDetailView` espongono `failure_kind: Literal['missed','pipeline_error'] | None` calcolato da `_failure_kind()` in `backend/app/api/calls.py` con whitelist `_MISSED_ERROR_CODES = {"empty_or_noise_audio", "missed_call"}`. Nessun nuovo campo DB. Frontend mostra label "Missed" (neutral) vs "Pipeline error" (red) basandosi su `failure_kind`, non sul boolean `error is None`. **Quando aggiungi un nuovo skip-style failure all'orchestrator, aggiorna la whitelist** o un missed reale finirà come pipeline_error.

2. **`payload_schema` arricchito al persistence boundary, NON dal wizard.** `ActionDefinitionDraft` (lo schema che esce da Gemini structured-output) non può portare `payload_schema` perché Gemini rifiuta `additionalProperties`. Conseguenza: il wizard ritorna sempre `payload_schema=None`. Soluzione: ogni `ActionCatalogEntry` carica un `default_payload_schema` (popolato in `backend/app/integrations/action_catalog.py` per booking/appointment/inspection/whatsapp/sms/email/case/booking.cancel). In `backend/app/api/templates.py:create_template` + `update_template` un helper `_enrich_action_types_with_catalog_schemas` fa `setdefault("payload_schema", entry.default_payload_schema)` sul dict serializzato di ogni action_type. Risultato: `action_planner._make_tool()` segue il typed branch (Pydantic via `jsonschema_to_pydantic`), il fallback `Optional[dict]` resta come safety net. **Non spostare il merge nel wizard layer** (verrebbe droppato dalla validazione Pydantic); **non popolare via DB seed** (i custom non passano dal seed).

3. **`action_planner` fallback `payload: Optional[dict] = None`.** ADK 1.18+ rifiuta `payload: dict = None` ("Default value None of parameter payload: dict is not compatible"). Stesso pattern già applicato a `evidence: list[str]`. Annotation cambia da `dict` a `Optional[dict]` (union ammette il None default). Vedi commit + `tests/test_action_planner_typed.py::test_make_tool_without_payload_schema_falls_back_to_dict` per la regressione.

4. **`UpdateTemplateRequest.name` editabile end-to-end.** Prima il rename era impossibile via API; ora `schemas/templates.py` accetta `name: Optional[str] = None`, `api/templates.py:update_template` strippa, valida non-vuoto (422), check unicity dentro `visibility_filter_seedable(session_id, is_seed)` (409 se collide con seed o template della stessa session). Frontend `app/templates/[id].tsx` espone TextInput "Name" per non-seed templates + gestione 409 con messaggio user-facing. Wizard `app/templates/wizard.tsx` ha già TextInput nel DraftSidebar bindato a `draft.name`. **Regola di prodotto**: il check di unicity replica esattamente il filtro della list endpoint, così "non ci sono mai due voci con lo stesso nome nella lista che vedi".

5. **Wizard "Integration discovery" HARD RULE.** Il system instruction di `agents/wizard_chat.py` ora include una regola esplicita: prima di draftare azioni `whatsapp.*` / `sms.*` / `email.*` / `case.open_insurance`, il wizard DEVE confermare con l'utente quali canali usa. Il primo turno è una domanda di clarification a meno che il primo messaggio utente menzioni esplicitamente i canali. Se BUDGET_EXHAUSTED e canali ancora ignoti → drafta omettendo le azioni canale-dipendenti (mai default a WhatsApp). Vedi [[feedback-wizard-agentic]] aggiornata. **Non rimuovere la regola** anche se l'agente sembrerà "meno snello al turno 1" — l'alternativa era proporre WhatsApp a un ristorante che non lo usa, percepito come "AI che non ascolta".

6. **Template validator deterministico puro.** `validate_template()` in `agents/template_validator.py` ritorna esclusivamente `ValidationReport(issues=validate_template_deterministic(template))`. Il source-based filter precedente esisteva perché un `_semantic_review` Gemini emetteva issue narrative ("instruction ambiguous", "label mismatch") che venivano loggate ma droppate dalla response — confondevano l'operatore. **2026-05-17**: `_semantic_review`, `_SEMANTIC_INSTRUCTION`, `ProposedMock`, il campo `ValidationReport.proposed_mocks` e `agents/prompts/template_validator.md` sono stati rimossi. La funzione è ora sincrona, niente LLM call, niente network. Il caso d'uso che `proposed_mocks` copriva (action key fuori catalogo) era già gestito server-side in `wizard_chat` che droppa la key dal draft e la espone via `proposed_actions_from_catalog`. Il messaggio del grammar checker `_validate_prompt_hint_when_grammar` resta business-friendly con `severity="error"`. Vedi [[project_template_validator_deterministic]].

7. **Pipeline status "in progress" in UI senza nuovo enum.** Originariamente proposto un nuovo `Call.status="processing"`. Scartato per non toccare il lifecycle. Soluzione: lato frontend, `status in {"transcribing", "analyzing"}` → label "Analyzing…" + icon `progress-clock` (sia in `CallRow` che in `statusChip` del call detail). Niente migrazione, niente cambio orchestrator.

**Cambi UI durature (round 5):**

- **Sidebar minimalista**: rimossi il wordmark "afterglow / AI dialer" e la voce "Contacts" dal drawer (`app/app/(drawer)/_layout.tsx`). Ordine attuale: `Calls`, `Templates`, `Audit log`, ─── `Test simulator`, ─── `Settings`, `[Reset demo]` (demo only). Divider sopra Test simulator separa app reale da area test.
- **Contacts top-right Home**: `IconButton account-multiple-outline` in `(tabs)/index.tsx` header (`router.push('/(drawer)/contacts')`). Pattern Pixel Dialer (vedi reference screenshots `tmp/WhatsApp Unknown 2026-05-17 at 02.26.39/`). La route `(drawer)/contacts` esiste ancora ma non è esposta come DrawerItem.
- **Welcome dialog fresh install**: nuovo Paper Dialog in `templates.tsx` mostrato al mount se `consumeFreshSession()` è true (consume nel useState init, dialog visible via useEffect). CTA `Pick a preset` (contained, primary) / `Build from prompt` (outlined). Si attiva una volta sola per sessione, fa il consume al mount NON in `activate()`.
- **Modal "Template activated" contrast fix**: bottone "Go to Calls" passa da `mode="contained-tonal"` a `mode="contained"` per contrasto leggibile nel Light theme.
- **Bookings sort chips**: in `(tabs)/index.tsx` quando la tab Bookings è attiva, appare un row di chip `By call date` (default) / `By booking date`. La sort logic in `slotMs` è applicata solo se `bookingsSortMode === 'booking_date'`.
- **CallRow / Call detail label semantiche**: `directionIcon()` rimossa. `statusLabel(call, theme)` ritorna `{ text, color }` con `Incoming` / `Missed` (failure_kind missed) / `Pipeline error` / `Analyzing…` / `Pending`. Icona phone droppata: il testo è autosufficiente.
- **Call detail spacing + JSX subtitle**: `Card.Title.leftStyle.marginRight: 16` (era 12); `subtitle` è ora un `<View>` JSX (NON una funzione — Card.Title types accettano ReactNode, non `() => ReactNode`) con flag emoji + phone + chip language. `customer/[id].tsx` segue lo stesso pattern. Riusa `flagFromE164` esistente.
- **Avatar lookup unified**: `app/lib/callerResolver.ts` espone ora anche `resolveFromCallDetail(call: CallDetailView)`; il call detail e il customer detail usano `findMockContact(phone)?.avatar_url` per mostrare la foto reale invece dell'iniziale verde.
- **Simulator FAB centering**: `fabRow.justifyContent: 'center'` + `gap: 40`; `fabCol` senza `minWidth`. Avatar ringing 128→96, talking 160→112. `CallerContext` wrappato in `ScrollView` per consentire scroll della briefing/recent calls senza coprire i FAB. Bottom-sheet expandable rinviato a post-hackathon.
- **Wizard editable name + save redirect**: `app/templates/wizard.tsx` ha `TextInput "Template name"` in cima al DraftSidebar bindato a `draft.name`; `save()` ora redirige a `/(drawer)/templates` (lista) invece che al detail del template appena creato. "Save & activate" attiva via `set_active=true` nel POST e poi redirige; il dialog "Template activated" appare comunque.
- **Settings cleanup**: rimossa la sezione `Diagnostics` con "Audit log" (era duplicata col DrawerItem); ordine finale: Appearance → Format → [Demo controls if demo] → About (in fondo).
- **Demo-site copy**: `demo-site/src/App.tsx` colonna sx aggiornata per descrivere il nuovo flow welcome-dialog → preset/wizard → Home → Simulator.

**File toccati in questa ondata (24 file):** `backend/app/{agents/{action_planner,template_validator,wizard_chat}.py, api/{calls,templates}.py, integrations/action_catalog.py, schemas/{calls,templates}.py}`; `app/{lib/{types,callerResolver}.ts, components/CallRow.tsx, app/(drawer)/{_layout,settings,templates,(tabs)/index}.tsx, app/{call,customer}/[id].tsx, app/incoming-call.tsx, app/templates/{[id],wizard}.tsx}`; `demo-site/src/App.tsx`; test backend aggiornati: `test_action_planner_typed.py`, `test_wizard_chat.py`, `test_template_validator.py`. **74/74 backend pytest verdi**, `tsc --noEmit` app verde, `vite build` demo-site verde.

**Why:** giro utente completo + audit esterno hanno trovato 7 cluster di problemi: onboarding mancante, contrast bug Light, ordinamento Bookings, navigazione Contacts mal posizionata, bug visivi Call/Customer detail, wizard troppo eager senza clarification, bottom-bar simulator non centrata, crash action_planner su template wizard-built (`payload: dict = None`), Settings con voce duplicata. La forma del fix (failure_kind computed + payload_schema enrichment + Integration discovery rule) è stata ricalibrata sull'audit per evitare assunzioni sbagliate sul contratto (es. l'idea iniziale "error null = missed" era sbagliata perché l'orchestrator setta sempre `error="empty_or_noise_audio"` sulle missed reali).

**How to apply:** quando si tocca un'area di questo cluster, leggere le regole 1-7 sopra prima di modificare. Le tentazioni ricorrenti da evitare: (a) discriminare missed/pipeline su `Call.error is None` invece di `failure_kind`; (b) provare a far emettere `payload_schema` dal wizard model (Gemini lo rifiuta); (c) rimuovere la Integration discovery rule perché "rallenta il primo turno"; (d) re-introdurre la voce "Contacts" nel Drawer; (e) re-introdurre un List.Item "Audit log" in Settings (è già nel Drawer); (f) ricorrere a `() => <View>...</View>` per `Card.Title.subtitle` (i types accettano solo ReactNode); (g) introdurre un nuovo `Call.status` valido senza aggiornare orchestrator + tests + idempotency check.

### 1.undici. Round 6 UI consistency (2026-05-18)

Quattro inconsistenze emerse durante la verifica live del round 5 (commit
`f3a9df5` / `059553f`), tutte risolte in un'unica passata frontend-only.
Plan: `.claude/plans/il-tuo-obiettivo-curried-lemur.md` (round 6, overwrite
del piano round 5).

**Decisioni durature:**

1. **Drawer active highlight per ogni DrawerItem.** Prima solo "Calls"
   leggeva `activeRouteName === '(tabs)'` e settava `focused +
   activeTintColor + activeBackgroundColor + labelStyle`. Templates / Audit
   log / Test simulator / Settings ignoravano lo stato corrente. Fix in
   `app/app/(drawer)/_layout.tsx`: derivare
   `isOnTemplates/isOnAudit/isOnSimulator/isOnSettings` da
   `props.state.routes[props.state.index]?.name` e applicare lo stesso
   pattern di styling a tutti gli item. Helper inline
   `itemLabelStyle(focused)` per evitare la duplicazione. **Quando
   aggiungi un nuovo DrawerItem, ricalcola il flag `isOnX`** o l'item non
   si evidenzierà.

2. **Test simulator vive nel `(drawer)`.** Era una `Stack.Screen` root,
   quindi mostrava back-arrow al posto dell'hamburger e mai nessun
   highlight nel drawer. Fix: `git mv app/app/simulator.tsx
   app/app/(drawer)/simulator.tsx`, registrato come `<Drawer.Screen
   name="simulator" options={{ drawerItemStyle: { display: 'none' } }}>`
   (il DrawerItem visibile è custom in `DrawerContent`, identico pattern
   di `(tabs)`), rimossa la `<Stack.Screen name="simulator">` dal root
   `_layout.tsx`. Aggiunto `Appbar.Header` con hamburger
   (`DrawerActions.openDrawer()`). Import relativi dentro al file:
   `../lib/…` → `../../lib/…`. **Non re-introdurre la
   `<Stack.Screen name="simulator">` nel root** o la route si
   sdoppierebbe.

3. **Call detail header — Pressable Card.Content + tags inline.** Il
   `<Card.Title>` di Paper non gestisce bene 3+ righe sotto il titolo e
   non supporta gerarchie cliccabili compound. Fix: sostituito con un
   `Card.Content` custom + `<Pressable>` a 3 colonne (avatar | text col |
   status chip). Avatar + nome cliccabili →
   `/customer/${customer_id}` quando il customer esiste, rimpiazzano
   la `Card.Actions "Open contact"` che è stata rimossa. Dal subtitle
   è uscito il chip `detected_language` (era ridondante con la
   bandiera). Sotto il subtitle: `formatDateTime(call.created_at,
   locale)` come `bodySmall`, poi una `tagRow` con
   `customer.tags.slice(0, 4)` come `Chip mode="outlined" compact`.
   L'error tecnico appare solo se `failure_kind === 'pipeline_error'`
   (regola già del round 5). **I tag in call detail sono read-only**:
   per editarli si va su customer detail.

4. **Customer detail header coerente + Calls list senza icone.** Stesso
   refactor a `Card.Content + headerRow` (senza Pressable, qui sei già
   sul customer). Rimosso il chip `preferred_language` a destra
   (duplicava la bandiera). Nella sezione "Calls (N)" rimossa
   `<List.Icon icon="phone-incoming">` e la description ridondante
   `${detected_language} · ${formatRelativeTime}`. Layout nuovo:
   `<TouchableRipple>` con `<View style={callRow}>` a 2 colonne (date
   + ora a sinistra, status chip a destra), `<Divider />` Paper-light
   tra le righe. **La coerenza visiva fra call detail e customer
   detail è il punto** — se cambi il layout in uno, replica nell'altro.

**Patterns da preservare:**

- Per ogni futuro screen drawer: registrare `<Drawer.Screen>` E
  rendere il `<DrawerItem>` custom con `focused={isOnX}` +
  `activeTintColor` + `activeBackgroundColor` + `labelStyle(isOnX)`.
- `Card.Title.subtitle` accetta solo `ReactNode`, **non**
  `() => ReactNode`. Se servono 2+ righe sotto il title, abbandona
  `Card.Title` e usa `Card.Content + custom layout`.
- `formatDateTime` resta l'unica funzione locale-aware per le date in UI
  — niente `.toLocaleString()` raw. Vedi [[feedback-locale-dates-only]].

**File toccati (round 6, 5 file frontend):**
`app/app/(drawer)/_layout.tsx`, `app/app/(drawer)/simulator.tsx`
(rinominato), `app/app/_layout.tsx`, `app/app/call/[id].tsx`,
`app/app/customer/[id].tsx`. Niente backend, niente test backend, `tsc
--noEmit` verde.

### 1.dodici. Round 7 UI polish + seed credibility (2026-05-18)

Dodici frizioni emerse dall'audit visivo post round 6, chiuse in un
unico ciclo frontend+backend additivo. Niente lifecycle changes nel
backend — solo response shape estesa (`CallListItem.customer_tags`) e
densificazione seed. Plan:
`.claude/plans/il-tuo-obiettivo-curried-lemur.md` (round 7, overwrite
del round 6).

**Decisioni durature:**

1. **Avatar legend brand.** `ContactAvatar` accetta `isCustomer?:
   boolean`. Quando true il border passa da `1dp rgba(0,0,0,0.08)` a
   `2dp theme.colors.primary`. Il chip `Clients` del filter row porta
   sempre un border `primary 1dp` (selected o no) — è la legenda
   visiva. **Non aggiungere badge testuali per distinguere
   customer vs phonebook**; il border + chip sono la convenzione del
   prodotto.

2. **Call non-client = no-op al tap.** In Home, `onPress` su una
   `CallRow` è `undefined` quando `call.customer_id == null`. La row
   diventa inerte (Paper TouchableRipple skippa il ripple). Niente
   "expand inline" né "save as contact" — è scope post-hackathon,
   vive in `afterglow/docs/future-ideas.md`. `CallRow.onPress` è ora
   `optional`; rilassare la signature di altri call site se servirà.

3. **`CallListItem.customer_tags` esposto dal backend.** Query in
   `list_calls` (FastAPI) estesa a 3-uple
   `select(Call, Customer.display_name, Customer.tags)` con
   `LEFT OUTER JOIN`; gli item senza customer ritornano `[]` (mai
   `None` lato client). Il frontend mostra questi tag come description
   delle row in modalità `bookings` (`tags.slice(0, 3).join(' · ')`);
   row senza tag → `description={undefined}` (la slot description di
   `List.Item` non lascia un buco bianco). **Non passare un `<Text>`
   vuoto come description**: `List.Item` riserva l'altezza anche per
   string vuote.

4. **Home filter chip — `primaryContainer` per selected.**
   Material 3 light mode: il `secondaryContainer` su background neutro
   è troppo sottile. Switch a `backgroundColor: primaryContainer +
   selectedColor: onPrimaryContainer` per il chip selezionato. Il
   chip `Clients` resta speciale (border primary sempre).

5. **Templates Activate button → `mode="outlined"`.** Distingue
   visivamente dall'Active chip filled del template attivo.

6. **Wizard DraftSidebar — ProgressBar al posto del chip %.**
   `<ProgressBar height=6 borderRadius=3>` con colore `primary` quando
   ready, `secondary` altrimenti; label `bodySmall` `X% ready` sotto.
   Fields e actions sono `<Chip mode="outlined" compact textStyle={{
   fontSize: 11 }}>` in un row `flexWrap`, niente più bullet `·` con
   tipo in parentesi.

7. **Simulator card multilinea (scope chirurgico).** SOLO la prima
   "status card" del simulator screen è cambiata: `Card.Title` →
   `Card.Content` custom (avatar + label `Active template` + nome
   multilinea + chip `Audio ready` con `alignSelf: 'flex-start'`). I
   blocchi aggiunti dal commit `640c962` (Trigger demo call, Generate
   script/audio, upload audio, Script preview con accordion existing/
   new) sono **preservati intatti**.

8. **Customer detail Calls list — relative time.** Ogni row ora ha
   `formatDateTime` su `bodyMedium` + `formatRelativeTime` su
   `bodySmall` sotto, chip status a destra. Style
   `callRowText: { flex: 1, gap: 2 }`. Coerente col pattern delle
   altre liste call.

9. **Call detail `prettyValue` helper.** `whatsapp` → `WhatsApp`,
   `sms` → `SMS`, `email` → `Email`, `phone` → `Phone`;
   capitalizzazione di single-token lowercase (`dinner` → `Dinner`);
   date / multi-word / mixed-case lasciati intatti. Sostituisce il
   vecchio `formatValue`. **Non espandere a date+time merge o
   field-name remapping**: dipenderebbe dal template schema e non
   vale la complessità.

10. **Template detail badge wrap.** Rimossa `numberOfLines={1}` da
    title/meta dell'`EditorHeader`. Badge `<Chip compact>` (Changes
    records / Needs transcript proof) ora vivono SOTTO title/meta
    (non a destra accanto al chevron) e con `textStyle={{ fontSize:
    11 }}`. `badgeRow.justifyContent` flippato `flex-end` →
    `flex-start`. Risolve il troncamento `Cre...` / `app...` su
    viewport 375px.

11. **Seed credibility — busy week densification + AI bookings mix.**
    Nuovo helper `_busy_week_specs()` che genera 43 entries (UUID5
    deterministico da `(phone, created_at.isoformat())`) sparpagliate
    9-17 mag con slot orari realistici (lunch/dinner per weekday,
    spread più largo per weekend). Mix:
    - **9 AI bookings** (Mark×4 restaurant, Julia×2 restaurant, Andrew×2
      bodyshop, Laura×1 dentist) — kind=`ai_booking` nel plan.
      `_make_ai_booking_spec()` materializza una spec
      `_emit_seeded_call_core`-compatibile dai blueprint in
      `_AI_BOOKING_BLUEPRINTS`; ogni AI call emette
      `Call+ExtractedFields+ExecutedAction+AuditLog` con
      `booking.create` (round 8 ha unificato anche dentist e bodyshop
      sotto questa key). La `booking_date` è `created_at + 2 days` per
      avere slot future-dated rispetto alla call.
    - **22 completed personal** (human-handled, niente extracted).
    - **11 missed** (`error="empty_or_noise_audio"`).
    - **1 pipeline_error** (`error="action_planner: simulated failure"`).
    Customer reuse: Mark Ross 4×, Andrew Green 2×, Julia White 2×,
    Laura Bennett 1× — `customer_id` risolto da phone via query.
    `Customer.total_calls` e `last_call_at` ricomputati post-insert
    (`func.count + func.max`).
    **`BOOKING_ACTION_TYPES`**: round 7 estendeva la lista a
    `appointment.*` come fallback per dentist/bodyshop; **round 8 ha
    eliminato `appointment.*` del tutto**, tornando a `("booking.create",
    "booking.cancel")`. Vedi sub-decisione `1.tredici` per i dettagli.
    **Quando aggiungi customer al seed**, aggiungili a
    `_CUSTOMER_PHONES_BY_NAME` (recompute) **e** opzionalmente a
    `_AI_BOOKING_BLUEPRINTS` (per generargli AI calls).

12. **Test backend pragmatico per `customer_tags`.** `Customer.tags`
    è `ARRAY(String)` Postgres-only — niente SQLite parity. Test
    integrato richiederebbe testcontainers, overkill per round UI.
    Soluzione: `test_calls_list_schema.py` testa la response shape
    al boundary Pydantic (default factory, roundtrip JSON, payload
    senza la key). 4 nuovi test, 0.12s. **Per un test HTTP/DB end-to-
    end servirebbe una fixture Postgres ephemeral** — se serve in
    futuro, è il punto giusto da estendere.

**Patterns da preservare:**

- `Customer.tags` espone tag scrivibili via `customer.update_profile`;
  ogni nuovo consumatore lato API deve unpackare `list(tags or [])`
  per assorbire i LEFT JOIN miss.
- `_ensure_personal_calls` recupera i customer per phone (non per ID
  passato come argomento) — il flow "already seeded, just top up"
  riusa lo stesso codepath del primo seed.
- Quando si introducono nuovi `Call` con `customer_id` valorizzato in
  un helper di seeding, aggiornare sempre `Customer.total_calls +
  last_call_at` nello stesso transactional batch.

**File toccati (round 7, ~10 file FE + 3 BE):**
- FE: `app/components/ContactAvatar.tsx`,
  `app/components/CallRow.tsx`,
  `app/app/(drawer)/(tabs)/index.tsx`,
  `app/app/(drawer)/contacts.tsx`,
  `app/app/(drawer)/simulator.tsx`,
  `app/app/(drawer)/templates.tsx`,
  `app/app/call/[id].tsx`,
  `app/app/customer/[id].tsx`,
  `app/app/templates/[id].tsx`,
  `app/app/templates/wizard.tsx`,
  `app/lib/types.ts`.
- BE: `backend/app/schemas/calls.py`, `backend/app/api/calls.py`,
  `backend/app/db/seed.py` + nuovo `backend/tests/test_calls_list_schema.py`.

### 1.tredici. Round 8 — avatar tonal ring + appointment unification (2026-05-18 sera)

Cluster di rifiniture post-pitch-test: avatar customer aveva un sottile
gap percepito e iniziali decentrate (border-width tagliava lo spazio
child a `size - 2*border` mentre `Avatar.Text size=size` rimaneva
centered su altro asse); inoltre `appointment.*` come doppione di
`booking.*` confondeva il prodotto.

**Decisioni durature:**

1. **Tonal ring pattern per ContactAvatar.** Wrapper outerSize =
   size + ringWidth*2 con `backgroundColor` = colore ring e `padding`
   = ringWidth. Child Avatar al centro col suo `size` naturale. Niente
   border, niente clipping, niente gap percepito (il colore del ring
   tocca direttamente lo sfondo del child). Pattern standard
   Material/iOS per avatar tonal ring. `ringWidth = isCustomer ? 2 :
   1`, colore `theme.colors.primary` per customer e
   `rgba(0,0,0,0.08)` per phonebook. **Quando estendi a un nuovo
   tipo di "highlight" sull'avatar, riusa lo stesso pattern: cambia
   solo `ringWidth` + `backgroundColor`** (es. emergency rosso,
   pending grigio mid-tone).

2. **`appointment.*` rimosso del tutto.** Catalog, mocks, API
   `BOOKING_ACTION_TYPES`, wizard prompt, seed templates, seeded
   calls, AI blueprints, `_make_ai_booking_spec`, REAL_ON_DEVICE: una
   sola action key `booking.create` (più `booking.cancel`) attraverso
   tutti i verticali (restaurant/dentist/bodyshop/clinic/salon/gym/
   hotel/events). Mock handler unico (`create_booking_mock`).
   `booking.create.compatible_domains` esteso a includere
   `dentist`, `bodyshop`, `clinic` (i 3 esistenti restano:
   restaurant, hotel, salon, gym, events). **Mai più due action key
   per la stessa operazione semantica con payload divergenti.**

3. **`payload.booking_date` + `payload.booking_time` (HH:MM) sono il
   contratto del BookingBadge.** Tutti i seed templates con
   `booking.create` hanno `booking_date` + `booking_time` in
   `preconditions` AND `payload_schema.required` — il planner non
   emette l'action senza slot. `booking_time` è SEMPRE `HH:MM` in
   24h; la nuance "morning/after lunch" vive in un campo separato
   `booking_notes` (string libera, non-required). Anti-regression
   in `tests/test_seed_templates.py` (3 contract assertions:
   preconditions, payload_schema.required, no-appointment-key-leak)
   + `tests/test_action_catalog.py` (appointment.* not in CATALOG +
   compatible_domains coverage).

4. **`formatRelativeTime` estesa per >24h.** "ieri" / "N giorni fa"
   / "una settimana fa" / "N settimane fa" / "un mese fa" / "N mesi
   fa" / "un anno fa" / "N anni fa" (it + en). Il vecchio fallback
   `formatTime(iso)` (solo HH:MM) era la causa del bug customer
   detail: row > 24h mostravano l'orario due volte. **Non
   reintrodurre il fallback time-only senza un contesto giorno
   esplicito** (la formula assoluta sopra è già `bodyMedium` =
   `formatDateTime`).

5. **`groupByDay` accetta `keyFn?` opzionale.** Permette al
   chiamante di raggruppare per una data alternativa (es. booking
   date invece di created_at). Il chiamante è responsabile del
   fallback su `created_at` quando la data alternativa è missing.

6. **Bookings sort: `{key, dir}` con default asimmetrici.** call_date
   default `desc` (newest call first), booking_date default `asc`
   (next-upcoming slot first, naturale per "cosa devo gestire
   prossimamente"). Tap sul chip attivo flippa `dir`. Tap sul chip
   non-attivo switcha `key` + applica il suo default `dir`. Icona
   arrow up/down sul chip attivo. **L'asimmetria è intenzionale**:
   evita 2 tap per ottenere il default semantico desiderato.

7. **Contacts Clients chip = parità Home.** `borderWidth: 1` +
   `borderColor: theme.colors.primary` permanente; bg
   `primaryContainer` se selected, `transparent` se non selected.
   Stessa legenda visiva del Home — niente difference tra le due
   screen.

8. **Ringing screen microcopy.** Chip orologio nel ringing screen
   mostra solo `relativeTime` (es. "12h ago"), non `"last 12h
   ago"`. L'icona clock-outline e il contesto del ringing screen
   rendono il significato chiaro senza l'articolo "last" che
   suonava sgrammaticato.

**Patterns da preservare:**

- Quando aggiungi una nuova action di tipo "reservation/booking",
  usa `booking.create`. Non creare `<verticale>.create` paralleli.
- Quando aggiungi un seed template, il suo `booking.create` deve
  avere `booking_date` + `booking_time` (HH:MM) sia in
  `preconditions` sia in `payload_schema.required` — i contract test
  in `tests/test_seed_templates.py` lo verificano.
- Avatar visivi: usa il tonal ring pattern per qualsiasi nuovo
  "highlight" sull'avatar (mai border classico).

**File toccati (round 8):**
- FE: `app/components/ContactAvatar.tsx`,
  `app/app/(drawer)/(tabs)/index.tsx`,
  `app/app/(drawer)/contacts.tsx`,
  `app/app/call/[id].tsx`,
  `app/app/incoming-call.tsx`,
  `app/lib/dateFormat.ts`,
  `app/lib/dateGrouping.ts`.
- BE: `backend/app/integrations/action_catalog.py`,
  `backend/app/integrations/mocks/__init__.py`,
  `backend/app/api/bookings.py`,
  `backend/app/agents/wizard_chat.py`,
  `backend/app/db/seed.py`.
- Tests: `backend/tests/test_action_catalog.py` (extended),
  `backend/tests/test_seed_templates.py` (new).
- Docs: `.claude/memory/project_afterglow_decisions.md`,
  `.claude/memory/feedback_real_on_device_whitelist.md`,
  `afterglow/README.md`.

### 1.quattordici. Round 9 — Pixel CallRow pattern + seed varietà (2026-05-18 sera)
Round 9 polish — non aggiunge funzionalità, allinea la list view al pattern Pixel system-dialer e spezza la monotonia del busy-week seed.

**CallRow trailing area**: il `BookingBadge` intero (`DD/MM HH:MM · party N`) resta solo nel filtro `bookings`. Nei filtri `all / missed / clients / saved / unsaved` con booking il badge è sostituito da `BookingMarker` — pill compatta 28×28 (View + Paper Icon `calendar-blank-outline` su `secondaryContainer`). Su ogni row, in qualunque filtro, c'è ora il **`RidialButton`** (Paper `IconButton` `phone-outline`, `onSurfaceVariant`, size 22) wrappato in `Pressable` con `stopPropagation` come safety net su react-native-web. La nuova prop `onRidial?: (phone) => void` su `CallRow` è bindata dall'Home (`(drawer)/(tabs)/index.tsx`) a un Paper `Snackbar` "Calling {phone}… (demo)". Niente `Chip` childless (la prop `children` è required dal type Paper — userebbe fail-`tsc`).

**Status come icona direzionale**: `statusLabel()` rimosso, sostituito da `statusIconInfo()` che ritorna `{icon, color}`. `description()` per non-bookings ora rende `<Icon size=14>` + `<Text>{formatRelativeTime}</Text>` invece di `"Incoming · 11h ago"`. Mapping: `completed` → `arrow-bottom-left` su `onSurfaceVariant`; `failed/missed` → `arrow-bottom-left` su `error`; `failed/pipeline_error` → `alert-circle-outline` su `error`; `transcribing/analyzing` → `progress-clock` su `primary`; `pending` → `clock-outline` su `onSurfaceVariant`. Niente più label testuali (Incoming/Missed/Pipeline error/Analyzing…/Pending) nelle list rows — restano solo in Call Detail.

**Sort chip swap-vertical**: il `Chip` per `By call date` / `By booking date` ora mostra `swap-vertical` quando inattivo (Material standard "tap to sort") invece di icon=undefined. Quando attivo: `arrow-up` (asc) o `arrow-down` (desc). Toggle direzione resta on tap-on-active.

**Seed varietà — 6 customer + busy-week ridistribuito**: nuova costante module-level `SEED_CUSTOMERS: list[tuple]` in `backend/app/db/seed.py` come **single source of truth** dei 6 seed customers. Il main seed path itera questa costante (niente più 4 `Customer(...)` hardcoded). Nuovi clienti:
- `Sophie Walker` (+15552223344, restaurant) — business dinner regular, party 4-6, corner table, callback email.
- `Tom Hughes` (+15557778899, dentist) — new patient ansioso, wisdom-tooth check.

Sia `_AI_BOOKING_BLUEPRINTS` che `_CUSTOMER_PHONES_BY_NAME` estesi ai 6 nomi (tre dict ora isomorfi — è esattamente quello che testano i nuovi contract test). `_busy_week_specs()` ridistribuito: Mark×2, Julia×1, Andrew×2, Laura×1, Sophie×2, Tom×1 = 9 `ai_booking`, mai >1 stesso customer/giorno e niente più streak Mark Ross 4× di fila nel sort Bookings desc. Aggiunte 2 seed AI calls fisse (`11111111-1111-4111-8111-000000000006` Sophie business dinner 8 May, `…007` Tom new-patient 7 May) in `_seed_call_specs`.

**Upsert idempotente per DB già seedato**: dal round 8 il DB di prod non viene più wipe-ato automaticamente (la migration `appointment.*` cleanup è dormiente). Quindi il main seed path è no-op sui boot successivi al primo. Nuovo helper async `_ensure_seed_customers(session)` chiamato in cima a `_ensure_personal_calls`: legge `Customer.phone_e164` esistenti `where is_seed=True`, inserisce solo quelli mancanti da `SEED_CUSTOMERS`. Effetto al deploy round 9: il DB clean-round-8 (Mark/Julia/Laura/Andrew presenti) riceve Sophie+Tom in upsert; il busy-week generator a sua volta li trova e emette le loro ai_booking. Nessun wipe necessario.

**Why:** l'audit visivo round 9 ha trovato 3 cluster (CallRow trailing rumoroso, status come testo poco Pixel-ish, Mark Ross 4× di fila nel sort Bookings desc). Il pattern Pixel dialer come reference è esplicito (utente ha fornito screenshot reale). Il fix con upsert idempotente — invece di un secondo wipe-migration — è motivato da [[feedback-db-disposable]] applicato con criterio: il DB è disposable, ma se posso evitare di wipe-are due volte in due round, lo evito.

**How to apply:**
- Quando tocchi `CallRow.tsx` non re-introdurre `statusLabel()` o testi tipo "Incoming"/"Missed" nella description — sono ricoperti dai test? No, ma `rg "'Incoming'|'Missed'|status\.text" afterglow/app/components/CallRow.tsx` deve restare zero. Le label testuali in Call Detail (`app/app/call/[id].tsx`) sono OK — la decision Pixel-icon-only riguarda solo la list view.
- Quando aggiungi un nuovo seed customer modifica `SEED_CUSTOMERS` (è la sola fonte di verità), poi aggiungi anche entry in `_AI_BOOKING_BLUEPRINTS` + `_CUSTOMER_PHONES_BY_NAME`. I test `test_ai_booking_blueprints_cover_six_customers`, `test_customer_phones_by_name_matches_blueprints`, `test_seed_customers_constant_matches_blueprints` falliscono se i tre dict divergono.
- Quando il busy-week tocca lo schema dei `kind` (es. nuovo `ai_cancel`), aggiorna anche il fixture `ai_booking=True` in `_ensure_personal_calls` per il ramo legacy-cleanup; il pattern UUID5 namespace evita le collisioni.

**File toccati nel round 9:**
- FE: `app/components/CallRow.tsx`, `app/app/(drawer)/(tabs)/index.tsx`.
- BE: `backend/app/db/seed.py`.
- Tests: `backend/tests/test_seed_templates.py` (+5 contract test).
- Docs: `.claude/memory/project_afterglow_decisions.md`, `afterglow/README.md`.

### 1.quindici. Round 9 (parte 2) — Seed expansion + RAG demo read-only + Audit overview + Regenerate briefing + Always-fresh dates (2026-05-18)
Round 9 secondo passaggio — alza il segnale Vultr Award + Agentic Workflow per i giudici (deadline 19 mag 2026) attraverso cinque cambi correlati senza toccare i 6 invarianti hard di [[project-afterglow-hackathon]].

**A) Seed roster da 6 → 12 customer.** Sopra ai 6 esistenti (Mark Ross, Julia White, Sophie Walker, Laura Bennett, Tom Hughes, Andrew Green) sono atterrati 6 nuovi: Marco Bianchi (`+15556667701`, restaurant), Olivia Hayes (`+447911111201`, restaurant), Emma Thompson (`+447911111202`, dentist), James O'Connor (`+15556667702`, dentist), Rachel Kim (`+15556667703`, bodyshop), Luca Romano (`+447911111203`, bodyshop). Phone scelti fuori dai pool `app/lib/mockContacts.ts` per evitare il "mock contact apre il seed". Ciascun nuovo customer ha 3-4 historical AI booking call distribuite 6-8 settimane indietro (~20 nuove call totali) emesse dal nuovo helper `_historical_window_specs()` in `seed.py` (NON `_busy_week_specs`, che resta densificato sulla pitch week 9-17 mag). UUID5 namespace separati per evitare collision con il busy-week generator.
**Why:** la RAG ha senso solo su repeat caller. Con 6 customer × 1-2 call hand-crafted ognuno + 9 busy-week, il dataset non sosteneva il retrieval. Con 12 customer × 4-5 call ciascuno + storia ramificata 6-8 settimane indietro, ogni "Call from existing customer" della demo retrieva fatti reali.

**B) Date sempre fresche via anchor relativo + BULK UPDATE al boot.** Nuova tabella `settings(key, value, updated_at)` (migration `0015_settings_table.py`, key=`seed_anchor_date`, value ISO date). Tutte le date hardcoded in `seed.py` (5 hand-crafted call + busy-week + historical window) sono ora `day_offset: int` relativi a `anchor_date`. UUID5 composition cambiata da `f"{phone}@{created_at.isoformat()}"` a `f"{phone}@day_{day_offset}@slot_{slot_idx}"` → gli ID restano stable a fronte di shift, niente FK breakage. Helper `app/services/settings.py` (`get_seed_anchor`, `set_seed_anchor`, `resolve_seed_anchor_for_materialization`). Al boot, `app/tasks/seed_date_refresh.py.refresh_seed_dates_if_needed(session, today)` fa BULK UPDATE su `Call.created_at/started_at/completed_at`, `AuditLog.created_at` (filtrato per call_id IN seed call ids), `ExecutedAction.created_at`, `ExtractedFields.created_at`, `Customer.last_call_at` (seed only). Per il `booking_date` dentro `ExecutedAction.payload` e `ExtractedFields.fields` (JSONB), usa `jsonb_set` + cast date arithmetic. `briefing_snapshot` + `memory_summary` rifrasati senza date assolute ("Last time he booked for 4 quiet" invece di "on 9 May"); transcript lasciati as-is.
**Why:** durante la judging window (5 giorni) un seed con date fisse appare sempre più stale. Con anchor relativo, ogni boot della VM ri-sincronizza le date a today. Trade-off: i chunk Vultr pre-seedati conservano la date stringa originale ("called on 2026-04-22") — accettato (il giudice non confronta date al millisecondo).

**C) Preseed Vultr Vector Store con per-call idempotency.** Nuovo `app/tasks/vector_preseed.py.preseed_demo_collection(session)`: calcola `expected_call_ids = SELECT id FROM calls WHERE is_seed AND raw_transcript IS NOT NULL` e `already_preseeded = SELECT call_id FROM customer_memory_chunks WHERE chunk_metadata @> '{"preseed": true}'::jsonb`, inserisce solo i mancanti. Estratto helper condiviso `orchestrator._format_briefing_chunk(call, customer, template, briefing, classification)` per non duplicare la stringa f"called the {domain} on..." tra preseed e `_persist_memory`. Try/except per-call → fallimento singolo non interrompe il loop. Wire-up nel `main.py:lifespan` DOPO `recover_orphans()` con catch separati: refresh fail → ERROR + skip preseed; preseed fail → WARNING + continua boot.
**Why:** vedi §1.quater rewrite. L'idempotency per-call sopravvive a partial failures Vultr e a aggiunta/rimozione seed Call senza richiedere reset manuale.

**D) RAG demo unskip via `preseed_available`.** `memory_retrieval.retrieve_customer_context(..., preseed_available: bool)` aggiornata: skip solo se `not collection_id` o se (`is_demo and not preseed_available`). `orchestrator.py` calcola `demo_can_rag = is_demo and collection_id and (customer.is_seed or await _seed_exists_for_phone(session, customer.phone_e164))` e passa `preseed_available=True` quando entra nel ramo RAG. Per gli unknown phone (cold call demo) → continua structured-empty. `_persist_memory` write-back resta invariato (skipped in demo). Audit payload arricchito: `memory_lookup` ha `prior_facts_preview` (primi 1000 char del retrieval), `action_planner` ha `actions[]`, `action_executor` ha `actions_executed[]` (derivato dal **return value** di `execute_planned_actions`, NON da `session.new`), `memory_updater` ha `vultr_item_id` + `collection` (prod). Bug fix latente: import `Any` aggiunto in `memory_retrieval.py` (usato in `_confidence_value` ma non importato).
**Why:** vedi §1.quater. Il giudice vede al PRIMO tap "Call from existing customer" su Mark un audit row `rag_semantic` con prior_facts non vuoto, non al secondo.

**E) `briefing_snapshot` esposto end-to-end + endpoint `Regenerate summary`.** Pre-requisito invisibile fixato in 4 layer:
- `backend/app/schemas/calls.py`: `CallExtractedView` aggiunge `briefing: Optional[str] = None` (alias API user-facing; DB column resta `briefing_snapshot`).
- `backend/app/api/calls.py`: mapper popola `briefing=extracted.briefing_snapshot`.
- `app/lib/types.ts`: TS type aggiunge `briefing?: string | null`.
- `app/app/call/[id].tsx`: Card "Extracted" rende un `<Surface>` italic con label "Next-call briefing" solo se truthy.

Nuovo modulo dedicato `backend/app/agents/briefing_regenerator.py` (NON riusa `call_analyzer.analyze_call` per non sprecare tokens / non tentare di "rifare anche i field"). Gemini call piccola (~120 token output), system instruction stretta. Endpoint `POST /api/v1/calls/{id}/regenerate-summary` con preconditions 409 (`status=completed`, `extracted_fields` esiste, `customer_id IS NOT NULL`). Re-fetcha `prior_facts` con la stessa logica orchestrator (helper estratto `_load_prior_facts`). Audit row `briefing_regenerator status=success` con tokens popolati. UI: `IconButton refresh` nel header Call detail accanto allo status chip, Paper `<Portal><Dialog>` di conferma (NO `window.confirm`, cf. [[feedback-drawer-window-confirm]]), Snackbar success.
**Why:** permette al giudice di re-eseguire l'agentic step più costoso senza triggerare una nuova call, e rende il briefing visibile sulla Call detail (oggi era scritto solo su `customer.memory_summary`).

**F) Audit drawer overview-first.** Backend `AuditLogEntry` (`schemas/audit.py`) aggiunge `call_phone_e164` / `call_display_name` / `call_status` via LEFT JOIN `Call` + **LEFT JOIN `Customer`** (display_name è su Customer, NON su Call — bug latente nella prima proposta). `api.listAudit({ limit: 500 })` default lato client (era 100 cap → 30% delle call non comparivano con 350+ entries). UI rewrite `app/app/(drawer)/audit.tsx`: ScrollView + `List.Accordion` overview per call (avatar = worst step status, title = display_name ?? phone, IconButton open-in-new → `/call/{id}`) → nested `List.Accordion` per agent → `List.Item` leaf con Pressable "Show payload" toggle che mostra Surface monospace JSON. Default tutto collassato. `friendlyAgentLabel` esteso con `briefing_regenerator → "Briefing regenerator"`. Pattern documentato in [[feedback-audit-collapse-pattern]].
**Why:** con la RAG attiva, il `prior_facts_preview` retrieved è il momento "wow" del pitch — ma una FlatList flat lo seppellisce. L'overview-first rende ogni call ispezionabile come un sub-tree.

**Why complessivo:** sale il segnale Vultr Award (RAG read attivo + preseed visibile + audit step `rag_semantic` con prior_facts reali) senza inquinare la collection condivisa tra giudici (write resta skipped). Sale il segnale Agentic Workflow (regenerate visible + audit drawer ispezionabile per call). Sale la credibility del dataset (date sempre fresche + roster ramificato 12 customer).

**How to apply:**
- Quando aggiungi una seed Call: niente da fare. Il preseed al prossimo boot inserisce il chunk Vultr mancante automaticamente.
- Quando rimuovi una seed Call: il chunk preseed resta orphan (call_id=NULL via FK SET NULL). Cleanup manuale via `DELETE FROM customer_memory_chunks WHERE chunk_metadata @> '{"preseed":true}'::jsonb` + dashboard Vultr (no SDK list endpoint).
- Quando aggiungi una nuova data hardcoded in `seed.py`: usa `day_offset` relativo all'anchor, NON `datetime(2026, M, D)`. Aggiorna il composition UUID5 con `f"{phone}@day_{N}@slot_{idx}"` (gli altri namespace sono già stabili).
- Quando tocchi `briefing` su `CallExtractedView`: i 4 layer (schema BE + mapper + TS + render) devono restare allineati, altrimenti l'utente vede il toast del regenerate ma niente cambio visibile.
- Quando aggiungi una pagina list-heavy (>100 entries): segui il pattern overview-first di [[feedback-audit-collapse-pattern]] — ScrollView + List.Accordion lazy + leaf con Pressable "Show payload" (NON un terzo Accordion per il payload — brutta UX).

**File toccati nel round-9 (parte 2):**
- BE schema: nuova tabella `settings` (migration `backend/alembic/versions/0015_settings_table.py`), `backend/app/db/models.py` aggiunto `Setting`.
- BE services: nuovo `backend/app/services/settings.py`.
- BE tasks: nuovi `backend/app/tasks/seed_date_refresh.py`, `backend/app/tasks/vector_preseed.py`.
- BE seed: `backend/app/db/seed.py` — 6 nuovi customer, `_AI_BOOKING_BLUEPRINTS` + `_CUSTOMER_PHONES_BY_NAME` estesi, nuovo `_historical_window_specs`, tutte le date come `day_offset`, UUID5 composition stabile.
- BE pipeline: `backend/app/agents/memory_retrieval.py` (nuovo param `preseed_available`, fix import `Any`), `backend/app/agents/orchestrator.py` (unskip RAG demo, `_seed_exists_for_phone`, helper estratti `_load_prior_facts` + `_format_briefing_chunk`, payload audit arricchito), `backend/app/main.py` (lifespan: refresh dates → preseed Vultr, catch separati).
- BE regenerate: nuovo `backend/app/agents/briefing_regenerator.py`, endpoint in `backend/app/api/calls.py`, `backend/app/schemas/calls.py` (`briefing` su `CallExtractedView`).
- BE audit: `backend/app/api/audit.py` + `backend/app/schemas/audit.py` (LEFT JOIN Customer, 3 campi optional).
- FE types + api: `app/lib/types.ts` (`briefing` su `CallExtractedView`, 3 campi su `AuditLogEntry`), `app/lib/api.ts` (`listAudit({limit})`, `regenerateSummary`), `app/lib/auditLabels.ts` (`briefing_regenerator → Briefing regenerator`).
- FE UI: `app/app/call/[id].tsx` (Surface briefing + IconButton refresh + Dialog + Snackbar), `app/app/(drawer)/audit.tsx` (rewrite ScrollView + Accordion).
- Docs: questo file, `CLAUDE.md`, `afterglow/README.md`, `afterglow/docs/ARCHITECTURE.md`, `afterglow/demo-site/src/App.tsx`, `.claude/memory/MEMORY.md`, due nuove memory `project_rag_demo_read_only.md` + `feedback_audit_collapse_pattern.md`.

### 1.sedici. Round 10 — Agentic post-call pipeline (2026-05-18, single multi-turn Gemini/ADK agent)

**Cosa cambia:** la pipeline post-call passa da tre stage indipendenti single-shot a **un unico Gemini/ADK agent multi-turn** che decide turno per turno quale tool invocare, osserva il risultato e si autocorregge. Concretamente:

- **`backend/app/agents/call_analyzer.py`** → alleggerito a soli `FieldExtraction` + `TokenUsage`. `analyze_call`, `_SYSTEM_INSTRUCTION`, `_user_prompt`, `CallAnalysisError`, `CallAnalysis`, `PlannedAction` rimossi.
- **`backend/app/agents/action_planner.py`** → **eliminato integralmente**. La logica `_make_tool` migrata in `backend/app/agents/tools/action_tool.py` con due differenze chiave: (a) il tool ora chiama `execute_single_action` *inline* invece di registrare nello state ADK; (b) ogni invocazione bumpa `tool_context.state["turn_counter"]` per correlation audit.
- **`backend/app/agents/call_agent.py`** (nuovo) — orchestra il loop ADK. Tool surface:
  - `lookup_customer_memory(query)` — RAG Vultr on-demand (NON più pre-fetch deterministico)
  - `search_transcript(keyword)` / `read_transcript_segment(start, end)` — re-read diarization-aware
  - `<action_key>(payload, ...)` — uno per ogni `template.action_types` con `execution_mode=auto`, esegue inline
  - `flag_for_review(reason, severity)` — setta `Call.review_flag`
  - `finalize_call(payload: FinalizeCallPayload)` — chiude il loop con payload `{fields, intent, sentiment, language, urgency, briefing}`
- **`backend/app/agents/tools/`** (nuova) — `memory_tool.py`, `transcript_tool.py`, `control_tool.py`, `action_tool.py`, `turn.py` (helper `bump_turn`).
- **`backend/app/executors/action_executor.py`** — estratto `execute_single_action(...)` da `execute_planned_actions`; il batch wrapper resta per backward compat dei test. Aggiunto un terzo livello di no-raise: anche le eccezioni dai handler `MOCK_REGISTRY` / `INTERNAL_HANDLERS` diventano `ExecutedAction.status="failed"` con `result.error`.
- **`backend/app/integrations/gemini_adk.py`** — nuovo `run_agent_loop(runner, prompt_text, max_iterations=12)` che traccia `turn_count`, `turn_trail`, `token_usage_total`, `final` state, `terminated_by`. Il vecchio `run_agent` resta come legacy helper.
- **`backend/app/agents/orchestrator.py`** — rimossi blocchi RAG pre-fetch + analyzer call + planner call + executor batch (~130 LOC). Sostituiti da un `audit_step("agent_loop_start")` + `run_call_agent(...)` + emissione di N `agent_turn` audit rows + `agent_loop_end`. Idempotency guard estesa con `"needs_review"` e `"failed"`. Status mapping:

  | `result.completion_reason` | `Call.status` | side effects |
  |---|---|---|
  | `"finalize"` | `"completed"` | persist `ExtractedFields`, push briefing su Vultr (prod only) |
  | `"max_turns"` | `"needs_review"` (NEW) | auto-fill `Call.review_flag` se l'agente non l'ha già settato |
  | `"error"` | `"failed"` | `Call.error = result.error` |

- **DB** — migration `0016_call_review_flag.py` aggiunge `Call.review_flag JSONB NULL`. Nessun CHECK constraint su `status` (`0001_init.py:90` lo definisce come `String(30)` libero, quindi `'needs_review'` è già accettato).
- **DTO** — `CallDetailView` + `CallListItem` portano `review_flag`. Nuovo schema `ReviewFlag` con campi `reason`/`severity`/`turn_count`/`flagged_by`. TS mirror in `app/lib/types.ts`.
- **API** — l'audit endpoint `/api/v1/audit?call_id=...&agent_name=...` accetta già `agent_name` da prima. Estesa solo la firma client `api.listAudit({call_id, agent_name, limit})`.
- **UI** — nuovo componente `app/components/AgentReasoningTrail.tsx`: timeline dei turni dell'agente (fetch dell'audit log filtrato `agent_name=call_agent` + `action_executor` per le sub-step, correlazione deterministica via `payload.agent_turn`). Banner giallo sulla call detail quando `review_flag != null`. Chip `Needs review` in `CallRow` quando `status==='needs_review' || review_flag`. Nuovo filtro `'review'` in Home. Customer detail rende `Review` invece della stringa raw.

**Audit trail per turn**:
- `agent_loop_start` (1×) — `payload.max_iterations`, `payload.available_tools`
- `agent_turn` (N×) — `payload.turn`, `payload.tool`, `payload.args_summary`, `payload.result_summary`, `input_tokens` + `output_tokens`
- `agent_loop_end` (1×) — `payload.turn_count`, `payload.completion_reason`, totale token
- `action_exec` (per ogni azione eseguita) — `payload.agent_turn` numerico, per join deterministico con il turno corrispondente

**No-raise contract (vincolante)** — vedi [[project-agentic-pipeline]]:
1. `execute_single_action` mai solleva (anche exception dai mock/internal handler diventano `status="failed"`).
2. `run_call_agent` mai solleva: cattura tutte le exception ADK/tool/model e ritorna `CallAgentResult(completion_reason="error", error=...)`.
3. `orchestrator.run_pipeline` NON re-solleva su error: setta `call.status="failed"` + `call.error`, commit, ritorna.
4. `_run_pipeline_isolated.except` (`api/calls.py:222`) rollback path resta come safety net SOLO per crash veramente uncaught (DB disconnect catastrofico).

Questo contratto è ciò che mantiene visibili gli `ExecutedAction` già flushed anche quando il loop max_turns o fallisce. La promessa "azioni restano visibili" non è una magia transazionale: è il commit dell'orchestrator che la garantisce.

**Test (`backend/tests/`)** — layout flat:
- `test_adk_smoke.py` (gate ADK 1.18 — async tools, state, function_call/response, usage_metadata)
- `test_execute_single_action.py` (6 test: no-raise su validation/evidence/handler exception/manual-only/mock/hallucinated)
- `test_action_tool_typed.py` (6 test: typed Pydantic annotation, fallback dict, attempt counter, refusal su double mutating success, turn counter monotonic)
- `test_call_agent_offline.py` (5 test: finalize, max_turns, missing API key, runner exception, schema sanity)
- `test_turn_counter_correlation.py` (3 test: bump_turn monotonic, agent_turn lands in action_exec audit payload)
- `test_call_review_flag.py` (5 test: round-trip schemas, _failure_kind non-trigger su needs_review)
- Test esistenti aggiornati: `test_action_planner_typed.py` eliminato (modulo rimosso), `test_pipeline_smoke.py` continua a passare, `test_action_executor_validation.py` invariato grazie al wrapper batch.
- Risultato: **113 backend test verdi** dopo il refactor.

**Hackathon alignment** (`hackathon-docs/07-judging-criteria.md`):
- **Application of Technology (25%)** — agentic architecture, multi-step reasoning, tool use, self-correction su `validation_failed`/`evidence_missing`, RAG come tool (Vultr) anziché prompt prefix. Bonus combo multi-tech: Gemini + Speechmatics + Vultr nello stesso audit trail.
- **Originality (25%)** — behaviour emergente: l'agente può cercare nel transcript ("search_transcript('Saturday')") o ri-interrogare la memoria con query specifiche, e si autocorregge su errori dell'executor. Visibile a colpo d'occhio nella "Agent reasoning" pane.
- **Business Value (25%)** — operatore vede ogni decisione + retry + perché l'azione è stata flaggata. Auditabile, undo-able.
- **Vultr "Web-Based Enterprise Agent" track** — multi-step agentic workflow su Vultr Inference + Vector Store, requisito letterale della track.

**File toccati nel round 10:**
- Backend pipeline: `backend/app/agents/{call_agent.py (NEW), call_analyzer.py (slim), orchestrator.py (rewritten), memory_retrieval.py (query param), briefing_regenerator.py (docstring), tools/__init__.py + tools/turn.py + tools/memory_tool.py + tools/transcript_tool.py + tools/control_tool.py + tools/action_tool.py (NEW)}`, `backend/app/agents/action_planner.py` (DELETED), `backend/app/executors/action_executor.py` (rewritten), `backend/app/integrations/gemini_adk.py` (extended).
- Backend schema/API: `backend/app/db/models.py` (Call.review_flag), `backend/app/schemas/calls.py` (ReviewFlag + DTO fields), `backend/app/schemas/__init__.py`, `backend/app/api/calls.py` (mapper updates), `backend/alembic/versions/0016_call_review_flag.py` (NEW).
- Backend cleanup: `backend/app/integrations/action_catalog.py` (commenti), `backend/app/api/templates.py` (commento), `backend/app/db/seed.py` (audit rows: `action_planner` → `call_agent` agent_loop_start/end).
- Backend tests: nuovi 6 file `test_*.py`, eliminato `test_action_planner_typed.py`.
- Frontend: `app/lib/types.ts` (ReviewFlag + DTO fields + status union), `app/lib/api.ts` (listAudit agent_name), `app/components/AgentReasoningTrail.tsx` (NEW), `app/components/CallRow.tsx` (chip + filter key), `app/app/call/[id].tsx` (banner + trail + placeholder Extracted), `app/app/(drawer)/(tabs)/index.tsx` (filter review), `app/app/customer/[id].tsx` (Review chip).
- Docs: questo file (1.ter SUPERSEDED + 1.sedici nuova), `CLAUDE.md` (hard constraint #2 riscritto), `.claude/memory/MEMORY.md` + nuovo `project_agentic_pipeline.md`, `afterglow/README.md`, `afterglow/docs/ARCHITECTURE.md`.

**Why:** entrare nei criteri agentic dell'hackathon non come etichetta ma come architettura. La pipeline pre-round-10 era "3 chiamate Gemini con tool calling spruzzato sopra" — descrivibile come agentic nel pitch ma non riconoscibile come tale nel codice o nell'audit. Ora ogni turno è una decisione del modello con feedback osservato; ogni azione fallita può essere corretta dal modello stesso; ogni look-up di memoria è scelto. La Trail UI lo rende leggibile in 5 secondi a un giudice.

**How to apply:** la pipeline è bloccata in questa forma fino alla submission. Modificare il prompt dell'agente o aggiungere tool è OK (passare per `app/agents/call_agent.py:_SYSTEM_INSTRUCTION` + nuove factory in `app/agents/tools/`). Cambiamenti sostanziali (es. aggiungere un secondo agente, re-introdurre un fallback) richiedono nuova memory file + audit del piano. Vedi [[project-agentic-pipeline]] per la spec completa di tool surface, status lifecycle e audit correlation.

### 1.diciassette. Round 10 polish — audit fixes + UX walkthrough README (2026-05-18 notte)

Cluster di fix post-audit pre-submission. Non tocca pipeline agentic (round-10 sub-decisione `1.sedici`) né demo-site; vive in `app/lib/` + `seed.py` + `README.md` + 1 docstring + memory.

**Cosa è cambiato:**

1. **`formatRelativeTime` → priorità calendar-day.** `app/lib/dateFormat.ts`: ridisegnata la logica. Se `diffDays(startOfDay(now) - startOfDay(d)) >= 1`, la description è `"ieri" / "X giorni fa" / "X settimane fa" / "X mesi fa" / "X anni fa"`, indipendentemente dalle ore di scostamento. Solo se `diffDays === 0` (stessa calendar day) la description resta ore-based (`"X min fa" / "X h fa" / "adesso"`). Razionale: la description deve mai contraddire il section header — un "9 h fa" sotto un header "Ieri" confondeva l'operatore.

2. **Dentist seed template rinominato `"Patient booking"`** (era `"Appointment intake"`) + label `booking_time` da `"Booking time (HH:MM)"` a `"Booking time"` su dentist + bodyshop. Format-hint `(HH:MM)` resta nel `description` del field, non nel label visibile. Allineamento al namespace `booking.*` unificato round 8.

3. **Helper idempotente `_ensure_seed_templates_fresh(session)`** in `seed.py`. Il `seed()` short-circuit (riga ~855) non re-applicava le costanti template al DB di prod (templates esistevano già dal round 8). Pattern uguale a `_ensure_seed_customers` round 9: select per `(is_seed=True, domain_hint=X)`, diff su campi mutabili (`name`, `description`, `fields_schema`, `action_types`, `prompt_hints`), UPDATE in-place solo se drift. Chiamato all'inizio di `_ensure_personal_calls` PRIMA di `_ensure_seed_customers` (chain template → customer → call mirroring le FK). Log greppabile: `[seed] refreshed seed template (domain=X, new_name=...)`. Edge case collisione `(name, version)`: fail-loud accettato (vedi `feedback_db_disposable`). Test idempotente in `test_seed_templates.py::test_ensure_seed_templates_fresh_idempotent` (3 scenari: drift / no-drift / missing).

4. **Wizard back action.** `app/app/templates/wizard.tsx`: `Stack.Screen.options.headerLeft = () => <Appbar.BackAction onPress={() => router.back()} />`. Le pagine registrate sotto un sub-stack (templates/_layout sotto (drawer)/_layout) NON ereditano il back default del root stack — vanno wirate esplicitamente.

5. **Avatar fallback per numeri unsaved → revert della decisione round 3 §R.** `app/lib/avatar.ts:initialsFromName(phone)` ora ritorna `"+"` se `trimmed.startsWith("+")`, `"#"` altrimenti — non più `""`. Il fallback `Avatar.Text` colorato hash-based mantiene la legenda avatar coerente con le row customer (la decisione precedente preferiva l'icon "person" generica, ma quella faceva sembrare la row un placeholder loading).

6. **`backend/app/api/admin.py` docstring stale aggiornata.** Diceva "Two endpoints" / "read-only" → ora corretta a "Three endpoints" (rag-stats + rag-probe + dry-run-pipeline) e nota che `dry-run-pipeline` scrive una `Call` e onora `X-Demo-Session`.

7. **README sub-section pitch-UX `## What to look at in the live demo`.** 7 bullet operativi che mappano URL → cosa il giudice nota — Audit accordion overview-first, AgentReasoningTrail in Call detail, Review filter, Regenerate summary, Next-call briefing in Customer detail, 3 admin curl-snippet, demo fresh date + 12 customer × 8 settimane. Non duplica le sub-section architetturali esistenti (Agentic architecture / Best use of Vultr / Best use of Gemini); è surface "open this URL, here's what proves it".

**File toccati:**
- FE: `app/lib/dateFormat.ts`, `app/lib/avatar.ts`, `app/app/templates/wizard.tsx`.
- BE: `backend/app/db/seed.py` (+ `backend/app/api/admin.py` docstring).
- Tests: `backend/tests/test_seed_templates.py` (+1 test).
- Docs: `afterglow/README.md` (sub-section), `afterglow/docs/ARCHITECTURE.md` (mezza-riga su `formatRelativeTime`), questo file (sub-decisione 1.diciassette + appendix round-10-polish a §R).

**Why:** chiudere i 4 finding visivi più visibili pre-submission e dare ai giudici una sub-section README "dove cliccare" che racconta il prodotto in 7 bullet senza dover dedurre architettura. Il refactor agentic single-loop (sub-decisione 1.sedici) c'era già; mancavano polish + pitch surface.

**How to apply:** quando aggiungi un nuovo seed template, ricordati che `_ensure_seed_templates_fresh` confronta `(name, description, fields_schema, action_types, prompt_hints)` — drift su uno di questi triggera UPDATE in-place. Per cambiare il nome di un seed template esistente, bumpare `version` non serve (l'helper UPDATE in-place); l'unica precauzione è la collisione con eventuali template user-built con stesso `(name, version)`. Quando aggiungi una pagina stack sotto un sub-stack, ricordati di wirarle `headerLeft: Appbar.BackAction`. `formatRelativeTime` deve restare calendar-day-first — riusa `startOfDay()` e calcola `diffDays` PRIMA del branching ore-based, non dopo.

### 9. Stato env in produzione (volatile, 2026-05-15)
Sezione "what's live right now" — da rileggere prima di pushare grossi cambi al backend.

- **`DEMO_MODE`**: ELIMINATA dal codice e dall'env (2026-05-15). I 6 MP3 demo reali (TTS Speechmatics, 3 domini × 2 caller mode) hanno sostituito i placeholder silenziosi, quindi non serve più il kill-switch. Quando deployi questa revisione: **rimuovere la variabile da Coolify** (Resource → Environment Variables) e fare redeploy del backend; lasciarla orfana è innocuo (Pydantic Settings ha `extra="ignore"`) ma sporca.
- **`GEMINI_DEFAULT_MODEL=gemini-3.1-flash-lite`** e **`GEMINI_TEMPLATE_BUILDER_MODEL=gemini-3.1-flash-lite`** sul backend (Coolify aggiornato 2026-05-16). Il codice ha lo stesso default in `backend/app/config.py`, quindi local dev e nuovi deploy non ricadono più su `gemini-2.5-flash`, `gemini-3-flash` o alias mobili.
- **`VULTR_VECTOR_DEFAULT_COLLECTION=afterglowbf073`** sul backend. Riusa la collection già provisionata (`afterglowbf073`); se viene svuotata, l'orchestrator degrada gracefully (skip RAG retrieval + skip write-back, briefing su Postgres comunque salvato).
- **`CORS_ORIGINS`** (CSV) sul backend: `https://app.95-179-245-107.sslip.io,https://demo.95-179-245-107.sslip.io,https://95-179-245-107.sslip.io`. Sostituisce `AFTERGLOW_CORS_EXTRA_ORIGINS` (eliminata).
- **`AFTERGLOW_DEFAULT_BUSINESS_ID`**: eliminata su Coolify e dal codice (single-tenant, niente più tabella `businesses`).

**Why:** queste env divergono da `.env.example` (che è la baseline locale). Senza questa sezione, un nuovo collaboratore che legge solo il file finisce per non capire perché in prod la pipeline si comporta diversamente.

**How to apply:** quando cambi env in Coolify ricordati di riportare qui le decisioni di stato (cosa è attivo, cosa è disattivato, da quando, perché).
