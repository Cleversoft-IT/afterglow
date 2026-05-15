---
name: reference-devops-pipeline
description: DevOps pipeline locale → GitHub → autodeploy Coolify su VM Vultr. Coordinate non-segrete delle risorse (UUID, IP, hostname). I segreti vivono in `~/.config/afterglow/` (vedi sezione "Credenziali").
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
                          ┌───────────────────────────────────┼───────────────────────────────────┐
                          ▼                                   ▼                                   ▼
                  afterglow-backend                   afterglow-app                       afterglow-demo
                  Dockerfile build                    Dockerfile build                    Dockerfile build
                  /entrypoint.sh                      expo export -p web                  vite build
                  alembic + seed                      → nginx static :3000                → nginx static :3000
                  uvicorn :8000                       (Expo + react-native-web)           (Vite + React landing)
                          │                                   │                                   │
                          └─────────────────────────  Traefik + Let's Encrypt  ───────────────────┘
                          ▼                                   ▼                                   ▼
       https://api.95-179-245-107.sslip.io   https://app.95-179-245-107.sslip.io   https://demo.95-179-245-107.sslip.io
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
| Coolify server `localhost` | `p6gvrqfeuwgq5ncuhammk2tx` | "server" Coolify che punta alla VM stessa (è quella su cui Coolify gira) |
| Coolify GitHub App source | `y10f2avbuly9kcoptintzmyz` | source `afterglow-coolify` da usare nel payload `private-github-app` |

Le risorse sono in regione FRA per latenza Milano. Free trial $250 (balance `-200.00` = `$200` disponibili) — stima spesa fino al 19 maggio ~$6.

## Coolify

- Dashboard admin: **http://95.179.245.107:8000** (HTTP plain, no TLS — proxy Traefik gestisce solo i deploy)
- Login admin: credenziali user-locali (vedi sezione "Credenziali" più sotto)
- Project: `afterglow` (id `rze0mzy6iwv52upsejpsgiw5`)
- Environment: `production` (id `i9ic0h92aypqqxh8jroi9tw0`)
- Applications:
  - `afterglow-backend` (id `lo1010mbgr6s32ag7zy9cngi`) → `https://api.95-179-245-107.sslip.io` · base `/afterglow/backend`
  - `afterglow-app` (id `liibgrkyxw4x1f4nrz8p91g7`) → `https://app.95-179-245-107.sslip.io` · base `/afterglow/app` (Expo SDK 54 + react-native-web, nginx static)
  - `afterglow-demo` (id `yh9o1m3ro8dg96rahedk9haq`) → `https://demo.95-179-245-107.sslip.io` · base `/afterglow/demo-site` (Vite + React, nginx static, iframes the app)
- Build pack: **Dockerfile** per tutte e tre
- Source: GitHub App `afterglow-coolify` — UUID e server UUID nella tabella risorse sopra
- Auto-deploy: webhook GitHub App alla push su `main` ricostruisce tutte e tre le applicazioni in parallelo (Advanced → Deployment → "Auto Deploy" on per ognuna). Build concorrenti: 2 (limite server settings)

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

## Credenziali — dove vivono

Hackathon mode: niente vault esterno. **Niente segreti nel repo**, niente env files committati con valori reali. I segreti vivono **fuori dalla repo**, scelta libera dell'utente — tipicamente:

- **Coolify API token**: `~/.config/afterglow/coolify.env` (user-locale, permessi `600`). Rigenerabile in qualunque momento dalla UI Coolify → Keys & Tokens → API Tokens. Scade ogni 30 giorni se creato con default expiry.
- **Env di runtime** (Vultr Inference, Google AI Studio, Speechmatics, DB password, …): gestite **da Coolify** sulla resource, criptate at-rest. Per modificarle: pagina Resource → Environment Variables → Update + Redeploy.
- **Personal Vultr API key**: in `~/.vultr-cli.yaml`. Mai nel repo.
- **SSH key VM**: `~/.ssh/afterglow_vultr_ed25519`. Mai nel repo.

Note di sicurezza: il repo è MIT public — un push accidentale di credenziali significa rotazione immediata. Per scaricare/leggere credenziali Coolify in un altro device, ricreale via UI invece di copiarle in giro.

## Dev locale → produzione: la spiegazione corta

1. Edit codice in `afterglow/` (Python o Next.js).
2. Test locale via `podman run postgres` + `.venv/uvicorn` + `npm run dev`.
3. `git commit && git push origin main`.
4. Webhook GitHub colpisce Coolify entro pochi secondi. Coolify ricostruisce **tutte e tre le applicazioni** (backend + app + demo) in parallelo, con limite di build concorrenti = 2 (settings server). Docker image cache riduce il tempo dopo la prima build.
5. Backend nuovo container scrive `alembic upgrade head` (no-op idempotente) e `python -m app.db.seed` (idempotente — short-circuita se i template preset sono già presenti). Poi sostituisce il vecchio container (rolling).
6. App e demo: container nginx con bundle statici (Expo web export e Vite build); nessuna logica di runtime.
7. Verifica:
   - `curl -s https://api.95-179-245-107.sslip.io/health` → `{"status":"ok"}`
   - `curl -s https://app.95-179-245-107.sslip.io/` → HTML Expo web (200)
   - `curl -s https://demo.95-179-245-107.sslip.io/` → HTML Vite landing (200)

Lo stato del DB Managed Vultr è **persistente** e indipendente dai redeploy. Il volume audio del backend per ora è dentro il container (non sopravvive ai redeploy; vedi roadmap per persistent volume).

## Roadmap residua

- [ ] Persistent volume per `/var/data/audio` (oggi il submit audio è ephemeral)
- [ ] `.github/workflows/ci.yml` con `npm run build` + `pytest` smoke
- [ ] Dominio custom + cert Let's Encrypt (oggi usiamo sslip.io free)
- [ ] Roll API key dopo la demo (Vultr Inference, Google AI Studio, Speechmatics, Coolify token, Postgres `vultradmin`)
