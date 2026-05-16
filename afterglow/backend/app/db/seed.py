"""Seed demo data: 3 template presets (restaurant/dentist/bodyshop) + sample customers.

Single-tenant: there is no Business row. The active template is what drives the
pipeline; the others are inactive presets the operator can switch to from the
dashboard.

The shape below is the v2 schema landed in migration 0006:
- `FieldDefinition` carries `pii_class`, `confidence_threshold`, `extractor_hint`,
  `depends_on`.
- `ActionDefinition` carries `preconditions`, `confidence_threshold`, `mutates`,
  `evidence_required`, `payload_schema` (JSONSchema feeding both the typed ADK
  FunctionDeclaration and the `action_executor` payload validation).
- `prompt_hints` is a JSON array of `{when, then}` rules, evaluated against the
  caller's prior structured fields before the analyzer prompt is built.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.engine import SessionLocal
from app.db.models import Customer, Template


RESTAURANT_TEMPLATE = {
    "name": "Standard booking",
    "domain_hint": "restaurant",
    "description": "Phone bookings for an Italian restaurant.",
    "fields_schema": [
        {
            "key": "party_size",
            "type": "integer",
            "label": "Number of guests",
            "required": True,
            "pii_class": "none",
            "extractor_hint": "regex",
        },
        {
            "key": "booking_date",
            "type": "date",
            "label": "Date",
            "required": True,
            "pii_class": "none",
            "extractor_hint": "regex",
        },
        {
            "key": "booking_time",
            "type": "time",
            "label": "Time",
            "required": True,
            "pii_class": "none",
            "extractor_hint": "regex",
            "depends_on": ["booking_date"],
        },
        {
            "key": "customer_name",
            "type": "string",
            "label": "Name",
            "required": True,
            "pii_class": "contact",
            "extractor_hint": "freeform",
        },
        {
            "key": "allergies",
            "type": "string_list",
            "label": "Allergies",
            "required": False,
            "sensitive": True,
            "pii_class": "health",
            "confidence_threshold": 0.90,
            "extractor_hint": "freeform",
        },
        {
            "key": "seating_preference",
            "type": "string",
            "label": "Seating preference",
            "required": False,
            "extractor_hint": "freeform",
        },
        {
            "key": "occasion",
            "type": "string",
            "label": "Special occasion",
            "required": False,
            "extractor_hint": "freeform",
        },
        {
            "key": "callback_channel",
            "type": "enum",
            "label": "Confirmation channel",
            "options": ["whatsapp", "sms", "email", "none"],
            "extractor_hint": "enum",
        },
    ],
    "action_types": [
        {
            "key": "booking.create",
            "label": "Create booking",
            "execution_mode": "auto",
            "mock_target": "booking",
            "preconditions": ["party_size", "booking_date", "booking_time", "customer_name"],
            "confidence_threshold": 0.75,
            "mutates": True,
            "evidence_required": True,
            "payload_schema": {
                "type": "object",
                "properties": {
                    "party_size": {"type": "integer", "minimum": 1},
                    "booking_date": {"type": "string", "format": "date"},
                    "booking_time": {"type": "string", "format": "time"},
                    "customer_name": {"type": "string"},
                    "seating_preference": {"type": "string"},
                    "occasion": {"type": "string"},
                },
                "required": ["party_size", "booking_date", "booking_time", "customer_name"],
                "additionalProperties": False,
            },
        },
        {
            "key": "whatsapp.send_confirmation",
            "label": "Send WhatsApp confirmation",
            "execution_mode": "auto",
            "mock_target": "whatsapp",
            "preconditions": ["customer_name", "booking_date", "booking_time"],
            "confidence_threshold": 0.70,
            "mutates": False,
            "evidence_required": False,
            "payload_schema": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "booking_date": {"type": "string", "format": "date"},
                    "booking_time": {"type": "string", "format": "time"},
                    "channel": {"type": "string", "enum": ["whatsapp", "sms", "email"]},
                },
                "required": ["customer_name"],
                "additionalProperties": False,
            },
        },
        {
            "key": "customer.update_profile",
            "label": "Update customer profile",
            "execution_mode": "auto",
            "mock_target": "crm",
            "preconditions": ["customer_name"],
            "confidence_threshold": 0.70,
            "mutates": False,
            "evidence_required": False,
            "payload_schema": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "allergies": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["customer_name"],
                "additionalProperties": False,
            },
        },
        {
            "key": "booking.cancel",
            "label": "Cancel booking",
            "execution_mode": "manual-only",
            "mock_target": "booking",
            "preconditions": ["booking_date"],
            "mutates": True,
            "evidence_required": True,
        },
    ],
    "custom_dictionary": [
        "celiac", "gluten", "lactose", "intolerance", "Nebbiolo", "Barolo",
        "table", "covers", "tasting menu", "vegan", "vegetarian",
    ],
    "prompt_hints": [
        {
            "when": "always",
            "then": "Extract values literally from the conversation. Do not infer party_size from vague phrases like 'a small group'.",
        },
        {
            "when": "field.allergies is not null",
            "then": "Confirm allergies verbatim and require an evidence span; health-class data requires confidence >= 0.90.",
        },
    ],
}

DENTIST_TEMPLATE = {
    "name": "Appointment intake",
    "domain_hint": "dentist",
    "description": "Phone intake for a dental clinic — handle existing patients, new requests and emergencies.",
    "fields_schema": [
        {
            "key": "patient_name",
            "type": "string",
            "label": "Patient name",
            "required": True,
            "pii_class": "contact",
            "extractor_hint": "freeform",
        },
        {
            "key": "is_new_patient",
            "type": "boolean",
            "label": "New patient?",
            "required": True,
            "extractor_hint": "regex",
        },
        {
            "key": "reason",
            "type": "string",
            "label": "Reason for visit",
            "required": True,
            "sensitive": True,
            "pii_class": "health",
            "confidence_threshold": 0.90,
            "extractor_hint": "freeform",
        },
        {
            "key": "urgency",
            "type": "enum",
            "label": "Urgency",
            "options": ["routine", "soon", "urgent", "emergency"],
            "extractor_hint": "enum",
        },
        {
            "key": "preferred_date",
            "type": "date",
            "label": "Preferred date",
            "extractor_hint": "regex",
        },
        {
            "key": "preferred_time_window",
            "type": "string",
            "label": "Preferred time window",
            "depends_on": ["preferred_date"],
            "extractor_hint": "freeform",
        },
    ],
    "action_types": [
        {
            "key": "appointment.create",
            "label": "Create appointment",
            "execution_mode": "auto",
            "mock_target": "booking",
            "preconditions": ["patient_name", "urgency"],
            "confidence_threshold": 0.75,
            "mutates": True,
            "evidence_required": True,
            "payload_schema": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "urgency": {
                        "type": "string",
                        "enum": ["routine", "soon", "urgent", "emergency"],
                    },
                    "preferred_date": {"type": "string", "format": "date"},
                    "preferred_time_window": {"type": "string"},
                    "is_new_patient": {"type": "boolean"},
                },
                "required": ["patient_name", "urgency"],
                "additionalProperties": False,
            },
        },
        {
            "key": "patient.update_profile",
            "label": "Update patient profile",
            "execution_mode": "manual-only",
            "mock_target": "crm",
            "preconditions": ["patient_name"],
            "mutates": False,
            "evidence_required": False,
        },
        {
            "key": "sms.send_reminder",
            "label": "Send SMS reminder",
            "execution_mode": "auto",
            "mock_target": "whatsapp",
            "preconditions": ["patient_name", "preferred_date"],
            "confidence_threshold": 0.70,
            "mutates": False,
            "evidence_required": False,
            "payload_schema": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "preferred_date": {"type": "string", "format": "date"},
                    "preferred_time_window": {"type": "string"},
                },
                "required": ["patient_name", "preferred_date"],
                "additionalProperties": False,
            },
        },
    ],
    "custom_dictionary": [
        "dental hygiene", "cavity", "extraction", "implant", "orthodontics",
        "root canal", "crown", "filling",
    ],
    "prompt_hints": [
        {
            "when": "always",
            "then": "Health-related fields are sensitive. Quote the patient verbatim in evidence and never paraphrase clinical descriptions.",
        },
        {
            "when": "field.urgency == 'emergency'",
            "then": "Set appointment.create payload with preferred_date=today; schedule sms.send_reminder immediately.",
        },
    ],
}

BODYSHOP_TEMPLATE = {
    "name": "Damage quote intake",
    "domain_hint": "bodyshop",
    "description": "Phone intake for a body shop — quotes, inspections, insurance claims.",
    "fields_schema": [
        {
            "key": "customer_name",
            "type": "string",
            "label": "Customer name",
            "required": True,
            "pii_class": "contact",
            "extractor_hint": "freeform",
        },
        {
            "key": "vehicle_make_model",
            "type": "string",
            "label": "Vehicle make/model",
            "required": True,
            "extractor_hint": "freeform",
        },
        {
            "key": "license_plate",
            "type": "string",
            "label": "License plate",
            "pii_class": "identity",
            "confidence_threshold": 0.85,
            "extractor_hint": "regex",
        },
        {
            "key": "damage_type",
            "type": "string",
            "label": "Damage description",
            "extractor_hint": "freeform",
        },
        {
            "key": "insurance_involved",
            "type": "boolean",
            "label": "Insurance claim?",
            "extractor_hint": "regex",
        },
        {
            "key": "drivable",
            "type": "boolean",
            "label": "Vehicle drivable?",
            "extractor_hint": "regex",
        },
    ],
    "action_types": [
        {
            "key": "appointment.create_inspection",
            "label": "Schedule inspection",
            "execution_mode": "auto",
            "mock_target": "booking",
            "preconditions": ["customer_name", "vehicle_make_model"],
            "confidence_threshold": 0.75,
            "mutates": True,
            "evidence_required": True,
            "payload_schema": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "vehicle_make_model": {"type": "string"},
                    "license_plate": {"type": "string"},
                    "damage_type": {"type": "string"},
                    "drivable": {"type": "boolean"},
                },
                "required": ["customer_name", "vehicle_make_model"],
                "additionalProperties": False,
            },
        },
        {
            "key": "whatsapp.request_photos",
            "label": "Request damage photos",
            "execution_mode": "auto",
            "mock_target": "whatsapp",
            "preconditions": ["customer_name"],
            "confidence_threshold": 0.65,
            "mutates": False,
            "evidence_required": False,
            "payload_schema": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["customer_name"],
                "additionalProperties": False,
            },
        },
        {
            "key": "case.open_insurance",
            "label": "Open insurance case",
            "execution_mode": "manual-only",
            "mock_target": "crm",
            "preconditions": ["customer_name", "license_plate", "damage_type"],
            "mutates": True,
            "evidence_required": True,
        },
    ],
    "custom_dictionary": [
        "bumper", "bodywork", "accident", "appraiser", "deductible", "plate",
        "fender", "panel", "dent", "scratch",
    ],
    "prompt_hints": [
        {
            "when": "always",
            "then": "Italian license plates follow AB123CD; preserve case and spacing exactly as spoken.",
        },
        {
            "when": "field.license_plate is null",
            "then": "Queue whatsapp.request_photos with reason='missing license plate'.",
        },
        {
            "when": "field.insurance_involved == 'true'",
            "then": "Flag case.open_insurance for manual review and capture the insurer name in damage_type evidence.",
        },
    ],
}


async def seed():
    async with SessionLocal() as session:
        existing = (await session.execute(select(Template))).scalars().all()
        if existing:
            print(f"[seed] {len(existing)} templates already present, skipping.")
            return

        # Restaurant is the active preset out of the box; the others are
        # selectable from the dashboard's Templates screen.
        for tpl, is_active in (
            (RESTAURANT_TEMPLATE, True),
            (DENTIST_TEMPLATE, False),
            (BODYSHOP_TEMPLATE, False),
        ):
            session.add(
                Template(
                    id=uuid.uuid4(),
                    name=tpl["name"],
                    version=1,
                    description=tpl["description"],
                    domain_hint=tpl["domain_hint"],
                    fields_schema=tpl["fields_schema"],
                    action_types=tpl["action_types"],
                    custom_dictionary=tpl["custom_dictionary"],
                    prompt_hints=tpl["prompt_hints"],
                    is_active=is_active,
                    is_seed=True,
                )
            )

        # Two known customers on the restaurant scenario for cross-call demo.
        session.add(
            Customer(
                id=uuid.uuid4(),
                phone_e164="+15551112233",
                display_name="Mark Ross",
                preferred_language="en",
                tags=["repeat", "gluten_free"],
                memory_summary=(
                    "Repeat customer, gluten intolerant. Last booking: party of "
                    "4, quiet table."
                ),
                total_calls=2,
                last_call_at=datetime(2026, 5, 7, 20, 30, tzinfo=timezone.utc),
                is_seed=True,
            )
        )
        session.add(
            Customer(
                id=uuid.uuid4(),
                phone_e164="+15554445566",
                display_name="Julia White",
                preferred_language="en",
                tags=["vip", "anniversary"],
                memory_summary=(
                    "VIP customer, prefers the table by the window. Celebrating "
                    "anniversary on May 20."
                ),
                total_calls=1,
                last_call_at=datetime(2026, 4, 15, 21, 0, tzinfo=timezone.utc),
                is_seed=True,
            )
        )

        await session.commit()
        print("[seed] Demo data inserted.")


if __name__ == "__main__":
    asyncio.run(seed())
