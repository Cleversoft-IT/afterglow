# Afterglow architecture

> What remains after the call.
> Human-first AI dialer that turns booking phone calls into structured data,
> customer memory, and autonomously executed actions.

## End-to-end shape

```
App (Expo + react-native-web)         ◄── embedded by ── Demo site (Vite)
       │ POST /api/v1/calls (audio + phone, X-Demo-Session header)
       ▼
FastAPI background task ─► Speechmatics batch (diarization + lang detect + custom dict)
       │                   (skipped in DEMO_MODE, falls back to a canned transcript)
       │
       ├─► Vultr Vector Store /v1/chat/completions/RAG  (pre-fetch: prior_facts)
       │   └─► single collection, configured via VULTR_VECTOR_DEFAULT_COLLECTION
       │       (skipped when the call carries a demo session_id — see below)
       │
       ├─► Gemini structured-output call  (single Gemini pass)
       │       prompt: transcript + template fields_schema + action_types + prompt_hints + prior_facts
       │       response_schema = CallAnalysis (Pydantic):
       │         - fields[]  (key, value, confidence, evidence)
       │         - intent, sentiment, language, urgency
       │         - planned_actions[]  (subset of template auto-actions)
       │         - next_call_briefing  (NL paragraph, detected language)
       │
       ├─► Action Executor (deterministic Python) ─► mock registry + Postgres + audit_log
       │
       └─► Memory write-back ─► customer.memory_summary (Postgres, operator-visible)
                                + new chunk pushed to Vultr Vector Store
                                  (skipped when the call carries a demo session_id)
```

The pipeline runs **entirely after the call ends**. The human-facing latency
is whatever Postgres takes to return `customer.memory_summary`. No AI in the
live-call hot path.

System of record: **Vultr Managed Postgres**. Deploy: **Vultr Cloud Compute +
Coolify**. IAM: Service User minimal-privilege + OIDC GitHub Actions.

## Multi-visitor demo isolation

The public iframe at `demo.95-179-245-107.sslip.io` is reachable concurrently
by judges, hackathon attendees and crawlers. The product itself is
single-tenant (one installation = one customer); the demo is a sandbox bolted
on top of the same backend so visitors do not stomp on each other.

```
demo.95...                 app.95...                   api.95...
 (iframe)        ──────►   (Expo web)        ──────►   FastAPI
                            localStorage:                middleware:
                            demo_session_id              SessionContext(session_id | None)
                                  │
                                  ▼
                            X-Demo-Session: <uuid>       Postgres
                                                          calls.session_id
                                                          audit_log.session_id
                                                          executed_actions.session_id
                                                          customer_memory_chunks.session_id
                                                          templates.session_id   (wizard outputs)
                                                          customers.session_id   (clone-on-write)
                                                          demo_sessions(id, last_seen_at,
                                                                        active_template_id)
                                                          Vultr Vector Store
                                                          └─ skipped when session_id is not None
```

**Identity.** The first request from a new browser carries
`X-Demo-Session: new`. The backend mints a fresh `DemoSession` row and echoes
the freshly-generated uuid back on the response. The frontend persists it to
`localStorage` and stamps every subsequent request with it. No cookies, so
SameSite/Partitioned cookie behaviour inside an iframe is irrelevant.

**Visibility rule.** Every read filters
`WHERE session_id = me OR session_id IS NULL`. Seed rows (the three template
presets, the two known customers) live with `session_id IS NULL` and stay
shared and read-only.

**Clone-on-write customer.** When a call lands on a phone number that matches
a seed customer, the orchestrator clones the seed (`memory_summary`, `tags`,
`total_calls`, etc.) into a row stamped with the visitor's `session_id` and
writes back to the clone. Two judges who call Marco Rossi (`+393331112233`)
each get their own divergent timeline.

**Active template.** In demo mode the "currently active template" lives in
`demo_sessions.active_template_id`, not in `Template.is_active`. Production
single-tenant keeps the original `is_active` flag (rescoped to seed rows by a
partial unique index).

**Vultr Vector Store skip.** The wrapper to `/vector_store/{id}/items` and
`/chat/completions/RAG` does not expose per-item metadata filters, so we
cannot safely partition a shared collection by `session_id`. Rather than
provision one Vultr collection per visitor (cleanup is not guaranteed across
a 6-day judging window), demo mode skips both the chunk push and the RAG
prefetch. Postgres remains the source of truth: the briefing is still saved
on the visitor's clone customer and shown post-call. The audit log keeps the
wiring visible with explicit `status=skipped reason=demo_session` rows on the
`memory_lookup` and `memory_updater` steps.

The production single-tenant path (no `X-Demo-Session` header, or
`?bypass=<token>` for pitch-day) runs the full Vultr loop unchanged.

**Cleanup.** A background asyncio task running in the FastAPI lifespan event
sweeps `demo_sessions` every 30 minutes and deletes everything that has been
idle longer than 24 hours (calls, audit, executed actions, memory chunks,
wizard-generated templates, cloned customers, the session row itself). Vultr
is not touched because we never wrote to it for demo sessions.

## Key tables

| Table                    | Carries `session_id`? | Purpose                                                |
|--------------------------|-----------------------|--------------------------------------------------------|
| `demo_sessions`          | (is the id)           | Per-visitor sandbox, plus the picked active template   |
| `templates`              | yes                   | Seed presets (`NULL`) + wizard-generated (per session) |
| `customers`              | yes                   | Seed customers (`NULL`) + clone-on-write per session   |
| `calls`                  | yes                   | Filtered on read and on cleanup                        |
| `audit_log`              | yes                   | Same; lets judges read their own audit trail           |
| `executed_actions`       | yes                   | Same                                                   |
| `customer_memory_chunks` | yes (always NULL today) | Demo mode skips the write; column exists for future   |
| `extracted_fields`       | no                    | Cascades via `calls`                                   |
