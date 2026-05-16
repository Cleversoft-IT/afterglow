# Future ideas — post-hackathon roadmap

> Material for the pitch's *"future work"* slide. Everything below is
> intentionally **out of scope** for the AI Agent Olympics @ Milan AI Week
> 2026 deadline (19 May 2026, 17:00 CEST). The three items here were
> validated as worthwhile during the v2 templates roadmap design but
> rolled out of the build to keep the demo surface small.

The hackathon's "produzione" surface = the public demo URL
(`https://app.95-179-245-107.sslip.io`). Everything below assumes a real
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

## Why not in the hackathon build

The v2 templates roadmap audit (2026-05-16) concluded that PII gating,
typed action payloads, structured `prompt_hints`, and the persisted
wizard already saturate the "Application of Technology" + "Agentic
Workflows" judging axes. Adding lineage / versioning / learning loops
would dilute the pitch's coherence — every minute spent on them is a
minute not spent making the four shipped features rock-solid. They go
on the slide, not on the merge queue.
