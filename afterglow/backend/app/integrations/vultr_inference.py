"""Vultr Serverless Inference client.

Wraps the OpenAI-compatible API at api.vultrinference.com/v1 and the dedicated
RAG endpoint /v1/chat/completions/RAG.

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


async def chat_completion(
    messages: list[dict[str, Any]],
    *,
    tools: Optional[list[dict[str, Any]]] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Plain chat completion (OpenAI-compatible)."""
    if not _is_configured():
        await asyncio.sleep(0.1)
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "[fake] vultr inference not configured",
                    }
                }
            ]
        }

    payload: dict[str, Any] = {
        "model": model or settings.vultr_inference_model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with _client() as client:
        resp = await client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()


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


async def create_vector_collection(name: str) -> Optional[str]:
    """Create a vector store collection and return its ID.

    Returns None in stub mode (no API key) so callers do NOT persist a fake
    collection_id on the Business row. If a fake ID were persisted, the
    `if not business.vultr_collection_id` guard would later treat the fake
    as real and skip creating the real collection once the key arrives —
    poisoning the Vector Store flow permanently.

    Vultr's response shape (verified 2026-05-15):
        {"collection": {"id": "...", "name": "...", "created": "..."}}
    """
    if not _is_configured():
        return None

    async with _client() as client:
        resp = await client.post("/vector_store", json={"name": name})
        resp.raise_for_status()
        data = resp.json()
        collection = data.get("collection") or {}
        return collection.get("id") or data.get("id") or data.get("collection_id")


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
