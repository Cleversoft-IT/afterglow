# Afterglow — Claude project context

Team-shared memory for Claude Code. Auto-loaded into every Claude Code session
that opens this repo. **Italian for the conversation; English for the code (see
[feedback_code_language.md](.claude/memory/feedback_code_language.md)).**

## Where to find what

- **`.claude/memory/`** — project memory, versioned & team-shared.
  - [`MEMORY.md`](.claude/memory/MEMORY.md) — index, one line per memory file.
  - [`project_afterglow_hackathon.md`](.claude/memory/project_afterglow_hackathon.md) — hackathon coordinates (deadline, partner targeting, tracks).
  - [`project_afterglow_decisions.md`](.claude/memory/project_afterglow_decisions.md) — locked product/architecture decisions. Read before changing the pipeline shape, the UI scope, or the tech stack.
  - [`project_agentic_pipeline.md`](.claude/memory/project_agentic_pipeline.md) — round-10 agentic pipeline: tool surface, turn budget, no-raise contract, `needs_review` status, audit correlation via `payload.agent_turn`. Read before touching `call_agent.py`, the tool modules, or the orchestrator status mapping.
  - [`reference_devops_pipeline.md`](.claude/memory/reference_devops_pipeline.md) — Vultr/Coolify/GitHub coordinates + auto-deploy flow. Read before touching deployment or infra.
  - [`reference_hackathon_docs.md`](.claude/memory/reference_hackathon_docs.md) — pointer table into `docs/hackathon-reference/`.
  - [`feedback_docs_freshness.md`](.claude/memory/feedback_docs_freshness.md) — docs + memory must be updated in the same commit as code changes (multi-person project, stale docs poison decisions).
  - [`feedback_code_language.md`](.claude/memory/feedback_code_language.md) — code + seed/demo data in English, conversation in Italian.
  - [`feedback_db_disposable.md`](.claude/memory/feedback_db_disposable.md) — DB records are disposable; no backward-compat for data shape; migrations may DELETE/TRUNCATE freely.
  - [`feedback_production_equals_hackathon.md`](.claude/memory/feedback_production_equals_hackathon.md) — "production" = the hackathon demo URL; post-hackathon work is out of scope (goes in [`docs/future-ideas.md`](docs/future-ideas.md) only).
  - [`feedback_drawer_window_confirm.md`](.claude/memory/feedback_drawer_window_confirm.md) — never `window.confirm` from a DrawerItem; use Paper `<Portal><Dialog>` to avoid the auto-close race that hangs the button.
  - [`feedback_locale_dates_only.md`](.claude/memory/feedback_locale_dates_only.md) — Settings → Format toggle is dates-only; route every date/time through `app/lib/dateFormat.ts` (`Intl.DateTimeFormat`-based), never `.toLocaleString()` raw.
  - [`feedback_real_on_device_whitelist.md`](.claude/memory/feedback_real_on_device_whitelist.md) — `REAL_ON_DEVICE` in `app/app/call/[id].tsx` is a UI-only badge filter; backend keeps `mock_external`.
  - [`feedback_mock_avatars_hardcoded.md`](.claude/memory/feedback_mock_avatars_hardcoded.md) — mock contact photos are hand-picked `randomuser.me` URLs; never delegate to seed-RNG generators.
  - [`feedback_web_first_paint.md`](.claude/memory/feedback_web_first_paint.md) — Afterglow's web build is SPA-shell (`app.json` `web.output: "single"`); do not flip back to `"static"` without an SSR-safety audit (theme/locale/insets all diverge and trip React error #418). The module-level theme sync in `_layout.tsx` minimizes the cold-load flash; the in-component `hydrated` guard stays as defensive scaffolding. Do not claim "pre-paint" without a custom Expo HTML template.
- **`.claude/plans/`** — implementation plans (the most recent one is the source of truth on the day-by-day roadmap).
- **`.claude/skills/`** — project-scoped Claude skills, auto-discovered by Claude Code sessions in this repo.
  - [`web-demo-gifs/SKILL.md`](.claude/skills/web-demo-gifs/SKILL.md) — recipes for product-demo GIFs (Playwright scripted recording, fake cursor + tap ripples, smooth scroll, variable per-frame delays, palette pipelines with ffmpeg/gifski/gifsicle, WebP/MP4 fallbacks). The reference implementation it points at is [`scripts/record-demo.cjs`](scripts/record-demo.cjs).
