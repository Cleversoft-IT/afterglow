"""PII policy — per-class confidence thresholds.

Revised 2026-05-16: redaction strategies are no longer applied at runtime
(the operator needs the verbatim briefing). The thresholds below still drive
two things:

  1. The minimum confidence at which an extraction is considered "trusted"
     vs. "manual_review" — surfaced in the operator UI and in the
     `pii_policy_applied` audit row.

  2. The deterministic depends_on chain in `orchestrator._coerce_extractions`,
     which marks dependent fields as manual_review when their PII dependency
     misses the threshold.

`redact_for_briefing` and `hash_for_audit` are retained as utility helpers
for callers who still want a redacted projection (none today in the runtime
pipeline). A per-field `confidence_threshold` on the FieldDefinition
overrides the class default. `pii_class="none"` means "no special handling".
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
