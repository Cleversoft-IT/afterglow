# Afterglow — Claude project context

Team-shared memory for Claude Code. Auto-loaded into every Claude Code session
that opens this repo. **Italian for the conversation; English for the code (see
[feedback_code_language.md](.claude/memory/feedback_code_language.md)).**

## Where to find what

- **`.claude/memory/`** — project memory, versioned & team-shared.
  - [`MEMORY.md`](.claude/memory/MEMORY.md) — index, one line per memory file.
  - [`project_afterglow_hackathon.md`](.claude/memory/project_afterglow_hackathon.md) — hackathon coordinates (deadline, partner targeting, tracks).
  - [`project_afterglow_decisions.md`](.claude/memory/project_afterglow_decisions.md) — locked product/architecture decisions. Read before changing the pipeline shape, the UI scope, or the tech stack.
  - [`reference_devops_pipeline.md`](.claude/memory/reference_devops_pipeline.md) — Vultr/Coolify/GitHub coordinates + auto-deploy flow. Read before touching deployment or infra.
  - [`reference_hackathon_docs.md`](.claude/memory/reference_hackathon_docs.md) — pointer table into `hackathon-docs/`.
  - [`feedback_code_language.md`](.claude/memory/feedback_code_language.md) — code goes in English, conversation in Italian.
- **`.claude/plans/`** — implementation plans (the most recent one is the source of truth on the day-by-day roadmap).
- **`hackathon-docs/`** — full lablab knowledge base (judging criteria, partner deep-dives, submission rules).
- **`afterglow/`** — the actual product code. The README inside has up-to-date setup instructions for local dev *and* the production stack.

## How code reaches production

```
local edit  →  git push origin main  →  GitHub App webhook  →  Coolify on Vultr VM
                                                                ├─ afterglow-backend  →  https://api.95-179-245-107.sslip.io
                                                                ├─ afterglow-app      →  https://app.95-179-245-107.sslip.io   (Expo web)
                                                                └─ afterglow-demo     →  https://demo.95-179-245-107.sslip.io  (Vite, iframes the app)
                                                                       └─ Vultr Managed Postgres (DB)
```

- Coolify admin: http://95.179.245.107:8000 (HTTP plain for the dashboard; Traefik + Let's Encrypt for the apps)
- Auto-deploy fires within seconds of a push to `main`. There is **no manual deploy path** — no SSH into the VM for app changes, no `docker compose up` on the host.
- Coordinates, IDs, and operational notes: [`reference_devops_pipeline.md`](.claude/memory/reference_devops_pipeline.md). Secrets live outside the repo in user-local files (typically `~/.config/afterglow/`) and inside Coolify Environment Variables — never committed.

## Hard constraints — do not change without re-discussion

1. **Single-tenant.** One installation = one customer. No `Business` table, no `business_id` anywhere. The dashboard exposes one active `Template` at a time (restaurant / dentist / bodyshop preset). Multi-tenant SaaS is not what the hackathon rewards.
2. **AI runs post-call, not during the call.** Operator UI reads `customer.memory_summary` from Postgres with zero latency. The single Gemini structured-output call in `backend/app/agents/call_analyzer.py` is where extraction, classification, action planning and the next-call briefing all happen at once.
3. **English code, Italian conversation.** Includes UI strings, comments, log messages. Seed/demo data simulating an Italian trattoria stays Italian (it is content, not code).
4. **MIT license** in repo from day one. No GPL/AGPL dependencies.
5. **Submission deadline:** 19 May 2026, 17:00 CEST.
6. **Production DB is Vultr Managed Postgres** — the `postgres` service in `docker-compose.yml` is a dev convenience only, never deployed in Coolify. Schema lives on the Managed instance, mirrored locally by `alembic upgrade head` in the backend `entrypoint.sh`.

## Conventions

- Container runtime locally: prefer `podman` (Fedora dev box). For Postgres a single `podman run` is enough; the compose file is rarely needed.
- Python 3.11 (not 3.12+) — pinned for `asyncpg`/lib wheel availability.
- The app (`afterglow/app/`, Expo SDK 54 + react-native-web) and the demo site (`afterglow/demo-site/`, Vite + React) are independent frontends. Each has its own `.env.local`: `EXPO_PUBLIC_API_BASE` for the app, `VITE_APP_URL` for the demo site. There is no Next.js, no BFF — every fetch goes absolute to the backend.
- Branch model: `main` is auto-deployed. Feature branches are fine but they don't deploy; merge to `main` to ship.
