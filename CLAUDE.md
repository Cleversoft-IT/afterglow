# Afterglow — Claude project context

Team-shared memory for Claude Code. Auto-loaded into every Claude Code session
that opens this repo. **Italian for the conversation; English for the code (see
[feedback_code_language.md](.claude/memory/feedback_code_language.md)).**

## Where to find what

- **`.claude/memory/`** — project memory, versioned & team-shared.
  - [`MEMORY.md`](.claude/memory/MEMORY.md) — index, one line per memory file.
  - [`project_afterglow_hackathon.md`](.claude/memory/project_afterglow_hackathon.md) — hackathon coordinates (deadline, partner targeting, tracks).
  - [`project_afterglow_decisions.md`](.claude/memory/project_afterglow_decisions.md) — locked product/architecture decisions. Read before changing the pipeline shape, the UI scope, or the tech stack.
  - [`reference_hackathon_docs.md`](.claude/memory/reference_hackathon_docs.md) — pointer table into `hackathon-docs/`.
  - [`feedback_code_language.md`](.claude/memory/feedback_code_language.md) — code goes in English, conversation in Italian.
- **`.claude/plans/procedi-col-planning-reactive-cocke.md`** — original implementation plan with a "Revision log" section at the top documenting day-1/2 decisions that diverge from the initial design.
- **`hackathon-docs/`** — full lablab knowledge base (5 files of judging criteria, partner deep-dives, submission rules).
- **`afterglow/`** — the actual product code. The README inside has up-to-date setup instructions for local dev.

## Hard constraints — do not change without re-discussion

1. **Single-tenant.** One installation = one customer. `Business` row pinned via `AFTERGLOW_DEFAULT_BUSINESS_ID`. Multi-tenant SaaS is not what the hackathon rewards.
2. **AI runs post-call, not during the call.** Operator UI reads `customer.memory_summary` from Postgres with zero latency. The single Gemini structured-output call in `backend/app/agents/call_analyzer.py` is where extraction, classification, action planning and the next-call briefing all happen at once.
3. **English code, Italian conversation.** Includes UI strings, comments, log messages. Seed/demo data simulating an Italian trattoria stays Italian (it is content, not code).
4. **MIT license** in repo from day one. No GPL/AGPL dependencies.
5. **Submission deadline:** 19 May 2026, 17:00 CEST.

## Conventions

- Container runtime: prefer `podman` (Fedora dev box). Compose file works with `podman-compose` if needed; for Postgres a single `podman run` is enough.
- Python 3.11 (not 3.12+) — pinned for `google-adk` / `asyncpg` wheel availability.
- Frontend env lives in `afterglow/frontend/.env.local` — Next.js does not read `afterglow/.env`.
