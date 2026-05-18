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
  - [`feedback_docs_freshness.md`](.claude/memory/feedback_docs_freshness.md) — docs + memory must be updated in the same commit as code changes (multi-person project, stale docs poison decisions).
  - [`feedback_code_language.md`](.claude/memory/feedback_code_language.md) — code + seed/demo data in English, conversation in Italian.
  - [`feedback_db_disposable.md`](.claude/memory/feedback_db_disposable.md) — DB records are disposable; no backward-compat for data shape; migrations may DELETE/TRUNCATE freely.
  - [`feedback_production_equals_hackathon.md`](.claude/memory/feedback_production_equals_hackathon.md) — "production" = the hackathon demo URL; post-hackathon work is out of scope (goes in [`afterglow/docs/future-ideas.md`](afterglow/docs/future-ideas.md) only).
  - [`feedback_drawer_window_confirm.md`](.claude/memory/feedback_drawer_window_confirm.md) — never `window.confirm` from a DrawerItem; use Paper `<Portal><Dialog>` to avoid the auto-close race that hangs the button.
  - [`feedback_locale_dates_only.md`](.claude/memory/feedback_locale_dates_only.md) — Settings → Format toggle is dates-only; route every date/time through `app/lib/dateFormat.ts` (`Intl.DateTimeFormat`-based), never `.toLocaleString()` raw.
  - [`feedback_real_on_device_whitelist.md`](.claude/memory/feedback_real_on_device_whitelist.md) — `REAL_ON_DEVICE` in `app/app/call/[id].tsx` is a UI-only badge filter; backend keeps `mock_external`.
  - [`feedback_mock_avatars_hardcoded.md`](.claude/memory/feedback_mock_avatars_hardcoded.md) — mock contact photos are hand-picked `randomuser.me` URLs; never delegate to seed-RNG generators.
  - [`feedback_web_first_paint.md`](.claude/memory/feedback_web_first_paint.md) — Afterglow's web build is SPA-shell (`app.json` `web.output: "single"`); do not flip back to `"static"` without an SSR-safety audit (theme/locale/insets all diverge and trip React error #418). The module-level theme sync in `_layout.tsx` minimizes the cold-load flash; the in-component `hydrated` guard stays as defensive scaffolding. Do not claim "pre-paint" without a custom Expo HTML template.
- **`.claude/plans/`** — implementation plans (the most recent one is the source of truth on the day-by-day roadmap).
- **`.claude/skills/`** — project-scoped Claude skills, auto-discovered by Claude Code sessions in this repo.
  - [`web-demo-gifs/SKILL.md`](.claude/skills/web-demo-gifs/SKILL.md) — recipes for product-demo GIFs (Playwright scripted recording, fake cursor + tap ripples, smooth scroll, variable per-frame delays, palette pipelines with ffmpeg/gifski/gifsicle, WebP/MP4 fallbacks). The reference implementation it points at is [`afterglow/scripts/record-demo.cjs`](afterglow/scripts/record-demo.cjs).
- **`hackathon-docs/`** — full lablab knowledge base (judging criteria, partner deep-dives, submission rules).
- **`afterglow/docs/future-ideas.md`** — post-hackathon roadmap (template lineage, status tri-state, wizard learning loop). Pitch-only material.
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

