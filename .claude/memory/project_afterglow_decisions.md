---
name: project-afterglow-decisions
description: Decisioni di prodotto/architettura di Afterglow. Pivot da non rinegoziare senza ridiscutere. Aggiornato 2026-05-16 dopo drop `businesses` (mig 0002) e rientro di action_planner agentic (ADK).
metadata:
  type: project
---

Decisioni iniziali del **2026-05-14** + revisioni del **2026-05-15** e **2026-05-16**. Ridiscutere solo con motivazione esplicita.

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

**Vultr Vector Store skipato in demo mode** (sia RAG read sia chunk write): l'SDK Vultr (`vultr_inference.py`) non espone metadata filter né su `/vector_store/{id}/items` né su `/chat/completions/RAG`, una collection-per-sessione moltiplicherebbe risorse Vultr senza garanzia di cleanup, e il valore della RAG nella demo è marginale (giudice fa 1-2 call, niente "seconda chiamata stesso chiamante"). L'audit log scrive esplicitamente `status=skipped reason=demo_session` sui passi `memory_lookup` e `memory_updater` così la wiring resta visibile. Production single-tenant continua a usare Vultr Vector Store a piena banda — il pitch Vultr Award è coperto raccontandolo in landing/README/ARCHITECTURE.md (sezione "Demo isolation policy").

**Cleanup:** asyncio task in lifespan FastAPI sweep ogni 30 min sessioni con `last_seen_at < now-24h`, cascade delete di tutto il sub-tree.

**Why:** la decisione 1.bis (single-tenant in produzione) resta vincolata. La sandbox è layer opzionale che si attiva solo quando l'header è presente; production senza header = comportamento single-tenant immutato. Aderiscere al vincolo di prodotto + non bruciare Presentation per concorrenza demo.

