"""`lookup_customer_memory` tool — RAG-backed memory lookup.

The agentic pipeline replaces the legacy pre-fetch of `prior_facts` with an
on-demand tool. The agent decides WHEN it needs prior context (it may not!)
and crafts a SPECIFIC query (not the catch-all default). The same Vultr
collection and demo gating used by the orchestrator pre-fetch are reused.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from app.agents import memory_retrieval
from app.agents.tools.turn import bump_turn

logger = logging.getLogger("afterglow")


def make_memory_tool(
    *,
    phone_e164: str,
    domain_hint: str,
    collection_id: Optional[str],
    is_demo: bool,
    preseed_available: bool,
) -> Callable[..., Any]:
    """Build the `lookup_customer_memory` callable for this call's context.

    The closure captures everything the RAG client needs except the query
    text, which the model fills in at call-time.
    """

    async def lookup_customer_memory(
        query: str, tool_context: Any = None
    ) -> dict[str, Any]:
        """Search the customer-memory store for facts about this caller.

        Use a SPECIFIC question, not "any facts". Examples:
          - "Has this caller complained about timing in past calls?"
          - "What is this caller's preferred booking time?"
          - "Has this caller asked about gluten-free options before?"

        Returns:
          - facts: short paragraph of prior facts, or empty string if none
          - source: "rag" when the store answered, "empty" when skipped/empty
          - input_tokens / output_tokens: Vultr usage block, may be None
        """
        bump_turn(tool_context)
        try:
            facts, in_tok, out_tok = await memory_retrieval.retrieve_customer_context(
                collection_id=collection_id,
                phone_e164=phone_e164,
                domain_hint=domain_hint,
                is_demo=is_demo,
                preseed_available=preseed_available,
                query=query,
            )
        except Exception as exc:  # noqa: BLE001
            # No-raise contract: a network/SDK error must not crash the
            # agent loop. Degrade to empty facts with the error surfaced.
            logger.warning("memory_tool: lookup failed (%s)", exc)
            return {
                "facts": "",
                "source": "empty",
                "input_tokens": None,
                "output_tokens": None,
                "error": str(exc)[:200],
            }
        return {
            "facts": facts or "",
            "source": "rag" if facts else "empty",
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }

    lookup_customer_memory.__annotations__ = {
        "query": str,
        "tool_context": Any,
        "return": dict,
    }
    return lookup_customer_memory
