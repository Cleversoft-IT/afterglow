"""Unit tests for the orchestrator's status-mapping helpers.

These cover the no-raise contract described in
`.claude/memory/project_agentic_pipeline.md`:

  - `completion_reason="error"`  → Call.status="failed" + Call.error
  - `completion_reason="max_turns"` → Call.status="needs_review" +
      Call.review_flag auto-filled when the agent did not set one itself
  - an agent-set review_flag (from `flag_for_review`) is honored, not
    overwritten by the system fallback

Pure unit tests on the orchestrator helpers — no DB, no Gemini, no ADK.
The end-to-end behaviour is exercised by the existing
`test_call_agent_offline.py` (loop returns a CallAgentResult) plus these
mapping tests (the orchestrator translates that result onto the Call row).
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.agents.call_agent import CallAgentResult
from app.agents.call_analyzer import TokenUsage
from app.agents.orchestrator import _apply_agent_error, _apply_agent_max_turns


def _fresh_call() -> SimpleNamespace:
    return SimpleNamespace(
        status="analyzing",
        error=None,
        review_flag=None,
        completed_at=None,
    )


def test_error_maps_to_failed_with_error_text():
    call = _fresh_call()
    result = CallAgentResult(
        completion_reason="error",
        turn_count=3,
        token_usage=TokenUsage(),
        error="adk_runner: simulated crash",
    )
    _apply_agent_error(call, result)

    assert call.status == "failed"
    assert call.error == "adk_runner: simulated crash"
    assert isinstance(call.completed_at, datetime)
    assert call.completed_at.tzinfo is not None
    # No review_flag side effect on error path.
    assert call.review_flag is None


def test_error_with_missing_error_string_falls_back_to_default():
    call = _fresh_call()
    result = CallAgentResult(completion_reason="error", token_usage=TokenUsage())
    _apply_agent_error(call, result)

    assert call.status == "failed"
    assert call.error == "call_agent error"


def test_error_truncates_to_1000_chars():
    call = _fresh_call()
    big = "x" * 5000
    result = CallAgentResult(
        completion_reason="error", token_usage=TokenUsage(), error=big,
    )
    _apply_agent_error(call, result)
    assert len(call.error) == 1000


def test_max_turns_maps_to_needs_review_with_auto_flag():
    call = _fresh_call()
    result = CallAgentResult(
        completion_reason="max_turns",
        turn_count=12,
        token_usage=TokenUsage(),
    )
    _apply_agent_max_turns(call, result)

    assert call.status == "needs_review"
    assert call.review_flag == {
        "reason": "agent_did_not_finalize",
        "severity": "high",
        "turn_count": 12,
        "flagged_by": "system",
    }
    assert isinstance(call.completed_at, datetime)
    # No Call.error on the needs_review branch — failure_kind must stay None.
    assert call.error is None


def test_max_turns_honors_existing_agent_set_flag():
    """If the agent invoked flag_for_review earlier in the loop, that flag
    must NOT be overwritten by the system fallback."""
    call = _fresh_call()
    call.review_flag = {
        "reason": "ambiguous booking time",
        "severity": "medium",
        "flagged_by": "agent",
    }
    result = CallAgentResult(
        completion_reason="max_turns",
        turn_count=12,
        token_usage=TokenUsage(),
    )
    _apply_agent_max_turns(call, result)

    assert call.status == "needs_review"
    # Preserved verbatim — flagged_by="agent" tells the UI who set it.
    assert call.review_flag == {
        "reason": "ambiguous booking time",
        "severity": "medium",
        "flagged_by": "agent",
    }


def test_pure_functions_do_not_raise_on_minimal_result():
    """No-raise contract: pure helpers tolerate a minimal CallAgentResult."""
    call = _fresh_call()
    result = CallAgentResult(completion_reason="error", token_usage=TokenUsage())
    _apply_agent_error(call, result)  # must not raise

    call2 = _fresh_call()
    result2 = CallAgentResult(completion_reason="max_turns", token_usage=TokenUsage())
    _apply_agent_max_turns(call2, result2)  # must not raise
    assert call2.review_flag is not None