**How to apply:** ogni nuovo endpoint deve aggiungere `ctx: SessionContext = Depends(get_session_context)` e usare `visibility_filter(Model.session_id, ctx)` per le letture, e impostare `session_id=ctx.session_id` sulle scritture. Ogni `audit_step(...)` deve ricevere `session_id=call.session_id` (o l'equivalente). Schema/migration: `0003_demo_sandbox_session.py`. Coordinate vive: `afterglow/backend/app/api/session_context.py`, `afterglow/backend/app/tasks/session_cleanup.py`.

### 1.ter. Pipeline post-call: Gemini analyzer + ADK action planner (revisione 2026-05-16)
**Architettura attuale:** zero AI durante la chiamata; tutta l'analisi gira **dopo** la fine call. La pipeline è in due stadi consecutivi, entrambi loggati nello stesso `audit_log`:

1. **`agents/call_analyzer.py`** — singolo Gemini structured-output call. Lo schema Pydantic `CallAnalysis` produce in un colpo: fields/confidence/evidence, intent/sentiment/language/urgency, `planned_actions[]` e `next_call_briefing` (paragrafo in linguaggio naturale per l'operatore della prossima call).
2. **`agents/action_planner.py`** — agentic loop via Google ADK (`integrations/gemini_adk.py`) che rilegge l'analisi del passo 1 e emette le tool call per le sole azioni `execution_mode=auto`. Modalità `agentic` per default; in caso di errore (no key, rate limit, schema mismatch) fa fallback **deterministico** a `analysis.planned_actions[]`. L'orchestrator scrive `payload.mode = "agentic" | "fallback"` sull'audit row così la presenza/assenza del giro ADK è ispezionabile.

La RAG di Vultr è **pre-fetch deterministico** prima del Gemini call (`memory_retrieval.retrieve_customer_context`) e fallisce gracefully a stringa vuota. Non è un "agente".

**Storia del rientro di `action_planner.py`:** nella prima revisione del 2026-05-15 era stato cancellato per collassare tutto in una sola Gemini call. È stato re-introdotto con ADK il 2026-05-16 (commit `1c86292`) per allinearsi al criterio judging "Agentic Workflows / decision-making systems, not copilots": un puro response_schema, per quanto efficace, appariva troppo "completion-style" nel pitch. Resta **un solo** sub-agent post-`call_analyzer`, e ha sempre il fallback deterministico — nessuno scaffolding ulteriore.

Cancellati (e tuttora assenti): `agents/extraction.py`, `agents/classification.py`, `agents/memory_updater.py`, l'intera cartella `app/tools/` e `app/pipeline/`.

**Why:** AI a fine call è il modello giusto per *human-first AI dialer*. L'operatore vede il `customer.memory_summary` da Postgres istantaneamente. Il double-step (analizzatore deterministico + planner agentico con fallback) tiene il pitch agentic senza ipotecare l'affidabilità della demo.

**How to apply:** `customer.memory_summary` è il "next-call briefing" Gemini-generated nella lingua detected. La tabella `extracted_fields.briefing_snapshot` (migration 0005) preserva la briefing storica per-call anche dopo overwrite di `memory_summary`. Quando si tocca la pipeline modifica `call_analyzer.py` per scope/prompt, `action_planner.py` per il tool registry / loop ADK, `orchestrator.py` per glue/persistence — non aggiungere altri sub-agent.

### 2. Speechmatics — voice-in + TTS per gli MP3 demo
Non puntiamo al cash Award Speechmatics (sfida ridefinita kick-off = voice-in→reasoning→voice-out). Usiamo i $200 credit per: trascrizione, language detection, diarization, multilingual, custom dictionary, **e** generazione TTS dei 3 MP3 demo. "Massive bonus love" dichiarati al kick-off → migliorano lo score Application of Technology su Vultr/Google Award.

**Why:** voice-out come prodotto runtime sarebbe scope-creep, ma usare Speechmatics TTS *offline* per generare i 3 audio della demo costa zero in complessità e raddoppia visivamente la dipendenza dal partner nel pitch ("STT + TTS, entrambi Speechmatics").

**How to apply:**
- STT runtime: `speechmatics-batch` SDK wirato live (`AsyncClient.transcribe` con `diarization=speaker`, `language=auto`, `additional_vocab` dal `custom_dictionary` del template). **Nessun fallback offline**: missing key o audio illeggibile sollevano e fanno fallire la call (vedi `backend/app/integrations/speechmatics.py`). Niente più `_FAKE_TRANSCRIPTS`, niente più flag `DEMO_MODE` (rimosso il 2026-05-15).
- TTS offline: i 3 MP3 demo (`afterglow/app/assets/audio/{restaurant,dentist,bodyshop}.mp3`, mirror in `backend/sample_audio/`) sono generati da Speechmatics TTS preview (`https://preview.tts.speechmatics.com/generate/<voice>`) via `afterglow/scripts/generate_demo_audio.py`. Le voci preview supportano solo EN UK/US (`sarah`/`theo`/`megan`/`jack`), quindi i copioni demo sono **in inglese**: il resto del seed (nomi business, customer IT in +39) resta italiano. Per rigenerare gli audio: `python afterglow/scripts/generate_demo_audio.py`. Stessa cartella contiene anche `ringtone.mp3` (synth ITU-T 425Hz · 1 s on / 4 s off) usato dall'incoming-call screen — non parte della pipeline AI.

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
4. Dashboard web: call log + action history (con revert) + customer profile + privacy settings ✅
5. Prompt-to-template agent funzionante (demo wow live-genera template carrozziere) ✅ (template_builder chiama `gemini-3-flash-preview` con structured output; fallback chain robusto)
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

### 8.ter. Gemini default model — `gemini-flash-latest` (verificato 2026-05-15)
Tutti i modelli **Flash** sono utilizzabili gratis con la key Google AI Studio (Workspace account). I **Pro** rispondono 429 RESOURCE_EXHAUSTED sul free tier. `gemini-3-flash-preview` è gratuito sul free-tier (la voce contraria su molti blog è errata) e resta come `GEMINI_TEMPLATE_BUILDER_MODEL` per l'Originality bonus.

**How to apply:** se serve un modello reasoning Pro, sappi che il free-tier non lo serve. Per la demo restiamo su Flash, dove la qualità di estrazione è già più che sufficiente.

### 9. Stato env in produzione (volatile, 2026-05-15)
Sezione "what's live right now" — da rileggere prima di pushare grossi cambi al backend.

- **`DEMO_MODE`**: ELIMINATA dal codice e dall'env (2026-05-15). I 3 MP3 demo reali (TTS Speechmatics) hanno sostituito i placeholder silenziosi, quindi non serve più il kill-switch. Quando deployi questa revisione: **rimuovere la variabile da Coolify** (Resource → Environment Variables) e fare redeploy del backend; lasciarla orfana è innocuo (Pydantic Settings ha `extra="ignore"`) ma sporca.
- **`VULTR_VECTOR_DEFAULT_COLLECTION=afterglowbf073`** sul backend. Riusa la collection già provisionata (`afterglowbf073`); se viene svuotata, l'orchestrator degrada gracefully (skip RAG retrieval + skip write-back, briefing su Postgres comunque salvato).
- **`CORS_ORIGINS`** (CSV) sul backend: `https://app.95-179-245-107.sslip.io,https://demo.95-179-245-107.sslip.io,https://95-179-245-107.sslip.io`. Sostituisce `AFTERGLOW_CORS_EXTRA_ORIGINS` (eliminata).
- **`AFTERGLOW_DEFAULT_BUSINESS_ID`**: eliminata su Coolify e dal codice (single-tenant, niente più tabella `businesses`).

**Why:** queste env divergono da `.env.example` (che è la baseline locale). Senza questa sezione, un nuovo collaboratore che legge solo il file finisce per non capire perché in prod la pipeline si comporta diversamente.

**How to apply:** quando cambi env in Coolify ricordati di riportare qui le decisioni di stato (cosa è attivo, cosa è disattivato, da quando, perché).
