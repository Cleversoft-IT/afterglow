"""Seed demo data: 3 template presets (restaurant/dentist/bodyshop) + sample customers.

Single-tenant: there is no Business row. The active template is what drives the
pipeline; the others are inactive presets the operator can switch to from the
dashboard.

Template shape (simplified 2026-05-17, see `project_template_simplified_2026_05_17`):
- `FieldDefinition` carries `confidence_threshold`, `extractor_hint`, `depends_on`.
- `ActionDefinition` carries `preconditions`, `confidence_threshold`,
  `evidence_required`, `payload_schema` (JSONSchema feeding both the typed ADK
  FunctionDeclaration and the `action_executor` payload validation).
- `mock_target` / `mutates` / `integration_kind` / `can_undo` live in
  `app/integrations/action_catalog.py`, not on the template.
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
# Each seed template ships TWO recordings — `<domain>_existing.mp3` for the
# "Call from existing customer" simulator button (caller already known by
# phone, no self-introduction) and `<domain>_new.mp3` for the new-caller
# button (first-time caller, full self-introduction). Custom wizard-built
# templates still produce ONE recording reused across both modes until
# the wizard is upgraded.
_SAMPLE_AUDIO_DIR = Path(__file__).resolve().parents[2] / "sample_audio"


def _bundled_scenario(
    *,
    domain_file: str,
    caller_name: str | None,
    caller_phone_e164: str | None,
    operator_voice: str,
    caller_voice: str,
    lines: list[tuple[str, str]],
) -> dict:
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


def _bundled_simulation_config(
    *,
    domain_file_existing: str,
    domain_file_new: str,
    caller_name_existing: str,
    caller_phone_e164_existing: str,
    operator_voice: str,
    caller_voice_existing: str,
    caller_voice_new: str,
    existing_lines: list[tuple[str, str]],
    new_lines: list[tuple[str, str]],
) -> dict:
    """Build a simulation_config dict with two scenarios for one bundled seed."""
    return {
        "scenarios": {
            "existing": _bundled_scenario(
                domain_file=domain_file_existing,
                caller_name=caller_name_existing,
                caller_phone_e164=caller_phone_e164_existing,
                operator_voice=operator_voice,
                caller_voice=caller_voice_existing,
                lines=existing_lines,
            ),
            "new": _bundled_scenario(
                domain_file=domain_file_new,
                caller_name=None,
                caller_phone_e164=None,
                operator_voice=operator_voice,
                caller_voice=caller_voice_new,
                lines=new_lines,
            ),
        }
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
            "extractor_hint": "regex",
        },
        {
            "key": "booking_date",
            "type": "date",
            "label": "Date",
            "required": True,
            "extractor_hint": "regex",
        },
        {
            "key": "booking_time",
            "type": "time",
            "label": "Time",
            "required": True,
            "extractor_hint": "regex",
            "depends_on": ["booking_date"],
        },
        {
            "key": "customer_name",
            "type": "string",
            "label": "Name",
            "required": True,
            "extractor_hint": "freeform",
        },
        {
            "key": "allergies",
            "type": "string_list",
            "label": "Allergies",
            "required": False,
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
            "preconditions": ["party_size", "booking_date", "booking_time", "customer_name"],
            "confidence_threshold": 0.75,
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
            "preconditions": ["customer_name", "booking_date", "booking_time"],
            "confidence_threshold": 0.70,
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
            # `customer_profile.apply_update`.
            "preconditions": ["customer_name"],
            "confidence_threshold": 0.70,
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
            "preconditions": ["booking_date"],
            "evidence_required": True,
        },
    ],
    "prompt_hints": [
        {
            "when": "always",
            "then": "Extract values literally from the conversation. Do not infer party_size from vague phrases like 'a small group'.",
        },
        {
            "when": "field.allergies is not null",
            "then": "Confirm allergies verbatim and require an evidence span (confidence >= 0.90).",
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
            "preconditions": ["patient_name", "urgency"],
            "confidence_threshold": 0.75,
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
            "preconditions": ["patient_name"],
            "evidence_required": False,
        },
        {
            "key": "sms.send_reminder",
            "label": "Send SMS reminder",
            "execution_mode": "auto",
            "preconditions": ["patient_name", "preferred_date"],
            "confidence_threshold": 0.70,
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
    "prompt_hints": [
        {
            "when": "always",
            "then": "Quote the patient verbatim in evidence and never paraphrase clinical descriptions.",
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
            "preconditions": ["customer_name", "vehicle_make_model"],
            "confidence_threshold": 0.75,
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
            "preconditions": ["customer_name"],
            "confidence_threshold": 0.65,
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
            "preconditions": ["customer_name", "license_plate", "damage_type"],
            "evidence_required": True,
        },
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

    Texts mirror what `scripts/generate_demo_audio.py` encodes into the six
    bundled MP3s, so the script_turns shown in the Simulator UI match what
    the operator will actually hear in each mode.
    """
    return {
        "restaurant": _bundled_simulation_config(
            domain_file_existing="restaurant_existing.mp3",
            domain_file_new="restaurant_new.mp3",
            caller_name_existing="Mark Ross",
            caller_phone_e164_existing="+15551112233",
            operator_voice="sarah",
            caller_voice_existing="theo",
            caller_voice_new="megan",
            existing_lines=[
                ("operator", "La Trattoria, good evening, this is Sarah."),
                ("caller", "Hi Sarah, it's Mark."),
                ("operator", "Hi Mark, lovely to hear you. The usual Friday booking?"),
                ("caller", "Yes please, party of four, around eight thirty."),
                ("operator", "Quiet table and gluten free menu, like last time?"),
                ("caller", "Exactly, same setup. Could you confirm on WhatsApp?"),
                ("operator", "Of course, I'll send it over in a minute. See you Friday."),
                ("caller", "Thanks Sarah, see you Friday."),
            ],
            new_lines=[
                ("operator", "La Trattoria, good evening, this is Sarah. How can I help?"),
                ("caller", "Hi, I've never booked with you before. I'd like a table for Saturday evening."),
                ("operator", "Of course. Could I have your name please?"),
                ("caller", "It's Hannah Clarke."),
                ("operator", "Thanks Hannah. How many guests, and what time?"),
                ("caller", "Three of us, around seven forty five."),
                ("operator", "Noted. Any allergies or special requests we should know about?"),
                ("caller", "Yes, one of us is lactose intolerant. Window table if you have one."),
                ("operator", "All set. I'll text you the confirmation by SMS. See you Saturday."),
                ("caller", "Perfect, thank you. Goodbye."),
            ],
        ),
        "dentist": _bundled_simulation_config(
            domain_file_existing="dentist_existing.mp3",
            domain_file_new="dentist_new.mp3",
            caller_name_existing="Laura Bennett",
            caller_phone_e164_existing="+15559991122",
            operator_voice="jack",
            caller_voice_existing="megan",
            caller_voice_new="sarah",
            existing_lines=[
                ("operator", "Greenwood Dental, this is Jack at the front desk."),
                ("caller", "Hi Jack, it's Laura."),
                ("operator", "Hi Laura, good to hear from you. What can we do today?"),
                ("caller", "The crown you fitted last month is feeling a little loose, I'd like it checked."),
                ("operator", "I'm sorry to hear that. Same chair as last time, with Dr. Patel?"),
                ("caller", "Yes please, if she has space."),
                ("operator", "She has a slot tomorrow at ten fifteen. Does that work?"),
                ("caller", "Tomorrow at ten fifteen is fine."),
                ("operator", "Booked. I'll WhatsApp you the reminder on your usual number. Take care."),
                ("caller", "Thanks Jack, see you tomorrow."),
            ],
            new_lines=[
                ("operator", "Greenwood Dental, this is Jack. How can I help?"),
                ("caller", "Hi, I'm not a patient here yet. I need an urgent appointment."),
                ("operator", "I'm sorry to hear that. May I have your name?"),
                ("caller", "Sophie Turner. I cracked a molar this morning eating a hard candy."),
                ("operator", "Painful. We can fit you in this afternoon. Is the tooth bleeding?"),
                ("caller", "No bleeding, but it's very sharp pain on the lower right."),
                ("operator", "Understood. Three thirty today with Dr. Patel — does that work?"),
                ("caller", "Yes, three thirty is perfect."),
                ("operator", "I'll text you the address and the new patient form. See you later."),
                ("caller", "Thank you so much, goodbye."),
            ],
        ),
        "bodyshop": _bundled_simulation_config(
            domain_file_existing="bodyshop_existing.mp3",
            domain_file_new="bodyshop_new.mp3",
            caller_name_existing="Andrew Green",
            caller_phone_e164_existing="+15558883344",
            operator_voice="megan",
            caller_voice_existing="jack",
            caller_voice_new="theo",
            existing_lines=[
                ("operator", "Greenline Auto Body, good afternoon, this is Megan."),
                ("caller", "Hey Megan, it's Andrew."),
                ("operator", "Hi Andrew. Is it the Fiat Panda again?"),
                ("caller", "Same car, yeah. I clipped a bollard, the front bumper has a dent and a long scratch."),
                ("operator", "Out of pocket like last time, or going through insurance this round?"),
                ("caller", "Out of pocket, same as before. Just need a quick quote."),
                ("operator", "Thursday afternoon at two works, same bay?"),
                ("caller", "Thursday at two is good. Thanks Megan."),
                ("operator", "See you Thursday, Andrew."),
            ],
            new_lines=[
                ("operator", "Greenline Auto Body, good afternoon, this is Megan. How can I help?"),
                ("caller", "Hi, first time calling you. I had a small fender-bender this morning."),
                ("operator", "Sorry to hear that. May I have your name and the vehicle?"),
                ("caller", "It's Daniel Reed. Twenty twenty Toyota Corolla, plate Bravo Mike six four Lima Whisky."),
                ("operator", "Got it. What's the damage, and is the car drivable?"),
                ("caller", "Rear quarter panel is dented, taillight is cracked. It's drivable, lights still work."),
                ("operator", "Are you opening an insurance claim?"),
                ("caller", "Yes, I've already filed with my insurer."),
                ("operator", "Understood. Could you come in Friday morning at ten for an inspection?"),
                ("caller", "Friday at ten is fine, thank you."),
                ("operator", "Great, I'll text you the address. See you Friday."),
                ("caller", "Thanks, goodbye."),
            ],
        ),
    }


