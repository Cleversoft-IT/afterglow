# Templates roadmap — future-facing notes

> **Status (2026-05-16):** every item below is still **deferred** — none has
> landed in code. Audited against `backend/app/schemas/templates.py`,
> `agents/template_builder.py`, `agents/action_planner.py` and
> `api/templates.py` on 2026-05-16; the runtime still uses free-form
> `payload_json` strings and free-text `prompt_hints`, and the wizard is
> still single-shot (`api/templates.py:215` "today only generates, does not
> persist"). Treat this file as a design pad, not a TODO list.

Afterglow's `Template` is the conceptual hinge between the human-curated
business knowledge and the agentic post-call pipeline. Today it carries five
useful primitives:

- `fields_schema` — the data the operator wants extracted.
- `action_types` — the actions Gemini/ADK can plan (subset: `execution_mode=auto`).
- `custom_dictionary` — domain terms fed to Speechmatics.
- `prompt_hints` — narrative instructions for the analyzer.
- `domain_hint` — semantic bucket used by Speechmatics + RAG.

This document collects the additive (non-breaking) evolutions that would make
the pipeline more agentic and unlock the prompt-to-template flow. **Nothing
here is implemented** — open it before designing the next iteration.

---

## Deferred from the May-19 milestone (intentional)

The following items were scoped out of the rev-2 plan to keep the demo
surface small. They are still worthwhile and should be the first targets of
the post-hackathon iteration.

### Bilingual briefing for the vector store

Today `_persist_memory` builds the Vultr Vector Store chunk in English with
the native-language briefing embedded inside. That hurts cross-lingual
retrieval once the customer accrues > 10 calls (which is when the semantic
RAG path actually triggers).

Plan: a small Gemini call (≤ 60 tokens, `temperature=0.1`) summarises the
native briefing into one English sentence; both go into the chunk. Adds one
LLM call per pipeline run — measure first.

### Sophisticated PII gating

The current gate flags sensitive fields with confidence below 0.85 in the
audit log and instructs Gemini to redact the value from the briefing. A
richer model:

- `pii_class` enum on each `FieldDefinition` (additive JSONB):
  `none | contact | health | financial | identity`.
- Per-class redaction strategy: e.g. hash `financial` values before audit log
  storage, never inline-cite `health` values in the briefing, etc.
- Per-class confidence thresholds (health stricter than contact).

---

## Template conceptual upgrade

Extensions are all additive — old templates keep working, new templates get
finer-grained control. The shape proposals below are pseudocode; the actual
Pydantic schema changes go in `backend/app/schemas/templates.py`.

### `FieldDefinition` extensions

```jsonc
{
  "key": "allergies",
  "type": "string_list",
  "label": "Allergies",
  "sensitive": true,
  "options": [],
  "description": "Comma-separated allergens mentioned by the caller.",

  // --- proposed additions ---
  "confidence_threshold": 0.8,        // below: downstream goes to manual_review
  "pii_class": "health",              // see PII gating section
  "extractor_hint": "freeform",       // regex | freeform | enum | llm_only
  "depends_on": ["customer_name"]     // these fields must be present too
}
```

The Action Planner reads `confidence_threshold` and `depends_on` when
deciding whether a tool's preconditions are satisfied.

### `ActionDefinition` extensions

```jsonc
{
  "key": "booking.create",
  "label": "Create booking",
  "execution_mode": "auto",
  "mock_target": "booking",
  "description": "Insert a new reservation in the booking system.",

  // --- proposed additions ---
  "preconditions": ["party_size", "booking_date", "booking_time"],
  "confidence_threshold": 0.7,
  "mutates": true,                    // irreversible — never auto-retry
  "evidence_required": true,
  "payload_schema": {                 // drives ADK FunctionDeclaration
    "type": "object",
    "properties": {
      "party_size": { "type": "integer", "minimum": 1 },
      "booking_date": { "type": "string", "format": "date" },
      "booking_time": { "type": "string", "format": "time" }
    },
    "required": ["party_size", "booking_date", "booking_time"]
  }
}
```

`payload_schema` is the most impactful addition: today the action planner's
tools accept a free-form `payload_json` string; a proper schema lets the
ADK runner expose typed parameters and the executor validate before calling
`MOCK_REGISTRY`. It also unlocks per-action documentation in the UI.

### Structured `prompt_hints`

Free-form text is hard to keep clean across the three seed templates plus
any wizard-generated additions. Move to an array of `{when, then}` triggers:

```jsonc
"prompt_hints": [
  { "when": "field.urgency == 'emergency'",
    "then": "escalate via callback action" },
  { "when": "field.license_plate is null",
    "then": "queue whatsapp.request_photos with reason='missing plate'" }
]
```

The orchestrator evaluates these rules before calling Gemini and prepends
their narrative form to the analyzer's prompt — predictable, reviewable,
testable.

---

## Prompt-to-template, iterative

`POST /api/v1/templates/wizard` already exists in
`backend/app/api/templates.py` and is wired to a single-shot Gemini call in
`backend/app/agents/template_builder.py`. The output is **not persisted**.
The iterative version turns it into a four-step loop:

1. **Generate** — Gemini drafts a candidate template from the operator's
   free-text description.
2. **Validate** — a small validator agent checks:
   - `fields_schema` keys are snake_case lowercase.
   - `action_types` keys are either present in `MOCK_REGISTRY` or come with
     a proposed mock declaration the operator must approve.
   - `custom_dictionary` terms fit `domain_hint`.
3. **Refine** — UI screen (proposed: `app/app/templates/edit.tsx`) lets the
   operator tweak fields, actions, and hints inline. Each change emits an
   audit row so we can show "before/after" diffs to the judges.
4. **Persist** — write the template with `is_seed=False`,
   `session_id=ctx.session_id` for demo or `NULL` for production tenant.
   The active-template index already supports this through the unique
   partial index `uq_template_active`.

Bonus: once the template is shaped, the wizard can re-run the loop with
"learning data" — pull `executed_actions` and `extracted_fields` for the
past 30 days and ask Gemini *"are there fields the operator keeps editing
manually that should become extractions? are there actions that always fail
because preconditions are missing?"*. The wizard becomes a tuning surface,
not a one-shot generator.

---

## Open questions for the next session

- Do we want `Template.parent_id` to track derivations (a custom template
  cloned from a seed should remember the lineage for the UI)?
- Should `Template.is_active` become a tri-state (`draft | active | retired`)
  to support staging new versions?
- Where does the wizard's "learning data" come from in demo mode, given
  that each session is isolated? Probably aggregate against seed data with
  a clear "this is illustrative" banner.
