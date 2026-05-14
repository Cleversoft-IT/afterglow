"""ADK tools for the Classification Agent.

Classification runs on Vultr `kimi-k2-instruct` via the OpenAI-compatible
chat completions endpoint, but this same shape works when called from ADK.
"""
from __future__ import annotations

from typing import Optional

from google.adk.tools.tool_context import ToolContext


def save_intent_sentiment_language(
    tool_context: ToolContext,
    intent: str,
    sentiment: str,
    language: str,
    urgency: Optional[str] = None,
    rationale: Optional[str] = None,
) -> str:
    """Save the call classification.

    Args:
        intent: One of: booking_new, booking_modify, booking_cancel, info_request,
                emergency, complaint, follow_up, other.
        sentiment: One of: positive, neutral, negative.
        language: ISO-639-1 (it, en, es, fr, ...).
        urgency: low | medium | high | emergency.
        rationale: Why this label (short, for audit).
    """
    tool_context.state["classification_result"] = {
        "intent": intent,
        "sentiment": sentiment,
        "language": language,
        "urgency": urgency or "low",
        "rationale": rationale,
    }
    return "Classification saved."
