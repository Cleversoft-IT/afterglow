"""Unit tests for app.agents.pii_policy — thresholds + redaction strategies."""
from __future__ import annotations

import pytest

from app.agents.pii_policy import (
    PII_THRESHOLDS,
    hash_for_audit,
    redact_for_briefing,
    threshold_for,
)


def test_thresholds_table_covers_every_pii_class():
    expected_classes = {"none", "contact", "health", "financial", "identity"}
    assert set(PII_THRESHOLDS.keys()) == expected_classes


def test_threshold_for_default():
    assert threshold_for("none") == 0.0
    assert threshold_for("contact") == 0.80
    assert threshold_for("health") == 0.90
    assert threshold_for("financial") == 0.90
    assert threshold_for("identity") == 0.85


def test_threshold_for_override_wins():
    assert threshold_for("health", override=0.75) == 0.75
    assert threshold_for("none", override=0.5) == 0.5


@pytest.mark.parametrize(
    "value,pii_class,expected_prefix",
    [
        ("Mario Rossi", "none", "Mario Rossi"),
        ("Mario Rossi", "contact", "[redacted: contact]"),
        ('["glutine", "lattosio"]', "health", "[redacted: health]"),
        ("4111111111111111", "financial", "[hash:"),
        ("AB123CD", "identity", "AB"),
        ("AB", "identity", "***"),
    ],
)
def test_redact_for_briefing_strategies(value, pii_class, expected_prefix):
    out = redact_for_briefing(value, pii_class)
    assert out.startswith(expected_prefix), (value, pii_class, out)


def test_redact_for_briefing_identity_format():
    out = redact_for_briefing("AB123CD", "identity")
    # AB + 3 stars + CD
    assert out == "AB***CD"


def test_redact_for_briefing_financial_deterministic():
    a = redact_for_briefing("4111111111111111", "financial")
    b = redact_for_briefing("4111111111111111", "financial")
    c = redact_for_briefing("4242424242424242", "financial")
    assert a == b
    assert a != c


def test_redact_for_briefing_handles_empty():
    assert redact_for_briefing("", "health") == ""
    assert redact_for_briefing(None, "health") is None  # type: ignore[arg-type]


def test_hash_for_audit_deterministic_per_salt():
    a = hash_for_audit("Marco Rossi", "session-1")
    b = hash_for_audit("Marco Rossi", "session-1")
    c = hash_for_audit("Marco Rossi", "session-2")
    assert a == b
    assert a != c
    assert len(a) == 12
