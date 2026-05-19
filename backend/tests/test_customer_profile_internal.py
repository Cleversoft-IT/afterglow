"""Tests for the internal_real customer.update_profile handler."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.integrations.internal.customer_profile import (
    apply_customer_update,
    revert_customer_update,
)


def _customer(**overrides):
    base = dict(
        id=uuid.uuid4(),
        display_name=None,
        tags=[],
        profile_facts={},
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_apply_backfills_display_name_when_empty():
    cust = _customer()
    result = apply_customer_update(cust, {"customer_name": "Mark Ross"})
    assert cust.display_name == "Mark Ross"
    assert result["applied"] is True
    # `mock` / `mutates` are no longer stamped by the handler; the executor
    # stamps them from the action catalog in _run_internal_real.
    assert "mock" not in result
    assert "mutates" not in result
    assert result["previous_state"]["display_name"] is None


def test_apply_does_not_overwrite_existing_name():
    cust = _customer(display_name="Manually Typed")
    result = apply_customer_update(cust, {"customer_name": "Mark Ross"})
    assert cust.display_name == "Manually Typed"
    assert "display_name" not in result["previous_state"]


def test_apply_merges_tags_dedup():
    cust = _customer(tags=["repeat"])
    result = apply_customer_update(cust, {"tags": ["repeat", "vip"]})
    assert sorted(cust.tags) == ["repeat", "vip"]
    assert result["tags_added"] == ["vip"]
    assert result["previous_state"]["tags"] == ["repeat"]


def test_apply_writes_allergies_into_profile_facts():
    cust = _customer()
    result = apply_customer_update(cust, {"allergies": ["gluten"]})
    assert cust.profile_facts == {"allergies": ["gluten"]}
    assert result["facts_changed"]["allergies"] == ["gluten"]


def test_apply_extra_keys_land_in_profile_facts():
    cust = _customer()
    apply_customer_update(
        cust,
        {"seating_preference": "window table", "occasion": "anniversary"},
    )
    assert cust.profile_facts["seating_preference"] == "window table"
    assert cust.profile_facts["occasion"] == "anniversary"


def test_revert_restores_previous_state():
    cust = _customer(display_name=None, tags=["repeat"], profile_facts={})
    res = apply_customer_update(
        cust,
        {
            "customer_name": "Mark Ross",
            "tags": ["vip"],
            "allergies": ["gluten"],
            "seating_preference": "window table",
        },
    )
    assert cust.display_name == "Mark Ross"
    assert sorted(cust.tags) == ["repeat", "vip"]
    assert cust.profile_facts == {
        "allergies": ["gluten"],
        "seating_preference": "window table",
    }

    action = SimpleNamespace(result=res)
    revert_summary = revert_customer_update(cust, action)

    assert revert_summary["reverted"] is True
    assert cust.display_name is None
    assert cust.tags == ["repeat"]
    assert cust.profile_facts == {}


def test_revert_idempotent_when_no_snapshot():
    cust = _customer(display_name="Untouched")
    action = SimpleNamespace(result={})
    out = revert_customer_update(cust, action)
    assert out["reverted"] is False
    assert cust.display_name == "Untouched"