- **`docs/hackathon-reference/`** — full lablab knowledge base (judging criteria, partner deep-dives, submission rules).
- **`docs/future-ideas.md`** — post-hackathon roadmap (template lineage, status tri-state, wizard learning loop). Pitch-only material.
- **`submission/`** — built deliverables for the lablab form (PDF deck, PNG cover, Playwright build scripts).
- **`README.md`** at the repo root has up-to-date setup instructions for local dev *and* the production stack.

## How code reaches production

```
local edit  →  git push origin main  →  GitHub App webhook  →  Coolify on Vultr VM
                                                                ├─ afterglow-backend  →  https://api.afterglow.cleversoft.it
                                                                ├─ afterglow-app      →  https://app.afterglow.cleversoft.it   (Expo web)
                                                                └─ afterglow-demo     →  https://afterglow.cleversoft.it      (Vite, iframes the app)
                                                                       └─ Vultr Managed Postgres (DB)
```

- Coolify admin: http://95.179.245.107:8000 (HTTP plain for the dashboard; Traefik + Let's Encrypt for the apps)
- Auto-deploy fires within seconds of a push to `main`. There is **no manual deploy path** — no SSH into the VM for app changes, no `docker compose up` on the host.
- Coordinates, IDs, and operational notes: [`reference_devops_pipeline.md`](.claude/memory/reference_devops_pipeline.md). Secrets live outside the repo in user-local files (typically `~/.config/afterglow/`) and inside Coolify Environment Variables — never committed.

## Hard constraints — do not change without re-discussion

