---
name: project-agentic-pipeline
description: Round-10 agentic post-call pipeline — single multi-turn Gemini/ADK loop, tool surface, no-raise contract, needs_review status, audit correlation. Read before touching call_agent or tool modules.
metadata:
  type: project
---

# Round-10 — agentic post-call pipeline (landed 2026-05-18)

## Why this exists

Through round-9 the post-call pipeline was three independent stages — a
single-shot `call_analyzer` (one Gemini structured-output call producing
`CallAnalysis`), a single-turn `action_planner` (Google ADK seeing the tools
once and registering them in state), and a deterministic batch
`action_executor` (no LLM in the loop). The model never observed the result
of an action, never iterated, never asked for context on demand.

The hackathon's "Application of Technology" and "Originality" criteria
(`hackathon-docs/07-judging-criteria.md`) reward exactly what was missing:
**multi-step reasoning, tool use, self-correction, emergent behaviour**. The
Vultr "Web-Based Enterprise Agent" track explicitly demands *multi-step
agentic workflows*. Three glued stages did not qualify.

Round-10 collapses everything into one **multi-turn Gemini/ADK agent**
(`backend/app/agents/call_agent.py`) that decides turn by turn which tool
to call, observes the response, and iterates.

## The new shape

```
orchestrator.run_pipeline
├─ speechmatics            (transcript + diarization + language)
├─ pre_classifier          (skip on empty/noise)
├─ _resolve_customer       (clone-on-write in demo)
├─ retrieve_structured_facts  (SQL pass for prompt_hints — NOT RAG)
├─ ╭──────────────────────────────────────────────────────────╮
│  │  run_call_agent — ADK Agent, up to 12 tool turns         │
│  │  Tools:                                                  │
│  │   · lookup_customer_memory(query)   ← Vultr RAG on demand│
│  │   · search_transcript(keyword)                           │
│  │   · read_transcript_segment(s, e)                        │
│  │   · <action_key>(payload, …)        ← inline execution   │
│  │   · flag_for_review(reason, sev)                         │
│  │   · finalize_call(payload)          ← stop the loop      │
│  ╰──────────────────────────────────────────────────────────╯
├─ map completion_reason → call.status (completed | needs_review | failed)
├─ persist ExtractedFields            (only on "finalize")
└─ _persist_memory                    (only on status="completed")
```

## Tool catalog at runtime

| Tool | Args | Returns | Side effect |
|---|---|---|---|
| `lookup_customer_memory` | `query: str` | `{facts, source, input_tokens, output_tokens}` | Vultr RAG call |
| `search_transcript` | `keyword: str` | `{matches: [{speaker, snippet, word_index}], count}` | pure |
| `read_transcript_segment` | `start_word: int`, `end_word: int` | `{text, word_count, start_speaker}` | pure |
| `<action_key>` (N tools) | typed Pydantic `payload` + `confidence` + `evidence` | `{status, result, attempt, agent_turn}` | Persists `ExecutedAction`; runs mock/internal handler |
| `flag_for_review` | `reason: str`, `severity` | `{flagged: true}` | Sets `Call.review_flag` (`flagged_by="agent"`) |
| `finalize_call` | `payload: FinalizeCallPayload` | `{final: true}` | Deposits payload in `state["final"]` |

`FinalizeCallPayload` = `{fields: list[FieldExtraction], intent, sentiment, language, urgency, briefing}` — note **`fields`**, not `extracted_fields`.

## No-raise contract (locked)

Every layer of the agentic loop is required to **translate failures into
data, never into exceptions**:

1. `execute_single_action` (`executors/action_executor.py`) catches
   exceptions from `MOCK_REGISTRY` / `INTERNAL_HANDLERS` and surfaces
   `status="failed"` with `result.error` instead of raising.
2. Action tool wrappers (`agents/tools/action_tool.py`) cap retries at 2
   per `action_type` and refuse second mutating calls after a success.
3. `run_call_agent` (`agents/call_agent.py`) catches every `Exception`
   from ADK and returns `CallAgentResult(completion_reason="error", error=...)`.
4. `orchestrator.run_pipeline` reads `completion_reason` and sets
   `call.status` accordingly — **never re-raises** to the BackgroundTask
   wrapper. The `_run_pipeline_isolated.except` rollback path
   (`api/calls.py:222`) remains the safety net only for catastrophic
   uncaught exceptions (DB disconnect, OOM).

