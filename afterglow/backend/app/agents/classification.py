"""Classification Agent — runs on Vultr kimi-k2-instruct via OpenAI-compatible API.

This is the second model in Afterglow (Gemini + Kimi-K2) — visible non-decorative
use of Vultr Serverless Inference, requirement for "Best use of Vultr".
"""
from __future__ import annotations

import json
from typing import Any

from app.integrations import vultr_inference

_CLASSIFY_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "save_intent_sentiment_language",
            "description": (
                "Classify the phone call along three axes. Always call this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": [
                            "booking_new",
                            "booking_modify",
                            "booking_cancel",
                            "info_request",
                            "emergency",
                            "complaint",
                            "follow_up",
                            "other",
                        ],
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative"],
                    },
                    "language": {"type": "string"},
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "emergency"],
                    },
                    "rationale": {"type": "string"},
                },
                "required": ["intent", "sentiment", "language", "urgency"],
            },
        },
    }
]

_SYSTEM_PROMPT = (
    "You are a phone-call classifier inside Afterglow. "
    "You receive a transcript and the business domain. "
    "Always call save_intent_sentiment_language with one labeled output."
)


async def classify(transcript_text: str, domain: str) -> dict[str, Any]:
    """Return {intent, sentiment, language, urgency, rationale}.

    Falls back to a deterministic stub when Vultr is not configured.
    """
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Business domain: {domain}\n\n"
                f"Transcript:\n{transcript_text}\n\n"
                "Classify and call the tool."
            ),
        },
    ]

    raw = await vultr_inference.chat_completion(messages, tools=_CLASSIFY_TOOLS)

    try:
        tool_calls = raw["choices"][0]["message"].get("tool_calls") or []
        if tool_calls:
            args = tool_calls[0]["function"]["arguments"]
            return json.loads(args) if isinstance(args, str) else args
    except (KeyError, IndexError, json.JSONDecodeError):
        pass

    # Fallback: simple heuristic
    text_lower = transcript_text.lower()
    intent = "booking_new" if "prenot" in text_lower or "book" in text_lower else "info_request"
    return {
        "intent": intent,
        "sentiment": "neutral",
        "language": "it" if any(w in text_lower for w in ["buonasera", "ciao", "vorrei"]) else "en",
        "urgency": "low",
        "rationale": "fallback heuristic — vultr inference unavailable",
    }