async def seed():
    async with SessionLocal() as session:
        existing = (await session.execute(select(Template))).scalars().all()
        if existing:
            print(
                f"[seed] {len(existing)} templates already present, "
                f"ensuring personal calls."
            )
            await _ensure_personal_calls(session)
            await session.commit()
            return

        # Restaurant is the active preset out of the box; the others are
        # selectable from the dashboard's Templates screen.
        restaurant_id = uuid.uuid4()
        dentist_id = uuid.uuid4()
        bodyshop_id = uuid.uuid4()
        sim_configs = _bundled_simulation_configs()
        for tpl, tpl_id, is_active in (
            (RESTAURANT_TEMPLATE, restaurant_id, True),
            (DENTIST_TEMPLATE, dentist_id, False),
            (BODYSHOP_TEMPLATE, bodyshop_id, False),
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
                    prompt_hints=tpl["prompt_hints"],
                    is_active=is_active,
                    is_seed=True,
                    simulation_config=sim_configs.get(tpl["domain_hint"]),
                )
            )

        # Four known customers — one per (template, returning caller) so the
        # "Call from existing customer" button produces a coherent memory
        # card on every preset, not just the restaurant.
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
        laura = Customer(
            id=uuid.uuid4(),
            phone_e164="+15559991122",
            display_name="Laura Bennett",
            preferred_language="en",
            tags=["returning_patient", "crown"],
            memory_summary=(
                "Laura had a porcelain crown fitted on her lower-right molar on 8 April "
                "by Dr. Patel. Sensitivity has settled; flag any looseness on the next visit."
            ),
            total_calls=1,
            last_call_at=datetime(2026, 4, 8, 9, 30, tzinfo=timezone.utc),
            is_seed=True,
        )
        andrew = Customer(
            id=uuid.uuid4(),
            phone_e164="+15558883344",
            display_name="Andrew Green",
            preferred_language="en",
            tags=["returning_customer", "out_of_pocket"],
            memory_summary=(
                "Andrew drives a 2019 Fiat Panda (plate AB123CD). Pays out of pocket — "
                "no insurance claim. Last visit: rear bumper repair on 3 May, paid invoice INV-DEMO0012."
            ),
            total_calls=1,
            last_call_at=datetime(2026, 5, 3, 14, 0, tzinfo=timezone.utc),
            is_seed=True,
        )
        session.add_all([mark, julia, laura, andrew])

        # Flush so the customer IDs are usable for the seeded Call rows.
        await session.flush()

        call_specs = list(
            _seed_call_specs(
                restaurant_id, dentist_id, bodyshop_id,
                mark.id, julia.id, laura.id, andrew.id,
            )
        )
        for spec in call_specs:
            # Two-phase insert: Postgres rejects the audit_log batch with
            # audit_log_call_id_fkey unless the matching Call has already
            # landed on disk. audit_log.call_id is ON DELETE SET NULL +
            # nullable so SQLAlchemy treats the FK as soft and batches
            # all rows across tables in an order that puts the children
            # first. Flushing between the parent and the children forces
            # the right order.
            _emit_seeded_call_core(session, spec)
            await session.flush()
            _emit_seeded_call_audit(session, spec)
            await session.flush()

        await _ensure_personal_calls(session)
        await session.commit()
        print(
            f"[seed] Demo data inserted: 3 templates, 4 customers, "
            f"{len(call_specs)} seeded calls."
        )


