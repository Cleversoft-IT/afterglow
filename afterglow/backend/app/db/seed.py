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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.engine import SessionLocal
from app.db.models import (
    AuditLog,
    Call,
    Customer,
    ExecutedAction,
    ExtractedFields,
    Template,
)


# Bundled demo MP3s shipped inside the backend container at /app/sample_audio/.
# The Simulator UI reads `simulation_config.audio_url` and the Calls endpoint
# /simulation/audio serves the file straight from this path. Seed templates
# get the bundled audio out of the box; custom templates have to generate or
# upload their own (see /simulation/script + /generate-audio + /upload-audio).
_SAMPLE_AUDIO_DIR = Path(__file__).resolve().parents[2] / "sample_audio"


def _bundled_simulation_config(
    *,
    domain_file: str,
    caller_name: str,
    caller_phone_e164: str,
    operator_voice: str,
    caller_voice: str,
    lines: list[tuple[str, str]],
) -> dict:
    """Build a simulation_config dict for one of the three bundled seeds."""
    return {
        "caller_name": caller_name,
        "caller_phone_e164": caller_phone_e164,
        "script_turns": [
            {
                "speaker": speaker,
                "voice": operator_voice if speaker == "operator" else caller_voice,
                "text": text,
            }
            for speaker, text in lines
        ],
        "audio_url": str(_SAMPLE_AUDIO_DIR / domain_file),
        "audio_status": "ready",
        "audio_generated_at": "2026-05-16T00:00:00Z",
        "audio_source": "bundled",
    }


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
            # internal_real action — executor uses action_catalog to route to
            # `customer_profile.apply_update`. `mock_target` is kept blank so
            # the validator / wizard render the action as "internal" in the UI.
            "mock_target": "internal",
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
                    "seating_preference": {"type": "string"},
                    "occasion": {"type": "string"},
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


def _bundled_simulation_configs() -> dict[str, dict]:
    """Return a domain_hint → simulation_config map for the three seeds.

    Texts mirror what `scripts/generate_demo_audio.py` already encodes into
    the bundled MP3s, so the script_turns shown in the Simulator UI match
    what the operator will actually hear.
    """
    return {
        "restaurant": _bundled_simulation_config(
            domain_file="restaurant.mp3",
            caller_name="Mark Ross",
            caller_phone_e164="+15551112233",
            operator_voice="sarah",
            caller_voice="theo",
            lines=[
                ("operator", "Good evening, La Trattoria. How may I help you?"),
                ("caller", "Hi, I'd like to book a table for Friday evening."),
                ("operator", "Of course. How many people?"),
                ("caller", "Four of us, around eight thirty. My name is Mark."),
                ("operator", "Got it, Mark. Any special requests?"),
                ("caller", "Yes — one person is gluten intolerant. Can you handle that?"),
                ("operator", "Absolutely, the kitchen has a dedicated gluten free menu."),
                ("caller", "Great. Could you confirm by WhatsApp?"),
                ("operator", "Sure, I'll send the confirmation right away. See you Friday!"),
                ("caller", "Thanks, goodbye."),
            ],
        ),
        "dentist": _bundled_simulation_config(
            domain_file="dentist.mp3",
            caller_name="Laura Bennett",
            caller_phone_e164="+15559991122",
            operator_voice="jack",
            caller_voice="megan",
            lines=[
                ("operator", "Greenwood Dental, this is the front desk. How can I help you?"),
                (
                    "caller",
                    "Hi, I urgently need an appointment. My filling came off and I have severe pain in my lower right molar.",
                ),
                ("operator", "I'm sorry to hear that. We can fit you in tomorrow morning. What's your name?"),
                ("caller", "I'm Laura Bennett, you already have my chart on file."),
                ("operator", "Perfect Laura. Do you have insurance coverage?"),
                ("caller", "Yes, BlueCross. I'll send the policy number on WhatsApp."),
                ("operator", "Great. Does nine fifteen tomorrow work for you?"),
                ("caller", "Yes, that's perfect."),
                ("operator", "I'll text you the details. Take care, see you tomorrow."),
                ("caller", "Thank you, goodbye."),
            ],
        ),
        "bodyshop": _bundled_simulation_config(
            domain_file="bodyshop.mp3",
            caller_name="Andrew Green",
            caller_phone_e164="+15558883344",
            operator_voice="megan",
            caller_voice="jack",
            lines=[
                ("operator", "Greenline Auto Body, good afternoon. How can I help?"),
                ("caller", "Hello, I backed into a pole and need to fix the rear bumper of a 2019 Fiat Panda."),
                ("operator", "Have you already opened an insurance claim?"),
                ("caller", "No, I'm not filing one. I'm paying out of pocket — I just need a quote."),
                ("operator", "Got it. When can you come in for the inspection?"),
                ("caller", "I'm free Thursday afternoon. My name is Andrew Green."),
                ("operator", "Let's say two o'clock Thursday. I'll text you the address."),
                ("caller", "Perfect. Thanks for the help."),
                ("operator", "You're welcome. See you Thursday."),
            ],
        ),
    }


