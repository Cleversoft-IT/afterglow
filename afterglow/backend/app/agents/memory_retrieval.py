"""Memory Retrieval Agent — Vultr /v1/chat/completions/RAG endpoint.

This is the killer Vultr feature: chat + retrieval in a single call against
the per-business Vector Store collection. The output becomes the caller context
injected into the Orchestrator.
"""
from __future__ import annotations

from typing import Optional

from app.integrations import vultr_inference


async def retrieve_customer_context(
    *,
    collection_id: Optional[str],
    phone_e164: str,
    business_domain: str,
) -> str:
    """Ask Vultr RAG for any prior facts about this phone number.

    Returns a short paragraph (or empty string) the Orchestrator can splice into
    its prompt as additional context.
    """
    if not collection_id:
        return ""

    messages = [
        {
            "role": "system",
            "content": (
                "You retrieve facts from a customer-memory store. "
                "Return ONLY the relevant facts about the given phone number, "
                "in 2-4 short sentences. If no facts are found, reply with 'NO_MEMORY'."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Business domain: {business_domain}\n"
                f"Phone number: {phone_e164}\n"
                "Return any prior call facts."
            ),
        },
    ]

    raw = await vultr_inference.chat_completion_rag(messages, collection=collection_id)
    try:
        content = raw["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        return ""

    if content.strip().upper().startswith("NO_MEMORY"):
        return ""
    return content.strip()
