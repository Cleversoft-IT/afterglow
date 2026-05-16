"""PII policy — per-class confidence thresholds and redaction strategies.

The Call Analyzer extracts every field in `template.fields_schema`. Some of
those fields carry PII; the policy below decides:

  1. The minimum confidence required to consider the extraction "trusted".
     Below that threshold the field is `flagged` for manual review and any
     mention of its value is stripped from the briefing.

  2. How the value is rendered when it MUST appear in a downstream surface
     that is not the operator-private `fields` blob:
       - `next_call_briefing` (visible in customer card + vector chunk)
       - `audit_log.payload.evidence`
       - `CustomerMemoryChunk.summary` (vector store embedding)

     The raw value always survives in `ExtractedFields.fields` so the
     operator can verify it manually and the deterministic action_executor
     can pass it to the mock target.

A per-field `confidence_threshold` on the FieldDefinition overrides the
class default. `pii_class="none"` means "no special handling".
"""
from __future__ import annotations

import hashlib
from typing import Final

from app.schemas.templates import PiiClass


# Confidence floors per pii_class. Empirically chosen — health/financial are
# the strictest because false positives carry the highest cost in those
# domains; identity (license plate, fiscal code, ID number) is also strict
# but slightly looser because OCR/STT errors are recoverable downstream;
# contact (name, phone) is moderate because most calls open with the
# operator hearing the name distinctly.
PII_THRESHOLDS: Final[dict[PiiClass, float]] = {
    "none": 0.0,
    "contact": 0.80,
    "identity": 0.85,
    "financial": 0.90,
    "health": 0.90,
}


def threshold_for(pii_class: PiiClass, override: float | None = None) -> float:
    """Return the threshold a field's confidence must clear.

    A per-field `confidence_threshold` on FieldDefinition wins over the
    class default when set.
    """
    if override is not None:
        return override
    return PII_THRESHOLDS.get(pii_class, 0.0)


def redact_for_briefing(value: str, pii_class: PiiClass) -> str:
    """Return the value as it should appear in any non-operator-private surface.

    Strategy per class:
      - none      → passthrough.
      - contact   → `[redacted: contact]` (e.g. customer name in briefing).
      - identity  → first-2 + asterisks + last-2 (so license plates stay
                    recognisable but not searchable verbatim).
      - financial → `[hash:<sha256[:8]>]` (deterministic per process so
                    consecutive briefings about the same value cluster).
      - health    → `[redacted: health]` — never inline.

    The redaction is intentionally not reversible. The raw value lives in
    `ExtractedFields.fields`; if the operator needs to read it they open
    the call detail screen, not the customer card / briefing.
    """
    if value is None or value == "":
        return value
    cls = pii_class or "none"
    if cls == "none":
        return value
    if cls == "contact":
        return "[redacted: contact]"
    if cls == "health":
        return "[redacted: health]"
    if cls == "financial":
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        return f"[hash:{digest}]"
    if cls == "identity":
        if len(value) <= 4:
            return "***"
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
    return value


def hash_for_audit(value: str, salt: str) -> str:
    """Salted SHA-256 truncated to 12 chars. Used when the audit_log must
    track WHICH redaction was applied to which raw value without storing
    the value itself.
    """
    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    h.update(b":")
    h.update((value or "").encode("utf-8"))
    return h.hexdigest()[:12]
