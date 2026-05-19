"""Deterministic evaluator for `PromptHintRule.when` mini-expressions.

The grammar is intentionally tiny so a regex is enough — we never want a
user-supplied `when` string to grow into a Python eval surface. Accepted forms:

    always
    field.<snake_case_key> == '<value>'
    field.<snake_case_key> == "<value>"
    field.<snake_case_key> is null
    field.<snake_case_key> is not null

The evaluator runs against the caller's PRIOR STRUCTURED FIELDS — the
typed `dict[str, Any]` returned by `memory_retrieval.retrieve_structured_history`
— not the raw transcript text. This is what makes the rules safe to
evaluate before the analyzer prompt is built: we only look at values the
operator has already verified in past calls.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.schemas.templates import PromptHintRule

logger = logging.getLogger("afterglow")


_RULE_EQ = re.compile(
    r"^\s*field\.([a-z][a-z0-9_]*)\s*==\s*['\"](.*?)['\"]\s*$"
)
_RULE_IS_NULL = re.compile(r"^\s*field\.([a-z][a-z0-9_]*)\s+is\s+null\s*$")
_RULE_IS_NOT_NULL = re.compile(
    r"^\s*field\.([a-z][a-z0-9_]*)\s+is\s+not\s+null\s*$"
)


def _matches(when: str, prior_structured: dict[str, Any]) -> bool:
    when_lc = (when or "").strip().lower()
    if not when_lc or when_lc == "always":
        return True

    m = _RULE_EQ.match(when)
    if m:
        key, expected = m.group(1), m.group(2)
        actual = prior_structured.get(key)
        if actual is None:
            return False
        return str(actual).lower() == expected.lower()

    m = _RULE_IS_NULL.match(when)
    if m:
        return prior_structured.get(m.group(1)) is None

    m = _RULE_IS_NOT_NULL.match(when)
    if m:
        return prior_structured.get(m.group(1)) is not None

    logger.warning(
        "prompt_hint_eval: unrecognised `when` expression %r — skipping rule.",
        when,
    )
    return False


def applicable_hints(
    rules: list[dict[str, Any]] | list[PromptHintRule] | None,
    prior_structured: dict[str, Any] | None,
) -> list[str]:
    """Return the ordered list of `then` strings whose `when` matches.

    Accepts both raw dicts (as they come out of `Template.prompt_hints` JSONB)
    and Pydantic `PromptHintRule` instances. Returns an empty list when no
    rules apply or when `rules` is None.
    """
    if not rules:
        return []
    state = prior_structured or {}
    out: list[str] = []
    for r in rules:
        when = r.get("when", "always") if isinstance(r, dict) else r.when
        then = r.get("then", "") if isinstance(r, dict) else r.then
        if not then:
            continue
        if _matches(when, state):
            out.append(then)
    return out
