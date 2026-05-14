"""Orchestrator — entry point for the multi-agent call pipeline.

For Day 1 this is a thin wrapper that exposes a single async function
`run_pipeline` invoked by the FastAPI background task. As we wire each
sub-agent (Day 2-4) the orchestrator gains real ADK + Vultr calls.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import classification, memory_retrieval
from app.audit.logger import audit_step
from app.config import get_settings
from app.db.models import (
    Business,
    Call,
    Customer,
    CustomerMemoryChunk,
    ExecutedAction,
    ExtractedFields,
    Template,
)
from app.executors.action_executor import execute_planned_actions
from app.integrations import speechmatics, vultr_inference

settings = get_settings()


async def run_pipeline(session: AsyncSession, call_id: uuid.UUID) -> None:
    """Drive a call through the full pipeline. Idempotent enough for retry."""
    call: Optional[Call] = (
        await session.execute(select(Call).where(Call.id == call_id))
    ).scalar_one_or_none()
    if call is None:
        return

    call.status = "transcribing"
    call.started_at = datetime.now(tz=timezone.utc)
    await session.commit()

    business = (
        await session.execute(select(Business).where(Business.id == call.business_id))
    ).scalar_one()
    template = (
        await session.execute(select(Template).where(Template.id == call.template_id))
    ).scalar_one()

    # 1) Speechmatics transcription
    async with audit_step(
        session, call_id=call.id, agent_name="speechmatics", step_type="tool_call"
    ):
        transcript = await speechmatics.transcribe_audio(
            Path(call.audio_url) if call.audio_url else Path("/dev/null"),
            custom_dictionary=template.custom_dictionary,
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

    # 2) Customer matching + memory retrieval (parallel-ish, serial for simplicity)
    customer = (
        await session.execute(
            select(Customer).where(
                Customer.business_id == business.id,
                Customer.phone_e164 == call.phone_e164,
            )
        )
    ).scalar_one_or_none()
    if customer:
        call.customer_id = customer.id

    memory_context = ""
    async with audit_step(
        session,
        call_id=call.id,
        agent_name="memory_retrieval",
        step_type="llm_call",
        model=settings.vultr_inference_model,
    ):
        memory_context = await memory_retrieval.retrieve_customer_context(
            collection_id=business.vultr_collection_id,
            phone_e164=call.phone_e164,
            business_domain=business.domain,
        )

    # 3) Classification (Vultr Kimi-K2)
    async with audit_step(
        session,
        call_id=call.id,
        agent_name="classification",
        step_type="llm_call",
        model=settings.vultr_inference_model,
    ):
        classification_result = await classification.classify(
            transcript_text=transcript.text, domain=business.domain
        )

    # 4) Extraction stub for Day 1 — surfaces template's first 3 fields with fake values.
    extraction_result = _stub_extraction(template, transcript.text)
    async with audit_step(
        session,
        call_id=call.id,
        agent_name="extraction",
        step_type="llm_call",
        model=settings.gemini_default_model,
        payload={"stub": True},
    ):
        pass

    extracted = ExtractedFields(
        call_id=call.id,
        fields=extraction_result["fields"],
        confidence=extraction_result["confidence"],
        evidence=extraction_result["evidence"],
        intent=classification_result.get("intent"),
        sentiment=classification_result.get("sentiment"),
        urgency=classification_result.get("urgency"),
    )
    session.add(extracted)

    # 5) Action plan stub for Day 1 — runs every 'auto' action from the template.
    plan = _stub_action_plan(template, extraction_result["fields"])

    # 6) Execute
    async with audit_step(
        session,
        call_id=call.id,
        agent_name="action_executor",
        step_type="action_exec",
    ):
        executed_actions = await execute_planned_actions(
            session, call=call, customer=customer, template=template, plan=plan
        )

    # 7) Memory update stub — push a chunk via Vultr Vector Store (or fake).
    if customer is not None:
        await _stub_memory_update(
            session,
            call=call,
            customer=customer,
            business=business,
            extraction=extraction_result,
            classification_result=classification_result,
        )

    call.status = "completed"
    call.completed_at = datetime.now(tz=timezone.utc)
    await session.commit()


# ---------------------------------------------------------------------------
# Day 1 stubs — replaced with real ADK calls in Day 2/3.
# ---------------------------------------------------------------------------


def _stub_extraction(template: Template, transcript_text: str) -> dict[str, Any]:
    """Heuristic extraction so the pipeline produces visible structured output."""
    fields: dict[str, Any] = {}
    confidence: dict[str, float] = {}
    evidence: dict[str, str] = {}

    text_lower = transcript_text.lower()
    if "quattro" in text_lower or "four" in text_lower:
        fields["party_size"] = 4
        confidence["party_size"] = 0.91
        evidence["party_size"] = "siamo in quattro"
    if "marco" in text_lower:
        fields["customer_name"] = "Marco"
        confidence["customer_name"] = 0.88
        evidence["customer_name"] = "Mi chiamo Marco."
    if "otto e mezza" in text_lower or "20:30" in text_lower:
        fields["booking_time"] = "20:30"
        confidence["booking_time"] = 0.86
        evidence["booking_time"] = "verso le otto e mezza"
    if "glutine" in text_lower:
        fields["allergies"] = ["glutine"]
        confidence["allergies"] = 0.78
        evidence["allergies"] = "una persona e intollerante al glutine"
    if "whatsapp" in text_lower:
        fields["callback_channel"] = "whatsapp"
        confidence["callback_channel"] = 0.95
        evidence["callback_channel"] = "Mi potete confermare su WhatsApp?"

    return {"fields": fields, "confidence": confidence, "evidence": evidence}


def _stub_action_plan(template: Template, fields: dict[str, Any]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for action in template.action_types:
        if action.get("execution_mode") == "manual-only":
            continue
        if action["key"] in ("booking.create", "appointment.create", "appointment.create_inspection"):
            plan.append(
                {
                    "action_type": action["key"],
                    "title": action["label"],
                    "summary": "Create booking from extracted fields",
                    "payload": fields,
                    "confidence": 0.9,
                    "execution_mode": "auto",
                    "evidence": ["siamo in quattro", "verso le otto e mezza"],
                }
            )
        elif action["key"].startswith("whatsapp."):
            plan.append(
                {
                    "action_type": action["key"],
                    "title": action["label"],
                    "summary": "Send confirmation",
                    "payload": {
                        "to": fields.get("phone_e164"),
                        "body": f"Confirmed for {fields.get('party_size', '?')} guests.",
                    },
                    "confidence": 0.88,
                    "execution_mode": "auto",
                    "evidence": [],
                }
            )
        elif action["key"] in ("customer.update_profile", "patient.update_profile"):
            plan.append(
                {
                    "action_type": action["key"],
                    "title": action["label"],
                    "summary": "Update customer profile",
                    "payload": {"fields": fields},
                    "confidence": 0.85,
                    "execution_mode": "auto",
                    "evidence": [],
                }
            )
    return plan


async def _stub_memory_update(
    session: AsyncSession,
    *,
    call: Call,
    customer: Customer,
    business: Business,
    extraction: dict[str, Any],
    classification_result: dict[str, Any],
) -> None:
    summary_text = (
        f"Customer called on {datetime.now(timezone.utc).date().isoformat()}. "
        f"Intent: {classification_result.get('intent')}. "
        f"Fields extracted: {json.dumps(extraction['fields'])[:240]}."
    )

    async with audit_step(
        session,
        call_id=call.id,
        agent_name="memory_updater",
        step_type="tool_call",
        model="vultr-vector-store",
    ):
        if not business.vultr_collection_id:
            business.vultr_collection_id = await vultr_inference.create_vector_collection(
                f"afterglow-{business.id}"
            )
        item_id = await vultr_inference.add_vector_item(
            business.vultr_collection_id,
            content=summary_text,
            description=f"call_{call.id}",
        )

    session.add(
        CustomerMemoryChunk(
            id=uuid.uuid4(),
            customer_id=customer.id,
            call_id=call.id,
            vultr_collection_id=business.vultr_collection_id,
            vultr_item_id=item_id,
            summary=summary_text,
            chunk_metadata={
                "intent": classification_result.get("intent"),
                "language": classification_result.get("language"),
            },
        )
    )
    customer.memory_summary = summary_text
    customer.total_calls = (customer.total_calls or 0) + 1
    customer.last_call_at = datetime.now(tz=timezone.utc)
