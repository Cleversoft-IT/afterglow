# Afterglow — Revisione architetturale (single-tenant + app/sito demo separati)

## Contesto

Afterglow è nato come progetto multi-tenant con 3 "Business" demo (trattoria, dentista, carrozziere) ciascuno con un proprio template, due frontend in un unico Next.js, e il dialer che routava per `business.domain`. È un retaggio della fase iniziale: per l'hackathon (deadline 19 maggio 2026) vogliamo una storia diversa e più convincente.

**Obiettivi della revisione:**
1. L'app è **single tenant puro** — `Business` sparisce dal codice e dallo schema. Nessun `business_id`, nessun selettore, nessuna dashboard "Businesses".
2. **App e sito demo sono separati**:
   - `afterglow/app/` — l'app vera (Expo + react-native-web, base per un eventuale React Native nativo)
   - `afterglow/demo-site/` — landing che spiega Afterglow e incorpora l'app in un iframe
3. I 3 settori restano come **template preset selezionabili**, 1 attivo per volta. La dashboard espone "Active template" e permette di switchare.
4. La chiamata è simulata con **3 audio precostituiti** (`restaurant.mp3`, `dentist.mp3`, `bodyshop.mp3`): il "tasto blu" carica l'audio del template attivo e lo manda a `POST /api/v1/calls`. Il resto della pipeline post-call resta invariato (Speechmatics → Gemini single call → action executor → memory writeback).
5. Mantenere il deploy attuale (Coolify su Vultr, auto-deploy da `main`), aggiungendo una terza app per il sito demo.

---

## Decisioni bloccanti (prese prima di codice)

Risolvono le dipendenze nascoste su `Business` che oggi funzionano come configurazione runtime.

