---
name: project-afterglow-decisions
description: Decisioni di prodotto/architettura di Afterglow. Pivot da non rinegoziare senza ridiscutere. Aggiornato 2026-05-17 — frontend Material 3 rewrite (Drawer + 2-tab Pixel-inspired, react-native-paper, mock personal contacts, KeyPad UI-only, pitch riformulato "sostituto del dialer di sistema") + UI bug cluster post-rewrite (AppTheme + successContainer palette, drawer theme propagation manuale, Templates listener rimosso, hangup AbortError swallow). 2026-05-16 — feedback round 2 (no PII redaction, action catalog, dialer non bloccante, Undo/Redo flip-only, simulator 2-mode con MP3 distinti existing/new e 4 customer seedati).
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

**Vultr Vector Store skipato in demo mode** (sia RAG read sia chunk write): l'SDK Vultr (`vultr_inference.py`) non espone metadata filter né su `/vector_store/{id}/items` né su `/chat/completions/RAG`, una collection-per-sessione moltiplicherebbe risorse Vultr senza garanzia di cleanup, e il valore della RAG nella demo è marginale (giudice fa 1-2 call, niente "seconda chiamata stesso chiamante"). L'audit log scrive esplicitamente `status=skipped reason=demo_session` sui passi `memory_lookup` e `memory_updater` così la wiring resta visibile. Production single-tenant continua a usare Vultr Vector Store a piena banda — il pitch Vultr Award è coperto raccontandolo in landing/README/ARCHITECTURE.md (sezione "Demo isolation policy").

**Cleanup:** asyncio task in lifespan FastAPI sweep ogni 30 min sessioni con `last_seen_at < now-24h`, cascade delete di tutto il sub-tree.

**Reset on-demand (2026-05-16):** `POST /api/v1/demo/reset` (`app/api/demo.py`) chiama la stessa `purge_session_data` del cron sul `session_id` corrente con `drop_session_row=False`, poi azzera `active_template_id` e bumpa `last_seen_at`. La row `DemoSession` resta viva → il client mantiene la stessa uuid in `localStorage`, niente nuovo handshake. 403 in production. Pulsante "Reset demo" nella tab Settings dell'app (`app/(tabs)/settings.tsx`), visibile solo se `isDemoMode()`. Dopo il reset il client fa hard reload (web) / `router.replace('/')` (native); il gate `ActiveTemplateBootstrap` in `app/_layout.tsx` redirige a `/(drawer)/templates` se `getActiveTemplate()` ritorna 204. Il modal "soft warning" in `app/(drawer)/templates.tsx` intercetta `tabPress` sul parent navigator e avverte se l'utente lascia la pagina senza aver scelto un template. `GET /api/v1/templates/active` ritorna **204** per demo senza `active_template_id` (no fallback al seed `is_active=TRUE`, che resta solo per production).

**Why:** la decisione 1.bis (single-tenant in produzione) resta vincolata. La sandbox è layer opzionale che si attiva solo quando l'header è presente; production senza header = comportamento single-tenant immutato. Aderiscere al vincolo di prodotto + non bruciare Presentation per concorrenza demo.

