"""PII sanitizer — observe-only inspector over a CallAnalysis.

Revised 2026-05-16 (post-feedback round 2): we stopped redacting the briefing.
The operator MUST see allergies, names, and other PII verbatim before picking
up the next call — a `[redacted: health]` placeholder is useless when the
goal is "remind the human that this customer is celiac". The raw values now
flow through to:

  - `customer.memory_summary` (UI-visible briefing on the caller card)
  - `ExtractedFields.briefing_snapshot` (per-call frozen copy)
  - the Vultr Vector Store chunk (semantic memory for future calls)
  - the audit_log payload (debugging surface)

What this module still does: it INSPECTS every field's pii_class and
confidence, and emits an audit trail entry (`pii_policy_applied`) that
records WHICH PII classes were present and AT WHAT confidence. Auditors can
answer "did this briefing carry health-class data?" without reading values.
The decision to redact is replaced by a decision to label.

If a future product flip needs redaction again, swap `audit_pii_actions[].action`
back to `redact|flag` and re-enable `_redact_text` on the briefing/evidence.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from app.agents.call_analyzer import CallAnalysis, FieldExtraction
from app.agents.pii_policy import threshold_for
from app.schemas.templates import PiiClass

logger = logging.getLogger("afterglow")


PolicyAction = Literal["passthrough", "observed_low_confidence", "observed"]


@dataclass
class PiiActionRecord:
    """One entry in the audit_log payload — what we observed, not what we did.

    `action` values:
      - `passthrough`:                pii_class == "none", nothing to track.
      - `observed`:                   pii_class != "none" and confidence
                                      meets the class threshold. The value is
                                      kept verbatim everywhere.
      - `observed_low_confidence`:    pii_class != "none" but confidence below
                                      the class threshold — the operator UI
                                      should surface this as "manual review".
    """

    field: str
    pii_class: PiiClass
    action: PolicyAction
    threshold: float
    confidence: float


@dataclass
class SanitizedAnalysis:
    """Wraps the (untouched) CallAnalysis plus the audit trail.

    Historically this used to wrap a *sanitized* copy; today the redaction is
    off (see module docstring). We keep the wrapper shape so the orchestrator
    contract stays stable.
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
        return ("observed_low_confidence", pii_class, threshold)
    return ("observed", pii_class, threshold)


def sanitize_analysis(
    template_fields_schema: list[dict[str, Any]],
    analysis: CallAnalysis,
    *,
    session_salt: Optional[str] = None,
) -> SanitizedAnalysis:
    """Inspect `analysis` and emit the PII observation trail.

    Does not mutate `analysis`. The returned `SanitizedAnalysis.analysis` is
    the input as-is (kept for orchestrator contract stability). The
    `audit_pii_actions` list records every non-`none` field with its
    pii_class, the class threshold, and the analyzer's confidence, so the
    audit_log can show "this briefing carries health-class data" without
    leaking the value itself.
    """
    _ = session_salt  # reserved for hash_for_audit integration

    index = _build_field_index(template_fields_schema)
    audit_records: list[PiiActionRecord] = []

    for extraction in analysis.fields:
        field_def = index.get(extraction.key)
        if field_def is None:
            continue
        action, pii_class, threshold = _decide(field_def, extraction)
        if action == "passthrough":
            continue
        audit_records.append(
            PiiActionRecord(
                field=extraction.key,
                pii_class=pii_class,
                action=action,
                threshold=threshold,
                confidence=extraction.confidence,
            )
        )

    if audit_records:
        logger.info(
            "pii_sanitizer: observed %d PII field(s) (%s)",
            len(audit_records),
            ",".join(f"{r.field}:{r.pii_class}" for r in audit_records),
        )

    return SanitizedAnalysis(analysis=analysis, audit_pii_actions=audit_records)
