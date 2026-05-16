---
name: reference-coolify-api
description: Playbook operativo per interagire con la Coolify v4 API — abilitazione, endpoint che funzionano davvero, gotchas che mi sono costati tempo, comandi pronti per cura/feeding dello stack Afterglow.
metadata:
  type: reference
---

Tutto quello che mi sarei voluto trovare scritto la prima volta che ho dovuto creare app via API invece di click-click in UI. Per ID/UUID di progetto/server/applicazioni vedi [[reference-devops-pipeline]].

## Abilitare l'API

L'API Coolify è **disabled di default**. Senza questi due passi qualunque chiamata torna `401 Unauthenticated.`.

1. Login UI → *Settings → Advanced → API Settings*
2. Spunta **API Access**
3. **Scrivi esplicitamente** `0.0.0.0/0` nel campo "Allowed IPs for API Access". Il warning dice "vuoto = anywhere" ma in pratica il 401 persiste finché il campo resta vuoto. Salva.

Poi genera il token in *Keys & Tokens → API Tokens*:

- Description: qualcosa di memorabile (es. `claude-deploy`)
- Expires: default 30 giorni (rigenerabile facilmente)
- **Spunta `root`** se vuoi fare anche PATCH/POST/DELETE; il default è solo `read` e quasi tutti gli endpoint operativi tornano 401/403
- Click *Create* → il token completo è mostrato **una sola volta** sotto "Please copy this token now"

Token format: `<id>|<plaintext>` (es. `2|EaMTFi31...`). Quando lo copi da una UI assistita (Chrome screenshot, OCR, ecc.), **leggi il valore dal DOM testuale**, non dallo screenshot: caratteri come `l/1/I` o `O/0` si confondono e ti fanno spendere mezz'ora a debuggare un 401.

Test rapido che il token funzioni:

```bash
curl -s -H "Authorization: Bearer $COOLIFY_TOKEN" http://95.179.245.107:8000/api/v1/version
# → 4.0.0
```

## Token user-local

Convenzione: `~/.config/afterglow/coolify.env` con permessi `600`, formato KEY="VALUE". Esempio di contenuto:

```
COOLIFY_TOKEN="2|...redacted..."
COOLIFY_URL="http://95.179.245.107:8000"
PROJECT_UUID="rze0mzy6iwv52upsejpsgiw5"
ENV_UUID="i9ic0h92aypqqxh8jroi9tw0"
SERVER_UUID="p6gvrqfeuwgq5ncuhammk2tx"
GITHUB_APP_UUID="y10f2avbuly9kcoptintzmyz"
BACKEND_UUID="lo1010mbgr6s32ag7zy9cngi"
APP_UUID="liibgrkyxw4x1f4nrz8p91g7"
DEMO_UUID="yh9o1m3ro8dg96rahedk9haq"
```

Carica le var in shell: `set -a; source ~/.config/afterglow/coolify.env; set +a`. Non usare `export VAR=$(...)` con il token: il `|` rompe il parsing.

Se perdi il file, regenera il token via UI in ~1 minuto. Non vale il rischio di copiarlo in giro.

## Endpoint affidabili (verified hackathon-week)

```bash
# Sanity / health
GET  /api/health                              # public, no auth required
GET  /api/v1/version                          # auth required
GET  /api/v1/teams                            # ditto

# Applicazioni
GET    /api/v1/applications                   # lista tutte le app del team
GET    /api/v1/applications/{uuid}            # full payload (env esclusi)
PATCH  /api/v1/applications/{uuid}            # update generic fields
DELETE /api/v1/applications/{uuid}?delete_volumes=true&docker_cleanup=true&delete_configurations=true

# Env vars su un'applicazione
GET    /api/v1/applications/{uuid}/envs
POST   /api/v1/applications/{uuid}/envs       # { key, value } — NO is_build_time
PATCH  /api/v1/applications/{uuid}/envs       # update by key
DELETE /api/v1/applications/{uuid}/envs/{env-uuid}

# Deploy / status
GET /api/v1/deploy?uuid={app-uuid}&force=true   # trigger deploy ad hoc
GET /api/v1/deployments/applications/{uuid}     # storico deploy + logs (JSON in "logs" field)
```

## Creare app da repo privato — SOLO `private-github-app`

`POST /api/v1/applications/public` accetta il payload ma poi il git clone fallisce con `fatal: could not read Username for github.com` perché non ha credenziali. Per repo private (compreso il nostro Cleversoft-IT/hackaton-lablab) usa l'endpoint `private-github-app` passando l'UUID del GitHub App source (Coolify side, non App ID GitHub):

```bash
curl -X POST -H "Authorization: Bearer $COOLIFY_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "project_uuid": "'$PROJECT_UUID'",
    "environment_name": "production",
    "server_uuid": "'$SERVER_UUID'",
    "github_app_uuid": "'$GITHUB_APP_UUID'",
    "git_repository": "Cleversoft-IT/hackaton-lablab",
    "git_branch": "main",
    "build_pack": "dockerfile",
    "base_directory": "/path/inside/repo",
    "dockerfile_location": "/Dockerfile",
    "ports_exposes": "3000",
    "name": "nome-app",
    "domains": "https://<host>.sslip.io",
    "instant_deploy": false
  }' \
  $COOLIFY_URL/api/v1/applications/private-github-app
```

App create così hanno **Auto Deploy ON** by default — il webhook del GitHub App `afterglow-coolify` triggera redeploy a ogni push su `main`. Verificabile in *App → Advanced → Deployment → Auto Deploy*.

## Gotchas che mi sono costati tempo

