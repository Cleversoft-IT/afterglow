# Templates roadmap — v2 shipped

> **Status (2026-05-16): all items below have landed in code (migration
> `0006_templates_v2.py` + companion code/tests/docs).** Three previously
> "open" questions (`parent_id` lineage, `is_active` tri-state, wizard
> learning loop) were intentionally **rolled out of scope** for the
> hackathon and now live in [`future-ideas.md`](./future-ideas.md) as
> pitch material.

Afterglow's `Template` is the hinge between the human-curated business
knowledge and the agentic post-call pipeline. After v2 it carries the
following primitives:

- `fields_schema` — fields the operator wants extracted, each with
  `pii_class`, optional `confidence_threshold`, `extractor_hint`, and
  `depends_on`.
- `action_types` — actions the planner can invoke, each with
  `preconditions`, `confidence_threshold`, `mutates`, `evidence_required`,
  and a JSONSchema `payload_schema` that drives both the typed ADK
  FunctionDeclaration and the executor-side validation.
- `custom_dictionary` — domain terms fed to Speechmatics.
- `prompt_hints` — a JSONB array of `{when, then}` rules evaluated
  against the caller's prior structured fields before the analyzer prompt
  is built. Grammar: `always | field.<key> == '<value>' | field.<key> is
  [not] null`.
- `domain_hint` — semantic bucket used by Speechmatics + RAG.

The unique constraint on `(name, version)` is now expressed as two partial
unique indexes — one for prod (`session_id IS NULL`) and one for demo
sessions — to avoid the Postgres "NULL distinct" trap when multiple demo
visitors save a template with the same name.

---

## What shipped

### Bilingual briefing for the vector store ✅

`orchestrator._persist_memory` now generates a one-sentence English
summary via a small Gemini call when the detected language is not
English, and pushes both into the Vultr Vector Store chunk
(`backend/app/agents/orchestrator.py:_summarize_to_english`). The chunk's
`chunk_metadata` includes the detected `language`, the `briefing_en`
text, and the list of PII redaction classes applied. Audit step
`memory_summarizer_bilingual` records `status=ok|degraded|skipped`. Demo
mode keeps skipping the vector push entirely (single-tenant invariant
preserved); production = the public hackathon URL, see
[`feedback_production_equals_hackathon`](../../.claude/memory/feedback_production_equals_hackathon.md).

### Per-`pii_class` PII gating ✅

`backend/app/agents/pii_policy.py` declares per-class thresholds
(`contact=0.80, identity=0.85, financial=0.90, health=0.90`) and class-
specific redaction strategies (passthrough / `[redacted: …]` / SHA-256
hash / first2+stars+last2). `backend/app/agents/pii_sanitizer.py` runs
**immediately after** the analyzer and produces a `SanitizedAnalysis`
whose briefing and planned-action evidence are scrubbed; the raw
`fields` survive untouched so the operator UI and the action executor
still see the original values. Audit step `pii_policy_applied` records
exactly what was redacted, with which threshold, and at what confidence.

### `FieldDefinition` v2 ✅

`backend/app/schemas/templates.py:FieldDefinition` now carries
`pii_class`, `confidence_threshold`, `extractor_hint`, `depends_on`. The
orchestrator's `_coerce_extractions` enforces `depends_on`: a field whose
dependency is missing or below the dependency's threshold lands in the
persisted `confidence` blob as
`{"value": …, "status": "manual_review", "reason": "depends_on_unmet", "unmet": […]}`.

### `ActionDefinition` v2 ✅

Same file. Each action now declares `preconditions`,
`confidence_threshold`, `mutates`, `evidence_required`, and an optional
JSONSchema `payload_schema`. The Action Planner
(`backend/app/agents/action_planner.py:_make_tool`) builds a Pydantic
model dynamically from the schema (`backend/app/integrations/
jsonschema_to_pydantic.py`) and uses it as the tool's `payload`
annotation, so Gemini ADK emits a FunctionDeclaration with typed
parameters. The Action Executor revalidates with
`jsonschema.validate` before MOCK_REGISTRY; refusals land as
`status="validation_failed"`. `evidence_required=True` + empty evidence
also refuses. `mutates=True` is flagged in audit + `ExecutedAction.result`
for the never-auto-retry UI.

### Structured `prompt_hints` ✅

`prompt_hints` migrated from `Text` to `JSONB` (migration 0006). Each
rule is a `{when, then}` pair. `backend/app/agents/prompt_hint_eval.py`
evaluates the `when` grammar deterministically against the caller's
prior structured fields (returned by
`memory_retrieval.retrieve_structured_facts`) and only the matching
`then` strings are prepended to the analyzer's system instruction.

### Prompt-to-template, iterative (Generate → Validate → Refine → Persist) ✅

The wizard is now a four-step loop:

1. **Generate** — `POST /api/v1/templates/wizard`
   (`backend/app/agents/template_builder.py`) emits a
   `TemplateWizardResponse` via Gemini structured output. Fail-fast: no
   API key or repeated failures → 502.
2. **Validate** — same endpoint immediately runs
   `backend/app/agents/template_validator.py` (deterministic
   snake_case / depends_on cycles / JSONSchema / mock-registry-missing
   checks + a Gemini semantic pass for soft issues + proposed
   mock_targets) and embeds a `validation: ValidationReport` in the
   response. The refine UI can re-run validation via
   `POST /api/v1/templates/validate`.
3. **Refine** — `app/templates/wizard.tsx` (Expo) lets the operator
   inspect every section + the validation report inline. The detail
   screen `app/templates/[id].tsx` exposes description / domain_hint /
   custom_dictionary edits via `PUT /api/v1/templates/{id}`.
4. **Persist** — `POST /api/v1/templates` writes `is_seed=False`,
   `session_id=ctx.session_id` (demo) or `NULL` (prod), auto-bumping the
   `version` per `(name, session_id)`. `set_active=true` switches the
   caller's active template in the same transaction.

---

## Future ideas — see [`future-ideas.md`](./future-ideas.md)

The three "open questions" from the old roadmap (parent_id lineage,
`is_active` tri-state, wizard learning loop) intentionally did **not**
land in v2. They are documented as pitch material — "what we would do
next if this project continued past the hackathon."

### Two-mode wizard scripts (post-hackathon)

The Simulator's "existing" / "new" buttons each play their own MP3 for
the three seeded templates (restaurant / dentist / bodyshop): each ships
two recordings via `_bundled_simulation_configs()` in
`backend/app/db/seed.py`, and the dialer reads
`simulation_config.scenarios.{existing,new}` to pick which one to play.

Custom wizard-built templates still produce ONE recording reused across
both buttons (graceful fallback: the API's
`GET /templates/{id}/simulation/audio?mode=…` falls back to the legacy
flat `audio_url` when no scenarios map is present). Follow-up: teach
`backend/app/agents/simulation_script.py` to emit two distinct scripts —
one that assumes the caller is already known by phone and one that
assumes a cold first contact — and have the wizard render two MP3s via
`speechmatics_tts.render_script_to_wav`. Effort: ~half a day for the
prompt + storage + UI (two upload slots, two TTS buttons).
