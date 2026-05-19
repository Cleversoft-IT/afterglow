"""Round-trip + mapping tests for `Call.review_flag` and `needs_review` status.

Pure unit tests on the schemas and mappers — no DB required.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.api.calls import _failure_kind
from app.schemas.calls import CallDetailView, CallListItem, ReviewFlag


def test_review_flag_pydantic_round_trip():
    flag = ReviewFlag(
        reason="agent flagged ambiguous evidence",
        severity="high",
        turn_count=7,
        flagged_by="agent",
    )
    raw = flag.model_dump()
    back = ReviewFlag.model_validate(raw)
    assert back == flag


def test_review_flag_defaults():
    flag = ReviewFlag(reason="something")
    assert flag.severity == "medium"
    assert flag.flagged_by == "agent"
    assert flag.turn_count is None


def test_call_detail_view_accepts_review_flag():
    cid = uuid4()
    flag = {
        "reason": "agent_did_not_finalize",
        "severity": "high",
        "turn_count": 12,
        "flagged_by": "system",
    }
    view = CallDetailView(
        id=cid,
        template_id=uuid4(),
        phone_e164="+393331112233",
        status="needs_review",
        created_at=datetime.now(tz=timezone.utc),
        review_flag=flag,
        executed_actions=[],
    )
    assert view.review_flag is not None
    assert view.review_flag.severity == "high"
    assert view.review_flag.flagged_by == "system"


def test_call_list_item_accepts_review_flag():
    item = CallListItem(
        id=uuid4(),
        phone_e164="+393331112233",
        template_id=uuid4(),
        status="needs_review",
        created_at=datetime.now(tz=timezone.utc),
        review_flag={"reason": "x", "severity": "low", "flagged_by": "agent"},
    )
    assert item.review_flag is not None
    assert item.review_flag.severity == "low"


def test_needs_review_does_not_trigger_failure_kind():
    """`failure_kind` is only computed for status='failed'. needs_review keeps it None."""
    assert _failure_kind("needs_review", None) is None
    assert _failure_kind("needs_review", "some_reason") is None
    assert _failure_kind("completed", None) is None
    # Sanity: still works for the failed branch.
    assert _failure_kind("failed", "empty_or_noise_audio") == "missed"
    assert _failure_kind("failed", "call_agent: ADK crash") == "pipeline_error"
