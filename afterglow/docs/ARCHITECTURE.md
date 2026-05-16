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
       │
       ├─► Vultr Vector Store /v1/chat/completions/RAG  (pre-fetch: prior_facts)
       │   └─► single collection, configured via VULTR_VECTOR_DEFAULT_COLLECTION
       │       (skipped when the call carries a demo session_id — see below)
       │
       ├─► Gemini structured-output call  (call_analyzer.py — single Gemini pass)
       │       prompt: transcript + template fields_schema (incl. pii_class /
       │               confidence_threshold / extractor_hint / depends_on) +
       │               action_types (incl. preconditions / confidence_threshold /
       │               mutates / evidence_required / payload_schema) +
       │               applicable prompt_hints rules (when evaluated against
       │               prior_structured) + prior_facts
       │       response_schema = CallAnalysis (Pydantic):
       │         - fields[]  (key, value, confidence, evidence)
       │         - intent, sentiment, language, urgency
       │         - planned_actions[]  (subset of template auto-actions, typed payload)
       │         - next_call_briefing  (NL paragraph, detected language)
       │       Fail-fast: missing key / error / schema mismatch → Call.failed.
       │
       ├─► PII sanitizer (pii_sanitizer.py — pure Python, no LLM)
       │       applies the per-pii_class redaction policy to next_call_briefing
       │       and planned_action evidence; audit step `pii_policy_applied`
       │       records exactly what was redacted, with which threshold.
       │       Raw `fields` survive untouched for UI + executor.
       │
       ├─► Action Planner (action_planner.py — Google ADK agentic loop)
       │       reads the SANITIZED analysis, exposes the template's auto-mode
       │       action_types as ADK tools with TYPED payload parameters
       │       (Pydantic models built from payload_schema). Gemini emits a
       │       structured object that matches the schema; the executor revalidates.
       │       Fail-fast: ADK runner error → Call.failed (no fallback).
       │
       ├─► Action Executor (deterministic Python) ─► jsonschema.validate(payload),
       │       evidence_required gate, mutates flag, `mock: True` stamp on the
       │       result (renders a "Simulated" badge in the operator UI) →
       │       mock registry + Postgres + audit_log
       │
       └─► Memory write-back ─► customer.memory_summary (Postgres, operator-visible)
                                + extracted_fields.briefing_snapshot (sanitized per-call copy)
                                + bilingual chunk pushed to Vultr Vector Store
                                  (native briefing + EN summary; skipped when the
                                   call carries a demo session_id)
```

The pipeline runs **entirely after the call ends**. The human-facing latency
is whatever Postgres takes to return `customer.memory_summary`. No AI in the
live-call hot path.

System of record: **Vultr Managed Postgres**. Deploy: **Vultr Cloud Compute +
Coolify** with auto-deploy via GitHub App webhook on push to `main` (no
manual deploy step, no GitHub Actions in the critical path). IAM: Vultr
Service User with minimal-privilege ACL.

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
| `extracted_fields`       | no                    | Cascades via `calls`. Carries `briefing_snapshot` (mig `0005`): a frozen copy of the SANITIZED briefing emitted for this specific call, kept even after `customer.memory_summary` is later overwritten by a newer call. |

## PII handling

Every `FieldDefinition` carries a `pii_class` (`none|contact|health|
financial|identity`) and an optional per-field `confidence_threshold`
that overrides the class default. The defaults are encoded in
`backend/app/agents/pii_policy.py`:

| Class      | Default threshold | Redaction strategy (briefing / vector chunk / audit evidence) |
|------------|-------------------|---------------------------------------------------------------|
| `none`     | 0.0               | passthrough                                                   |
| `contact`  | 0.80              | `[redacted: contact]`                                         |
| `identity` | 0.85              | first2 + asterisks + last2 (e.g. `AB***CD`)                  |
| `financial`| 0.90              | `[hash:<sha256[:8]>]` deterministic per value                |
| `health`   | 0.90              | `[redacted: health]` — never inline                          |

The sanitizer (`backend/app/agents/pii_sanitizer.py`) runs **immediately
after** the call_analyzer and produces a `SanitizedAnalysis` that:

1. Redacts every occurrence of a PII field's raw value from
   `next_call_briefing` and from each `planned_action.evidence` span.
2. Leaves `analysis.fields` untouched — the operator UI and the action
   executor still need the original value (booking the right table, sending
   the right WhatsApp to the right customer).
3. Emits a `pii_policy_applied` audit row enumerating which fields
   triggered the policy, the class, the threshold, and the action taken
   (`flag` when confidence is below threshold, `redact` otherwise). The
   raw values never appear in the audit payload — only the field key.

The chunk that lands in the Vultr Vector Store metadata records
`pii_redactions_applied: list[pii_class]` so an auditor can answer "did
we leak any health data into the embedding?" without re-reading the
chunk text.

## Bilingual briefing

When `transcript.language != "en"` (and we are not in demo mode), the
orchestrator's `_persist_memory` makes one extra small Gemini call
(`_summarize_to_english`, ≤120 output tokens) to produce an English
restatement of the (already sanitized) briefing. Both copies are pushed
to the Vultr Vector Store chunk so semantic retrieval works across the
operator's spoken language and the embedding model's bias toward
English. Failure of the bilingual call lands as
`audit.memory_summarizer_bilingual.status=degraded` and the chunk falls
back to native-only — the briefing on Postgres is unaffected.

## Token accounting

Every LLM step on the post-call path writes the token counts it consumed
into `audit_log.input_tokens` / `audit_log.output_tokens`:

- `call_analyzer.llm_call` — Gemini `response.usage_metadata`
  (`prompt_token_count` / `candidates_token_count`).
- `memory_summarizer_bilingual.llm_call` — same source.
- `memory_lookup.rag_semantic` — Vultr RAG's `usage.prompt_tokens` /
  `usage.completion_tokens` from the JSON response body.

The wizard surface (`template_builder`, `template_validator`) is not in
the post-call path and is not audited per token today.
