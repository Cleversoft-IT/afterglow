# Future ideas — post-hackathon roadmap

> Material for the pitch's *"future work"* slide. Everything below is
> intentionally **out of scope** for the AI Agent Olympics @ Milan AI Week
> 2026 deadline (19 May 2026, 17:00 CEST). The items here were validated
> as worthwhile during the v2 templates roadmap design but rolled out of
> the build to keep the demo surface small.

The hackathon's "produzione" surface = the public demo URL
(`https://app.afterglow.cleversoft.it`). Everything below assumes a real
production deployment that does not exist today; see
[`../../.claude/memory/feedback_production_equals_hackathon.md`](../../.claude/memory/feedback_production_equals_hackathon.md).

---

## 1. Template lineage — `parent_id`

**Scenario.** Operator opens `Restaurant` (seed), clicks *New from prompt*,
describes "same as Restaurant but for an ice-cream shop with a cone of
the day". The wizard runs, the new template lands with
`parent_id=<Restaurant.id>`. The list view renders the new row as *"Cone of
the day" — derived from Restaurant*. A `Diff` tab shows exactly what
changed (which fields/actions were added, removed, or tweaked).

**Why it matters.** Today the wizard generates a self-contained template
and the lineage is lost. With `parent_id` the wizard becomes
*incremental*, not a single-shot generator — the operator sees what the
LLM added on top of a known good baseline, which is easier to trust.

**Cost.** One nullable UUID column on `templates` + a small UI badge + a
diff view (computed in the client from the parent + child JSON). No
runtime cost beyond the wizard call. About a day of work.

---

## 2. Template versioning — `status` tri-state

**Scenario today.** The wizard saves a new template and it appears
immediately in the operator's list alongside the seed presets. Two
problems: (a) the new template is visible before the operator has
finished refining it; (b) replacing the currently-active template is a
hard cut — no way to stage a new version, A/B it on a few calls, and
promote it.

**Scenario tri-state.** `Template.is_active: bool` becomes
`Template.status: enum(draft, active, retired)`. The wizard saves as
`draft`; a dedicated *Drafts* tab keeps drafts separate from the
operator's library. Clicking *Promote* moves the draft to `active` and
demotes the previously-active row to `retired` (kept for history). The
incoming-call dialer always reads the latest `active` row.

**Why it matters.** Versioning is a basic enterprise feature. The pitch
narrative is "your template is a living document, not a paste-from-LLM".

**Cost.** Migration with backfill (`is_active=True → status='active'`,
all others → `'retired'`), partial-unique-index rewrite, two new
endpoints (`POST /templates/{id}/promote`, `POST /templates/{id}/retire`),
and two UI sections. About two days of work.

---

## 3. Wizard learning loop — feedback from real calls

**Scenario.** The Restaurant template has been active for a week and
processed 80 calls. The operator opens the template detail and sees a
new *Tuning suggestions* card. The card calls a new endpoint
`POST /api/v1/templates/{id}/tuning` which:

- aggregates `audit_log` + `executed_actions` + `extracted_fields` for
  the last 30 days,
- asks Gemini "what patterns do you see? Which fields are missing from
  the template but the operator keeps editing manually after the call?
  Which actions fail their preconditions over and over because a
  precondition is too strict or refers to a field that is usually
  missing?",
- returns structured suggestions (proposed field additions, proposed
  threshold tweaks, proposed prompt-hint rules).

The operator reviews each suggestion in a diff card; *Apply* turns it
into an edit to the template.

**Why it matters.** This is the pitch's strongest "agentic systems, not
copilots" punchline — *the system tunes itself based on its own audit
trail.* In demo mode the loop runs against the seed audit log with a
banner *"illustrative; in production this would use your real call
history."*

**Cost.** One new endpoint, one new Gemini agent (`agents/template_tuner.py`),
one new aggregator query, one new UI card with diff visualisation. About
three days of work — by far the largest of the three, and the most
demo-worthy.

---

## 4. PII / privacy gating

**Scenario.** Each `FieldDefinition` carries a `pii_class`
(`contact|health|financial|identity`) plus a per-class threshold; the
post-call pipeline runs a sanitizer that redacts low-confidence
classified fields out of the briefing and the audit log, surfaces a
`pii_policy_applied` audit row, and pushes a `pii_classes_present` list
into the Vultr Vector Store chunk metadata so an auditor can answer
"which chunks carry health-class data" without parsing the chunk body.

**Why it matters.** Real-world dialer deployments hit GDPR / HIPAA the
moment the operator starts hearing names and allergies. The hackathon
build deliberately ships **without** this layer: the operator needs to
see allergies verbatim before the next pickup, and a half-built privacy
system is more dangerous than no system at all. A grown-up version would
also need DSAR endpoints, retention policy on `customer_memory_chunks`,
and a redaction queue for the audit log.

**Cost.** One sanitizer module, one policy module with per-class
thresholds, audit shape changes, Vector Store metadata changes, plus
end-to-end tests. About three days of work — and a non-trivial
governance/legal review that is outside the hackathon's brief. **Removed
from the runtime on 2026-05-17** along with `pii_sanitizer.py` /
`pii_policy.py` (see
[`.claude/memory/project_template_simplified_2026_05_17.md`](../../.claude/memory/project_template_simplified_2026_05_17.md))
so this section becomes the canonical place to find the original design
when we pick it back up.

---

## 5. Speechmatics custom dictionary per template

**Scenario.** Each template carries a small `custom_dictionary: list[str]`
of domain terms (`celiac`, `crown`, `bumper`, …) that the orchestrator
passes to Speechmatics as `additional_vocab`. The Wizard's LLM generates
the list at template creation time.

**Why it matters.** Speechmatics auto-detection is already good on the
six bundled MP3s, but a real production deployment on real audio would
benefit from domain-specific vocabulary hints — especially for medical
and legal terminology where ASR errors land at the wrong end of the
threshold and either flag a field as low-confidence or extract a wrong
value.

**Cost.** Already done once and reverted on 2026-05-17 (migration
`0012_drop_template_custom_dictionary.py`). The original implementation
lived in `Template.custom_dictionary` (ARRAY column), the
`additional_vocab` parameter on `speechmatics.transcribe_audio`, plus a
Wizard prompt rule. Adding it back is a couple of hours; the reason it
was removed was UX — it pushed the template editor toward "ASR config
panel" instead of "what the business wants the AI to capture".

---

## Why not in the hackathon build

The v2 templates roadmap audit (2026-05-16) plus the 2026-05-17
simplification concluded that typed action payloads, structured
`prompt_hints`, the agentic action planner, the typed executor with
`mutates` + `evidence_required` gates, and the persisted Wizard already
saturate the "Application of Technology" + "Agentic Workflows" judging
axes. Adding lineage / versioning / learning loops / PII gating / ASR
dictionaries on top would dilute the pitch's coherence — every minute
spent on them is a minute not spent making the shipped features
rock-solid. They go on the slide, not on the merge queue.
