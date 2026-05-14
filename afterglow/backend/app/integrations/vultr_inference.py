"""Vultr Serverless Inference client.

Wraps the OpenAI-compatible API at api.vultrinference.com/v1 and the dedicated
RAG endpoint /v1/chat/completions/RAG (only `kimi-k2-instruct` supports both
tool calling and RAG — see hackathon-docs/12-vultr-deep-dive.md r. 144-198).

Day 1: returns deterministic fakes if no API key is configured, so the pipeline
can be exercised end-to-end. Real calls activate as soon as VULTR_INFERENCE_API_KEY
is set.
"""
from __future__ import annotations

import asyncio
import uuid
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


async def create_vector_collection(name: str) -> str:
    """Create a vector store collection and return its ID."""
    if not _is_configured():
        fake_id = f"local-collection-{uuid.uuid4().hex[:8]}"
        return fake_id

    async with _client() as client:
        resp = await client.post("/vector_store", json={"name": name})
        resp.raise_for_status()
        data = resp.json()
        return data.get("id") or data.get("collection_id")


async def add_vector_item(
    collection_id: str,
    *,
    content: str,
    description: str,
) -> str:
    """Add an item to a vector store collection. Embedding is auto-computed."""
    if not _is_configured():
        return f"local-item-{uuid.uuid4().hex[:8]}"

    async with _client() as client:
        resp = await client.post(
            f"/vector_store/{collection_id}/items",
            json={"content": content, "description": description},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("id") or data.get("item_id")