1. **Vultr collection ID** → **env obbligatoria** (`VULTR_VECTOR_DEFAULT_COLLECTION`). In produzione è già settata (`afterglowbf073`). In dev, se assente, l'orchestrator **degrada gracefully** (skip RAG retrieval, niente write-back vettoriale). Niente tabella singleton, niente persistenza ulteriore.
2. **`POST /calls` e `template_id`** → il backend **usa sempre il template attivo**, il client non manda più `template_id`. Form field rimosso, contratto semplificato. Nessun rischio di drift tra frontend e backend.
3. **Transcript demo** → mapping deterministico **da `template.domain_hint`** (template attivo al momento dell'upload), non da filename, non da form field. Backend in `DEMO_MODE` legge `domain_hint` e restituisce il transcript canned corrispondente.
4. **Expo API client** → **tutte le fetch assolute** via `EXPO_PUBLIC_API_BASE`. Niente path relativi, niente BFF/rewrites (assenti in static export). CORS reale va testato dal browser di un device esterno prima di chiudere la sezione B.
5. **Audio asset Expo** → **mappa statica** con `require()`, non dynamic require — Metro bundla solo i `require()` letterali:
   ```ts
   const audioByDomain = {
     restaurant: require('../assets/audio/restaurant.mp3'),
     dentist: require('../assets/audio/dentist.mp3'),
     bodyshop: require('../assets/audio/bodyshop.mp3'),
   };
   ```

---

## Sezione A — Backend (single-tenant)

### A1. Migration Alembic `0002_drop_business.py`
File nuovo: `afterglow/backend/alembic/versions/0002_drop_business.py`. Distruttiva (i dati attuali sono solo seed). Operazioni in ordine:
1. Drop indici `idx_templates_business`, `idx_customers_phone`, `idx_calls_business_status`.
2. Drop unique constraints `uq_template_name_version`, `uq_customer_phone`.
3. Drop foreign keys `business_id` su `templates`, `customers`, `calls` (e verificare/rimuovere riferimenti su `customer_memory_chunks`, `audit_log`).
4. **Drop esplicito delle colonne** `business_id` su `templates`, `customers`, `calls` (e altre tabelle se referenziano). Le colonne esistono in `0001_init.py:37,65,82` e vanno rimosse con `op.drop_column()` separato dal drop della FK.
5. Drop table `businesses`.
6. Aggiungere colonna `domain_hint VARCHAR(32) NOT NULL DEFAULT 'generic'` a `templates` (valori previsti: `restaurant`/`dentist`/`bodyshop`/`generic`).
7. Ricreare unique `uq_template_name_version` su `(name, version)` globale.
8. Ricreare `uq_customer_phone` come `UNIQUE (phone_e164)` globale.
9. Indice unico parziale `uq_template_active` `WHERE is_active IS TRUE` → impedisce 2+ attivi (lo "0 attivi" è gestito a livello applicativo, vedi A4).
10. Ricreare `idx_calls_status (status)`, `idx_customers_phone (phone_e164)`.

### A2. Modelli SQLAlchemy
`afterglow/backend/app/db/models.py`:
- Eliminare `class Business` e tutte le `relationship` puntate (Template, Customer, Call).
- Rimuovere `business_id` da `Template`, `Customer`, `Call`. Aggiornare `__table_args__` di ognuno.
- Aggiungere `domain_hint: Mapped[str]` a `Template`.
- `is_active` su Template c'è già (line 83): conservare; valorizzato dal seed.

### A3. Schemas Pydantic
Gli schemi sono in package `afterglow/backend/app/schemas/` (non in un singolo file). Tocca:
- `schemas/templates.py` — rimuovere `business_id` (linee `:29`, `:42`); eliminare eventuali `BusinessView` se presente in `schemas/__init__.py` o file dedicato.
- `schemas/calls.py` — rimuovere `business_id` (linea `:40`) da `CallListItem` / `CallDetailView`; togliere il form field `business_id` dalla request di upload.
- `schemas/customers.py` — rimuovere `business_id` da `CustomerCard` ovunque compaia.

### A4. Endpoint
`afterglow/backend/app/api/`:
- **Eliminare** `business.py` e la sua inclusione da `app/main.py` (router include).
- `calls.py`:
  - togliere il form field `business_id` da `POST /calls` (oggi obbligatorio, `calls.py:55`);
  - **togliere anche il form field `template_id`**: il backend lo risolve sempre dal template attivo (helper `_get_active_template(session)`). Niente parametro override → niente possibilità di drift fra UI e DB durante uno switch.
  - se non c'è un template attivo, rispondere `409 Conflict` con messaggio chiaro (`"no active template set"`).
  - togliere il query param `business_id` da `GET /calls`.
- `customers.py`: togliere `business_id` da `GET /customers/by-phone/{phone}`.
- `templates.py`: togliere filtro `business_id` da `GET /templates` e da `POST /templates/wizard`.
- Nuovo: `GET /api/v1/templates/active`:
  - se esiste una row con `is_active=True`, ritornarla;
  - se non esiste (stato "0 attivi"), `409 Conflict` con `{"detail": "no active template"}`.
- Nuovo: `PUT /api/v1/templates/active` body `{template_id}`:
  - prima validare che il template esista (`404` se no);
  - in una transazione atomica: `UPDATE templates SET is_active=false`; `UPDATE templates SET is_active=true WHERE id=:id`;
  - ritornare il template aggiornato.

### A5. Config
`afterglow/backend/app/config.py`:
- Rimuovere `default_business_id`.
- Mantenere `vultr_vector_default_collection` (ora unico).
- **Rinominare** `AFTERGLOW_CORS_EXTRA_ORIGINS` → `CORS_ORIGINS` (CSV), settings Pydantic. `app/main.py:51` oggi importa `os` e legge l'env direttamente: passare a `settings.cors_origins`, rimuovere l'import `os` locale, niente fallback al vecchio nome. Aggiornare `.env.example`, `docker-compose.yml`, Coolify.

### A6. Agenti — sostituire `business.domain` con `template.domain_hint`
`afterglow/backend/app/agents/orchestrator.py` (oggi legge/aggiorna `business.vultr_collection_id` a `:128` e `:293`):
- Rimuovere import `Business` e la `select(Business)`.
- Sostituire `business.vultr_collection_id` con `settings.vultr_vector_default_collection` (env obbligatoria in prod, vedi Decisione 1). Se vuota → log warning + skip RAG retrieval e skip write-back. Niente persistenza dell'ID lato app: è già su Coolify.
- Passare `domain_hint=template.domain_hint` al `call_analyzer` e al `memory_retrieval`.
- `_persist_memory` perde il parametro `business`.

`afterglow/backend/app/agents/call_analyzer.py` e `memory_retrieval.py`: rinominare param `business_domain` → `domain_hint`. In `memory_retrieval`, la collection può essere `None` (degrade in dev senza env): gestire l'early-return.

`afterglow/backend/app/agents/template_builder.py`: togliere `business_id` dall'input.

### A7. Seed
`afterglow/backend/app/db/seed.py`:
- Eliminare la creazione di 3 `Business`.
- Inserire 3 `Template` (i dict `RESTAURANT_TEMPLATE/DENTIST_TEMPLATE/BODYSHOP_TEMPLATE` già esistono): valorizzare `domain_hint`; `is_active=True` solo su Restaurant, gli altri `False`.
- Demo customers (Marco Rossi `+393331112233`, Giulia Bianchi `+393334445566`) diventano globali (no `business_id`).
- Short-circuit del seed deve basarsi su `Template` invece che `Business`.

### A8. Entrypoint
`afterglow/backend/entrypoint.sh` — nessun cambio di logica, ma il commento sul seed short-circuit menziona `businesses`: aggiornare per coerenza.

---

## Sezione B — App Expo (`afterglow/app/`)

### B1. Bootstrap
- `npx create-expo-app@latest afterglow/app --template default` con TypeScript.
- `npx expo install react-native-web@~0.19 react-dom @expo/metro-runtime expo-av expo-file-system expo-router`.
- **Styling: NativeWind v4** (compile-time → `StyleSheet`, zero runtime, DX Tailwind identica). Porting diretto dei token colore dal vecchio `frontend/tailwind.config.ts`.
- `app.json`: `web.bundler: "metro"`, `web.output: "static"`, `scheme: "afterglow"`.

### B2. Routing (expo-router file-based)
```
afterglow/app/app/
├── _layout.tsx              Stack root
├── (tabs)/
│   ├── _layout.tsx          Bottom tabs
│   ├── index.tsx            Lista chiamate (Calls)
│   ├── templates.tsx        3 preset + selettore Active
│   ├── audit.tsx            Audit log
│   └── settings.tsx         Diagnostica
├── call/[id].tsx            Dettaglio call: fields, actions (con Revert), transcript
└── simulator.tsx            "Tasto blu" (incoming call simulator)
```

**Customers tab — deferred (post-hackathon).** Il piano originale prevedeva `customers.tsx` ma la implementazione l'ha omessa di proposito: il backend espone solo `GET /customers/by-phone/{phone}` e `GET /customers/{id}` — manca un endpoint di lista, che sarebbe necessario per una screen utilizzabile. Costo non giustificato per la demo, dove l'unico flusso operativo è il "tasto blu" → call detail. Da riprendere se vorremo una vera dashboard cliente.

### B3. Componenti (RN primitives, niente HTML)
Sotto `afterglow/app/components/`: `Card`, `Badge`, `Button`, `ListRow`, `TranscriptBlock`, `FieldRow`, `ActionRow`, `BlueCallButton`. Basati su `View / Text / Pressable / ScrollView / FlatList / Modal`. Audio in `simulator.tsx` con `expo-av`.

### B4. Client API
`afterglow/app/lib/api.ts` — porting da `afterglow/frontend/src/lib/api.ts`. Attenzione: il client Next.js usa **path relativi** (`afterglow/frontend/src/lib/api.ts:1,41`) e si appoggia ai Next rewrites/BFF. In Expo statico non c'è BFF → **ogni fetch va prefissata con `EXPO_PUBLIC_API_BASE`**, incluso il multipart upload di `submitAudio`.
- Rimuovere `getCurrentBusiness()`, `listBusinesses()`, `getBusiness()`.
- Aggiungere `getActiveTemplate()`, `setActiveTemplate(id)`.
- `submitAudio(audio: Blob, phone: string)` — nessun `business_id`, nessun `template_id` (backend usa l'attivo).
- Base URL da `process.env.EXPO_PUBLIC_API_BASE` (fallback `http://localhost:8000` in dev).
- **Test CORS reale**: una volta deployato `afterglow-app`, aprirlo dal browser (non da localhost) e verificare che le richieste preflight passino verso `api.95-179-245-107.sslip.io`.

`afterglow/app/lib/types.ts` — porting da `frontend/src/lib/types.ts`: eliminare `Business`, rimuovere `business_id` da ogni interfaccia.

### B5. Asset audio
`afterglow/app/assets/audio/{restaurant.mp3,dentist.mp3,bodyshop.mp3}` — bundle con l'app Expo. ~1 MB ciascuno è ok. Vanno creati (utente ha detto: "che creeremo per le demo").

### B6. Build web
`npx expo export --platform web` → `dist/`. Servito da nginx in container Coolify.

---

## Sezione C — Sito demo (`afterglow/demo-site/`)

### C1. Stack: Vite + React + TypeScript
Motivazione: il sito demo è una landing statica con un iframe — Next.js è sovradimensionato. Vite dà bundle ~30 KB, una build veloce, un solo `vite.config.ts`. Zero chiamate API.

### C2. File
```
afterglow/demo-site/
├── index.html
├── src/main.tsx
├── src/App.tsx            Hero + How it works (3 step) + iframe in cornice "phone bezel"
├── src/styles.css
├── vite.config.ts
├── package.json
├── tsconfig.json
├── .env.production        VITE_APP_URL=https://app.95-179-245-107.sslip.io
└── Dockerfile             Multi-stage: node build, nginx serve dist/
```

L'iframe punta a `import.meta.env.VITE_APP_URL`.

---

## Sezione D — Audio demo & flusso "tasto blu"

### D1. Mapping
`template.domain_hint` (`restaurant`/`dentist`/`bodyshop`) determina sia l'asset audio sul frontend sia il transcript canned sul backend. Una singola sorgente di verità.

### D2. Asset audio Expo (mappa statica, no dynamic require)
In `afterglow/app/lib/audio.ts`:
```ts
export const audioByDomain = {
  restaurant: require('../assets/audio/restaurant.mp3'),
  dentist: require('../assets/audio/dentist.mp3'),
  bodyshop: require('../assets/audio/bodyshop.mp3'),
} as const;
```
Solo `require()` letterali — Metro non bundle dynamic require, e il bundle web fallirebbe in silenzio all'export.

### D3. Flusso `simulator.tsx`
1. `GET /api/v1/templates/active` → leggere `domain_hint`.
2. `audioByDomain[domain_hint]` → asset module; risolvere a Blob (web: `fetch(uri).then(r => r.blob())`; nativo: `expo-file-system`).
3. `FormData`: `audio`, `phone_e164` (default `+393331112233` per Trattoria; il backend è single-tenant, niente `business_id`, niente `template_id`).
4. `POST ${EXPO_PUBLIC_API_BASE}/api/v1/calls`.
5. Polling `GET /api/v1/calls/{id}` ogni 1.5s finché `status === "completed"`.
6. Navigare a `/call/[id]`.

### D4. Speechmatics in `DEMO_MODE` — mapping da `domain_hint`
`afterglow/backend/app/integrations/speechmatics.py` oggi ha un solo transcript canned restaurant (`:28`), scelto solo per file piccoli o assenza di API key (`:68`). Cambi:
- L'orchestrator passa `domain_hint` al transcriber.
- Il transcriber, in `DEMO_MODE=true` o senza API key, sceglie da un dict `_DEMO_TRANSCRIPTS = {"restaurant": "...", "dentist": "...", "bodyshop": "..."}`.
- Niente dipendenza dal filename originale (perso comunque per via dello storage UUID).

Copia degli audio anche in `afterglow/backend/sample_audio/` per smoke test backend isolati (es. `curl` da CLI).

---

## Sezione E — DevOps (Coolify su Vultr `95.179.245.107`)

| App Coolify | URL | Build | Env principali |
|---|---|---|---|
| `afterglow-backend` | `api.95-179-245-107.sslip.io` | `afterglow/backend/Dockerfile` (invariato) | `DATABASE_URL`, `GOOGLE_API_KEY`, `SPEECHMATICS_API_KEY`, `VULTR_VECTOR_DEFAULT_COLLECTION`, `DEMO_MODE`, `CORS_ORIGINS=https://app.95-179-245-107.sslip.io,https://demo.95-179-245-107.sslip.io` |
| `afterglow-app` | `app.95-179-245-107.sslip.io` | nuovo `afterglow/app/Dockerfile` (multistage: node `expo export -p web`, nginx serve `dist/`) | `EXPO_PUBLIC_API_BASE=https://api.95-179-245-107.sslip.io` |
| `afterglow-demo` | `demo.95-179-245-107.sslip.io` | `afterglow/demo-site/Dockerfile` (nginx) | `VITE_APP_URL=https://app.95-179-245-107.sslip.io` |

**Iframe headers**: nginx dell'app **non** deve impostare `X-Frame-Options: DENY`. In `afterglow/app/nginx.conf` emettere esplicitamente `Content-Security-Policy: frame-ancestors https://demo.95-179-245-107.sslip.io 'self'`.

**CORS**: `afterglow/backend/app/main.py` legge `settings.cors_origins` (Pydantic, da env `CORS_ORIGINS` CSV) invece dei valori hardcoded e dell'attuale `AFTERGLOW_CORS_EXTRA_ORIGINS` letto via `os.environ`. Migrazione completa, niente fallback al vecchio nome.

`afterglow/docker-compose.yml`: aggiungere servizi `app` (dev server `npx expo start --web`, porta 8081) e `demo-site` (dev server `vite`, porta 5173) per iterazione locale con HMR. La produzione gira solo su Coolify con container nginx statici — il compose locale non replica quei container per non aggiungere attrito allo sviluppo.

---

## Sezione F — Cleanup (ultimo step, commit unico)

Eliminare:
- Intera cartella `afterglow/frontend/` (vecchio Next.js).
- `afterglow/backend/app/api/business.py`.
- Tutti i riferimenti residui a `Business`, `business_id`, `business_domain` nel backend (sweep `grep -r`).
- Servizio `frontend` da `afterglow/docker-compose.yml`.
- Env vars in `.env.example` e su Coolify: `AFTERGLOW_DEFAULT_BUSINESS_ID`, `AFTERGLOW_CORS_EXTRA_ORIGINS` (sostituita da `CORS_ORIGINS`).

**Ordine sicuro**: prima fare landing di tutto il resto (A→E), verificare che `afterglow-app` parli col backend in produzione, **poi** cancellare `frontend/`. Così resta un fallback durante il debug Expo.

---

## Sezione G — Ordine di esecuzione

1. **Backend single-tenant** — sezione A: migration, modelli, schemas, config, endpoint, agenti, seed. Smoke locale: POST `/calls` con audio finto → polling → `GET /calls/{id}` completed.
2. **App Expo skeleton (read-only)** — B1, B2, B4 client API, B5 types: tab Calls, Templates con switch Active, Call detail, Settings. Deploy come `afterglow-app` su Coolify e verifica che parli con il backend in produzione.
3. **Tasto blu + azioni** — B3 componenti, `simulator.tsx`, sezione D (audio + mapping + demo transcripts), revert in `call/[id].tsx`, audit log screen.
4. **Sito demo** — sezione C: Vite landing + Dockerfile + Coolify app `afterglow-demo`. Sezione E: CORS, CSP, verifica iframe cross-origin.
5. **Cleanup** — sezione F: rimozione `frontend/`, prune compose, sweep dei riferimenti `business_*`.
6. **Demo content** — copy italiano, screenshot, video MP4 ≤5 min.

---

## File critici

- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/backend/alembic/versions/0002_drop_business.py` (nuovo)
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/backend/app/db/models.py`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/backend/app/db/seed.py`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/backend/app/api/templates.py`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/backend/app/api/calls.py`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/backend/app/agents/orchestrator.py`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/backend/app/config.py`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/backend/app/main.py`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/app/` (intera cartella nuova — Expo)
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/app/app/simulator.tsx`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/app/lib/api.ts`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/demo-site/` (intera cartella nuova)
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/docker-compose.yml`
- `/home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow/frontend/` (da eliminare a fine percorso)

---

## Verifica end-to-end

### Smoke test in locale (backend-only)
Richiede `DEMO_MODE=true` finché gli MP3 in `afterglow/backend/sample_audio/` sono i placeholder silenziosi (vedi sezione "Stato env in produzione" in [[project-afterglow-decisions]]).

```sh
cd /home/sepa/cleversoft/hackaton/hackaton-lablab/afterglow
docker compose up -d postgres backend
curl -s http://localhost:8000/api/v1/templates | jq '.[].name'

# Switch active template to restaurant
RESTO=$(curl -s http://localhost:8000/api/v1/templates \
  | jq -r '.[]|select(.domain_hint=="restaurant")|.id')
curl -s -X PUT -H 'content-type: application/json' \
  -d "{\"template_id\":\"$RESTO\"}" http://localhost:8000/api/v1/templates/active

# POST /calls only takes audio + phone_e164. The backend resolves template_id
# from the currently active template (returns 409 if none).
curl -s -F audio=@backend/sample_audio/restaurant.mp3 \
     -F phone_e164=+393331112233 \
     http://localhost:8000/api/v1/calls
# poll fino a "completed" → GET /api/v1/calls/{id} → verificare extracted_fields + executed_actions.
```

### Checklist manuale in produzione (Giorno 4)
1. Aprire `https://demo.95-179-245-107.sslip.io` → l'iframe carica l'app, nessuna violazione CSP in console.
2. Nell'iframe, switch Active Template su "Trattoria" → indicatore aggiornato.
3. Premere il tasto blu → toast "Call submitted" → dopo ~5s redirect su detail call con fields valorizzati e 2-3 azioni eseguite.
4. Revert di un'azione → status `reverted`, audit log mostra l'evento.
5. Switch a "Dentist" → tasto blu → audio diverso, fields/azioni diversi.
6. `https://api.95-179-245-107.sslip.io/api/v1/calls` lista entrambe le chiamate.
