"""Vultr Serverless Inference client.

Two endpoints used by Afterglow: `/v1/chat/completions/RAG` for memory-grounded
retrieval (`chat_completion_rag`) and `/v1/vector_store/{id}/items` for chunk
ingestion (`add_vector_item`).

Model: MiniMaxAI/MiniMax-M2.7 — the actual model Vultr serves for /RAG
(verified 2026-05-15: requests for kimi-k2-instruct are transparently swapped
to MiniMax-M2.7, so we call it by its real name to keep audit_log honest).

Stub mode: returns None / fake responses when VULTR_INFERENCE_API_KEY is empty,
so the rest of the pipeline can be exercised offline without poisoning the
real Vector Store state.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx

from app.config import get_settings

settings = get_settings()

_HTTP_TIMEOUT = httpx.Timeout(30.0)


def _is_configured() -> bool:
    return bool(settings.vultr_inference_api_key)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.vultr_inference_base_url,
        headers={
            "Authorization": f"Bearer {settings.vultr_inference_api_key}",
            "Content-Type": "application/json",
        },
        timeout=_HTTP_TIMEOUT,
    )


async def chat_completion_rag(
    messages: list[dict[str, Any]],
    *,
    collection: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> dict[str, Any]:
    """Chat + retrieval in one call — the Vultr killer feature."""
    if not _is_configured() or not collection:
        await asyncio.sleep(0.1)
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "[fake] no memory available — vultr RAG not configured",
                    }
                }
            ]
        }

    payload = {
        "collection": collection,
        "model": model or settings.vultr_inference_model,
        "messages": messages,
        "temperature": temperature,
    }
    async with _client() as client:
        resp = await client.post("/chat/completions/RAG", json=payload)
        resp.raise_for_status()
        return resp.json()


async def add_vector_item(
    collection_id: str,
    *,
    content: str,
    description: str,
) -> Optional[str]:
    """Add an item to a vector store collection. Embedding is auto-computed.

    Returns None in stub mode so the caller does not write a fake item ID
    into the CustomerMemoryChunk audit row.

    Vultr's response shape (verified 2026-05-15):
        {"item": {"id": "<uuid>", "created": "...", "description": "...",
                  "content": "..."}, "usage": {"prompt_tokens": N, ...}}
    """
    if not _is_configured():
        return None

    async with _client() as client:
        resp = await client.post(
            f"/vector_store/{collection_id}/items",
            json={"content": content, "description": description},
        )
        resp.raise_for_status()
        data = resp.json()
        item = data.get("item") or {}
        return item.get("id") or data.get("id") or data.get("item_id")