async def seed():
    async with SessionLocal() as session:
        existing = (await session.execute(select(Template))).scalars().all()
        if existing:
            print(f"[seed] {len(existing)} templates already present, skipping.")
            return

        # Restaurant is the active preset out of the box; the others are
        # selectable from the dashboard's Templates screen.
        restaurant_id = uuid.uuid4()
        sim_configs = _bundled_simulation_configs()
        for tpl, tpl_id, is_active in (
            (RESTAURANT_TEMPLATE, restaurant_id, True),
            (DENTIST_TEMPLATE, uuid.uuid4(), False),
            (BODYSHOP_TEMPLATE, uuid.uuid4(), False),
        ):
            session.add(
                Template(
                    id=tpl_id,
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
                    simulation_config=sim_configs.get(tpl["domain_hint"]),
                )
            )

        # Two known customers on the restaurant scenario for cross-call demo.
        mark = Customer(
            id=uuid.uuid4(),
            phone_e164="+15551112233",
            display_name="Mark Ross",
            preferred_language="en",
            tags=["repeat", "gluten_free"],
            memory_summary=(
                "Mark prefers a quiet table and is gluten-intolerant. "
                "Last booked party of 4 on 9 May — confirm the same setup if he calls again."
            ),
            total_calls=2,
            last_call_at=datetime(2026, 5, 7, 20, 30, tzinfo=timezone.utc),
            is_seed=True,
        )
        julia = Customer(
            id=uuid.uuid4(),
            phone_e164="+15554445566",
            display_name="Julia White",
            preferred_language="en",
            tags=["vip", "anniversary"],
            memory_summary=(
                "Julia is a VIP, prefers the window table. Celebrating her anniversary "
                "on 20 May — surprise dessert was offered last time."
            ),
            total_calls=1,
            last_call_at=datetime(2026, 4, 15, 21, 0, tzinfo=timezone.utc),
            is_seed=True,
        )
        session.add_all([mark, julia])

        # Flush so the customer IDs are usable for the seeded Call rows.
        await session.flush()

        for spec in _seed_call_specs(restaurant_id, mark.id, julia.id):
            _emit_seeded_call(session, spec)

        await session.commit()
        print(
            f"[seed] Demo data inserted: 3 templates, 2 customers, "
            f"{sum(1 for _ in _seed_call_specs(restaurant_id, mark.id, julia.id))} seeded calls."
        )


# ---------------------------------------------------------------------------
# Seeded calls for Mark / Julia — restaurant scenario
# ---------------------------------------------------------------------------


