"""ADK tool for Memory Updater — writes a summary chunk to session state.

The orchestrator then ships this chunk to Vultr Vector Store + Postgres.
"""
from __future__ import annotations

from typing import Optional

from google.adk.tools.tool_context import ToolContext


def save_memory_chunk(
    tool_context: ToolContext,
    summary: str,
    tags: list[str],
    intent: str,
    language: str,
    party_size: Optional[int] = None,
    booking_date: Optional[str] = None,
) -> str:
    """Save a short memory chunk to attach to the customer profile.

    The summary should be 2-4 sentences in English (canonical store language)
    and weave in the most important fields so future RAG retrieval finds it.
    """
    tool_context.state["memory_chunk"] = {
        "summary": summary,
        "tags": tags,
        "metadata": {
            "intent": intent,
            "language": language,
            "party_size": party_size,
            "booking_date": booking_date,
        },
    }
    return "Memory chunk saved."