# ---------------------------------------------------------------------------
# Seeded calls — one per (template, returning caller).
#   restaurant: Mark (×2), Julia (×1)
#   dentist:    Laura (×1)
#   bodyshop:   Andrew (×1)
# ---------------------------------------------------------------------------


def _seed_call_specs(
    restaurant_template_id,
    dentist_template_id,
    bodyshop_template_id,
    mark_id,
    julia_id,
    laura_id,
    andrew_id,
):
    """Yield the SeedCallSpec list."""
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
                    "mutates": True,
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
                    "mutates": True,
                },
            },
        ],
    }
    yield {
        "id": uuid.UUID("11111111-1111-4111-8111-000000000004"),
        "customer_id": laura_id,
        "template_id": dentist_template_id,
        "phone_e164": "+15559991122",
        "phone_display": "Laura Bennett",
        "language": "en",
        "created_at": datetime(2026, 4, 8, 9, 30, tzinfo=timezone.utc),
        "transcript": (
            "Operator: Greenwood Dental, this is the front desk.\n"
            "Caller: Hi, it's Laura Bennett. I'm confirming the crown fitting today.\n"
            "Operator: Yes, ten o'clock with Dr. Patel — lower-right molar.\n"
            "Caller: Perfect, I'll be there in twenty minutes."
        ),
        "fields": {
            "patient_name": "Laura Bennett",
            "is_new_patient": False,
            "reason": "crown fitting on lower-right molar",
            "urgency": "soon",
            "preferred_date": "2026-04-08",
            "preferred_time_window": "morning",
        },
        "confidence": {
            "patient_name": 0.95,
            "is_new_patient": 0.92,
            "reason": 0.94,
            "urgency": 0.86,
            "preferred_date": 0.96,
            "preferred_time_window": 0.84,
        },
        "evidence": {
            "patient_name": "it's Laura Bennett",
            "is_new_patient": "Yes, ten o'clock with Dr. Patel",
            "reason": "crown fitting today",
            "urgency": "in twenty minutes",
            "preferred_date": "today",
            "preferred_time_window": "ten o'clock",
        },
        "intent": "appointment_confirm",
        "sentiment": "neutral",
        "urgency": "soon",
        "briefing": (
            "Laura had a porcelain crown fitted on her lower-right molar on 8 April. "
            "Sensitivity settled; flag any looseness on the next visit."
        ),
        "actions": [
            {
                "action_type": "appointment.create",
                "title": "Confirm appointment",
                "summary": "Crown fitting · 8 Apr · 10:00 with Dr. Patel",
                "payload": {
                    "patient_name": "Laura Bennett",
                    "is_new_patient": False,
                    "reason": "crown fitting on lower-right molar",
                    "urgency": "soon",
                    "preferred_date": "2026-04-08",
                    "preferred_time_window": "morning",
                },
                "confidence": 0.93,
                "evidence": ["ten o'clock with Dr. Patel"],
                "result": {
                    "booking_id": "BK-DENT0001",
                    "status": "confirmed",
                    "mock": True,
                    "mutates": True,
                },
            },
        ],
    }
    yield {
        "id": uuid.UUID("11111111-1111-4111-8111-000000000005"),
        "customer_id": andrew_id,
        "template_id": bodyshop_template_id,
        "phone_e164": "+15558883344",
        "phone_display": "Andrew Green",
        "language": "en",
        "created_at": datetime(2026, 5, 3, 14, 0, tzinfo=timezone.utc),
        "transcript": (
            "Operator: Greenline Auto Body, good afternoon.\n"
            "Caller: Hi, it's Andrew. The Panda needs a rear bumper repair.\n"
            "Operator: Same plate, AB123CD? Out of pocket as usual?\n"
            "Caller: Yes, no insurance. When can I bring it in?\n"
            "Operator: Thursday at two, same bay."
        ),
        "fields": {
            "customer_name": "Andrew Green",
            "vehicle_make_model": "2019 Fiat Panda",
            "license_plate": "AB123CD",
            "damage_type": "rear bumper dent",
            "insurance_involved": False,
            "drivable": True,
        },
        "confidence": {
            "customer_name": 0.94,
            "vehicle_make_model": 0.93,
            "license_plate": 0.90,
            "damage_type": 0.88,
            "insurance_involved": 0.96,
            "drivable": 0.80,
        },
        "evidence": {
            "customer_name": "it's Andrew",
            "vehicle_make_model": "The Panda",
            "license_plate": "AB123CD",
            "damage_type": "rear bumper repair",
            "insurance_involved": "no insurance",
            "drivable": "When can I bring it in?",
        },
        "intent": "repair_quote",
        "sentiment": "neutral",
        "urgency": "routine",
        "briefing": (
            "Andrew drives a 2019 Fiat Panda (plate AB123CD). Pays out of pocket — "
            "no insurance claim. Last visit: rear bumper repair on 3 May."
        ),
        "actions": [
            {
                "action_type": "appointment.create_inspection",
                "title": "Schedule inspection",
                "summary": "Rear bumper · Thursday 14:00",
                "payload": {
                    "customer_name": "Andrew Green",
                    "vehicle_make_model": "2019 Fiat Panda",
                    "license_plate": "AB123CD",
                    "damage_type": "rear bumper dent",
                    "drivable": True,
                },
                "confidence": 0.90,
                "evidence": ["Thursday at two, same bay"],
                "result": {
                    "booking_id": "BK-BSHOP0001",
                    "status": "confirmed",
                    "mock": True,
                    "mutates": True,
                },
            },
        ],
    }


