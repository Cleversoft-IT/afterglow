---
name: reference-devops-pipeline
description: DevOps pipeline locale → GitHub → autodeploy Coolify su VM Vultr. Coordinate non-segrete delle risorse (UUID, IP, hostname). Ogni credenziale vive in 1Password, NIENTE secret qui.
metadata:
  type: reference
---

## Flusso end-to-end

```
local dev (Fedora podman)  ──git push origin main──▶  github.com/Cleversoft-IT/hackaton-lablab
                                                              │
                                                  GitHub App webhook (afterglow-coolify)
                                                              ▼
                                              Coolify @ http://95.179.245.107:8000
                                                              │
                                              ┌───────────────┼───────────────┐
                                              ▼                               ▼
                                  afterglow-backend                afterglow-frontend
                                  Dockerfile build                 Dockerfile build (next standalone)
                                  /entrypoint.sh                   node server.js
                                  alembic upgrade + seed           
                                  + uvicorn :8000                  :3000
                                              │                               │
                                              └─────────  Traefik  ───────────┘
                                                              │
                                              Let's Encrypt cert auto
                                              ┌───────────────┼───────────────┐
                                              ▼                               ▼
                          https://api.95-179-245-107.sslip.io       https://95-179-245-107.sslip.io
                                              │
                                              ▼
                          Vultr Managed Postgres 16 (FRA, hobbyist 1GB)
                          trusted-ips: VM /32 + tuo IP dev /32
```

## Risorse Vultr (coordinate non-segrete)

| Risorsa | ID Vultr | Coordinate |
|---|---|---|
| Cloud Compute VM | `72347eb3-5ff1-434c-99ec-f29f0480a669` | label `afterglow-coolify` · plan `vhf-2c-4gb` · region `fra` · OS Ubuntu 22.04 (`1743`) |
| VM public IP | – | `95.179.245.107` |
| Managed Postgres | `221ca284-5b27-4bcb-9561-e75798d342ac` | label `afterglow-pg` · plan `vultr-dbaas-hobbyist-cc-1-25-1` · region `FRA` · engine pg 16.13 |
| Postgres host | – | `vultr-prod-221ca284-5b27-4bcb-9561-e75798d342ac-vultr-prod-05ed.vultrdb.com:16751` · db `defaultdb` · user `vultradmin` · `?ssl=require` |
| Vector Store collection (Trattoria) | `afterglowbf073` | popolata live durante i test del 15 maggio |
| SSH key | `e5b9390b-3afb-4675-b03c-2d18fcbeb1ed` | name `afterglow-coolify` · privata locale `~/.ssh/afterglow_vultr_ed25519` |
| IAM service user | `1d2b9f42-e713-4891-bc0b-0ddb4da4d4c3` | name `afterglow-service` · email `stefano+afterglow@cleversoft.it` · ACL `[subscriptions_view, subscriptions, provisioning, firewall]` |

Le risorse sono in regione FRA per latenza Milano. Free trial $250 (balance `-200.00` = `$200` disponibili) — stima spesa fino al 19 maggio ~$6.

## Coolify

- Dashboard admin: **http://95.179.245.107:8000** (HTTP plain, no TLS — proxy Traefik gestisce solo i deploy)
- Login: account Coolify creato durante setup (vedi 1Password)
- Project: `afterglow` (id `rze0mzy6iwv52upsejpsgiw5`)
- Environment: `production` (id `i9ic0h92aypqqxh8jroi9tw0`)
- Applications:
  - `afterglow-backend` (id `lo1010mbgr6s32ag7zy9cngi`) → `https://api.95-179-245-107.sslip.io`
  - `afterglow-frontend` (id `uggyvda4g4gnvzq49v8bksob`) → `https://95-179-245-107.sslip.io`
- Build pack: **Dockerfile** per entrambi
- Base Directory:
  - backend → `/afterglow/backend`
  - frontend → `/afterglow/frontend`
- Auto-deploy: webhook GitHub App alla push su `main` ricostruisce e rolling-update

### Operazioni Coolify comuni

- **Update env**: app → Environment Variables → click sulla riga → modifica value → Update → poi **Actions menu → Redeploy** (il button `Restart` NON ri-carica le env, fa solo restart container in-place; serve **wire:click="deploy"** ovvero "Redeploy")
- **Rebuild on demand**: top action bar → `Deploy` (o `Redeploy` se la risorsa è già Running)
- **Logs live**: tab Logs nel resource page

## GitHub

- Remote: `git@github.com:Cleversoft-IT/hackaton-lablab.git`
- Web: https://github.com/Cleversoft-IT/hackaton-lablab
- Branch protetto convenzione: `main` — ogni push triggera autodeploy. Lavorare su feature branch + PR è raccomandato ma non enforced.
- GitHub App `afterglow-coolify`: App ID `3724801`, Installation ID `132616803`, installata SOLO su `Cleversoft-IT/hackaton-lablab` (least privilege)
- Permessi: Read su Contents/Metadata/PRs, Read+Write su Deployments/Checks/Statuses

## Credenziali — dove NON cercarle

NIENTE credential in questa memoria, nel repo, o nel codice. Tutte vivono in **1Password** del team:

- `VULTR_INFERENCE_API_KEY` (Serverless Inference)
- `GOOGLE_API_KEY` (AI Studio)
- `SPEECHMATICS_API_KEY`
- Coolify admin login (email + password)
- Postgres Managed `vultradmin` password
- Personal `VULTR_API_KEY` (in `~/.vultr-cli.yaml` locale, **MAI** committarlo)
- Service user `afterglow-service` API key + password
- Coolify GitHub App: client_id / client_secret / webhook_secret / private key (autogenerati, conservati cripted in Coolify DB)

Le env reali del deploy sono **gestite da Coolify**, criptate at-rest. Per modificarle: vai sulla pagina della Resource → Environment Variables.

## Dev locale → produzione: la spiegazione corta

1. Edit codice in `afterglow/` (Python o Next.js).
2. Test locale via `podman run postgres` + `.venv/uvicorn` + `npm run dev`.
3. `git commit && git push origin main`.
4. Webhook GitHub colpisce Coolify entro pochi secondi. Coolify ricostruisce backend + frontend in parallelo (Docker image cache ridurre il tempo dopo la prima build).
5. Backend nuovo container scrive `alembic upgrade head` (no-op idempotente) e `python -m app.db.seed` (idempotente — short-circuita se 3 business già presenti). Poi sostituisce il vecchio container (rolling).
6. Frontend deploy uguale, con HMR Tailwind/Next già pre-built dall'immagine.
7. Verifica: `curl -sk https://api.95-179-245-107.sslip.io/health` → `{"status":"ok"}`.

Lo stato del DB Managed Vultr è **persistente** e indipendente dai redeploy. Il volume audio del backend per ora è dentro il container (non sopravvive ai redeploy; vedi roadmap per persistent volume).

## Roadmap residua

- [ ] Persistent volume per `/var/data/audio` (oggi il submit audio è ephemeral)
- [ ] `.github/workflows/ci.yml` con `npm run build` + `pytest` smoke
- [ ] Dominio custom + cert Let's Encrypt (oggi usiamo sslip.io free)
- [ ] Roll API key in 1Password dopo la demo
