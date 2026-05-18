"""Memory Retrieval Agent — Vultr /v1/chat/completions/RAG endpoint
plus a structured fallback that serializes recent SQL rows directly.

Strategy (post round-9):
- Few calls (``customer.total_calls <= 10``) → ``retrieve_structured_history``
  reads ``Call ⨝ ExtractedFields`` for that customer and formats them as
  Markdown. Cheap, exact, and never reads from the shared Vultr collection.
- Many calls (``> 10``) → semantic RAG via Vultr. The killer Vultr feature:
  chat + retrieval in a single call against the collection.
- Demo mode: RAG is **enabled for seed customers** because the lifespan
  task `vector_preseed` populates the collection with one chunk per seed
  call. The orchestrator passes ``preseed_available=True`` for those
  callers so the read path runs even in demo. Write-back stays skipped
  to avoid cross-visitor pollution of the shared collection.

The output of either path becomes the ``prior_facts`` blob the Orchestrator
splices into the Gemini Call Analyzer prompt.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Call, Customer, ExtractedFields
from app.integrations import vultr_inference

logger = logging.getLogger("afterglow")


def _confidence_value(raw: Any) -> float:
    """Extract a scalar confidence from the JSONB column.

    `_coerce_extractions` writes either a plain float or a dict of the form
    `{"value": <float>, "status": "manual_review", ...}` when a field's
    `depends_on` chain is unmet. Older rows that were never re-coerced may
    still carry plain floats, so the reader must handle both shapes.
    """
    if isinstance(raw, dict):
        try:
            return float(raw.get("value", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0

# Vultr's RAG models (kimi-k2, MiniMax-M2) emit reasoning inside <think>...</think>
# blocks before the answer. We strip them so the orchestrator passes clean facts
# (not raw chain-of-thought) to Gemini as prior_facts.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


async def retrieve_structured_history(
    session: AsyncSession,
    customer: Customer,
    *,
    limit: int = 10,
) -> tuple[str, str]:
    """Serialize the last ``limit`` calls for this customer as structured facts.

    Returns ``(text, source)`` where ``source`` is one of:
      - ``"sql"`` — at least one Call row was found.
      - ``"memory_summary"`` — no Call rows, falling back to ``customer.memory_summary``.
      - ``"empty"`` — neither calls nor memory_summary; returns ``""``.

    The query filters strictly by ``customer_id``. Session isolation is already
    guaranteed upstream by ``_resolve_customer`` (clone-on-write in demo),
    so there is no need to plug a ``visibility_filter`` in here.
    """
    stmt = (
        select(Call, ExtractedFields)
        .join(ExtractedFields, ExtractedFields.call_id == Call.id, isouter=True)
        .where(Call.customer_id == customer.id)
        .order_by(Call.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()

    if not rows:
        summary = (customer.memory_summary or "").strip()
        if summary:
            return summary, "memory_summary"
        return "", "empty"

    pieces: list[str] = []
    for idx, (call, extracted) in enumerate(rows, start=1):
        date = (call.completed_at or call.started_at or call.created_at).date().isoformat()
        intent = (extracted.intent if extracted else None) or "unknown"
        sentiment = (extracted.sentiment if extracted else None) or "unknown"
        urgency = (extracted.urgency if extracted else None) or "unknown"
        language = call.detected_language or "unknown"

        salient_fields = _top_fields(extracted)
        briefing = (extracted.briefing_snapshot if extracted else None) or ""

        section_lines = [
            f"## Call {idx} ({date})",
            f"- intent: {intent}",
            f"- sentiment: {sentiment}",
            f"- urgency: {urgency}",
            f"- language: {language}",
        ]
        if salient_fields:
            section_lines.append(f"- fields: {salient_fields}")
        if briefing:
            section_lines.append(f"- briefing: {briefing}")

        pieces.append("\n".join(section_lines))

    return "\n\n".join(pieces), "sql"


async def retrieve_structured_facts(
    session: AsyncSession,
    customer: Customer,
    *,
    limit: int = 10,
    confidence_threshold: float = 0.7,
) -> dict[str, str]:
    """Return the latest known value (above ``confidence_threshold``) for each
    field key the customer has ever produced.

    Used by the orchestrator to evaluate ``prompt_hints`` rules (``when``
    expressions like ``field.urgency == 'emergency'``) BEFORE building the
    analyzer prompt. Limits to ``limit`` calls so the dict stays small and
    only the most-recent value per key wins.
    """
    stmt = (
        select(Call, ExtractedFields)
        .join(ExtractedFields, ExtractedFields.call_id == Call.id, isouter=True)
        .where(Call.customer_id == customer.id)
        .order_by(Call.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()

    out: dict[str, str] = {}
    for _call, extracted in rows:
        if extracted is None or not extracted.fields:
            continue
        confidences = extracted.confidence or {}
        for key, value in extracted.fields.items():
            if key in out:
                continue  # most-recent wins (rows are DESC by created_at)
            conf = _confidence_value(confidences.get(key))
            if conf < confidence_threshold:
                continue
            out[key] = str(value) if value is not None else ""
    return out


def _top_fields(extracted: Optional[ExtractedFields], *, threshold: float = 0.7, max_items: int = 5) -> str:
    """Pick the top extracted fields by confidence and render them compactly."""
    if extracted is None or not extracted.fields:
        return ""
    confidences = extracted.confidence or {}
    ranked = sorted(
        extracted.fields.items(),
        key=lambda kv: -_confidence_value(confidences.get(kv[0])),
    )
    kept: list[str] = []
    for key, value in ranked:
        conf = _confidence_value(confidences.get(key))
        if conf < threshold:
            continue
        kept.append(f"{key}={value!r}")
        if len(kept) >= max_items:
            break
    return ", ".join(kept)


async def retrieve_customer_context(
    *,
    collection_id: Optional[str],
    phone_e164: str,
    domain_hint: str,
    is_demo: bool = False,
    preseed_available: bool = False,
    query: Optional[str] = None,
) -> tuple[str, Optional[int], Optional[int]]:
    """Ask Vultr RAG for facts about this phone number.

    `query` (round-10): when provided, becomes the user message verbatim so
    the agentic `lookup_customer_memory` tool can ask focused questions
    (e.g. "any past complaints about the steak?") instead of the default
    catch-all. The default text matches the legacy pre-fetch behaviour.

    Returns ``(prior_facts, input_tokens, output_tokens)``. The two int fields
    come from Vultr's ``usage`` block (prompt_tokens / completion_tokens) and
    feed `audit_log.input_tokens` / `output_tokens` so the cost-per-call view
    covers Vultr too, not just Gemini. They are ``None`` when the call was
    skipped or when the SDK omitted the usage block.

    Demo semantics (round-9):
    - ``is_demo=True`` + ``preseed_available=False`` → skip the RAG call
      (unknown caller in demo, the shared collection has no chunk for this
      phone; reading would just burn tokens for a NO_MEMORY reply).
    - ``is_demo=True`` + ``preseed_available=True`` → seed customer in demo.
      The lifespan preseed task has populated the collection with this
      customer's prior facts; reading is safe (no cross-visitor leakage,
      the chunks belong to the shared seed dataset) and is what makes
      Vultr visible in the audit log on the very first demo call.
    - ``is_demo=False`` → production single-tenant, always read.

    Failures degrade gracefully to ``("", None, None)`` so the rest of the
    pipeline keeps running.
    """
    if not collection_id:
        return "", None, None
    if is_demo and not preseed_available:
        return "", None, None

    user_query = (query or "Return any prior call facts.").strip() or "Return any prior call facts."
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
                f"Domain: {domain_hint}\n"
                f"Phone number: {phone_e164}\n"
                f"{user_query}"
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
        return "", None, None
    except httpx.HTTPError as exc:
        logger.warning(
            "memory_retrieval: Vultr RAG network error (%s) — proceeding without prior memory.",
            exc,
        )
        return "", None, None

    usage = raw.get("usage") if isinstance(raw, dict) else None
    input_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    output_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None

    try:
        content = raw["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        return "", input_tokens, output_tokens

    content = _THINK_BLOCK_RE.sub("", content).strip()
    if not content or content.upper().startswith("NO_MEMORY"):
        return "", input_tokens, output_tokens
    return content, input_tokens, output_tokens