1. **Validation `is_build_time` su POST envs**: il body non accetta quel campo (validation error). Sembra di doverlo settare per le var di build, ma Coolify lo decide in autonomia in base ad altri segnali (`is_runtime` di default).
2. **Token Sanctum format**: `<id>|<plaintext>`. Il `|` rompe `export VAR=...` non quotato. Usa sempre virgolette.
3. **`GET /api/v1/sources/github` non esiste**. L'UUID del GitHub App source si recupera solo dalla UI (`/sources` → click sull'app → URL contiene l'UUID).
4. **App nuove restano `exited:unhealthy` finché il primo deploy non è triggerato**. Il `POST /api/v1/applications/private-github-app` crea il record ma non costruisce; chiama `GET /api/v1/deploy?uuid=…` subito dopo.
5. **Let's Encrypt cert non immediato**. Dopo che l'app è `running`, può servire 1-3 minuti perché Traefik faccia ACME challenge. Nel mentre i client vedono `TRAEFIK DEFAULT CERT` (self-signed). Chrome MCP non sa accettare l'errore, devi aspettare.
6. **DELETE app non sempre immediata**. La risposta è "Application deletion request queued.", e il GET subito dopo torna ancora l'oggetto. Aspetta 5-10s e ricontrolla.
7. **Build time stimati su VM `vhf-2c-4gb`** (2 CPU, 4 GB RAM): backend Python ~3-4 min (pip install), app Expo ~5 min (npm ci + expo export), demo Vite ~1 min. Concurrent builds limit = 2 (settings server) — quindi una delle tre app sta sempre in coda fra le altre due.
8. **Env per static build (`EXPO_PUBLIC_*`, `VITE_*`)** sono **build args**, non runtime: il bundle JS contiene il valore *inlinato* al momento di `expo export` / `vite build`. Coolify crea le env con `is_buildtime=true is_runtime=true` di default, quindi le passa come `--build-arg` al `docker build` *e* le esporta nel container — il Dockerfile però deve dichiarare `ARG NAME` prima dell'`ENV NAME=${NAME}` perché il valore arrivi in build. Conseguenza: per cambiare un `EXPO_PUBLIC_API_BASE` non basta editare la env e fare *Restart*, serve **Redeploy** (rebuild) — il restart pesca il valore vecchio dal bundle.
9. **POST envs e duplicati**: chiamare `POST /api/v1/applications/{uuid}/envs` su un'app dove Coolify ha già creato la env automaticamente (perché vista come ARG nel Dockerfile durante un build precedente) crea un duplicato silenzioso con stesso key/value ma uuid diverso. Non rompe nulla, ma sporca la lista — dedupa col `DELETE /envs/{env-uuid}`.

## Snippet ricorrenti

```bash
# Carica env e tools shorthand
set -a; source ~/.config/afterglow/coolify.env; set +a
cf() { curl -s -H "Authorization: Bearer $COOLIFY_TOKEN" -H "Content-Type: application/json" "$@"; }

# Stato veloce delle 3 app
cf $COOLIFY_URL/api/v1/applications | jq -r '.[] | "\(.name)\t\(.uuid)\t\(.status)"'

# Tail dei log dell'ultimo deploy
cf $COOLIFY_URL/api/v1/deployments/applications/$APP_UUID \
  | jq -r '.deployments[0].logs' | jq -r '.[] | .output' | tail -30

# Redeploy on-demand
cf "$COOLIFY_URL/api/v1/deploy?uuid=$APP_UUID&force=true"

# Aggiorna una env var per key
# (esempio: la collection del Vultr Vector Store — env attualmente usata, vedi project-afterglow-decisions §9)
cf -X PATCH -d '{"key":"VULTR_VECTOR_DEFAULT_COLLECTION","value":"afterglowbf073"}' \
  $COOLIFY_URL/api/v1/applications/$BACKEND_UUID/envs
```

Nota: `DEMO_MODE` non esiste più (rimossa il 2026-05-15, commit `3a6f038`). Se la trovi orfana su un'app Coolify, eliminala con `DELETE /envs/{env-uuid}`.

## `watch_paths` — limitare il rebuild alla sotto-cartella giusta

Il campo `watch_paths` su un'applicazione è una stringa con righe newline-separated, pattern glob relativi alla root del repo. `null` = ogni push rebuilda (default storico Afterglow fino al 2026-05-16). Tre app distinte sullo stesso monorepo → senza `watch_paths` ogni push triggera tutte e tre, riempiendo la coda Coolify (concurrent builds = 2).

Setting via API (un solo `PATCH`, una sola riga di body — più righe si passano con `\n` letterale nel JSON):

```bash
set -a; source ~/.config/afterglow/coolify.env; set +a
patch_paths() {
  curl -s -X PATCH -H "Authorization: Bearer $COOLIFY_TOKEN" \
    -H "Content-Type: application/json" \
    "$COOLIFY_URL/api/v1/applications/$1" \
    -d "$(jq -n --arg p "$2" '{watch_paths:$p}')"
}
patch_paths $BACKEND_UUID 'afterglow/backend/**'
patch_paths $APP_UUID     'afterglow/app/**'
patch_paths $DEMO_UUID    'afterglow/demo-site/**'

# Verifica
for u in $BACKEND_UUID $APP_UUID $DEMO_UUID; do
  cf $COOLIFY_URL/api/v1/applications/$u | jq '{name, watch_paths}'
done
```

Contratto operativo: qualunque nuovo input di build esterno alla sotto-cartella (es. script root, futura `shared/`) **deve essere aggiunto a mano** ai `watch_paths` di ogni app che ne dipende, altrimenti i deploy non partono.

Linkato da [[reference-devops-pipeline]] per il dato infrastrutturale; questo file si concentra su come parlarci.
