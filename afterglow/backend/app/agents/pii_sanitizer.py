"""PII sanitizer — applies the policy from `pii_policy` to a CallAnalysis.

Invoked by the orchestrator IMMEDIATELY after `call_analyzer.analyze_call`
and BEFORE any persist step. Downstream consumers (briefing_snapshot,
memory write-back, vector chunk, audit_log payload) read the sanitized
copy. The raw `analysis.fields` survives separately because:

  - the operator needs to verify the raw value in the call detail UI;
  - `action_executor` must pass the real value to the mock target so the
    booking/SMS/etc. payloads stay meaningful.

The audit log receives a `pii_policy_applied` row whose payload is the list
returned in `audit_pii_actions` — one entry per field that triggered the
policy. Auditors can answer "did we redact X?" without reading any value.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from app.agents.call_analyzer import CallAnalysis, FieldExtraction, PlannedAction
from app.agents.pii_policy import redact_for_briefing, threshold_for
from app.schemas.templates import PiiClass

logger = logging.getLogger("afterglow")


PolicyAction = Literal["passthrough", "redact", "flag"]


@dataclass
class PiiActionRecord:
    """One entry in the audit_log payload — what we did and why."""

    field: str
    pii_class: PiiClass
    action: PolicyAction
    threshold: float
    confidence: float


@dataclass
class SanitizedAnalysis:
    """Wraps a sanitized copy of the CallAnalysis plus the audit trail.

    `fields` and `planned_actions` keep their raw values — `next_call_briefing`
    and the evidence on planned_actions are the only mutated payloads. The
    orchestrator decides which surface receives which copy.
    """

    analysis: CallAnalysis
    audit_pii_actions: list[PiiActionRecord] = field(default_factory=list)


def _build_field_index(
    template_fields_schema: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {f["key"]: f for f in template_fields_schema if f.get("key")}


def _decide(
    field_def: dict[str, Any], extraction: FieldExtraction
) -> tuple[PolicyAction, PiiClass, float]:
    pii_class: PiiClass = field_def.get("pii_class") or (
        "contact" if field_def.get("sensitive") else "none"
    )
    threshold = threshold_for(pii_class, field_def.get("confidence_threshold"))

    if pii_class == "none":
        return ("passthrough", pii_class, threshold)
    if extraction.confidence < threshold:
        return ("flag", pii_class, threshold)
    return ("redact", pii_class, threshold)


def _redact_text(text: str, value: str, pii_class: PiiClass) -> str:
    """Replace every case-insensitive occurrence of `value` in `text` with
    the redacted form for `pii_class`.

    Only matches whole-or-partial occurrences as a literal substring. List
    values arrive serialised as JSON literals (e.g. `["glutine"]`) so we
    also try to redact each element individually.
    """
    if not value or not text:
        return text

    replacements = [value]
    # Cheap list extraction: if the value looks like a JSON list of strings,
    # also redact each element so a briefing that paraphrases the items is
    # still scrubbed.
    if value.startswith("[") and value.endswith("]"):
        try:
            import json as _json

            items = _json.loads(value)
            if isinstance(items, list):
                replacements.extend(str(x) for x in items if x)
        except Exception:  # noqa: BLE001
            pass

    redaction = redact_for_briefing(value, pii_class)
    out = text
    for token in replacements:
        if not token:
            continue
        # Case-insensitive literal replace; avoid regex injection by escaping.
        out = re.sub(re.escape(token), redaction, out, flags=re.IGNORECASE)
    return out


def sanitize_analysis(
    template_fields_schema: list[dict[str, Any]],
    analysis: CallAnalysis,
    *,
    session_salt: Optional[str] = None,
) -> SanitizedAnalysis:
    """Return a `SanitizedAnalysis` whose briefing and evidence are scrubbed
    according to the per-field PII policy.

    `session_salt` is plumbed through for future audit-hash use. Today
    callers do not need to pass it.
    """
    _ = session_salt  # reserved for hash_for_audit integration

    index = _build_field_index(template_fields_schema)

    audit_records: list[PiiActionRecord] = []
    briefing = analysis.next_call_briefing or ""

    # Pass 1: per-field decisions + briefing scrub.
    for extraction in analysis.fields:
        field_def = index.get(extraction.key)
        if field_def is None:
            continue
        action, pii_class, threshold = _decide(field_def, extraction)
        if action == "passthrough":
            continue
        if pii_class != "none":
            briefing = _redact_text(briefing, extraction.value, pii_class)
        audit_records.append(
            PiiActionRecord(
                field=extraction.key,
                pii_class=pii_class,
                action=action,
                threshold=threshold,
                confidence=extraction.confidence,
            )
        )

    # Pass 2: scrub each planned_action's evidence list. Evidence spans are
    # verbatim quotes from the transcript and frequently contain the same
    # PII values we just redacted from the briefing.
    sanitized_planned: list[PlannedAction] = []
    for pa in analysis.planned_actions:
        new_evidence: list[str] = []
        for ev in pa.evidence:
            scrubbed = ev
            for extraction in analysis.fields:
                field_def = index.get(extraction.key)
                if field_def is None:
                    continue
                action, pii_class, _ = _decide(field_def, extraction)
                if action in ("redact", "flag") and pii_class != "none":
                    scrubbed = _redact_text(scrubbed, extraction.value, pii_class)
            new_evidence.append(scrubbed)
        sanitized_planned.append(pa.model_copy(update={"evidence": new_evidence}))

    sanitized = analysis.model_copy(
        update={
            "next_call_briefing": briefing,
            "planned_actions": sanitized_planned,
        }
    )

    if audit_records:
        logger.info(
            "pii_sanitizer: applied policy to %d field(s) (%s)",
            len(audit_records),
            ",".join(f"{r.field}:{r.action}" for r in audit_records),
        )

    return SanitizedAnalysis(analysis=sanitized, audit_pii_actions=audit_records)