1. **Single-tenant.** One installation = one customer. The `Business` table has been dropped (migration `0002_drop_business.py`); single-tenant is enforced at schema level. The dashboard exposes one active `Template` at a time (restaurant / dentist / bodyshop preset). Multi-tenant SaaS is not what the hackathon rewards.
2. **AI runs post-call as a multi-turn agentic loop, not during the call.** Operator UI reads `customer.memory_summary` from Postgres with zero latency. The post-call pipeline is **one Gemini/ADK agent** (`backend/app/agents/call_agent.py`, round-10) that loops up to 12 turns over the diarized transcript, picking tools as needed:
   - `lookup_customer_memory(query)` — on-demand RAG against the Vultr Vector Store (no pre-fetch; the model decides when prior facts are useful and asks SPECIFIC questions);
   - `search_transcript(keyword)` + `read_transcript_segment(start, end)` — diarization-aware re-reads of the transcript;
   - one tool per `template.action_types[*]` (`backend/app/agents/tools/action_tool.py`), executed **inline** through `executors.action_executor.execute_single_action`: the result (`executed`/`validation_failed`/`evidence_missing`/`failed`/`refused`) flows back to the model, which can retry with a corrected payload (cap 2 attempts; mutating actions can't be replayed after success);
   - `flag_for_review(reason, severity)` — sets `Call.review_flag` so an operator inspects the call;
   - `finalize_call(payload: FinalizeCallPayload)` — emits the structured analysis (`fields`, intent, sentiment, language, urgency, briefing) and ends the loop.

   Outcome → `Call.status`:
   - `finalize` → `"completed"` + `ExtractedFields` persisted + briefing pushed to Vultr Vector Store (prod only).
   - `max_turns` → `"needs_review"` (new status, round-10) + `Call.review_flag = {reason: "agent_did_not_finalize", severity: "high", ...}`. ExecutedAction rows from the loop stay visible; no `ExtractedFields` persisted.
   - `error` (any ADK/tool/model failure caught by the no-raise contract) → `"failed"` + `Call.error`.

   **No-raise contract**: `run_call_agent` NEVER raises for normal ADK/tool/model errors — it returns `completion_reason="error"`. The orchestrator commits the final status and returns; `api/calls._run_pipeline_isolated.except` rollback is only for catastrophic uncaught exceptions. This is what keeps ExecutedAction rows visible even when the loop stalls. The legacy single-shot `call_analyzer.analyze_call` + `action_planner.plan_actions` + deterministic-batch `execute_planned_actions` have been DELETED; what remains in `call_analyzer.py` is only the shared `FieldExtraction` and `TokenUsage` schemas.

   **Session-lock invariant (round-11)**: `run_call_agent` requires a `session_lock: asyncio.Lock` created per-run by `orchestrator.run_pipeline`. The lock is wired into every action tool (`make_action_tool`) and `flag_for_review` (`make_flag_for_review`) so concurrent `session.flush()` calls from Gemini's parallel function calling are serialized. Without it, two tools racing on the shared `AsyncSession` raised `InvalidRequestError("Session is already flushing")` and surfaced as `Call.status="failed"` with `error="adk_runner [InvalidRequestError]: ..."`. See [`feedback_session_lock_concurrent_tools.md`](.claude/memory/feedback_session_lock_concurrent_tools.md).

   **Demo mode (round-9 → round-10)**: RAG READ is active on a pre-seeded collection. At backend boot, `backend/app/tasks/vector_preseed.py` populates the Vultr collection with one chunk per seed call (per-call idempotency via `chunk_metadata.preseed=true` + diff on `call_id`). Round-10 surface: the agent decides whether to invoke `lookup_customer_memory` (and with what specific question) instead of always burning tokens on a default catch-all query. Write-back still skipped in demo (`memory_updater status=skipped reason=demo_sandbox_vector_store_disabled`). See [`project_rag_demo_read_only.md`](.claude/memory/project_rag_demo_read_only.md) and [`project_agentic_pipeline.md`](.claude/memory/project_agentic_pipeline.md).

   **Audit & telemetry**: every turn emits one `agent_name="call_agent" step_type="agent_turn"` row; an enclosing `agent_loop_start` / `agent_loop_end` brackets the run. Token usage is aggregated in `agent_loop_end.input_tokens / output_tokens`. Every action execution emits `agent_name="action_executor" step_type="action_exec"` with `payload.agent_turn = <int>` so the UI's `<AgentReasoningTrail>` correlates action results to their source turn deterministically — never by timestamp join.

   **Fail-fast where it matters**: missing GOOGLE_API_KEY at boot, schema-broken `payload_schema` on a template, jsonschema validation refusals — surface visible status (`failed` / `validation_failed`) but the loop NEVER crashes the pipeline. PII/privacy classification is out of scope for the hackathon (`pii_sanitizer` was removed 2026-05-17).
3. **English code, English seed/demo data, Italian conversation.** Codice, UI strings, comments, log messages, **seed data** (`backend/app/db/seed.py`), demo customer profiles, demo transcripts — all in English. The bundled demo MP3s under `app/assets/audio/` are EN UK/US (Speechmatics TTS preview voices). Each of the three domain presets ships TWO MP3s — `<domain>_existing.mp3` (returning caller, references shared history) and `<domain>_new.mp3` (first-time caller, full self-introduction) — wired to the Simulator's "existing" / "new" buttons. Custom wizard-built templates STILL generate two MP3 files (`<template_id>_existing.mp3` + `<template_id>_new.mp3`, concat'd in PCM via Python's `wave` stdlib and transcoded to mono 48kbps MP3 via the `lame` CLI — picked over ffmpeg because ffmpeg's apt install OOM-kills the 4 GB Coolify build VM on cache miss, see `project_coolify_oom_silent_deploys.md` and `backend/app/integrations/speechmatics_tts.py`), BUT the Simulator only exposes the "new customer" button for non-seed templates: the existing-caller phone is fabricated and would never match a seeded Customer, so the incoming-call screen would mislabel the call anyway. See [`project_wizard_template_new_only.md`](.claude/memory/project_wizard_template_new_only.md). Quality bar for all demo scripts in [`feedback_demo_scripts_quality.md`](.claude/memory/feedback_demo_scripts_quality.md). The Italian-only surface is the user-Claude conversation. See [`feedback_code_language.md`](.claude/memory/feedback_code_language.md).
4. **MIT license** in repo from day one. No GPL/AGPL dependencies.
5. **Submission deadline:** 19 May 2026, 17:00 CEST.
6. **Production DB is Vultr Managed Postgres** — the `postgres` service in `docker-compose.yml` is a dev convenience only, never deployed in Coolify. Schema lives on the Managed instance, mirrored locally by `alembic upgrade head` in the backend `entrypoint.sh`.
7. **Seed dates are always fresh.** All hardcoded seed timestamps are materialized as `day_offset` relative to a `seed_anchor_date` row stored in the new `settings` table (migration `0015_settings_table.py`). At backend boot, `backend/app/tasks/seed_date_refresh.py` compares `today` against the anchor and, if it has drifted, BULK UPDATEs `Call` / `AuditLog` / `ExecutedAction` / `ExtractedFields.created_at` + `Customer.last_call_at` and `jsonb_set`s `booking_date` inside `ExecutedAction.payload` / `ExtractedFields.fields`. UUID5 keys are derived from `phone@day_{offset}@slot_{idx}` so the shift never touches PKs. Visitor clone-on-write rows (`session_id IS NOT NULL`) are not touched. **Round-11 update**: `_busy_week_specs` is allowed to emit anchor-day entries (`day_offset=0`) ONLY at hardcoded early-morning slots (07:00 + 08:30 UTC) so the demo shows live "today" activity without colliding with later same-day simulator calls. Migration `0017_reshape_busy_week.py` purges legacy seed `Call` rows once so the new shape (denser `day_offset=-1` + the `day_offset=0` slots) materializes on every deployed DB. **Round-12 update**: anchor-day slots are flagged `Call.is_anchor_day=True` (migration `0018_call_is_anchor_day.py`); `refresh_seed_dates_if_needed(session, today, now)` ALWAYS runs `_reposition_anchor_day_calls` (even when `delta_days == 0`) so those rows are slid to `[now-5h, now-2h]` on every boot — without this they materialize at 07:00/08:30 UTC and float in the future for any visitor opening the demo before mid-morning UTC, sorting above legitimate "just now" simulator calls.
8. **`ActionCatalogEntry.domain_payload_schemas`** is the per-domain override mechanism for action `payload_schema` (since 2026-05-19): the catalog's `default_payload_schema` is the fallback, and `domain_payload_schemas[domain_hint]` wins when the template's domain matches. Seed templates can still hand-write their own `action_types[*].payload_schema` and override both. Hotel `booking.create` keeps `booking_date` canonical (= check-in date) so the BookingBadge / Home `Bookings` tab keep working; `booking_time` stays optional (check-in times are institutional, the agent shouldn't have to invent one). The new field is NOT exposed in `entry.to_dict()` — the public `GET /api/v1/actions/catalog` keeps a single canonical schema per action.

## Keep docs & memory in sync — non-negotiable

This is a **multi-person project**. The files under `.claude/memory/`, the plan files under `.claude/plans/`, `README.md`, `docs/ARCHITECTURE.md`, `docs/future-ideas.md`, `docs/SUBMISSION.md` (the pitch bible used to produce the lablab submission artifacts), the inline system prompts in `backend/app/agents/*.py` (`call_agent.py`, `briefing_regenerator.py`, `wizard_chat.py`, `simulation_script.py`, `memory_retrieval.py`), and this `CLAUDE.md` are all **shared onboarding surface**: every teammate (human or future Claude session) reads them to understand the project state. Stale docs poison every downstream decision — a sub-agent that trusts an outdated memory file will propose code based on a world that no longer exists.

**Whenever a change in code, infra, or product decision lands, in the same commit/PR update the docs and memory that are affected.** Concretely:

- Changing an architecture decision (pipeline shape, schema, single-tenant invariant, etc.) → update `.claude/memory/project_afterglow_decisions.md` **before** merging.
- Changing infra / deploy / env vars → update `.claude/memory/reference_devops_pipeline.md` (+ `reference_coolify_api.md` if API surface) and the relevant section of `README.md`.
- Adding/removing/renaming a top-level file or directory referenced by docs → grep for it across MD files and fix the pointers.
- Removing an env var, endpoint, table, or flag → search every MD for the old name and either delete the reference or mark it explicitly as historical.
- Renaming the project, partners, deadline, license, or scope → `project_afterglow_hackathon.md` + `CLAUDE.md` constraints.
- Completing or abandoning a plan in `.claude/plans/` → add a `SUPERSEDED` / `COMPLETED` header at the top of the plan file with a one-paragraph delta vs reality, instead of leaving the old wording standing as a TODO.

Details on how to write a memory update and the categories of memory (project / feedback / reference / user) → [`feedback_docs_freshness.md`](.claude/memory/feedback_docs_freshness.md).

When you are unsure whether a doc is still accurate, **trust the code, not the memory**, and update the memory to match. Memory is a snapshot in time; the code is the live state.

## Conventions

- Container runtime locally: prefer `podman` (Fedora dev box). For Postgres a single `podman run` is enough; the compose file is rarely needed.
- Python 3.11 (not 3.12+) — pinned for `asyncpg`/lib wheel availability.
- The app (`app/`, Expo SDK 54 + react-native-web) and the demo site (`demo-site/`, Vite + React) are independent frontends. The two build-time env vars they consume — `EXPO_PUBLIC_API_BASE` for the app, `VITE_APP_URL` for the demo site — are documented in the single root `.env.example`; each frontend reads its own `.env.local` (per Expo / Vite conventions) when running locally. There is no Next.js, no BFF — every fetch goes absolute to the backend.
- Branch model: `main` is auto-deployed. Feature branches are fine but they don't deploy; merge to `main` to ship.
