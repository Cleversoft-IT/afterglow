"""Internal action: update the customer row in Postgres for real.

Payload shape (subset; ignored keys are no-ops):
  - `customer_name`: str       → backfill `customer.display_name` (only when
                                  the current row has no name yet, to avoid
                                  clobbering a manually-typed name).
  - `tags`: list[str]          → merge into `customer.tags`, deduped.
  - `allergies`: list[str]     → merge into `profile_facts["allergies"]`.
  - any other scalar/list      → write under `profile_facts[key]`, last-wins.

Result shape:
  {
    "applied": True,
    "tags_added": [...],
    "facts_changed": {"allergies": ["gluten"], ...},
    "mock": False,
    "mutates": False,
    "previous_state": { ... only the keys we changed ... },
  }

The `previous_state` block is the snapshot the undo endpoint replays on the
customer row to restore the prior values. We snapshot ONLY the keys we
actually modified, so undoing one of these never disturbs facts that came
from another call.
"""
from __future__ import annotations

from typing import Any, Iterable

from app.db.models import Customer, ExecutedAction


_RESERVED_KEYS = {"customer_name", "tags"}


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)]


def _merge_dedup(existing: Iterable[str], new: Iterable[str]) -> list[str]:
    seen: dict[str, None] = {}
    for v in list(existing) + list(new):
        if not v:
            continue
        seen.setdefault(v, None)
    return list(seen.keys())


def apply_customer_update(customer: Customer, payload: dict[str, Any]) -> dict[str, Any]:
    """Mutate `customer` in-place; the caller commits the session."""
    previous_state: dict[str, Any] = {}
    tags_added: list[str] = []
    facts_changed: dict[str, Any] = {}

    # 1) Optional display_name backfill (only when empty — never clobber a
    #    name typed by the operator).
    new_name = (payload.get("customer_name") or "").strip()
    if new_name and not customer.display_name:
        previous_state["display_name"] = customer.display_name
        customer.display_name = new_name[:200]

    # 2) Tag merge (deduped).
    incoming_tags = _coerce_list(payload.get("tags"))
    if incoming_tags:
        existing = list(customer.tags or [])
        merged = _merge_dedup(existing, incoming_tags)
        if merged != existing:
            previous_state["tags"] = existing
            customer.tags = merged
            tags_added = [t for t in incoming_tags if t not in existing]

    # 3) Allergies special case — keep as list inside profile_facts. Snapshot
    #    the RAW prior value (None when the key was missing) so revert can
    #    distinguish "wasn't there" from "was an empty list".
    incoming_allergies = _coerce_list(payload.get("allergies"))
    facts = dict(customer.profile_facts or {})
    if incoming_allergies:
        prior_raw = facts.get("allergies")  # None | list | other
        prior_list = _coerce_list(prior_raw)
        merged = _merge_dedup(prior_list, incoming_allergies)
        if merged != prior_list:
            previous_state.setdefault("profile_facts", {})["allergies"] = prior_raw
            facts["allergies"] = merged
            facts_changed["allergies"] = merged

    # 4) Free-form scalar/list keys.
    for key, value in payload.items():
        if key in _RESERVED_KEYS or key == "allergies":
            continue
        if value in (None, "", []):
            continue
        if facts.get(key) == value:
            continue
        # `setdefault` so multiple writes to the same key within one apply
        # do not clobber the original prior value (the FIRST snapshot wins).
        previous_state.setdefault("profile_facts", {}).setdefault(
            key, facts.get(key)  # None if not previously set
        )
        facts[key] = value
        facts_changed[key] = value

    customer.profile_facts = facts

    return {
        "applied": True,
        "tags_added": tags_added,
        "facts_changed": facts_changed,
        "mock": False,
        "mutates": False,
        "previous_state": previous_state,
    }


def revert_customer_update(customer: Customer, action: ExecutedAction) -> dict[str, Any]:
    """Roll back a customer.update_profile by replaying the snapshot.

    Idempotent: re-applying revert on an already-undone action is a no-op
    because the snapshot has been wiped.
    """
    result = action.result or {}
    snapshot = result.get("previous_state") or {}
    if not snapshot:
        return {"reverted": False, "reason": "no_snapshot"}

    if "display_name" in snapshot:
        customer.display_name = snapshot["display_name"]
    if "tags" in snapshot:
        customer.tags = list(snapshot["tags"])
    facts_snapshot = snapshot.get("profile_facts") or {}
    if facts_snapshot:
        facts = dict(customer.profile_facts or {})
        for k, v in facts_snapshot.items():
            if v is None:
                facts.pop(k, None)
            else:
                facts[k] = v
        customer.profile_facts = facts

    return {"reverted": True, "snapshot_keys": sorted(snapshot.keys())}