1. **Single-tenant.** One installation = one customer. The `Business` table has been dropped (migration `0002_drop_business.py`); single-tenant is enforced at schema level. The dashboard exposes one active `Template` at a time (restaurant / dentist / bodyshop preset). Multi-tenant SaaS is not what the hackathon rewards.
2. **AI runs post-call, not during the call.** Operator UI reads `customer.memory_summary` from Postgres with zero latency. The post-call pipeline is: (a) a single Gemini structured-output call in `backend/app/agents/call_analyzer.py` does extraction, classification, planned actions and the next-call briefing in one shot; (b) `backend/app/agents/action_planner.py` re-reads the analysis through Google ADK and emits typed tool calls (Pydantic models built dynamically from each action's `payload_schema`); (c) `backend/app/executors/action_executor.py` revalidates each payload with `jsonschema.validate`, refuses empty-evidence actions when `evidence_required=True`, reads `mutates` from `app/integrations/action_catalog.py` (single source of truth) and flags it in the audit + ExecutedAction.result, and stamps `mock: True` on the result of every action whose `integration_kind="mock_external"` so the UI renders a "Simulated" badge; (d) `_persist_memory` writes a bilingual chunk (native + EN summary) to the Vultr Vector Store in prod (skipped in demo). **Fail-fast everywhere**: missing key, Gemini error, ADK error, schema mismatch → `Call.status="failed"` + audit row with `status="error"`. No deterministic stub / fallback. PII/privacy classification is out of scope for the hackathon — `pii_sanitizer` was removed 2026-05-17. Every step is recorded in `audit_log`, with `input_tokens` / `output_tokens` populated from `usage_metadata` for Gemini calls and from the `usage` block for Vultr RAG.
3. **English code, English seed/demo data, Italian conversation.** Codice, UI strings, comments, log messages, **seed data** (`backend/app/db/seed.py`), demo customer profiles, demo transcripts — all in English. The bundled demo MP3s under `app/assets/audio/` are EN UK/US (Speechmatics TTS preview voices). Each of the three domain presets ships TWO MP3s — `<domain>_existing.mp3` (returning caller, references shared history) and `<domain>_new.mp3` (first-time caller, full self-introduction) — wired to the Simulator's "existing" / "new" buttons. Custom wizard-built templates follow the same two-scenarios shape since 2026-05-18 (two WAV files per template: `<template_id>_existing.wav` + `<template_id>_new.wav`). Quality bar for all demo scripts in [`feedback_demo_scripts_quality.md`](.claude/memory/feedback_demo_scripts_quality.md). The Italian-only surface is the user-Claude conversation. See [`feedback_code_language.md`](.claude/memory/feedback_code_language.md).
4. **MIT license** in repo from day one. No GPL/AGPL dependencies. (LICENSE file lives at `afterglow/LICENSE`, not the repo root.)
5. **Submission deadline:** 19 May 2026, 17:00 CEST.
6. **Production DB is Vultr Managed Postgres** — the `postgres` service in `docker-compose.yml` is a dev convenience only, never deployed in Coolify. Schema lives on the Managed instance, mirrored locally by `alembic upgrade head` in the backend `entrypoint.sh`.

## Keep docs & memory in sync — non-negotiable

This is a **multi-person project**. The files under `.claude/memory/`, the plan files under `.claude/plans/`, `afterglow/README.md`, `afterglow/docs/ARCHITECTURE.md`, `afterglow/docs/templates-roadmap.md`, the agent prompts in `afterglow/backend/app/agents/prompts/`, and this `CLAUDE.md` are all **shared onboarding surface**: every teammate (human or future Claude session) reads them to understand the project state. Stale docs poison every downstream decision — a sub-agent that trusts an outdated memory file will propose code based on a world that no longer exists.

**Whenever a change in code, infra, or product decision lands, in the same commit/PR update the docs and memory that are affected.** Concretely:

- Changing an architecture decision (pipeline shape, schema, single-tenant invariant, etc.) → update `.claude/memory/project_afterglow_decisions.md` **before** merging.
- Changing infra / deploy / env vars → update `.claude/memory/reference_devops_pipeline.md` (+ `reference_coolify_api.md` if API surface) and the relevant section of `afterglow/README.md`.
- Adding/removing/renaming a top-level file or directory referenced by docs → grep for it across MD files and fix the pointers.
- Removing an env var, endpoint, table, or flag → search every MD for the old name and either delete the reference or mark it explicitly as historical.
- Renaming the project, partners, deadline, license, or scope → `project_afterglow_hackathon.md` + `CLAUDE.md` constraints.
- Completing or abandoning a plan in `.claude/plans/` → add a `SUPERSEDED` / `COMPLETED` header at the top of the plan file with a one-paragraph delta vs reality, instead of leaving the old wording standing as a TODO.

Details on how to write a memory update and the categories of memory (project / feedback / reference / user) → [`feedback_docs_freshness.md`](.claude/memory/feedback_docs_freshness.md).

When you are unsure whether a doc is still accurate, **trust the code, not the memory**, and update the memory to match. Memory is a snapshot in time; the code is the live state.

## Conventions

- Container runtime locally: prefer `podman` (Fedora dev box). For Postgres a single `podman run` is enough; the compose file is rarely needed.
- Python 3.11 (not 3.12+) — pinned for `asyncpg`/lib wheel availability.
- The app (`afterglow/app/`, Expo SDK 54 + react-native-web) and the demo site (`afterglow/demo-site/`, Vite + React) are independent frontends. The two build-time env vars they consume — `EXPO_PUBLIC_API_BASE` for the app, `VITE_APP_URL` for the demo site — are documented in the single `afterglow/.env.example`; each frontend reads its own `.env.local` (per Expo / Vite conventions) when running locally. There is no Next.js, no BFF — every fetch goes absolute to the backend.
- Branch model: `main` is auto-deployed. Feature branches are fine but they don't deploy; merge to `main` to ship.