**How to apply:** ogni nuovo endpoint deve aggiungere `ctx: SessionContext = Depends(get_session_context)` e usare `visibility_filter(Model.session_id, ctx)` per le letture, e impostare `session_id=ctx.session_id` sulle scritture. Ogni `audit_step(...)` deve ricevere `session_id=call.session_id` (o l'equivalente). Schema/migration: `0003_demo_sandbox_session.py`. Coordinate vive: `afterglow/backend/app/api/session_context.py`, `afterglow/backend/app/tasks/session_cleanup.py`.

### 1.ter. Pipeline post-call: Gemini analyzer + ADK action planner (revisione 2026-05-16)
**Architettura attuale:** zero AI durante la chiamata; tutta l'analisi gira **dopo** la fine call. La pipeline è in due stadi consecutivi, entrambi loggati nello stesso `audit_log`:

1. **`agents/call_analyzer.py`** — singolo Gemini structured-output call. Lo schema Pydantic `CallAnalysis` produce in un colpo: fields/confidence/evidence, intent/sentiment/language/urgency, `planned_actions[]` (con `payload: dict[str, Any]` tipato, niente più `payload_json: str`) e `next_call_briefing` (paragrafo in linguaggio naturale per l'operatore della prossima call). Il prompt cita le soglie di confidence per-`pii_class`, i `depends_on` per-field, e le `preconditions` / `confidence_threshold` / `mutates` / `evidence_required` per-action. Le `prompt_hints` (struttura `list[{when, then}]` dopo migration 0006) vengono valutate deterministicamente in Python contro `memory_retrieval.retrieve_structured_facts` PRIMA di costruire il prompt e prependute al system instruction quando matchano.
2. **`agents/pii_sanitizer.py`** — pure-Python, gira **subito** dopo il `call_analyzer` e prima di qualunque persist/audit. Redige `next_call_briefing` e le `evidence` dei `planned_actions[]` secondo la policy in `agents/pii_policy.py` (`contact=0.80, identity=0.85, financial=0.90, health=0.90`, strategie per-classe). I `fields[]` raw restano intatti perché servono al persist (UI review) e ai mock target (`booking.create` deve ricevere il nome reale). Audit step `pii_policy_applied` registra esattamente cosa è stato redatto, con quale soglia.
3. **`agents/action_planner.py`** — agentic loop via Google ADK (`integrations/gemini_adk.py`) che rilegge l'analisi SANITIZZATA del passo 1 e emette le tool call per le sole azioni `execution_mode=auto`. Ogni tool ha un parametro `payload` con annotation Pydantic dinamica costruita da `ActionDefinition.payload_schema` via `integrations/jsonschema_to_pydantic.py` (FunctionDeclaration tipizzata per Gemini). L'`executors/action_executor.py` ri-valida il payload con `jsonschema.validate` prima di MOCK_REGISTRY, rifiuta azioni con `evidence_required=True` ed evidence vuota, e propaga `mutates=True` nell'audit + `ExecutedAction.result`. `memory_summarizer_bilingual` è un piccolo Gemini call extra (~120 token) che genera l'EN summary del briefing quando la lingua detected non è EN (solo in prod), poi il chunk del Vector Store contiene native + EN.

**Fail-fast esplicito, niente fallback silenziosi (deciso 2026-05-16):** se manca `GOOGLE_API_KEY`, se Gemini fa raise/empty/JSON malformato, se l'ADK runner fallisce, la `Call` va in stato `failed` con `failure_reason` leggibile + audit row con `status="error"`. La UI mostra un banner rosso con la ragione. **Nessun stub deterministico, nessun "_fallback_planner".** Un demo che inventa "Marco in 4 alle 20:30" per ogni MP3 è una bugia che inquina la judging window; meglio mostrare l'errore vero e dimostrare che la pipeline è davvero AI-driven.

La RAG di Vultr è **pre-fetch deterministico** prima del Gemini call (`memory_retrieval.retrieve_customer_context`) e fallisce gracefully a stringa vuota — è degrado tollerabile perché "no prior facts" è uno stato semantico valido (cliente nuovo). Non confondere con un fallback AI.

**Storia del rientro di `action_planner.py`:** nella prima revisione del 2026-05-15 era stato cancellato per collassare tutto in una sola Gemini call. È stato re-introdotto con ADK il 2026-05-16 (commit `1c86292`) per allinearsi al criterio judging "Agentic Workflows / decision-making systems, not copilots". Resta **un solo** sub-agent post-`call_analyzer`, nessuno scaffolding ulteriore.

Cancellati (e tuttora assenti): `agents/extraction.py`, `agents/classification.py`, `agents/memory_updater.py`, l'intera cartella `app/tools/` e `app/pipeline/`. Cancellati il 2026-05-16: `_stub_analysis` in `call_analyzer.py` e `_fallback_planner` in `action_planner.py` (~115 LOC totali) — vedi sopra "Fail-fast esplicito".

**Token accounting (2026-05-16):** `audit_log.input_tokens` / `output_tokens` vengono popolate da `resp.usage_metadata` (Gemini) e dall'equivalente Vultr. Erano già a schema ma mai scritte; ora le scriviamo davvero per dare ai giudici la visibilità "trustworthy AI / cost-per-call audit".

**Why:** AI a fine call è il modello giusto per *human-first AI dialer*. L'operatore vede il `customer.memory_summary` da Postgres istantaneamente. Il double-step (analizzatore structured + planner agentico) tiene il pitch agentic; il fail-fast esplicito sostituisce la falsa robustezza del fallback con audit reale e UI onesta.

**How to apply:** `customer.memory_summary` è il "next-call briefing" Gemini-generated **sanitizzato** nella lingua detected. La tabella `extracted_fields.briefing_snapshot` (migration 0005) preserva la briefing storica per-call anche dopo overwrite di `memory_summary`. Quando si tocca la pipeline modifica `call_analyzer.py` per scope/prompt, `pii_sanitizer.py` per la policy PII, `action_planner.py` per il tool registry / loop ADK, `action_executor.py` per la validation deterministica, `orchestrator.py` per glue/persistence + error state — non aggiungere altri sub-agent (l'unica eccezione è il `template_validator.py` del wizard, che è scope wizard, NON pipeline post-call), non re-introdurre fallback "per sicurezza".

### 1.cinque. Templates v2 — schema strutturato + wizard 4-step (2026-05-16)
Estensione completa del `Template` landata con migration `0006_templates_v2.py`. Tutta v2 è additive a livello di codice ma cancella i dati esistenti (vedi [[feedback-db-disposable]]) per riallineare la shape.

**Schema esteso:**
- `FieldDefinition` ora include `pii_class` (`none|contact|health|financial|identity`), `confidence_threshold` opzionale per-field, `extractor_hint` (`regex|freeform|enum|llm_only`), `depends_on: list[str]`.
- `ActionDefinition` ora include `preconditions: list[str]`, `confidence_threshold: float`, `mutates: bool`, `evidence_required: bool`, `payload_schema: dict | None` (JSONSchema). Il payload_schema serve sia al planner (FunctionDeclaration tipizzata) sia all'executor (`jsonschema.validate`).
- `Template.prompt_hints` da `Text` a `JSONB` (`list[PromptHintRule]` con grammatica `always | field.<key> == '<value>' | field.<key> is [not] null`).
- Unique `(name, version)` espressa come **due partial unique index** (`session_id IS NULL` vs `IS NOT NULL`) per evitare la trappola Postgres "NULL distinct". POST `/templates` auto-bumpa la `version` per `(name, session_id)`.

**Wizard 4-step:** `Generate` (template_builder.py) → `Validate` (template_validator.py: hard deterministic + soft Gemini semantic, restituisce `ValidationReport`) → `Refine` (UI Expo `app/templates/wizard.tsx` + `[id].tsx`) → `Persist` (POST `/templates`, scrive con `session_id=ctx.session_id` in demo o `NULL` in prod, set_active opzionale nella stessa transazione).

**PII policy:** `agents/pii_policy.py` codifica soglie per-classe (`contact 0.80, identity 0.85, financial 0.90, health 0.90`) + strategie di redaction (`passthrough | [redacted: <class>] | hash | first2+***+last2`). `agents/pii_sanitizer.py` la applica **subito** dopo il `call_analyzer`, prima di ogni persist/audit (vedi 1.ter sopra).

**Bilingual briefing:** in prod, se `transcript.language != "en"`, `_summarize_to_english` produce un EN summary del briefing sanitizzato; il chunk del Vector Store contiene `native\n\n[EN] <en>` + metadata `language` + `briefing_en` + `pii_redactions_applied`. In demo è skipped.

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
4. Dashboard web: call log + action history (con revert) + customer profile + privacy settings ✅
5. Prompt-to-template wizard 4-step (Generate → Validate → Refine → Persist) ✅ — `template_builder` chiama `gemini-3.1-flash-lite` con structured output, `template_validator` runs deterministic + Gemini semantic, UI `app/templates/wizard.tsx` editora inline e POST `/templates` persiste con session_id corretto + version auto-bump. Vedi sub-decisione 1.cinque.
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

**A. PII redaction sul briefing → disabilitata.** `agents/pii_sanitizer.py` è ora **observe-only**: lascia briefing e evidence verbatim e registra solo `pii_classes_present` nell'audit log come `pii_policy_applied` con `mode="observe_only"`. Motivo: l'operatore deve sapere che il cliente è celiaco; `[redacted: health]` è inutile. La utility `redact_for_briefing` resta in `pii_policy.py` per usi futuri ma non viene chiamata dalla pipeline runtime. Test riscritti in `tests/test_pii_sanitizer.py`.

**B. Dialer fire-and-forget.** `app/app/incoming-call.tsx` non polla più la pipeline: dopo che l'audio finisce, submit + `router.replace('/(tabs)')` + toast pubblicato via `app/lib/pipelineToast.ts`. La tab Calls (`app/app/(tabs)/index.tsx`) ha un banner "Analysis in progress" e auto-refresh ogni 2s finché ci sono call non-terminali. NESSUN auto-redirect a Card Detail quando la call completa: l'utente può cliccare quando vuole. Sostituisce la vecchia logica `phase='analyzing'` con polling bloccante (rimossa).

**C. Simulator a due bottoni con MP3 distinti per modalità.** `app/app/simulator.tsx` espone "Call from existing customer" (phone seedato per il domain) e "Call from new customer" (phone random `+1 555 0XX XXXX` generato lato client). `incoming-call.tsx` legge `?caller=existing|new` e salta il customer lookup quando `new` per dimostrare la creazione del Customer durante la pipeline. **Dal 2026-05-16 ogni template ha DUE MP3** (`<domain>_existing.mp3` / `<domain>_new.mp3`): lo script "existing" presume il caller già noto dal numero ("Hi Sarah, it's Mark") e fa riferimento a interazioni passate; lo script "new" è un primo contatto ("Hi, I've never booked with you before. It's Hannah Clarke"). La shape `simulation_config` è cambiata: ora ha `scenarios.{existing,new}.{caller_name,caller_phone_e164,script_turns,audio_url,audio_status,audio_generated_at,audio_source}` — i template seed lo popolano via `_bundled_simulation_configs()` in `seed.py`; i template custom del wizard mantengono lo shape flat legacy e ne riusano l'unico MP3 in entrambi i modi (graceful fallback nell'endpoint `GET /templates/{id}/simulation/audio?mode=`). L'estensione del wizard a due script è tracciata come follow-up in `afterglow/docs/templates-roadmap.md`.

**D. Seed Call rows visibili.** `db/seed.py` ora inserisce ANCHE Call rows fittizie per i clienti seedati con transcript EN, ExtractedFields completi, briefing_snapshot, ExecutedAction e audit_log entries. Dal 2026-05-16 i customer seedati sono **quattro** (uno per ogni `existing` button così la card "Recent calls" non resta vuota su 2/3 template): Mark Ross +15551112233 (restaurant · 2 call: 20 Apr + 7 Mag), Julia White +15554445566 (restaurant · 1 call: 15 Apr), Laura Bennett +15559991122 (dentist · 1 call: 8 Apr, crown fitting on file), Andrew Green +15558883344 (bodyshop · 1 call: 3 Mag, returning Fiat Panda owner). Migration `0008_call_executedaction_is_seed.py` aggiunge il flag `is_seed` su `calls` e `executed_actions`. Le seed sono **visibili anche nella lista globale Calls** (no filter): l'utente ha esplicitamente chiesto di vederle al fresh install per dare contesto.

**E. Action catalog server-side (`integrations/action_catalog.py`).** Single source of truth per ogni action key Afterglow conosce: `integration_kind` (`mock_external` | `internal_real`), `mock_target` o `internal_handler`, `can_undo`, `compatible_domains`. L'`action_executor` consulta il catalog per scegliere il path (MOCK_REGISTRY vs `INTERNAL_HANDLERS`), e `CallActionView.is_simulated` / `can_undo` sono **server-computed dal catalog** (non più derivati da `result.mock` o da euristiche client). Il `template_validator` ora flagga template che citano action keys non nel catalog (sostituisce il vecchio import da `app.integrations.mocks.available_keys`).

**F. `customer.update_profile` è `internal_real`.** Nuovo modulo `integrations/internal/customer_profile.py`: muta davvero `customer.display_name` (solo se vuoto), `customer.tags` (deduped merge), `customer.profile_facts` (JSONB, migration `0009_customer_profile_facts.py`). Cattura `previous_state` nel `result` per abilitare l'undo che ripristina lo stato. Il `result.mock = False` significa "niente badge Simulated" nella UI: questa è un'azione interna REALE.

**G. Undo / Redo flip-only.** Endpoint `POST /actions/{id}/undo` (status `executed → undone`, replay del `previous_state` per internal_real) e `POST /actions/{id}/redo` (flip `undone → executed`, niente nuovo mock call — scelta esplicita). `POST /actions/{id}/revert` resta come alias retro-compat. La UI mostra il bottone Undo solo quando `action.can_undo === true` (sent messages → niente Undo). Niente bottone "Revert" dappertutto come prima.

**H. Endpoint nuovo `GET /api/v1/actions/catalog`.** Restituisce ogni entry per il wizard chat (Fase 8 in arrivo) e per il template editor (Fase 7). Sostituirà l'attuale `Template.action_types[].mock_target` come fonte di verità nel template builder.

**I. UI label.** "Memory summary" → "Next-call briefing" in customer profile + dialer caller card. "Re-validate" → "Check draft" nel wizard. Field UI in Call Detail mostra `FieldDefinition.label` come primario e `key` come stringa monospace piccola sotto (`CallExtractedView.field_definitions` espone label+pii_class server-side). Settings tab non mostra più l'API base.

**J. Prompt analyzer briefing style.** `agents/call_analyzer.py` ora chiede esplicitamente "1-2 short sentences, operator-actionable" invece di "1-3 sentences" generici. Esempio target: *"Mark prefers a quiet table and is gluten-intolerant. Last booked party of 4 on 9 May — confirm the same setup if he calls again."*

**Why:** il primo test reale ha mostrato che la pipeline e l'UI sono corrette ma vivono in mondi separati: l'operatore vedeva `[redacted: health]` e non sapeva cosa cucinare, vedeva il dialer bloccato in `preparing/processing` mentre la pipeline girava, vedeva action senza badge Simulated e senza poter undo, e si trovava in Card Detail teletrasportato senza averlo chiesto. Queste decisioni allineano l'UX al modello mentale dell'operatore.

**How to apply:**
- Quando aggiungi una nuova action key, **deve** apparire in `action_catalog.CATALOG` con `integration_kind` esplicito. Se è `internal_real`, registra anche un handler in `INTERNAL_HANDLERS` e (se è undoable) un reverter in `INTERNAL_REVERTERS`. Aggiorna `tests/test_action_catalog.py` se serve.
- NON ri-introdurre la redaction del briefing senza ridiscutere — i test in `test_pii_sanitizer.py` lockano la semantica observe-only.
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

### 9. Stato env in produzione (volatile, 2026-05-15)
Sezione "what's live right now" — da rileggere prima di pushare grossi cambi al backend.

- **`DEMO_MODE`**: ELIMINATA dal codice e dall'env (2026-05-15). I 6 MP3 demo reali (TTS Speechmatics, 3 domini × 2 caller mode) hanno sostituito i placeholder silenziosi, quindi non serve più il kill-switch. Quando deployi questa revisione: **rimuovere la variabile da Coolify** (Resource → Environment Variables) e fare redeploy del backend; lasciarla orfana è innocuo (Pydantic Settings ha `extra="ignore"`) ma sporca.
- **`GEMINI_DEFAULT_MODEL=gemini-3.1-flash-lite`** e **`GEMINI_TEMPLATE_BUILDER_MODEL=gemini-3.1-flash-lite`** sul backend (Coolify aggiornato 2026-05-16). Il codice ha lo stesso default in `backend/app/config.py`, quindi local dev e nuovi deploy non ricadono più su `gemini-2.5-flash`, `gemini-3-flash` o alias mobili.
- **`VULTR_VECTOR_DEFAULT_COLLECTION=afterglowbf073`** sul backend. Riusa la collection già provisionata (`afterglowbf073`); se viene svuotata, l'orchestrator degrada gracefully (skip RAG retrieval + skip write-back, briefing su Postgres comunque salvato).
- **`CORS_ORIGINS`** (CSV) sul backend: `https://app.95-179-245-107.sslip.io,https://demo.95-179-245-107.sslip.io,https://95-179-245-107.sslip.io`. Sostituisce `AFTERGLOW_CORS_EXTRA_ORIGINS` (eliminata).
- **`AFTERGLOW_DEFAULT_BUSINESS_ID`**: eliminata su Coolify e dal codice (single-tenant, niente più tabella `businesses`).

**Why:** queste env divergono da `.env.example` (che è la baseline locale). Senza questa sezione, un nuovo collaboratore che legge solo il file finisce per non capire perché in prod la pipeline si comporta diversamente.

**How to apply:** quando cambi env in Coolify ricordati di riportare qui le decisioni di stato (cosa è attivo, cosa è disattivato, da quando, perché).
