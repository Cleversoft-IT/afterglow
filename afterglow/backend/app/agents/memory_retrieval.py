"""Memory Retrieval Agent — Vultr /v1/chat/completions/RAG endpoint.

This is the killer Vultr feature: chat + retrieval in a single call against
the per-business Vector Store collection. The output becomes the caller context
injected into the Orchestrator.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from app.integrations import vultr_inference

logger = logging.getLogger("afterglow")

# Vultr's RAG models (kimi-k2, MiniMax-M2) emit reasoning inside <think>...</think>
# blocks before the answer. We strip them so the orchestrator passes clean facts
# (not raw chain-of-thought) to Gemini as prior_facts.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


async def retrieve_customer_context(
    *,
    collection_id: Optional[str],
    phone_e164: str,
    business_domain: str,
) -> str:
    """Ask Vultr RAG for any prior facts about this phone number.

    Returns a short paragraph (or empty string) the Orchestrator can splice into
    its prompt as additional context. Failures degrade gracefully to "" so the
    rest of the pipeline keeps running.
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

    try:
        raw = await vultr_inference.chat_completion_rag(
            messages, collection=collection_id
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "memory_retrieval: Vultr RAG returned %s — proceeding without prior memory.",
            exc.response.status_code,
        )
        return ""
    except httpx.HTTPError as exc:
        logger.warning(
            "memory_retrieval: Vultr RAG network error (%s) — proceeding without prior memory.",
            exc,
        )
        return ""

    try:
        content = raw["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        return ""

    content = _THINK_BLOCK_RE.sub("", content).strip()
    if not content or content.upper().startswith("NO_MEMORY"):
        return ""
    return content