**Why this matters**: a transaction rollback inside
`_run_pipeline_isolated` would erase every `ExecutedAction` flushed by the
agent loop before the failure. The no-raise contract keeps the loop's
side effects visible (an operator can review or undo them) even when the
agent itself bails out.

## Session-lock invariant (round-11, 2026-05-19)

Gemini supports parallel function calling — two `function_call` parts can
arrive in the same agent turn and ADK's `InMemoryRunner` fires them
concurrently. The shared `bg_session` (`AsyncSession`) is NOT re-entrant:
two `await session.flush()` coroutines collide with
`InvalidRequestError("Session is already flushing")`.

`orchestrator.run_pipeline` creates a single `asyncio.Lock` per pipeline
invocation and threads it through `run_call_agent(session_lock=...)` →
`make_action_tool(session_lock=...)` → `make_flag_for_review(session_lock=...)`.
Every tool wraps its `session.add` / `flush` / `execute` block in
`async with session_lock:`. Audit rows are not affected: `audit_step`
opens its own `SessionLocal()` (`audit/logger.py`) and is outside the
shared-session contract.

The `session_lock` kw-arg is **required** on `run_call_agent`,
`make_action_tool`, `make_flag_for_review`. Any new tool that mutates
`bg_session` must accept it. Rationale and rejected alternatives are in
[[feedback-session-lock-concurrent-tools]].

## `Call.status` values

| status | When | UI |
|---|---|---|
| `pending`, `transcribing`, `analyzing` | non-terminal, Home polls every 2s | progress chip |
| `completed` | agent invoked `finalize_call` | green chip |
| `needs_review` | round-10 NEW — `completion_reason="max_turns"` OR agent called `flag_for_review` | yellow chip + banner |
| `failed` | `completion_reason="error"` (or empty audio) | red chip; `failure_kind` discriminates `missed` vs `pipeline_error` |

The idempotency guard (`orchestrator.py:60`) skips re-runs when status is
in `{"transcribing", "analyzing", "completed", "needs_review", "failed"}` —
adding `needs_review` and `failed` so a retry click cannot re-trigger the
loop on an already-terminal call.

## Audit correlation (deterministic)

Every audit row carries `payload.agent_turn: int` whenever it relates to
the agentic loop. The counter is bumped by every tool wrapper as its first
instruction (`tools/turn.bump_turn`) and forwarded to
`execute_single_action(agent_turn=…)`. The UI joins:

```sql
-- agent's own turns
SELECT ... FROM audit_log
WHERE agent_name='call_agent' AND step_type='agent_turn';

-- action_exec rows nested under their source turn
SELECT ... FROM audit_log
WHERE agent_name='action_executor' AND step_type='action_exec'
  AND payload->>'agent_turn' = '<N>';
```

No fragile timestamp joins.

## How the demo earns hackathon points

- **Application of Technology** — agentic architecture, multi-step
  reasoning, self-correction on `validation_failed`/`evidence_missing`,
  tool use, RAG as a tool (not as a prompt prefix). Combo Gemini +
  Speechmatics + Vultr visible in the same audit trail.
- **Originality** — emergent behaviour: the agent may ask
  `lookup_customer_memory("Does this caller prefer window seats?")` and
  fold the answer into the briefing without being asked. Retry-after-failure
  shows the model adapting on-the-fly.
- **Vultr "Web-Based Enterprise Agent" track** — multi-step workflow,
  Vultr Vector Store + Inference both invoked from the loop.
- **Business Value** — operator's "Agent reasoning" pane explains every
  action: an auditable, undoable AI that a small-business owner can trust.

## Status of legacy artifacts

- `agents/action_planner.py` — **deleted**.
- `agents/call_analyzer.py` — alleggerito a soli `FieldExtraction` + `TokenUsage`.
- `executors/action_executor.execute_planned_actions` — kept as a batch
  wrapper around `execute_single_action` for the legacy test
  (`test_action_executor_validation.py`), not exercised by the live path.

If you find any reference to `action_planner` or `CallAnalysis` outside
`call_agent.py`'s historical comment block, treat it as a bug to fix.
