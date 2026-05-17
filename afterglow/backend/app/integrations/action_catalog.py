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


CATALOG: dict[str, ActionCatalogEntry] = {
    "booking.create": ActionCatalogEntry(
        key="booking.create",
        label="Create booking",
        description="Schedule a reservation in the venue's booking system.",
        integration_kind="mock_external",
        mock_target="booking",
        can_undo=True,
        mutates=True,
        compatible_domains=["restaurant", "*"],
    ),
    "booking.cancel": ActionCatalogEntry(
        key="booking.cancel",
        label="Cancel booking",
        description="Cancel a previously created booking.",
        integration_kind="mock_external",
        mock_target="booking",
        can_undo=False,  # cancellation is the undo itself
        mutates=True,
        compatible_domains=["restaurant", "*"],
    ),
    "appointment.create": ActionCatalogEntry(
        key="appointment.create",
        label="Create appointment",
        description="Schedule an appointment slot.",
        integration_kind="mock_external",
        mock_target="booking",
        can_undo=True,
        mutates=True,
        compatible_domains=["dentist", "*"],
    ),
    "appointment.create_inspection": ActionCatalogEntry(
        key="appointment.create_inspection",
        label="Schedule inspection",
        description="Reserve a slot for a damage inspection or quote.",
        integration_kind="mock_external",
        mock_target="booking",
        can_undo=True,
        mutates=True,
        compatible_domains=["bodyshop", "*"],
    ),
    "whatsapp.send_confirmation": ActionCatalogEntry(
        key="whatsapp.send_confirmation",
        label="Send WhatsApp confirmation",
        description="Send a confirmation message to the caller's WhatsApp.",
        integration_kind="mock_external",
        mock_target="whatsapp",
        can_undo=False,  # sent messages cannot be unsent
    ),
    "whatsapp.request_photos": ActionCatalogEntry(
        key="whatsapp.request_photos",
        label="Request damage photos",
        description="Ask the caller to send photos via WhatsApp.",
        integration_kind="mock_external",
        mock_target="whatsapp",
        can_undo=False,
        compatible_domains=["bodyshop", "*"],
    ),
    "sms.send_reminder": ActionCatalogEntry(
        key="sms.send_reminder",
        label="Send SMS reminder",
        description="Send the caller an SMS reminder for the upcoming appointment.",
        integration_kind="mock_external",
        mock_target="whatsapp",
        can_undo=False,
    ),
    "email.send": ActionCatalogEntry(
        key="email.send",
        label="Send email",
        description="Send the caller a follow-up email.",
        integration_kind="mock_external",
        mock_target="email",
        can_undo=False,
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
        compatible_domains=["bodyshop", "*"],
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
    and by `action_planner._format_action_docstring` (Gemini tool docstring).
    Unknown keys default to False — the executor will reject them earlier
    anyway because they are not in the template's `action_types`.
    """
    entry = CATALOG.get(action_key)
    if entry is None:
        return False
    return entry.mutates
