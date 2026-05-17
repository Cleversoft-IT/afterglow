"""Orchestrator — drives a call through the post-call pipeline.

Design:
    The human handles the call live. The orchestrator runs entirely AFTER the
    call ends. There is one Gemini pass (see call_analyzer.py) that produces
    the structured analysis in a single shot, grounded on the transcript,
    template and prior facts retrieved from the Vultr Vector Store.

Steps:
    1. Speechmatics → transcript (diarization + language auto-detect)
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

from app.agents import action_planner, call_analyzer, memory_retrieval
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

    # 1) Speechmatics — transcribe with diarization + language auto-detect.
    async with audit_step(
        call_id=call.id,
        session_id=call.session_id,
        agent_name="speechmatics",
        step_type="tool_call",
    ):
        transcript = await speechmatics.transcribe_audio(
            Path(call.audio_url) if call.audio_url else Path("/dev/null"),
            domain_hint=template.domain_hint,
        )
    call.raw_transcript = {
        "text": transcript.text,
        "speakers": transcript.speakers,
        "language": transcript.language,
        "raw": transcript.raw,
    }
    call.detected_language = transcript.language
    await session.commit()

    # 1b) Pre-classifier — short-circuit on empty / noise audio so we don't
    # spend Gemini tokens on a transcript that has no semantic content.
    if not _pre_classify(transcript.text):
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="pre_classifier",
            step_type="pre_classify",
            status="skipped",
            payload={"reason": "empty_or_noise_audio", "word_count": len(transcript.text.split())},
        ):
            pass
        call.status = "failed"
        call.error = "empty_or_noise_audio"
        call.completed_at = datetime.now(tz=timezone.utc)
        await session.commit()
        return

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

    # 3) Memory lookup — structured-first, RAG only when the customer has
    # enough history for semantic retrieval to beat a straight serialization.
    # In demo we never read from the shared Vultr collection (cross-visitor
    # leakage); the SQL fallback is already session-isolated upstream.
    #
    # We pull TWO things from prior calls:
    #   (a) `prior_facts` — Markdown-formatted text, spliced into the analyzer
    #       prompt as PRIOR FACTS section.
    #   (b) `prior_structured` — typed dict[field_key, latest_value], used by
    #       the analyzer to evaluate `prompt_hints` rules (`when: field.X is
    #       null`) deterministically BEFORE the LLM call.
    collection_id = settings.vultr_vector_default_collection or None
    total_calls = customer.total_calls or 0
    use_structured = is_demo or total_calls <= 10
    prior_facts = ""
    prior_structured: dict[str, Any] = await memory_retrieval.retrieve_structured_facts(
        session, customer
    )

    if use_structured:
        history_text, source = await memory_retrieval.retrieve_structured_history(
            session, customer
        )
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="memory_lookup",
            step_type="structured_history",
            payload={"count": total_calls, "source": source, "demo": is_demo},
        ):
            prior_facts = history_text
    else:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="memory_lookup",
            step_type="rag_semantic",
            model="vultr-rag",
            payload={"count": total_calls},
        ) as rag_audit:
            prior_facts, rag_input_tokens, rag_output_tokens = (
                await memory_retrieval.retrieve_customer_context(
                    collection_id=collection_id,
                    phone_e164=call.phone_e164,
                    domain_hint=template.domain_hint,
                    is_demo=False,
                )
            )
            rag_audit.input_tokens = rag_input_tokens
            rag_audit.output_tokens = rag_output_tokens

    # 4) Single Gemini structured-output call. Fail-fast: a missing key or a
    # Gemini error bubbles up as CallAnalysisError; the orchestrator catches
    # it below, marks the call as failed, and surfaces the reason to the UI.
    try:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="call_analyzer",
            step_type="llm_call",
            model=settings.gemini_default_model,
        ) as analyzer_audit:
            analysis, analyzer_usage = await call_analyzer.analyze_call(
                transcript_text=transcript.text,
                template_name=template.name,
                fields_schema=template.fields_schema,
                action_types=template.action_types,
                prompt_hints=template.prompt_hints,
                prior_structured=prior_structured,
                domain_hint=template.domain_hint,
                prior_facts=prior_facts,
            )
            analyzer_audit.input_tokens = analyzer_usage.input_tokens
            analyzer_audit.output_tokens = analyzer_usage.output_tokens
    except call_analyzer.CallAnalysisError as exc:
        logger.warning("call_analyzer failed for call %s: %s", call.id, exc)
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="call_analyzer",
            step_type="llm_call",
            status="error",
            payload={"reason": str(exc)},
        ):
            pass
        call.status = "failed"
        call.error = f"call_analyzer: {exc}"
        call.completed_at = datetime.now(tz=timezone.utc)
        await session.commit()
        return

    # 5) Persist extracted fields. briefing_snapshot freezes the briefing
    # generated for *this* call so future structured_history lookups can show
    # the same operator-visible view that was used at call time.
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
            briefing_snapshot=analysis.next_call_briefing,
        )
    )

    # 6a) Agentic action planning — Gemini ADK with the template's auto-mode
    # action_types exposed as typed tools (Pydantic models built from each
    # action's payload_schema). The tools only *record* requested actions;
    # the deterministic executor is the single place where they actually
    # run. Fail-fast: an ADK error becomes a failed call (no fallback).
    try:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="action_planner",
            step_type="agent_loop",
            model=settings.gemini_default_model,
        ) as planner_audit:
            plan, planner_mode = await action_planner.plan_actions(
                analysis=analysis,
                template=template,
                customer=customer,
                transcript_text=transcript.text,
            )
            planner_audit.payload = {"mode": planner_mode, "count": len(plan)}
    except action_planner.ActionPlannerError as exc:
        logger.warning("action_planner failed for call %s: %s", call.id, exc)
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="action_planner",
            step_type="agent_loop",
            status="error",
            payload={"reason": str(exc)},
        ):
            pass
        call.status = "failed"
        call.error = f"action_planner: {exc}"
        call.completed_at = datetime.now(tz=timezone.utc)
        await session.commit()
        return

    # 6b) Deterministic action executor — the only place where MOCK_REGISTRY
    # is invoked. Hallucination rejection + execution_mode read from the
    # template stay here so the agentic planner cannot bypass them.
    async with audit_step(
        call_id=call.id,
        session_id=call.session_id,
        agent_name="action_executor",
        step_type="action_exec",
    ):
        await execute_planned_actions(
            session, call=call, customer=customer, template=template, plan=plan
        )

    # 6c) display_name backfill — if we just learned the caller's name and
    # the Customer row has none yet, persist it so the next ring of the
    # dialer shows "Mark Ross" instead of just the phone number.
    _backfill_display_name(customer, template.fields_schema, analysis)

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


_MIN_TRANSCRIPT_WORDS = 8


# Field keys we treat as "the caller's name" when backfilling display_name.
# Templates name the field differently per domain (customer_name, patient_name,
# guest_name, …) so we pattern-match on the `_name` suffix plus a small
# alias list.
_NAME_FIELD_KEYS = ("full_name", "caller_name")


def _is_name_field(key: str) -> bool:
    if key in _NAME_FIELD_KEYS:
        return True
    return key.endswith("_name")


def _backfill_display_name(
    customer: Customer,
    fields_schema: list[dict[str, Any]],
    analysis: "call_analyzer.CallAnalysis",
) -> None:
    """Set `customer.display_name` when we extract the caller's name and the
    Customer row does not have one yet.

    Idempotent: if `display_name` is already set, do nothing.
    """
    if customer.display_name:
        return

    for extraction in analysis.fields:
        if not _is_name_field(extraction.key):
            continue
        value = (extraction.value or "").strip()
        if not value:
            continue
        customer.display_name = value[:200]
        return


def _pre_classify(transcript_text: str) -> bool:
    """Return False if the transcript is too short / empty to analyze.

    Speechmatics happily transcribes silence into an empty string. Running the
    full Gemini pipeline on those is wasted budget; we instead fail fast and
    surface the reason in the audit trail.
    """
    if not transcript_text or not transcript_text.strip():
        return False
    if len(transcript_text.split()) < _MIN_TRANSCRIPT_WORDS:
        return False
    return True


def _coerce_extractions(
    extractions: list[call_analyzer.FieldExtraction],
    fields_schema: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Turn the LLM's typed list into three keyed dicts, cast values, and
    flag fields whose `depends_on` chain is not satisfied.

    A field is marked `manual_review` when any of its `depends_on` keys is
    either missing from the extractions or below the dependency's
    `confidence_threshold` (defaulting to 0.0 — i.e. presence alone is
    enough when no threshold is configured). The flag lives inside
    `confidence_dict` as a sentinel value
    `{"value": <float>, "status": "manual_review", "reason": ...}` so the UI
    can render a warning without losing the LLM's confidence.
    """
    type_by_key = {f["key"]: f.get("type", "string") for f in fields_schema}
    field_def_by_key = {f["key"]: f for f in fields_schema}

    fields: dict[str, Any] = {}
    confidence: dict[str, Any] = {}
    evidence: dict[str, str] = {}

    extracted_by_key = {item.key: item for item in extractions}

    for item in extractions:
        ftype = type_by_key.get(item.key, "string")
        fields[item.key] = _cast_value(item.value, ftype)
        confidence[item.key] = item.confidence
        evidence[item.key] = item.evidence

    # Second pass: enforce depends_on.
    for item in extractions:
        field_def = field_def_by_key.get(item.key) or {}
        deps: list[str] = field_def.get("depends_on") or []
        if not deps:
            continue
        unmet: list[str] = []
        for dep_key in deps:
            dep_item = extracted_by_key.get(dep_key)
            if dep_item is None:
                unmet.append(f"{dep_key}:missing")
                continue
            dep_def = field_def_by_key.get(dep_key) or {}
            dep_threshold = dep_def.get("confidence_threshold") or 0.0
            if dep_item.confidence < dep_threshold:
                unmet.append(f"{dep_key}:low_confidence")
        if unmet:
            confidence[item.key] = {
                "value": item.confidence,
                "status": "manual_review",
                "reason": "depends_on_unmet",
                "unmet": unmet,
            }

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
            call_id=call.id,
            session_id=call.session_id,
            agent_name="memory_updater",
            step_type="tool_call",
            model="vultr-vector-store",
            status="skipped",
            payload={
                "reason": "demo_sandbox_vector_store_disabled",
                "human_label": "Demo sandbox: vector store disabled",
            },
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
    detected_language = (classification.get("language") or "en").lower()

    # Bilingual chunk: if the call was not already in English, ask Gemini for
    # a short EN summary so the vector index is searchable cross-language.
    # Fail-fast: any error logs an audit row but still pushes the native chunk.
    briefing_en: Optional[str] = None
    if detected_language and detected_language != "en":
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="memory_summarizer_bilingual",
            step_type="llm_call",
            model=settings.gemini_default_model,
        ) as bilingual_audit:
            try:
                briefing_en, bilingual_usage = await _summarize_to_english(briefing)
                bilingual_audit.payload = {"chars": len(briefing_en or "")}
                bilingual_audit.input_tokens = bilingual_usage.input_tokens
                bilingual_audit.output_tokens = bilingual_usage.output_tokens
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "memory_summarizer_bilingual: failed (%s) — native-only chunk",
                    exc,
                )
                bilingual_audit.status = "degraded"
                bilingual_audit.payload = {"reason": str(exc)}

    bilingual_tail = f"\n\n[EN] {briefing_en}" if briefing_en else ""
    chunk_content = (
        f"Customer {display_label} ({customer.phone_e164}) called "
        f"the {template.domain_hint} on {call_date.isoformat()}. "
        f"Intent: {classification.get('intent', 'unknown')}. "
        f"Sentiment: {classification.get('sentiment', 'unknown')}. "
        f"Urgency: {classification.get('urgency', 'unknown')}. "
        f"Briefing: {briefing}{bilingual_tail}"
    )

    item_id: Optional[str] = None
    try:
        async with audit_step(
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
                summary=briefing + (f"\n\n[EN] {briefing_en}" if briefing_en else ""),
                chunk_metadata={
                    **classification,
                    "phone_e164": customer.phone_e164,
                    "customer_id": str(customer.id),
                    "language": detected_language,
                    "briefing_en": briefing_en,
                },
                session_id=call.session_id,
            )
        )


async def _summarize_to_english(briefing: str) -> tuple[str, call_analyzer.TokenUsage]:
    """Translate / summarize the briefing to a one-sentence English line.

    Used to populate the bilingual chunk for the Vultr Vector Store: native
    + EN, so semantic retrieval works across the operator's spoken language
    and the embedding language. Capped at ~80 tokens by the system instruction;
    Gemini does this for free on the Flash tier.

    Raises on missing key / SDK error / empty response. The caller catches
    and degrades to native-only chunk.
    """
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY not set")

    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.google_api_key)
    resp = await client.aio.models.generate_content(
        model=settings.gemini_default_model,
        contents=briefing,
        config=genai_types.GenerateContentConfig(
            system_instruction=(
                "Translate the following next-call briefing into one short "
                "English sentence (max 30 words). Output the sentence only, "
                "no prefix."
            ),
            temperature=0.1,
            max_output_tokens=120,
        ),
    )
    out = (resp.text or "").strip()
    if not out:
        raise RuntimeError("empty response")
    return out, call_analyzer.TokenUsage.from_gemini(resp)