def _seed_call_specs(restaurant_template_id, mark_id, julia_id):
    """Yield the SeedCallSpec list. Kept as a generator so the count line in
    `seed()` can rerun it cheaply without keeping the full list around."""
    yield {
        "id": uuid.UUID("11111111-1111-4111-8111-000000000001"),
        "customer_id": mark_id,
        "template_id": restaurant_template_id,
        "phone_e164": "+15551112233",
        "phone_display": "Mark Ross",
        "language": "en",
        "created_at": datetime(2026, 4, 20, 19, 45, tzinfo=timezone.utc),
        "transcript": (
            "Operator: Good evening, La Trattoria. How may I help you?\n"
            "Caller: Hi, I'd like to book a table for Wednesday at eight. "
            "My name is Mark, party of two.\n"
            "Operator: Sure, any preference on the table?\n"
            "Caller: Somewhere quiet, please. I'm gluten-intolerant, "
            "could you confirm the gluten-free menu?\n"
            "Operator: Absolutely. I'll WhatsApp you the confirmation. See you Wednesday."
        ),
        "fields": {
            "party_size": 2,
            "booking_date": "2026-04-22",
            "booking_time": "20:00",
            "customer_name": "Mark",
            "allergies": ["gluten"],
            "seating_preference": "quiet table",
            "callback_channel": "whatsapp",
        },
        "confidence": {
            "party_size": 0.96,
            "booking_date": 0.94,
            "booking_time": 0.93,
            "customer_name": 0.92,
            "allergies": 0.95,
            "seating_preference": 0.88,
            "callback_channel": 0.90,
        },
        "evidence": {
            "party_size": "party of two",
            "booking_date": "Wednesday",
            "booking_time": "eight",
            "customer_name": "My name is Mark",
            "allergies": "I'm gluten-intolerant",
            "seating_preference": "Somewhere quiet, please",
            "callback_channel": "I'll WhatsApp you the confirmation",
        },
        "intent": "booking_new",
        "sentiment": "positive",
        "urgency": "routine",
        "briefing": (
            "Mark is gluten-intolerant and prefers quiet tables. "
            "Confirm the gluten-free menu when he calls again."
        ),
        "actions": [
            {
                "action_type": "booking.create",
                "title": "Create booking",
                "summary": "Quiet table for 2 on 22 Apr at 20:00, gluten-free menu",
                "payload": {
                    "party_size": 2,
                    "booking_date": "2026-04-22",
                    "booking_time": "20:00",
                    "customer_name": "Mark",
                    "seating_preference": "quiet table",
                },
                "confidence": 0.93,
                "evidence": ["party of two", "Wednesday at eight"],
                "result": {
                    "booking_id": "BK-DEMO0001",
                    "status": "confirmed",
                    "mock": True,
                    "mutates": True,
                },
            },
            {
                "action_type": "whatsapp.send_confirmation",
                "title": "Send WhatsApp confirmation",
                "summary": "Sent to +1 (555) 111-2233",
                "payload": {
                    "customer_name": "Mark",
                    "booking_date": "2026-04-22",
                    "booking_time": "20:00",
                    "channel": "whatsapp",
                },
                "confidence": 0.91,
                "evidence": ["I'll WhatsApp you the confirmation"],
                "result": {
                    "message_id": "WA-DEMO0001",
                    "status": "sent",
                    "mock": True,
                    "mutates": False,
                },
            },
        ],
    }
    yield {
        "id": uuid.UUID("11111111-1111-4111-8111-000000000002"),
        "customer_id": mark_id,
        "template_id": restaurant_template_id,
        "phone_e164": "+15551112233",
        "phone_display": "Mark Ross",
        "language": "en",
        "created_at": datetime(2026, 5, 7, 20, 30, tzinfo=timezone.utc),
        "transcript": (
            "Operator: La Trattoria, good evening.\n"
            "Caller: Hi, it's Mark. Friday eight-thirty, party of four. "
            "Same as usual — gluten-free, quiet table if you can.\n"
            "Operator: Of course Mark. I'll send the confirmation on WhatsApp.\n"
            "Caller: Thanks, see you Friday."
        ),
        "fields": {
            "party_size": 4,
            "booking_date": "2026-05-09",
            "booking_time": "20:30",
            "customer_name": "Mark",
            "allergies": ["gluten"],
            "seating_preference": "quiet table",
            "occasion": "dinner",
            "callback_channel": "whatsapp",
        },
        "confidence": {
            "party_size": 0.97,
            "booking_date": 0.95,
            "booking_time": 0.96,
            "customer_name": 0.93,
            "allergies": 0.94,
            "seating_preference": 0.86,
            "occasion": 0.72,
            "callback_channel": 0.92,
        },
        "evidence": {
            "party_size": "party of four",
            "booking_date": "Friday",
            "booking_time": "eight-thirty",
            "customer_name": "it's Mark",
            "allergies": "gluten-free",
            "seating_preference": "quiet table if you can",
            "occasion": "Friday eight-thirty",
            "callback_channel": "I'll send the confirmation on WhatsApp",
        },
        "intent": "booking_new",
        "sentiment": "positive",
        "urgency": "routine",
        "briefing": (
            "Mark prefers a quiet table and is gluten-intolerant. "
            "Last booked party of 4 on 9 May — confirm the same setup if he calls again."
        ),
        "actions": [
            {
                "action_type": "booking.create",
                "title": "Create booking",
                "summary": "Quiet table for 4 on 9 May at 20:30, gluten-free menu",
                "payload": {
                    "party_size": 4,
                    "booking_date": "2026-05-09",
                    "booking_time": "20:30",
                    "customer_name": "Mark",
                    "seating_preference": "quiet table",
                },
                "confidence": 0.95,
                "evidence": ["Friday eight-thirty", "party of four"],
                "result": {
                    "booking_id": "BK-DEMO0002",
                    "status": "confirmed",
                    "mock": True,
                    "mutates": True,
                },
            },
            {
                "action_type": "whatsapp.send_confirmation",
                "title": "Send WhatsApp confirmation",
                "summary": "Sent to +1 (555) 111-2233",
                "payload": {
                    "customer_name": "Mark",
                    "booking_date": "2026-05-09",
                    "booking_time": "20:30",
                    "channel": "whatsapp",
                },
                "confidence": 0.92,
                "evidence": ["I'll send the confirmation on WhatsApp"],
                "result": {
                    "message_id": "WA-DEMO0002",
                    "status": "sent",
                    "mock": True,
                    "mutates": False,
                },
            },
            {
                "action_type": "customer.update_profile",
                "title": "Update customer profile",
                "summary": "Tagged as `repeat`, gluten-free preference preserved",
                "payload": {
                    "customer_name": "Mark",
                    "tags": ["repeat"],
                    "allergies": ["gluten"],
                },
                "confidence": 0.88,
                "evidence": ["Same as usual — gluten-free"],
                "result": {
                    "applied": True,
                    "tags_added": ["repeat"],
                    "mock": False,
                    "mutates": False,
                },
            },
        ],
    }
    yield {
        "id": uuid.UUID("11111111-1111-4111-8111-000000000003"),
        "customer_id": julia_id,
        "template_id": restaurant_template_id,
        "phone_e164": "+15554445566",
        "phone_display": "Julia White",
        "language": "en",
        "created_at": datetime(2026, 4, 15, 21, 0, tzinfo=timezone.utc),
        "transcript": (
            "Operator: La Trattoria, good evening.\n"
            "Caller: Hi, it's Julia White. I'd like to book for our anniversary "
            "on 20 May, party of two, by the window please.\n"
            "Operator: Of course Julia. Anything special you'd like us to prepare?\n"
            "Caller: A surprise dessert would be lovely.\n"
            "Operator: Wonderful. We'll see you on the 20th."
        ),
        "fields": {
            "party_size": 2,
            "booking_date": "2026-05-20",
            "booking_time": "20:30",
            "customer_name": "Julia White",
            "seating_preference": "window table",
            "occasion": "anniversary",
            "callback_channel": "none",
        },
        "confidence": {
            "party_size": 0.97,
            "booking_date": 0.96,
            "booking_time": 0.78,
            "customer_name": 0.94,
            "seating_preference": 0.92,
            "occasion": 0.95,
            "callback_channel": 0.65,
        },
        "evidence": {
            "party_size": "party of two",
            "booking_date": "20 May",
            "booking_time": "anniversary",
            "customer_name": "it's Julia White",
            "seating_preference": "by the window please",
            "occasion": "for our anniversary",
            "callback_channel": "We'll see you on the 20th",
        },
        "intent": "booking_new",
        "sentiment": "positive",
        "urgency": "routine",
        "briefing": (
            "Julia is a VIP, prefers the window table. Celebrating her anniversary "
            "on 20 May — surprise dessert was offered last time."
        ),
        "actions": [
            {
                "action_type": "booking.create",
                "title": "Create booking",
                "summary": "Window table for 2 on 20 May, anniversary",
                "payload": {
                    "party_size": 2,
                    "booking_date": "2026-05-20",
                    "booking_time": "20:30",
                    "customer_name": "Julia White",
                    "seating_preference": "window table",
                    "occasion": "anniversary",
                },
                "confidence": 0.92,
                "evidence": ["20 May, party of two, by the window"],
                "result": {
                    "booking_id": "BK-DEMO0003",
                    "status": "confirmed",
                    "mock": True,
                    "mutates": True,
                },
            },
            {
                "action_type": "customer.update_profile",
                "title": "Update customer profile",
                "summary": "Tagged `vip` + `anniversary`",
                "payload": {
                    "customer_name": "Julia White",
                    "tags": ["vip", "anniversary"],
                },
                "confidence": 0.86,
                "evidence": ["for our anniversary"],
                "result": {
                    "applied": True,
                    "tags_added": ["vip", "anniversary"],
                    "mock": False,
                    "mutates": False,
                },
            },
        ],
    }


