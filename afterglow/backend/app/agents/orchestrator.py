"""Orchestrator — drives a call through the post-call pipeline.

Design:
    The human handles the call live. The orchestrator runs entirely AFTER the
    call ends. There is one Gemini pass (see call_analyzer.py) that produces
    the structured analysis in a single shot, grounded on the transcript,
    template and prior facts retrieved from the Vultr Vector Store.

Steps:
    1. Speechmatics → transcript (stubbed in DEMO_MODE or until day-2 wiring)
    2. Customer match by phone (global, single-tenant)
    3. Vultr Vector Store RAG pre-fetch → prior_facts text
    4. Gemini Call Analyzer → CallAnalysis (single structured-output call)
    5. Persist ExtractedFields
    6. Deterministic Action Executor
    7. Memory write-back: customer.memory_summary + push to Vector Store
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import call_analyzer, memory_retrieval
from app.audit.logger import audit_step
from app.config import get_settings
from app.db.models import (
    Call,
    Customer,
    CustomerMemoryChunk,
    ExtractedFields,
    Template,
)
from app.executors.action_executor import execute_planned_actions
from app.integrations import speechmatics, vultr_inference

logger = logging.getLogger("afterglow")
settings = get_settings()


async def run_pipeline(session: AsyncSession, call_id: uuid.UUID) -> None:
    """Drive a call through the full pipeline.

    Idempotent: a second invocation on the same call_id while the first is
    still running (or has already completed) is a no-op. Prevents double
    booking on double-clicks of the operator's blue button.
    """
    call: Optional[Call] = (
        await session.execute(select(Call).where(Call.id == call_id))
    ).scalar_one_or_none()
    if call is None:
        return
    if call.status in ("transcribing", "analyzing", "completed"):
        logger.info("orchestrator: call %s already in status %s — skipping", call_id, call.status)
        return

    call.status = "transcribing"
    call.started_at = datetime.now(tz=timezone.utc)
    await session.commit()

    is_demo = call.session_id is not None

    template = (
        await session.execute(select(Template).where(Template.id == call.template_id))
    ).scalar_one()

    # 1) Speechmatics — transcribe (stub when DEMO_MODE or no key).
    async with audit_step(
        session,
        call_id=call.id,
        session_id=call.session_id,
        agent_name="speechmatics",
        step_type="tool_call",
    ):
        transcript = await speechmatics.transcribe_audio(
            Path(call.audio_url) if call.audio_url else Path("/dev/null"),
            custom_dictionary=template.custom_dictionary,
            domain_hint=template.domain_hint,
        )
    call.raw_transcript = {
        "text": transcript.text,
        "speakers": transcript.speakers,
        "language": transcript.language,
        "raw": transcript.raw,
    }
    call.detected_language = transcript.language
    call.status = "analyzing"
    await session.commit()

    # 2) Customer match — production single-tenant writes directly on the
    # shared row; demo mode clones the seed (or makes a fresh session-scoped
    # row) so concurrent visitors do not stomp on each other's memory.
    customer = await _resolve_customer(
        session,
        phone_e164=call.phone_e164,
        session_id=call.session_id,
        preferred_language=transcript.language or "it",
    )
    call.customer_id = customer.id

    # 3) RAG pre-fetch — semantic lookup of past calls from this number.
    # Skipped in demo mode: visitors are isolated, so we never read from the
    # shared Vultr collection. The audit row keeps the wiring visible.
    collection_id = settings.vultr_vector_default_collection or None
    prior_facts = ""
    async with audit_step(
        session,
        call_id=call.id,
        session_id=call.session_id,
        agent_name="memory_lookup",
        step_type="tool_call",
        model="vultr-rag",
        status="skipped" if is_demo else "success",
        payload={"reason": "demo_session"} if is_demo else None,
    ):
        prior_facts = await memory_retrieval.retrieve_customer_context(
            collection_id=collection_id,
            phone_e164=call.phone_e164,
            domain_hint=template.domain_hint,
            is_demo=is_demo,
        )

    # 4) Single Gemini structured-output call.
    async with audit_step(
        session,
        call_id=call.id,
        session_id=call.session_id,
        agent_name="call_analyzer",
        step_type="llm_call",
        model=settings.gemini_default_model,
    ):
        analysis = await call_analyzer.analyze_call(
            transcript_text=transcript.text,
            template_name=template.name,
            fields_schema=template.fields_schema,
            action_types=template.action_types,
            prompt_hints=template.prompt_hints,
            domain_hint=template.domain_hint,
            prior_facts=prior_facts,
        )

    # 5) Persist extracted fields.
    fields_dict, confidence_dict, evidence_dict = _coerce_extractions(
        analysis.fields, template.fields_schema
    )
    session.add(
        ExtractedFields(
            call_id=call.id,
            fields=fields_dict,
            confidence=confidence_dict,
            evidence=evidence_dict,
            intent=analysis.intent,
            sentiment=analysis.sentiment,
            urgency=analysis.urgency,
        )
    )

    # 6) Deterministic action executor.
    plan = []
    for a in analysis.planned_actions:
        entry = a.model_dump()
        try:
            entry["payload"] = json.loads(entry.pop("payload_json") or "{}")
        except json.JSONDecodeError:
            entry["payload"] = {}
            entry.pop("payload_json", None)
        plan.append(entry)
    async with audit_step(
        session,
        call_id=call.id,
        session_id=call.session_id,
        agent_name="action_executor",
        step_type="action_exec",
    ):
        await execute_planned_actions(
            session, call=call, customer=customer, template=template, plan=plan
        )

    # 7) Memory write-back. The briefing is the only AI-authored summary the
    # operator will read on the next call's caller card.
    await _persist_memory(
        session,
        call=call,
        customer=customer,
        template=template,
        collection_id=collection_id,
        briefing=analysis.next_call_briefing,
        classification={
            "intent": analysis.intent,
            "sentiment": analysis.sentiment,
            "language": analysis.language,
            "urgency": analysis.urgency,
        },
    )

    call.status = "completed"
    call.completed_at = datetime.now(tz=timezone.utc)
    await session.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_extractions(
    extractions: list[call_analyzer.FieldExtraction],
    fields_schema: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, float], dict[str, str]]:
    """Turn the LLM's typed list into three keyed dicts and cast values."""
    type_by_key = {f["key"]: f.get("type", "string") for f in fields_schema}

    fields: dict[str, Any] = {}
    confidence: dict[str, float] = {}
    evidence: dict[str, str] = {}

    for item in extractions:
        ftype = type_by_key.get(item.key, "string")
        fields[item.key] = _cast_value(item.value, ftype)
        confidence[item.key] = item.confidence
        evidence[item.key] = item.evidence

    return fields, confidence, evidence


