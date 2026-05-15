---
name: project-afterglow-decisions
description: Decisioni di prodotto/architettura di Afterglow. Pivot da non rinegoziare senza ridiscutere. Aggiornato 2026-05-15 dopo refactor combinato single-tenant + single Gemini orchestrator.
metadata:
  type: project
---

Decisioni iniziali del **2026-05-14** + revisione del **2026-05-15**. Ridiscutere solo con motivazione esplicita.

### 1. Autonomia agent — FULL
L'AI esegue **autonomamente** anche le azioni esterne (booking, WhatsApp, email, follow-up). Nel dialer le ex "pending actions" diventano **"executed actions con revert manuale"**. Eccezioni: nel backend l'utente può marcare alcune azioni specifiche come "manual-only" (no auto-execute).

**Why:** la sfida hackathon chiede esplicitamente *"autonomous decision-making systems, not copilots"*. Tenere human-in-the-loop su ogni azione classifica come copilot e perde punti su Originality + Application of Technology.

**How to apply:** UI dialer post-call mostra "executed / Revert" (non "Approve / Dismiss"). Backend ha `template.action_types[].execution_mode: auto | manual-only`. Default = auto. Tutto loggato in audit. Confidence/evidence visibili per giustificare l'esecuzione automatica.

### 1.bis. Single-tenant deployment (revisione 2026-05-15)
**1 installazione = 1 cliente.** I 3 business demo (ristorante/dentista/carrozziere) restano nel seed come *esempi di template verticali*, **non** come tenant attivi multi-SaaS.

`Business` resta come tabella nel DB (non valeva la pena toglierla), ma in UI è pinned via env `AFTERGLOW_DEFAULT_BUSINESS_ID` e l'endpoint `GET /api/v1/businesses/current`. Rimosse: pagina `/dashboard/business`, voce nav "Business", dropdown nel Template Wizard. Il dialer demo `/dialer/incoming/[callId]` continua a usare `listBusinesses()` perché è esattamente lo show "3 verticali su 3 URL" del pitch.

**Why:** l'hackathon premia *Enterprise Utility verticale + autonomia decisionale*, non SaaS multi-tenant (vedi `hackathon-docs/07-judging-criteria.md` e `02-challenge.md`).

**How to apply:** ogni UI nuova chiama `api.getCurrentBusiness()`. Niente selettori "business" per la dashboard. Le demo URL del dialer (`demo-restaurant-known`, `demo-dentist`, ecc.) restano multi-business.

### 1.ter. Pipeline post-call collassata in un solo Gemini call (revisione 2026-05-15)
**Architettura attuale:** zero AI durante la chiamata; tutta l'analisi gira **dopo** la fine call in un singolo Gemini structured-output call (`backend/app/agents/call_analyzer.py`). Lo schema Pydantic `CallAnalysis` produce in un colpo: fields/confidence/evidence, intent/sentiment/language/urgency, planned_actions e `next_call_briefing` (paragrafo in linguaggio naturale per l'operatore della prossima call).

La RAG di Vultr è **pre-fetch deterministico** prima dell'unico Gemini call (`memory_retrieval.retrieve_customer_context`) e fallisce gracefully a stringa vuota. Non è più un "agente".

Cancellati: `agents/extraction.py`, `agents/classification.py`, `agents/action_planner.py`, `agents/memory_updater.py`, l'intera cartella `app/tools/` e `app/pipeline/`.

**Why:** modello "AI a fine call" è quello giusto per *human-first AI dialer*. L'operatore vede il `customer.memory_summary` da Postgres istantaneamente; l'AI ha il transcript completo e tutta la memoria semantica disponibile a fine call. Architettura più semplice, pattern più aderente all'idea di Gemini structured output, costi più bassi (1 call invece di 4).

**How to apply:** `customer.memory_summary` è ora il "next-call briefing" Gemini-generated nella lingua detected. Etichetta UI in CallerMemoryCard: **"Next-call briefing"**. Quando si tocca la pipeline, modificare *solo* `call_analyzer.py` per scope/prompt e `orchestrator.py` per glue/persistence — niente nuovi sub-agent.

### 2. Speechmatics — solo voice-in
Non puntiamo al cash Award Speechmatics (sfida ridefinita kick-off = voice-in→reasoning→voice-out). Usiamo i $200 credit per: trascrizione, language detection, diarization, multilingual, custom dictionary. "Massive bonus love" dichiarati al kick-off → migliorano lo score Application of Technology su Vultr/Google Award.

**Why:** voice-out (TTS callback / Flow API) era scope-creep e snaturava il posizionamento human-first.

**How to apply:** integrare `speechmatics-batch` SDK con preset, diarization sempre attiva, custom dictionary per termini food/medico/automotive, supporto multilingua dimostrato in demo. *Stato attuale 2026-05-15: SDK wirato live (`AsyncClient.transcribe` con `diarization=speaker`, `language=auto`, `additional_vocab`). Una heuristic `audio_path.stat().st_size < 4096` fa fallback al transcript canned per il `silence.wav` della demo (44 byte), così non si paga per job vuoti. `DEMO_MODE=true` resta come hard kill-switch per registrare il video offline.*

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
- **Vultr Vector Store** per customer memory RAG ✅ (wirato, attende key Inference valida)
- **Vultr Serverless Inference (Kimi-K2)** per almeno un task agentico oltre Gemini ⚠️ — *revisione 2026-05-15:* la Classification è stata assorbita nel single Gemini call. Vultr Kimi-K2 resta esclusivamente nell'endpoint `/v1/chat/completions/RAG` per il memory retrieval pre-fetch. Se servisse un secondo uso di Kimi non-RAG per il pitch, riattivare un mini-agente.
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

- **`DEMO_MODE=true`** sul backend Coolify. Necessario finché gli MP3 demo sono placeholder silenziosi: Speechmatics SDK crasha con `KeyError: 'type'` su audio quasi-vuoti. Da invertire a `false` appena i 3 MP3 reali (`restaurant`, `dentist`, `bodyshop`) sono bundlati in `afterglow/app/assets/audio/`.
- **`VULTR_VECTOR_DEFAULT_COLLECTION=afterglowbf073`** sul backend. Riusa la collection già provisionata (`afterglowbf073`); se viene svuotata, l'orchestrator degrada gracefully (skip RAG retrieval + skip write-back, briefing su Postgres comunque salvato).
- **`CORS_ORIGINS`** (CSV) sul backend: `https://app.95-179-245-107.sslip.io,https://demo.95-179-245-107.sslip.io,https://95-179-245-107.sslip.io`. Sostituisce `AFTERGLOW_CORS_EXTRA_ORIGINS` (eliminata).
- **`AFTERGLOW_DEFAULT_BUSINESS_ID`**: eliminata su Coolify e dal codice (single-tenant, niente più tabella `businesses`).

**Why:** queste env divergono da `.env.example` (che è la baseline locale). Senza questa sezione, un nuovo collaboratore che legge solo il file finisce per non capire perché in prod la pipeline si comporta diversamente.

**How to apply:** quando cambi env in Coolify ricordati di riportare qui le decisioni di stato (cosa è attivo, cosa è disattivato, da quando, perché). Quando inverti `DEMO_MODE`, aggiorna questa sezione di conseguenza.
