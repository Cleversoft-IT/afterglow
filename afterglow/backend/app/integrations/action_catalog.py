"""Action catalog — single source of truth for which actions Afterglow can run.

Templates carry a list of `action_types` they want the planner to consider.
Each action key must resolve to one entry in this catalog. The entry tells
the rest of the system:

  - `integration_kind`:
      * `"mock_external"` — the executor invokes a MOCK_REGISTRY function;
        result is stamped `mock=True` so the UI shows the "Simulated" badge.
      * `"internal_real"` — the executor mutates Postgres for real (customer
        profile, tags, memory). No "Simulated" badge.

  - `can_undo`: True when there is a meaningful compensation for the action.
    Today undo is a UI-level flip (status `executed` → `undone`); we do not
    actually call a counter-mock at the moment (per feedback round 2). Undo
    visibility is suppressed for irreversible side-effects (sent messages,
    insurance cases).

  - `mock_target`: only meaningful for `mock_external` — names the bucket in
    `MOCK_REGISTRY` that backs the action.

  - `internal_handler`: only meaningful for `internal_real` — names the
    callable the executor invokes. Avoids hard-coding action_type strings
    inside the executor.

  - `compatible_domains`: hint surface used by the wizard chat to filter
    suggestions. `["*"]` means "any business".

Future work: a future iteration can add `compensation_action` so undo
actually invokes a counter-mock (e.g. booking.cancel) — see
`afterglow/docs/future-ideas.md`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


IntegrationKind = Literal["mock_external", "internal_real"]


# Recognized `domain_hint` values across the system. Single source of truth
# consumed by the wizard prompt (see `agents/wizard_chat._system_instruction`).
# The first three are the seed templates shipped in `db/seed.py`; the rest
# are vertical hints the wizard can assign when inferring `domain_hint` from
# a user's business description. `generic` is the fallback for anything that
# doesn't fit one of the verticals.
KNOWN_DOMAINS: list[str] = [
    "restaurant",
    "dentist",
    "bodyshop",
    "hotel",
    "salon",
    "clinic",
    "legal",
    "realestate",
    "gym",
    "events",
    "generic",
]


# Bucket labels surfaced by `aggregate_integrations` for the Integrations
# drawer screen. Keys must match every `mock_target` in `CATALOG` plus every
# prefix derived from `internal_handler` (the part before the first `.`).
_BUCKET_LABELS: dict[str, str] = {
    "booking": "Booking system",
    "whatsapp": "WhatsApp",
    "sms": "SMS gateway",
    "email": "Email",
    "crm": "CRM",
    "calendar": "Calendar",
    "payment": "Payments",
    "review": "Reviews",
    "customer_profile": "Customer database",
}


@dataclass(frozen=True)
class ActionCatalogEntry:
    key: str
    label: str
    description: str
    integration_kind: IntegrationKind
    mock_target: Optional[str] = None
    internal_handler: Optional[str] = None
    can_undo: bool = False
    # True when the action creates / modifies / deletes records in the target
    # system. Surfaced to the Action Planner (tool docstring) and stamped on
    # the executor's audit row + ExecutedAction.result. Independent of
    # `can_undo`: a booking creation mutates state but is also undoable.
    mutates: bool = False
    default_payload_schema: Optional[dict[str, Any]] = None
    compatible_domains: list[str] = field(default_factory=lambda: ["*"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "integration_kind": self.integration_kind,
            "mock_target": self.mock_target,
            "internal_handler": self.internal_handler,
            "can_undo": self.can_undo,
            "mutates": self.mutates,
            "default_payload_schema": self.default_payload_schema,
            "compatible_domains": self.compatible_domains,
        }


# Default JSONSchema payloads applied at the persistence boundary in
# `backend/app/api/templates.py` (create_template / update_template) when
# an action_type arrives without an explicit payload_schema. This guarantees
# that the call_agent's `make_action_tool` builds a typed Pydantic model for
# Gemini structured-output, rather than falling back to an untyped `dict`
# annotation that ADK 1.18+ now rejects with "default value None of
# parameter payload: dict is not compatible". The wizard's
# `ActionDefinitionDraft` model cannot carry payload_schema directly
# (Gemini structured-output rejects schemas with `additionalProperties`),
# so the catalog is the single source of truth.

_BOOKING_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "booking_date": {"type": "string", "description": "YYYY-MM-DD"},
        "booking_time": {"type": "string", "description": "HH:MM (24h)"},
        "party_size": {"type": "integer", "minimum": 1},
        "name": {"type": "string", "description": "Caller display name"},
        "phone_e164": {"type": "string", "description": "E.164 phone number"},
        "notes": {"type": "string", "description": "Free-form notes from the call"},
    },
    "required": ["booking_date", "booking_time"],
}

_INSPECTION_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "booking_date": {"type": "string", "description": "YYYY-MM-DD"},
        "booking_time": {"type": "string", "description": "HH:MM (24h)"},
        "vehicle_plate": {"type": "string"},
        "damage_summary": {"type": "string"},
        "phone_e164": {"type": "string"},
    },
    "required": ["booking_date", "booking_time"],
}

_WHATSAPP_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "phone_e164": {"type": "string", "description": "E.164 phone number"},
        "message": {"type": "string", "description": "Message body in caller's language"},
    },
    "required": ["phone_e164", "message"],
}

_SMS_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "phone_e164": {"type": "string"},
        "message": {"type": "string"},
    },
    "required": ["phone_e164", "message"],
}

_EMAIL_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "to": {"type": "string", "description": "Recipient email address"},
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["to", "subject", "body"],
}

_CASE_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "case_type": {"type": "string", "description": "e.g. collision, theft"},
        "notes": {"type": "string", "description": "Free-form context from the call"},
        "phone_e164": {"type": "string"},
    },
    "required": ["notes"],
}

_BOOKING_CANCEL_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "booking_id": {"type": "string", "description": "Identifier of the booking to cancel"},
        "reason": {"type": "string"},
    },
    "required": ["booking_id"],
}

_BOOKING_RESCHEDULE_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "booking_id": {"type": "string", "description": "Identifier of the booking to move"},
        "new_booking_date": {"type": "string", "description": "YYYY-MM-DD"},
        "new_booking_time": {"type": "string", "description": "HH:MM (24h)"},
        "reason": {"type": "string"},
    },
    "required": ["new_booking_date", "new_booking_time"],
}

_CALENDAR_EVENT_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "start": {"type": "string", "description": "ISO 8601 datetime"},
        "end": {"type": "string", "description": "ISO 8601 datetime"},
        "attendees": {
            "type": "array",
            "items": {"type": "string", "description": "Attendee email or phone"},
        },
        "notes": {"type": "string"},
    },
    "required": ["title", "start"],
}

_CALENDAR_INVITE_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "to": {"type": "string", "description": "Recipient email"},
    },
    "required": ["to"],
}

_CALENDAR_BLOCK_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "start": {"type": "string", "description": "ISO 8601 datetime"},
        "end": {"type": "string", "description": "ISO 8601 datetime"},
        "reason": {"type": "string"},
    },
    "required": ["start", "end"],
}

_PAYMENT_LINK_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {"type": "number", "minimum": 0},
        "currency": {"type": "string", "description": "ISO 4217, defaults to EUR"},
        "description": {"type": "string"},
        "phone_e164": {"type": "string"},
        "email": {"type": "string"},
    },
    "required": ["amount"],
}

_PAYMENT_DEPOSIT_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {"type": "number", "minimum": 0},
        "currency": {"type": "string"},
        "booking_reference": {"type": "string"},
        "phone_e164": {"type": "string"},
    },
    "required": ["amount"],
}

_PAYMENT_INVOICE_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {"type": "number", "minimum": 0},
        "currency": {"type": "string"},
        "to": {"type": "string", "description": "Recipient email"},
        "line_items": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["amount", "to"],
}

_REVIEW_REQUEST_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "channel": {"type": "string", "enum": ["whatsapp", "sms", "email"]},
        "phone_e164": {"type": "string"},
        "email": {"type": "string"},
        "platform": {"type": "string", "description": "google, tripadvisor, yelp, ..."},
    },
    "required": ["channel"],
}

_REVIEW_RESPONSE_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "review_id": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["review_id", "body"],
}

_LEAD_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "phone_e164": {"type": "string"},
        "email": {"type": "string"},
        "source": {"type": "string", "description": "phone_call, referral, ..."},
        "notes": {"type": "string"},
    },
    "required": ["name"],
}

_TICKET_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
        "notes": {"type": "string"},
        "phone_e164": {"type": "string"},
    },
    "required": ["subject"],
}

_EMAIL_QUOTE_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "to": {"type": "string"},
        "subject": {"type": "string"},
        "body": {"type": "string"},
        "quote_amount": {"type": "number"},
    },
    "required": ["to", "subject"],
}


CATALOG: dict[str, ActionCatalogEntry] = {
    "booking.create": ActionCatalogEntry(
        key="booking.create",
        label="Create booking",
        description="Reserve a slot in the venue's booking system (restaurant table, dental visit, body-shop inspection, salon, gym, etc.).",
        integration_kind="mock_external",
        mock_target="booking",
        can_undo=True,
        mutates=True,
        default_payload_schema=_BOOKING_PAYLOAD_SCHEMA,
        compatible_domains=[
            "restaurant", "hotel", "salon", "gym", "events",
            "dentist", "bodyshop", "clinic", "*",
        ],
    ),
    "booking.cancel": ActionCatalogEntry(
        key="booking.cancel",
        label="Cancel booking",
        description="Cancel a previously created booking.",
        integration_kind="mock_external",
        mock_target="booking",
        can_undo=False,  # cancellation is the undo itself
        mutates=True,
        default_payload_schema=_BOOKING_CANCEL_PAYLOAD_SCHEMA,
        compatible_domains=[
            "restaurant", "hotel", "salon", "gym", "events",
            "dentist", "bodyshop", "clinic", "*",
        ],
    ),
    "whatsapp.send_confirmation": ActionCatalogEntry(
        key="whatsapp.send_confirmation",
        label="Send WhatsApp confirmation",
        description="Send a confirmation message to the caller's WhatsApp.",
        integration_kind="mock_external",
        mock_target="whatsapp",
        can_undo=False,  # sent messages cannot be unsent
        default_payload_schema=_WHATSAPP_PAYLOAD_SCHEMA,
    ),
    "whatsapp.request_photos": ActionCatalogEntry(
        key="whatsapp.request_photos",
        label="Request damage photos",
        description="Ask the caller to send photos via WhatsApp.",
        integration_kind="mock_external",
        mock_target="whatsapp",
        can_undo=False,
        default_payload_schema=_WHATSAPP_PAYLOAD_SCHEMA,
        compatible_domains=["bodyshop", "*"],
    ),
    "sms.send_reminder": ActionCatalogEntry(
        key="sms.send_reminder",
        label="Send SMS reminder",
        description="Send the caller an SMS reminder for the upcoming booking.",
        integration_kind="mock_external",
        mock_target="sms",
        can_undo=False,
        default_payload_schema=_SMS_PAYLOAD_SCHEMA,
    ),
    "email.send": ActionCatalogEntry(
        key="email.send",
        label="Send email",
        description="Send the caller a follow-up email.",
        integration_kind="mock_external",
        mock_target="email",
        can_undo=False,
        default_payload_schema=_EMAIL_PAYLOAD_SCHEMA,
    ),
    "customer.update_profile": ActionCatalogEntry(
        key="customer.update_profile",
        label="Update customer profile",
        description=(
            "Update the customer row in Afterglow with the latest known name, "
            "tags, allergies and free-form facts. Internal action: this runs "
            "against Postgres for real."
        ),
        integration_kind="internal_real",
        internal_handler="customer_profile.apply_update",
        can_undo=True,
        mutates=True,
    ),
    "patient.update_profile": ActionCatalogEntry(
        key="patient.update_profile",
        label="Update patient profile",
        description=(
            "Update the patient row in Afterglow with the latest known name, "
            "tags and free-form facts. Internal action: this runs against "
            "Postgres for real."
        ),
        integration_kind="internal_real",
        internal_handler="customer_profile.apply_update",
        can_undo=True,
        mutates=True,
        compatible_domains=["dentist", "*"],
    ),
    "case.open_insurance": ActionCatalogEntry(
        key="case.open_insurance",
        label="Open insurance case",
        description="Open a manual insurance claim case in the CRM.",
        integration_kind="mock_external",
        mock_target="crm",
        can_undo=False,  # legal artefact — never auto-undone
        mutates=True,
        default_payload_schema=_CASE_PAYLOAD_SCHEMA,
        compatible_domains=["bodyshop", "*"],
    ),
    # --- New mock buckets (sms / calendar / payment / review) ----------------
    "sms.send_confirmation": ActionCatalogEntry(
        key="sms.send_confirmation",
        label="Send SMS confirmation",
        description="Send the caller an SMS confirming the booking.",
        integration_kind="mock_external",
        mock_target="sms",
        can_undo=False,  # sent messages cannot be unsent
        default_payload_schema=_SMS_PAYLOAD_SCHEMA,
    ),
    "sms.send_link": ActionCatalogEntry(
        key="sms.send_link",
        label="Send SMS with link",
        description="Send the caller a short SMS with a tracking / form / payment link.",
        integration_kind="mock_external",
        mock_target="sms",
        can_undo=False,
        default_payload_schema=_SMS_PAYLOAD_SCHEMA,
    ),
    "calendar.add_event": ActionCatalogEntry(
        key="calendar.add_event",
        label="Add calendar event",
        description="Create an event on the operator's calendar (Google / Outlook).",
        integration_kind="mock_external",
        mock_target="calendar",
        can_undo=True,
        mutates=True,
        default_payload_schema=_CALENDAR_EVENT_PAYLOAD_SCHEMA,
        compatible_domains=["hotel", "clinic", "legal", "realestate", "events", "*"],
    ),
    "calendar.send_invite": ActionCatalogEntry(
        key="calendar.send_invite",
        label="Send calendar invite",
        description="Send the caller an ICS calendar invite for a meeting or booking.",
        integration_kind="mock_external",
        mock_target="calendar",
        can_undo=False,  # an invite already delivered can't be unsent
        default_payload_schema=_CALENDAR_INVITE_PAYLOAD_SCHEMA,
        compatible_domains=["legal", "events", "realestate", "*"],
    ),
    "calendar.block_slot": ActionCatalogEntry(
        key="calendar.block_slot",
        label="Block calendar slot",
        description="Reserve a slot on the operator's calendar (e.g. emergency hold).",
        integration_kind="mock_external",
        mock_target="calendar",
        can_undo=True,
        mutates=True,
        default_payload_schema=_CALENDAR_BLOCK_PAYLOAD_SCHEMA,
        compatible_domains=["clinic", "salon", "dentist", "*"],
    ),
    "payment.create_link": ActionCatalogEntry(
        key="payment.create_link",
        label="Create payment link",
        description="Issue a hosted payment link the caller can settle later.",
        integration_kind="mock_external",
        mock_target="payment",
        can_undo=False,  # link is idempotent — operator just doesn't share it
        mutates=True,
        default_payload_schema=_PAYMENT_LINK_PAYLOAD_SCHEMA,
        compatible_domains=["hotel", "gym", "realestate", "events", "*"],
    ),
    "payment.request_deposit": ActionCatalogEntry(
        key="payment.request_deposit",
        label="Request deposit",
        description="Request a deposit payment from the caller to secure the booking.",
        integration_kind="mock_external",
        mock_target="payment",
        can_undo=False,
        mutates=True,
        default_payload_schema=_PAYMENT_DEPOSIT_PAYLOAD_SCHEMA,
        compatible_domains=["hotel", "events", "bodyshop", "*"],
    ),
    "payment.send_invoice": ActionCatalogEntry(
        key="payment.send_invoice",
        label="Send invoice",
        description="Email the caller a formal invoice for services rendered or quoted.",
        integration_kind="mock_external",
        mock_target="payment",
        can_undo=False,
        mutates=True,
        default_payload_schema=_PAYMENT_INVOICE_PAYLOAD_SCHEMA,
        compatible_domains=["legal", "bodyshop", "*"],
    ),
    "review.request_feedback": ActionCatalogEntry(
        key="review.request_feedback",
        label="Request review feedback",
        description="Ask the caller to leave a public review (Google / TripAdvisor / Yelp).",
        integration_kind="mock_external",
        mock_target="review",
        can_undo=False,  # the request has been sent
        default_payload_schema=_REVIEW_REQUEST_PAYLOAD_SCHEMA,
        compatible_domains=["restaurant", "hotel", "salon", "*"],
    ),
    "review.publish_response": ActionCatalogEntry(
        key="review.publish_response",
        label="Publish review response",
        description="Publish the operator's reply to a customer review.",
        integration_kind="mock_external",
        mock_target="review",
        can_undo=True,
        mutates=True,
        default_payload_schema=_REVIEW_RESPONSE_PAYLOAD_SCHEMA,
        compatible_domains=["restaurant", "hotel", "*"],
    ),
    # --- New entries on existing buckets -------------------------------------
    "booking.reschedule": ActionCatalogEntry(
        key="booking.reschedule",
        label="Reschedule booking",
        description="Move an existing booking to a different date or time.",
        integration_kind="mock_external",
        mock_target="booking",
        can_undo=True,
        mutates=True,
        default_payload_schema=_BOOKING_RESCHEDULE_PAYLOAD_SCHEMA,
        compatible_domains=["restaurant", "hotel", "dentist", "salon", "gym", "*"],
    ),
    "crm.create_lead": ActionCatalogEntry(
        key="crm.create_lead",
        label="Create CRM lead",
        description="Add the caller as a new lead in the CRM pipeline.",
        integration_kind="mock_external",
        mock_target="crm",
        can_undo=True,
        mutates=True,
        default_payload_schema=_LEAD_PAYLOAD_SCHEMA,
        compatible_domains=["realestate", "legal", "gym", "*"],
    ),
    "crm.create_ticket": ActionCatalogEntry(
        key="crm.create_ticket",
        label="Open CRM ticket",
        description="Open a support / case ticket so the team can follow up after the call.",
        integration_kind="mock_external",
        mock_target="crm",
        can_undo=True,
        mutates=True,
        default_payload_schema=_TICKET_PAYLOAD_SCHEMA,
        compatible_domains=["legal", "bodyshop", "*"],
    ),
    "email.send_quote": ActionCatalogEntry(
        key="email.send_quote",
        label="Send quote by email",
        description="Email the caller a written quote or proposal.",
        integration_kind="mock_external",
        mock_target="email",
        can_undo=False,
        default_payload_schema=_EMAIL_QUOTE_PAYLOAD_SCHEMA,
        compatible_domains=["legal", "bodyshop", "events", "realestate", "*"],
    ),
}


def get(key: str) -> Optional[ActionCatalogEntry]:
    return CATALOG.get(key)


def available_keys() -> list[str]:
    """Returns every key in the catalog (mock + internal).

    Used by the template_validator: a template that lists an action key
    not in the catalog is flagged because the executor would refuse it.
    """
    return sorted(CATALOG.keys())


def is_simulated(action_key: str) -> bool:
    entry = CATALOG.get(action_key)
    if entry is None:
        # Unknown actions land as `mock_external` in the executor's
        # MOCK_REGISTRY check; treat them as simulated for UI honesty.
        return True
    return entry.integration_kind == "mock_external"


def can_undo(action_key: str) -> bool:
    entry = CATALOG.get(action_key)
    if entry is None:
        return False
    return entry.can_undo


def mutates(action_key: str) -> bool:
    """True when the action creates / modifies / deletes records in its target.

    Used by `action_executor` (audit step + ExecutedAction.result["mutates"])
    and by `tools/action_tool._format_action_docstring` (Gemini tool docstring).
    Unknown keys default to False — the executor will reject them earlier
    anyway because they are not in the template's `action_types`.
    """
    entry = CATALOG.get(action_key)
    if entry is None:
        return False
    return entry.mutates


def aggregate_integrations(
    catalog: Optional[dict[str, ActionCatalogEntry]] = None,
) -> list[dict[str, Any]]:
    """Group every catalog entry by its target bucket — the data behind
    `GET /api/v1/integrations` and the read-only Integrations drawer screen.

    `mock_external` actions are bucketed by `mock_target`; `internal_real`
    actions are bucketed by the prefix of `internal_handler` before the
    first `.` (so `customer_profile.apply_update` → bucket `customer_profile`,
    NOT the full handler path).

    The function is **pure**: takes no I/O, hits no DB, raises nothing for
    a well-formed catalog. Tests should call it directly instead of booting
    the FastAPI lifespan.

    Returns a list of dicts shaped like `IntegrationSummary`:
      `{key, label, kind, action_count}`
    sorted alphabetically by `key` for stable output.
    """
    cat = catalog if catalog is not None else CATALOG
    buckets: dict[str, dict[str, Any]] = {}

    for entry in cat.values():
        if entry.integration_kind == "mock_external":
            if not entry.mock_target:
                continue
            bucket_key = entry.mock_target
            kind = "simulated"
        else:  # internal_real
            if not entry.internal_handler:
                continue
            bucket_key = entry.internal_handler.split(".", 1)[0]
            kind = "live"

        existing = buckets.get(bucket_key)
        if existing is None:
            buckets[bucket_key] = {
                "key": bucket_key,
                "label": _BUCKET_LABELS.get(
                    bucket_key, bucket_key.replace("_", " ").title()
                ),
                "kind": kind,
                "action_count": 1,
            }
        else:
            existing["action_count"] += 1

    return sorted(buckets.values(), key=lambda b: b["key"])