def _cast_value(raw: str, ftype: str) -> Any:
    if raw is None:
        return None
    if ftype == "integer":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw
    if ftype == "boolean":
        return raw.strip().lower() in ("true", "yes", "sì", "si", "1")
    if ftype == "string_list":
        s = raw.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in s.split(",") if item.strip()]
    return raw


async def _resolve_customer(
    session: AsyncSession,
    *,
    phone_e164: str,
    session_id: Optional[uuid.UUID],
    preferred_language: str,
) -> Customer:
    """Get-or-create the Customer row for a call.

    - Production (`session_id IS None`): match the seed customer, create a new
      one if the phone is unknown. This is the legacy single-tenant path.
    - Demo (`session_id IS NOT None`):
        1. look up an existing per-session clone for this phone
        2. otherwise, if a seed exists for this phone, clone its memory and
           tag the clone with `session_id` (clone-on-write)
        3. otherwise create a fresh customer scoped to the session
      The seed row is never mutated in demo mode, so two visitors who call
      Marco Rossi on +393331112233 each get their own divergent timeline.
    """
    if session_id is not None:
        clone = (
            await session.execute(
                select(Customer).where(
                    Customer.phone_e164 == phone_e164,
                    Customer.session_id == session_id,
                )
            )
        ).scalar_one_or_none()
        if clone is not None:
            return clone

        seed = (
            await session.execute(
                select(Customer).where(
                    Customer.phone_e164 == phone_e164,
                    Customer.is_seed.is_(True),
                )
            )
        ).scalar_one_or_none()
        if seed is not None:
            clone = Customer(
                id=uuid.uuid4(),
                phone_e164=seed.phone_e164,
                display_name=seed.display_name,
                preferred_language=seed.preferred_language,
                tags=list(seed.tags or []),
                memory_summary=seed.memory_summary,
                total_calls=seed.total_calls or 0,
                last_call_at=seed.last_call_at,
                session_id=session_id,
                is_seed=False,
            )
            session.add(clone)
            await session.flush()
            return clone

        fresh = Customer(
            id=uuid.uuid4(),
            phone_e164=phone_e164,
            preferred_language=preferred_language,
            total_calls=0,
            session_id=session_id,
        )
        session.add(fresh)
        await session.flush()
        return fresh

    existing = (
        await session.execute(
            select(Customer).where(
                Customer.phone_e164 == phone_e164,
                Customer.session_id.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    fresh = Customer(
        id=uuid.uuid4(),
        phone_e164=phone_e164,
        preferred_language=preferred_language,
        total_calls=0,
    )
    session.add(fresh)
    await session.flush()
    return fresh


async def _persist_memory(
    session: AsyncSession,
    *,
    call: Call,
    customer: Customer,
    template: Template,
    collection_id: Optional[str],
    briefing: str,
    classification: dict[str, Any],
) -> None:
    """Save the next-call briefing on Postgres + push a chunk to Vector Store.

    Postgres is the source of truth and is updated regardless of demo / prod.
    The Vultr Vector Store push is skipped in demo mode so concurrent visitors
    cannot pollute the shared collection.
    """
    customer.memory_summary = briefing
    customer.total_calls = (customer.total_calls or 0) + 1
    customer.last_call_at = datetime.now(tz=timezone.utc)

    is_demo = call.session_id is not None
    if is_demo:
        async with audit_step(
            session,
            call_id=call.id,
            session_id=call.session_id,
            agent_name="memory_updater",
            step_type="tool_call",
            model="vultr-vector-store",
            status="skipped",
            payload={"reason": "demo_session"},
        ):
            pass
        return

    if not collection_id:
        logger.info(
            "memory_updater: VULTR_VECTOR_DEFAULT_COLLECTION not set — "
            "Postgres briefing kept, vector indexing skipped."
        )
        return

    # Make the chunk content phone-queryable. The RAG retrieval asks
    # "facts about phone {e164}", so the phone number MUST appear inside the
    # indexed content (Vultr embeds `content`; `description` is metadata).
    call_date = (call.completed_at or call.started_at or datetime.now(tz=timezone.utc)).date()
    display_label = customer.display_name or customer.phone_e164
    chunk_content = (
        f"Customer {display_label} ({customer.phone_e164}) called "
        f"the {template.domain_hint} on {call_date.isoformat()}. "
        f"Intent: {classification.get('intent', 'unknown')}. "
        f"Sentiment: {classification.get('sentiment', 'unknown')}. "
        f"Urgency: {classification.get('urgency', 'unknown')}. "
        f"Briefing: {briefing}"
    )

    item_id: Optional[str] = None
    try:
        async with audit_step(
            session,
            call_id=call.id,
            session_id=call.session_id,
            agent_name="memory_updater",
            step_type="tool_call",
            model="vultr-vector-store",
        ):
            item_id = await vultr_inference.add_vector_item(
                collection_id,
                content=chunk_content,
                description=f"call_{call.id} phone_{customer.phone_e164}",
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "memory_updater: Vultr Vector Store push failed (%s) — "
            "Postgres briefing kept, vector indexing skipped.",
            exc,
        )

    if item_id is not None:
        session.add(
            CustomerMemoryChunk(
                id=uuid.uuid4(),
                customer_id=customer.id,
                call_id=call.id,
                vultr_collection_id=collection_id,
                vultr_item_id=item_id,
                summary=briefing,
                chunk_metadata={
                    **classification,
                    "phone_e164": customer.phone_e164,
                    "customer_id": str(customer.id),
                },
                session_id=call.session_id,
            )
        )
