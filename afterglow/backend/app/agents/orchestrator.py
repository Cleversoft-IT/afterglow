"""Orchestrator — drives a call through the agentic post-call pipeline.

The human handles the call live. The orchestrator runs entirely AFTER the
call ends. As of round-10 the analysis stage is a single multi-turn ADK
agent (`agents/call_agent.py`) that fuses the previous analyzer + planner +
deterministic executor into one loop where every action is a tool the model
can invoke with self-correction on failures.

Steps:
    1. Speechmatics → transcript (diarization + language auto-detect)
    2. Pre-classifier — short-circuit on empty / noise audio
    3. Customer match by phone (single-tenant prod / clone-on-write in demo)
    4. retrieve_structured_facts — fast SQL pass for prompt_hints evaluation
    5. **run_call_agent** — agentic loop (multi-turn ADK)
         Tools: lookup_customer_memory, search_transcript, read_transcript_segment,
                flag_for_review, <action_key>... (executed inline), finalize_call
    6. Map completion_reason → call.status (completed / needs_review / failed)
    7. Persist ExtractedFields (only when completion_reason="finalize")
    8. display_name backfill
    9. Memory write-back (only when status="completed")

**No-raise contract**: `run_call_agent` never raises for normal ADK/tool/model
errors — it returns `completion_reason="error"`. `run_pipeline` translates
that into `Call.status="failed"` + `Call.error`, commits, and returns. The
`_run_pipeline_isolated` rollback path (`api/calls.py:222`) is left as a
safety net for catastrophic uncaught exceptions only.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import call_agent, call_analyzer, memory_retrieval
from app.audit.logger import audit_step
from app.config import get_settings
from app.db.models import (
    Call,
    Customer,
    CustomerMemoryChunk,
    ExtractedFields,
    Template,
)
from app.integrations import speechmatics, vultr_inference

logger = logging.getLogger("afterglow")
settings = get_settings()


async def run_pipeline(session: AsyncSession, call_id: uuid.UUID) -> None:
    """Drive a call through the full pipeline.

    Idempotent: a second invocation on the same call_id while the first is
    still running (or has already terminated) is a no-op. Includes
    `needs_review` and `failed` in the terminal set so retries cannot
    accidentally re-run the agent.
    """
    call: Optional[Call] = (
        await session.execute(select(Call).where(Call.id == call_id))
    ).scalar_one_or_none()
    if call is None:
        return
    if call.status in (
        "transcribing", "analyzing", "completed", "needs_review", "failed"
    ):
        logger.info("orchestrator: call %s already in status %s — skipping", call_id, call.status)
        return

    # Serializes every ORM mutation that the agent loop's parallel tool
    # calls would otherwise issue concurrently against this single
    # AsyncSession. Without it, two `await session.flush()` coroutines
    # racing on the same session raise SQLAlchemy's
    # "Session is already flushing" InvalidRequestError, which the call
    # agent surfaces as "adk_runner: ... pipeline error".
    session_lock = asyncio.Lock()

    call.status = "transcribing"
    call.started_at = datetime.now(tz=timezone.utc)
    await session.commit()

    is_demo = call.session_id is not None

    template = (
        await session.execute(select(Template).where(Template.id == call.template_id))
    ).scalar_one()

    # 1) Speechmatics — transcribe with diarization + language auto-detect.
    # Admin-injected calls (debug endpoint) pre-populate `raw_transcript.text`
    # before kicking the pipeline; in that case we skip the transcription step
    # and reuse the supplied transcript so judges can probe the agent loop
    # with a custom utterance without recording audio.
    pre_loaded_text = (call.raw_transcript or {}).get("text") if call.raw_transcript else None
    if pre_loaded_text:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="speechmatics",
            step_type="tool_call",
            status="skipped",
            payload={"reason": "transcript_preloaded", "human_label": "Transcript injected (admin probe)"},
        ):
            pass
        transcript = speechmatics.TranscriptResult(
            text=pre_loaded_text,
            language=(call.raw_transcript or {}).get("language") or "en",
            speakers=(call.raw_transcript or {}).get("speakers") or [],
            raw=(call.raw_transcript or {}).get("raw") or {},
        )
        call.detected_language = transcript.language
        await session.commit()
    else:
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
    # spend tokens on a transcript that has no semantic content.
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

    # 3) Memory lookup (structured fast-path only). The semantic RAG read is
    # now an on-demand TOOL the agent invokes from inside its loop
    # (`tools/memory_tool.py`), so it doesn't pre-burn tokens when the agent
    # decides it doesn't need prior context.
    collection_id = settings.vultr_vector_default_collection or None
    preseed_available = False
    if is_demo and collection_id:
        preseed_available = customer.is_seed or await _seed_exists_for_phone(
            session, call.phone_e164
        )
    prior_structured: dict[str, Any] = await memory_retrieval.retrieve_structured_facts(
        session, customer
    )

    # 4-6) Agentic loop. The agent invokes action tools that execute INLINE
    # via execute_single_action, so ExecutedAction rows are flushed turn by
    # turn. Audit rows (`agent_turn`, `action_exec`) are linked deterministically
    # via the `agent_turn` numeric counter in their payload.
    async with audit_step(
        call_id=call.id,
        session_id=call.session_id,
        agent_name="call_agent",
        step_type="agent_loop_start",
        model=settings.gemini_default_model,
        payload={"max_iterations": 12},
    ):
        pass

    result = await call_agent.run_call_agent(
        session,
        call=call,
        customer=customer,
        template=template,
        transcript_text=transcript.text,
        prompt_hints=template.prompt_hints,
        prior_structured=prior_structured,
        is_demo=is_demo,
        preseed_available=preseed_available,
        collection_id=collection_id,
        max_iterations=12,
        session_lock=session_lock,
    )

    # Emit the per-turn audit rows. We do this AFTER the loop so they share
    # the orchestrator's session and stay visible even on rollback paths.
    for entry in result.turn_trail:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="call_agent",
            step_type="agent_turn",
            payload={
                "turn": entry.get("turn"),
                "tool": entry.get("tool"),
                "args_summary": entry.get("args_summary"),
                "result_summary": entry.get("result_summary"),
            },
        ):
            pass

    async with audit_step(
        call_id=call.id,
        session_id=call.session_id,
        agent_name="call_agent",
        step_type="agent_loop_end",
        payload={
            "turn_count": result.turn_count,
            "completion_reason": result.completion_reason,
            "available_tools": result.available_tools,
            "error": result.error,
        },
    ) as loop_audit:
        loop_audit.input_tokens = result.token_usage.input_tokens
        loop_audit.output_tokens = result.token_usage.output_tokens

    # Map completion_reason → call.status (no re-raise on error).
    if result.completion_reason == "error":
        _apply_agent_error(call, result)
        await session.commit()
        return

    if result.completion_reason == "max_turns":
        _apply_agent_max_turns(call, result)
        await session.commit()
        return

    # ----- completion_reason == "finalize" path -----

    fields = result.fields or []
    fields_dict, confidence_dict, evidence_dict = _coerce_extractions(
        fields, template.fields_schema
    )
    session.add(
        ExtractedFields(
            call_id=call.id,
            fields=fields_dict,
            confidence=confidence_dict,
            evidence=evidence_dict,
            intent=result.intent,
            sentiment=result.sentiment,
            urgency=result.urgency,
            briefing_snapshot=result.briefing,
        )
    )

    # display_name backfill — if we just learned the caller's name and the
    # Customer row has none yet, persist it so the next dial shows "Mark Ross"
    # instead of the phone number.
    _backfill_display_name(customer, template.fields_schema, fields)

    # Memory write-back: persist the briefing on Postgres + push a chunk into
    # the Vultr Vector Store (prod only — demo writes are skipped to avoid
    # cross-visitor pollution of the shared collection).
    await _persist_memory(
        session,
        call=call,
        customer=customer,
        template=template,
        collection_id=collection_id,
        briefing=result.briefing or "",
        classification={
            "intent": result.intent,
            "sentiment": result.sentiment,
            "language": result.language,
            "urgency": result.urgency,
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
    fields: list[call_analyzer.FieldExtraction],
) -> None:
    """Set `customer.display_name` when we extract the caller's name and the
    Customer row does not have one yet.

    Idempotent: if `display_name` is already set, do nothing.
    """
    if customer.display_name:
        return

    for extraction in fields:
        if not _is_name_field(extraction.key):
            continue
        value = (extraction.value or "").strip()
        if not value:
            continue
        customer.display_name = value[:200]
        return


async def _seed_exists_for_phone(
    session: AsyncSession, phone_e164: str
) -> bool:
    """Return True iff a seed Customer row exists for this phone."""
    return bool(
        await session.scalar(
            select(Customer.id).where(
                Customer.phone_e164 == phone_e164,
                Customer.is_seed.is_(True),
            )
        )
    )


def _format_briefing_chunk(
    *,
    call: Call,
    customer: Customer,
    template: Template,
    briefing: str,
    briefing_en: Optional[str],
    classification: dict[str, Any],
) -> str:
    """Render the indexed content of a Vultr Vector Store chunk."""
    call_date = (
        call.completed_at or call.started_at or datetime.now(tz=timezone.utc)
    ).date()
    display_label = customer.display_name or customer.phone_e164
    bilingual_tail = f"\n\n[EN] {briefing_en}" if briefing_en else ""
    return (
        f"Customer {display_label} ({customer.phone_e164}) called "
        f"the {template.domain_hint} on {call_date.isoformat()}. "
        f"Intent: {classification.get('intent', 'unknown')}. "
        f"Sentiment: {classification.get('sentiment', 'unknown')}. "
        f"Urgency: {classification.get('urgency', 'unknown')}. "
        f"Briefing: {briefing}{bilingual_tail}"
    )


def _pre_classify(transcript_text: str) -> bool:
    """Return False if the transcript is too short / empty to analyze."""
    if not transcript_text or not transcript_text.strip():
        return False
    if len(transcript_text.split()) < _MIN_TRANSCRIPT_WORDS:
        return False
    return True


def _apply_agent_error(call: Call, result: "call_agent.CallAgentResult") -> None:
    """Apply CallAgentResult(completion_reason='error') onto the Call row.

    Pure function: mutates `call` in place, never raises, never touches the
    DB session. The orchestrator's commit comes next so the error landing
    cannot be lost to a rollback.
    """
    call.status = "failed"
    call.error = (result.error or "call_agent error")[:1000]
    call.completed_at = datetime.now(tz=timezone.utc)


def _apply_agent_max_turns(call: Call, result: "call_agent.CallAgentResult") -> None:
    """Apply CallAgentResult(completion_reason='max_turns') onto the Call row.

    Honor an agent-set review_flag (from `flag_for_review`) if present;
    otherwise auto-fill a `system`-flagged entry.
    """
    call.status = "needs_review"
    if call.review_flag is None:
        call.review_flag = {
            "reason": "agent_did_not_finalize",
            "severity": "high",
            "turn_count": result.turn_count,
            "flagged_by": "system",
        }
    call.completed_at = datetime.now(tz=timezone.utc)


def _coerce_extractions(
    extractions: list[call_analyzer.FieldExtraction],
    fields_schema: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Turn the agent's typed list into three keyed dicts, cast values, and
    flag fields whose `depends_on` chain is not satisfied.
    """
    import json

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
        import json
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

    detected_language = (classification.get("language") or "en").lower()

    # Bilingual chunk: if the call was not already in English, ask Gemini for
    # a short EN summary so the vector index is searchable cross-language.
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

    chunk_content = _format_briefing_chunk(
        call=call,
        customer=customer,
        template=template,
        briefing=briefing,
        briefing_en=briefing_en,
        classification=classification,
    )

    item_id: Optional[str] = None
    try:
        async with audit_step(
            call_id=call.id,
            session_id=call.session_id,
            agent_name="memory_updater",
            step_type="tool_call",
            model="vultr-vector-store",
        ) as updater_audit:
            item_id = await vultr_inference.add_vector_item(
                collection_id,
                content=chunk_content,
                description=f"call_{call.id} phone_{customer.phone_e164}",
            )
            updater_audit.payload = {
                "collection": collection_id,
                "vultr_item_id": item_id,
                "chars": len(chunk_content),
            }
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
    """Translate / summarize the briefing to a one-sentence English line."""
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