def _emit_seeded_call(session, spec) -> None:
    """Insert one Call + ExtractedFields + ExecutedAction[] + audit_log rows
    for a seed scenario. Idempotent via fixed UUIDs (re-running seed on an
    empty DB always produces the same IDs)."""
    call = Call(
        id=spec["id"],
        customer_id=spec["customer_id"],
        template_id=spec["template_id"],
        phone_e164=spec["phone_e164"],
        audio_url=None,
        detected_language=spec["language"],
        raw_transcript={"text": spec["transcript"], "speakers": [], "language": spec["language"]},
        status="completed",
        started_at=spec["created_at"],
        completed_at=spec["created_at"] + timedelta(seconds=45),
        is_seed=True,
        created_at=spec["created_at"],
    )
    session.add(call)

    session.add(
        ExtractedFields(
            id=uuid.uuid4(),
            call_id=spec["id"],
            fields=spec["fields"],
            confidence=spec["confidence"],
            evidence=spec["evidence"],
            intent=spec["intent"],
            sentiment=spec["sentiment"],
            urgency=spec["urgency"],
            briefing_snapshot=spec["briefing"],
            created_at=spec["created_at"] + timedelta(seconds=30),
        )
    )

    for offset, raw_action in enumerate(spec["actions"]):
        session.add(
            ExecutedAction(
                id=uuid.uuid4(),
                call_id=spec["id"],
                customer_id=spec["customer_id"],
                action_type=raw_action["action_type"],
                title=raw_action["title"],
                summary=raw_action.get("summary"),
                payload=raw_action["payload"],
                result=raw_action.get("result"),
                confidence=raw_action.get("confidence"),
                evidence=raw_action.get("evidence"),
                execution_mode="auto",
                status="executed",
                is_seed=True,
                created_at=spec["created_at"] + timedelta(seconds=35 + offset),
            )
        )

    # Lean audit trail so the Audit tab is not empty on fresh install.
    audit_steps = [
        ("speechmatics", "tool_call", "success"),
        ("call_analyzer", "llm_call", "success"),
        ("pii_sanitizer", "pii_policy_applied", "success"),
        ("action_planner", "agent_loop", "success"),
        ("action_executor", "action_exec", "success"),
        ("memory_updater", "tool_call", "success"),
    ]
    for idx, (agent, step_type, status) in enumerate(audit_steps):
        session.add(
            AuditLog(
                id=uuid.uuid4(),
                call_id=spec["id"],
                agent_name=agent,
                step_type=step_type,
                model="gemini-3.1-flash-lite" if agent.startswith("call_") or agent == "action_planner" else None,
                status=status,
                created_at=spec["created_at"] + timedelta(seconds=10 + idx * 5),
            )
        )


if __name__ == "__main__":
    asyncio.run(seed())