def _emit_seeded_call_core(session, spec) -> None:
    """Insert Call + ExtractedFields + ExecutedAction[] for a seed scenario.

    Idempotent via fixed Call UUIDs. Caller MUST flush before invoking
    `_emit_seeded_call_audit` so the audit_log rows can resolve the FK.
    """
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


def _emit_seeded_call_audit(session, spec) -> None:
    """Insert the audit_log rows for a seed scenario. The Call has already
    been flushed by `_emit_seeded_call_core`, so the FK resolves now."""
    audit_steps = [
        ("speechmatics", "tool_call", "success"),
        ("call_analyzer", "llm_call", "success"),
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


# ---------------------------------------------------------------------------
# Personal phonebook calls — missed/unsaved/human-handled rows that make the
# Home feed look like a real device, not a pristine demo.
#
# Idempotency: fixed UUIDs, INSERT-or-skip via Call.id existence check.
# Visibility: every row has `is_seed=True, session_id=None` so the demo
# session filter (`visibility_filter_seedable`) lets all visitors see them.
#
# Caller fixtures duplicate phone + display_name from
# `afterglow/app/lib/mockContacts.ts` — keep these in sync with the
# matching `pc_xxx` entries listed in the comment below.
# ---------------------------------------------------------------------------

# Source of truth on the client side: afterglow/app/lib/mockContacts.ts
# Entries used here:
#   pc_001 Amelia Brooks     +447911100001
#   pc_003 Charlotte Davies  +447911100003
#   pc_004 Daniel Edwards    +447911100004
#   pc_008 Henry Iverson     +447911100008
#   pc_009 Isla Johnson      +447911100009
_PERSONAL_CALL_FIXTURES = [
    # 3 × missed (status='failed') — appear in the Missed filter + Saved (mock)
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000001"),
        "phone_e164": "+447911100001",  # Amelia Brooks
        "status": "failed",
        "created_at": datetime(2026, 5, 16, 9, 12, tzinfo=timezone.utc),
        "language": None,
    },
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000002"),
        "phone_e164": "+447911100004",  # Daniel Edwards
        "status": "failed",
        "created_at": datetime(2026, 5, 15, 14, 47, tzinfo=timezone.utc),
        "language": None,
    },
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000003"),
        "phone_e164": "+447911100009",  # Isla Johnson
        "status": "failed",
        "created_at": datetime(2026, 5, 14, 18, 5, tzinfo=timezone.utc),
        "language": None,
    },
    # 2 × unsaved (status='completed', phone NOT in mock list, no customer)
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000004"),
        "phone_e164": "+15550009999",
        "status": "completed",
        "created_at": datetime(2026, 5, 13, 11, 30, tzinfo=timezone.utc),
        "language": "en",
    },
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000005"),
        "phone_e164": "+447700900800",
        "status": "completed",
        "created_at": datetime(2026, 5, 12, 16, 22, tzinfo=timezone.utc),
        "language": "en",
    },
    # 2 × human-handled (status='completed' but no extracted/no actions —
    # the operator answered personally, Afterglow was not engaged)
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000006"),
        "phone_e164": "+447911100003",  # Charlotte Davies
        "status": "completed",
        "created_at": datetime(2026, 5, 11, 20, 0, tzinfo=timezone.utc),
        "language": "en",
    },
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000007"),
        "phone_e164": "+447911100008",  # Henry Iverson
        "status": "completed",
        "created_at": datetime(2026, 5, 10, 8, 45, tzinfo=timezone.utc),
        "language": "en",
    },
]


