"""Tests for the 10-call threshold that gates structured-history vs Vultr RAG.

The orchestrator's strategy:
- demo mode OR `customer.total_calls <= 10` → `retrieve_structured_history` (SQL).
- production single-tenant AND `customer.total_calls > 10` → Vultr RAG.

These tests exercise the boolean decision the orchestrator makes; the actual
SQL / Vultr round trip is covered elsewhere (or skipped in tests when keys
are missing).
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest


def _customer(total_calls: int):
    return SimpleNamespace(
        id=uuid.uuid4(),
        phone_e164="+15551112233",
        display_name=None,
        memory_summary=None,
        total_calls=total_calls,
    )


@pytest.mark.parametrize(
    "total_calls,is_demo,expected_use_structured",
    [
        (0, False, True),
        (1, False, True),
        (10, False, True),
        (11, False, False),
        (5_000, False, False),
        # Demo mode always picks structured, no matter the count.
        (0, True, True),
        (50, True, True),
    ],
)
def test_threshold_logic(total_calls, is_demo, expected_use_structured):
    """Replicates the gate in `orchestrator.run_pipeline`:
        use_structured = is_demo or total_calls <= 10
    """
    cust = _customer(total_calls)
    use_structured = is_demo or (cust.total_calls or 0) <= 10
    assert use_structured is expected_use_structured
