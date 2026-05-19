---
name: feedback-session-lock-concurrent-tools
description: Why the agent loop wraps every tool's session mutation in an asyncio.Lock instead of opening a fresh AsyncSession per tool.
metadata:
  type: feedback
---

The round-10 agentic pipeline shares ONE `AsyncSession` (`bg_session`, opened by `api/calls._run_pipeline_isolated` or `api/admin._bg_run_pipeline`) between every action tool, `flag_for_review`, and the orchestrator's own commits. Gemini supports parallel function calling — a single agent turn can emit two `function_call`s that ADK's `InMemoryRunner` fires concurrently. Two `await session.flush()` coroutines hitting the same `AsyncSession` raise `sqlalchemy.exc.InvalidRequestError("Session is already flushing")`, which the call agent surfaces as `Call.status="failed"` with `error="adk_runner [InvalidRequestError]: ..."`. Mark Ross + restaurant template was the first reproducer (preseed RAG lookup + booking action emitted in the same turn).

**Rule**: every tool that mutates `bg_session` must wrap the mutation in `async with session_lock:`. The lock is created once per `run_pipeline` invocation in `orchestrator.py` and passed down (`session_lock` kw-arg required on `run_call_agent`, `make_action_tool`, `make_flag_for_review`).

**Why:** parallel function calling at the model side is the source of the race. SQLAlchemy's `AsyncSession` is not re-entrant, and the audit logger already proves that opening fresh `SessionLocal()` per write costs us the ability to keep state inside the pipeline transaction. The lock keeps the shared session model intact (executed actions visible mid-loop, briefing write-back tied to the same commit cycle) while serializing the bits SQLAlchemy can't share.

**How to apply:** any future tool that touches `bg_session` (new action types, new control tools, post-loop hooks) must accept `session_lock` and wrap `session.add` / `session.flush` / `session.execute` calls with `async with session_lock:`. Audit rows go through `audit_step` which uses its OWN `SessionLocal()` (`audit/logger.py:61-63`) — those do NOT need the lock.

**Alternative rejected:** "open a fresh `SessionLocal()` per tool" — would lose the in-transaction visibility of executed actions and force a redesign of the briefing write-back path. The lock is a 5-line fix that respects every existing invariant.

Related: [[project-agentic-pipeline]], [[project-afterglow-decisions]].