async def _ensure_personal_calls(session) -> None:
    """Insert missing personal phonebook calls. Idempotent via fixed UUIDs.

    Call.template_id is non-nullable, so we attach personal calls to the
    first seed template we find. These rows carry no extracted fields and
    no executed actions, so the template choice is cosmetic only — the UI
    renders them as plain phonebook entries.
    """
    seed_template = (
        await session.execute(
            select(Template).where(Template.is_seed.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    if seed_template is None:
        print("[seed] no seed template found, skipping personal calls.")
        return

    inserted = 0
    for fx in _PERSONAL_CALL_FIXTURES:
        present = await session.scalar(select(Call.id).where(Call.id == fx["id"]))
        if present is not None:
            continue
        session.add(
            Call(
                id=fx["id"],
                template_id=seed_template.id,
                customer_id=None,
                phone_e164=fx["phone_e164"],
                audio_url=None,
                detected_language=fx["language"],
                raw_transcript=None,
                status=fx["status"],
                started_at=fx["created_at"],
                completed_at=fx["created_at"] if fx["status"] != "failed" else None,
                is_seed=True,
                session_id=None,
                created_at=fx["created_at"],
            )
        )
        inserted += 1
    if inserted:
        await session.flush()
        print(f"[seed] inserted {inserted} personal calls.")


if __name__ == "__main__":
    asyncio.run(seed())
