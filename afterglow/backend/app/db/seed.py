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
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, select

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
        {
            "key": "booking.reschedule",
            "label": "Reschedule booking",
            "execution_mode": "auto",
            "preconditions": ["customer_name", "booking_date", "booking_time"],
            "confidence_threshold": 0.75,
            "evidence_required": True,
        },
        {
            "key": "review.request_feedback",
            "label": "Request review feedback",
            "execution_mode": "auto",
            "preconditions": ["customer_name"],
            "confidence_threshold": 0.70,
            "evidence_required": False,
        },
        {
            "key": "payment.request_deposit",
            "label": "Request deposit",
            "execution_mode": "auto",
            "preconditions": ["customer_name", "party_size"],
            "confidence_threshold": 0.75,
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
            "key": "booking_date",
            "type": "date",
            "label": "Booking date",
            "extractor_hint": "regex",
        },
        {
            "key": "booking_time",
            "type": "string",
            "label": "Booking time (HH:MM)",
            "description": "Slot time in 24-hour HH:MM format, e.g. 10:00 or 14:30.",
            "depends_on": ["booking_date"],
            "extractor_hint": "regex",
        },
        {
            "key": "booking_notes",
            "type": "string",
            "label": "Booking notes",
            "description": "Free-form caller phrasing (e.g. 'morning slot', 'after lunch').",
            "extractor_hint": "freeform",
        },
    ],
    "action_types": [
        {
            "key": "booking.create",
            "label": "Create booking",
            "execution_mode": "auto",
            "preconditions": [
                "patient_name", "urgency", "booking_date", "booking_time",
            ],
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
                    "booking_date": {"type": "string", "format": "date"},
                    "booking_time": {"type": "string"},
                    "booking_notes": {"type": "string"},
                    "is_new_patient": {"type": "boolean"},
                },
                "required": [
                    "patient_name", "urgency", "booking_date", "booking_time",
                ],
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
            "preconditions": ["patient_name", "booking_date"],
            "confidence_threshold": 0.70,
            "evidence_required": False,
            "payload_schema": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "booking_date": {"type": "string", "format": "date"},
                    "booking_time": {"type": "string"},
                },
                "required": ["patient_name", "booking_date"],
                "additionalProperties": False,
            },
        },
        {
            "key": "calendar.send_invite",
            "label": "Send calendar invite",
            "execution_mode": "auto",
            "preconditions": ["patient_name", "booking_date"],
            "confidence_threshold": 0.70,
            "evidence_required": False,
        },
        {
            "key": "calendar.block_slot",
            "label": "Block calendar slot",
            "execution_mode": "auto",
            "preconditions": ["booking_date", "urgency"],
            "confidence_threshold": 0.75,
            "evidence_required": True,
        },
        {
            "key": "email.send",
            "label": "Send email",
            "execution_mode": "auto",
            "preconditions": ["patient_name"],
            "confidence_threshold": 0.65,
            "evidence_required": False,
        },
    ],
    "prompt_hints": [
        {
            "when": "always",
            "then": "Quote the patient verbatim in evidence and never paraphrase clinical descriptions.",
        },
        {
            "when": "field.urgency == 'emergency'",
            "then": "Set booking.create payload with booking_date=today; schedule sms.send_reminder immediately.",
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
        {
            "key": "booking_date",
            "type": "date",
            "label": "Booking date",
            "extractor_hint": "regex",
        },
        {
            "key": "booking_time",
            "type": "string",
            "label": "Booking time (HH:MM)",
            "description": "Slot time in 24-hour HH:MM format (e.g. 10:00).",
            "depends_on": ["booking_date"],
            "extractor_hint": "regex",
        },
    ],
    "action_types": [
        {
            "key": "booking.create",
            "label": "Create booking",
            "execution_mode": "auto",
            "preconditions": [
                "customer_name", "vehicle_make_model",
                "booking_date", "booking_time",
            ],
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
                    "booking_date": {"type": "string", "format": "date"},
                    "booking_time": {"type": "string"},
                },
                "required": [
                    "customer_name", "vehicle_make_model",
                    "booking_date", "booking_time",
                ],
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
        {
            "key": "payment.request_deposit",
            "label": "Request parts deposit",
            "execution_mode": "auto",
            "preconditions": ["customer_name", "damage_type"],
            "confidence_threshold": 0.75,
            "evidence_required": True,
        },
        {
            "key": "payment.send_invoice",
            "label": "Send quote invoice",
            "execution_mode": "auto",
            "preconditions": ["customer_name", "damage_type"],
            "confidence_threshold": 0.70,
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

    Quality bar (every script must clear before regenerating the audio):
    - Each scenario surfaces 2-3 actions of the seed template naturally —
      it is not a soliloquy of the caller, it is a conversation that lands
      observable post-call actions. See `feedback_demo_scripts_quality.md`.
    - Each domain has a distinctive voice: restaurant = warm hospitality,
      dentist = clinical-empathetic, bodyshop = pragmatic-technical.
    - Each caller has a small arc and at least one specific detail (a
      memory for `existing`, a fresh complication for `new`) so the script
      sounds like a person, not a form.
    - Short turns, natural hesitations ("hmm", "let me think"), no
      placeholder strings or "test test test" filler.
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
            # Surfaces: booking.reschedule + review.request_feedback
            # Mark is a regular — he references the previous booking date,
            # asks to move it, accepts a post-dinner review request.
            existing_lines=[
                ("operator", "La Trattoria, good evening, this is Sarah."),
                ("caller", "Hi Sarah, it's Mark Ross. The Friday eight thirty for four — any chance we move it?"),
                ("operator", "Hi Mark, of course. Same week or a different one?"),
                ("caller", "Same week. Saturday at eight would be better. My in-laws are flying in late."),
                ("operator", "Saturday at eight, party of four, gluten free menu and the quiet table by the window — like last time?"),
                ("caller", "You remembered. Yes, identical setup."),
                ("operator", "Done. After dinner I'll send a short note asking for a Google review — only if you enjoyed it."),
                ("caller", "Happy to leave one if the tiramisù is on form."),
                ("operator", "I'll have a word with the kitchen. See you Saturday, Mark."),
                ("caller", "Thanks Sarah, see you then."),
            ],
            # Surfaces: booking.create + whatsapp.send_confirmation
            #           + payment.request_deposit
            # Hannah is a first-timer with a special occasion + large party
            # — the deposit ask is the realistic outcome.
            new_lines=[
                ("operator", "La Trattoria, good evening, this is Sarah. How can I help?"),
                ("caller", "Hi, first time calling. I'd like to book Saturday evening — it's my mother's seventieth."),
                ("operator", "Lovely. Could I have your name and how many guests?"),
                ("caller", "Hannah Clarke. Seven of us, around eight."),
                ("operator", "Seven for a celebration on Saturday at eight. Any allergies or dietary needs in the group?"),
                ("caller", "My sister is lactose intolerant, and Mum wants the chef's tasting menu if you do it."),
                ("operator", "We do, it's a fixed five courses. For parties of six or more we ask for a small deposit by card — fifty euro per guest, refundable up to forty-eight hours before."),
                ("caller", "That's fair, go ahead."),
                ("operator", "I'll send the deposit link by WhatsApp along with the booking confirmation. Anything else, Hannah?"),
                ("caller", "A little something on the table for her would be magical. No singing though."),
                ("operator", "Discreet candle, no singing — noted. See you Saturday."),
                ("caller", "Thank you so much. Goodbye."),
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
            # Surfaces: booking.create + sms.send_reminder (now on the
            # dedicated sms bucket, not whatsapp) + calendar.send_invite.
            # Laura is a known patient with a follow-up on her recent crown.
            existing_lines=[
                ("operator", "Greenwood Dental, this is Jack at the front desk."),
                ("caller", "Hi Jack, it's Laura Bennett. The crown Dr. Patel fitted last month is feeling a touch loose when I bite on the left."),
                ("operator", "I'm sorry, Laura. No pain, just movement?"),
                ("caller", "No pain. More like the surface shifted half a millimetre."),
                ("operator", "Let's not wait. Dr. Patel has tomorrow at ten fifteen — does that work?"),
                ("caller", "Tomorrow at ten fifteen is fine."),
                ("operator", "I'll text the SMS reminder the morning of, and I'll drop the booking on your Google calendar as an invite — same e-mail as last time?"),
                ("caller", "Same one, yes. Thanks for syncing it, I keep missing the wall calendar at home."),
                ("operator", "See you tomorrow, Laura."),
                ("caller", "Thanks Jack."),
            ],
            # Surfaces: booking.create (urgent) + calendar.block_slot
            # + email.send (welcome packet with intake form). Sophie has a
            # vivid, specific complaint — emergency tone done with restraint.
            new_lines=[
                ("operator", "Greenwood Dental, this is Jack. How can I help?"),
                ("caller", "Hi, I'm a new patient. I cracked a molar on a hard candy about an hour ago."),
                ("operator", "I'm sorry to hear that. May I have your name?"),
                ("caller", "Sophie Turner. The pain is sharp, lower right, when air hits it."),
                ("operator", "Understood. Any bleeding or fever?"),
                ("caller", "No bleeding, no fever — just the pain."),
                ("operator", "I'll block the three thirty slot today and hold it for you with Dr. Patel. Could you come in then?"),
                ("caller", "Yes, three thirty works."),
                ("operator", "Good. I'll e-mail you a welcome packet — the new patient form, our address, parking instructions. What's the best e-mail?"),
                ("caller", "sophie dot turner at fast-mail dot com."),
                ("operator", "Got it. Fill the form before you arrive if you can, it saves us ten minutes."),
                ("caller", "Will do. Thank you so much. Goodbye."),
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
            # Surfaces: booking.create (existing customer, known car) +
            # payment.request_deposit (parts deposit for the bumper).
            # Andrew is a repeat customer, pragmatic and frugal.
            existing_lines=[
                ("operator", "Greenline Auto Body, good afternoon, this is Megan."),
                ("caller", "Hey Megan, it's Andrew Green. The Fiat Panda, plate Bravo Romeo six six four Charlie Yankee — clipped a bollard outside Lidl this morning."),
                ("operator", "Hi Andrew, ouch. Bumper again?"),
                ("caller", "Front bumper, dent and a long scratch down the wing. No mechanical issue, still drives clean."),
                ("operator", "Out of pocket like the last two times?"),
                ("caller", "Out of pocket. Just need a quick estimate."),
                ("operator", "Thursday afternoon at two for the inspection, same bay as before — works?"),
                ("caller", "Thursday at two is good."),
                ("operator", "If the colour code matches what's already on the shelf we can start straight away. Otherwise we order it in — and for that I'd ask a hundred-and-fifty deposit on the paint by Friday."),
                ("caller", "Understood. Send me the deposit link if it comes to that."),
                ("operator", "Will do. See you Thursday, Andrew."),
                ("caller", "Thanks Megan."),
            ],
            # Surfaces: booking.create + case.open_insurance
            # (manual-only — operator promises follow-up) + payment.send_invoice
            # (formal quote by e-mail for the insurer file).
            new_lines=[
                ("operator", "Greenline Auto Body, good afternoon, this is Megan. How can I help?"),
                ("caller", "Hi, first time calling you. I was rear-ended at a roundabout this morning — fault is the other driver."),
                ("operator", "Sorry to hear that. May I have your name and the vehicle?"),
                ("caller", "Daniel Reed. Twenty twenty Toyota Corolla, plate Bravo Mike six four Lima Whisky."),
                ("operator", "Got it. What's the damage, and is the car drivable?"),
                ("caller", "Rear quarter panel is dented, the taillight is cracked. Drivable, lights still work."),
                ("operator", "Are you opening an insurance claim?"),
                ("caller", "Yes — Allianz, claim number TC twelve forty-five oh nine."),
                ("operator", "Thanks. I'll have my colleague open the file on our side after the call. Could you come in Friday at ten for the inspection?"),
                ("caller", "Friday at ten is fine."),
                ("operator", "After the inspection I'll e-mail a formal quote — they'll need it as a PDF invoice for the claim. What's your e-mail?"),
                ("caller", "Daniel dot reed at proton mail dot com."),
                ("operator", "Got it. We'll see you Friday."),
                ("caller", "Thanks. Goodbye."),
            ],
        ),
    }


# Module-level constant — single source of truth for the 6 seed customers.
# Both the main seed path (fresh DB) and `_ensure_seed_customers` (already-
# seeded DB) iterate this list. Memory summaries are full prose strings, not
# placeholders.
SEED_CUSTOMERS: list[tuple] = [
    # (display_name, phone, tags, memory_summary, language, total_calls, last_call_at)
    ("Mark Ross", "+15551112233", ["repeat", "gluten_free"],
     "Mark prefers a quiet table and is gluten-intolerant. "
     "Last booked party of 4 on 9 May — confirm the same setup if he calls again.",
     "en", 2, datetime(2026, 5, 7, 20, 30, tzinfo=timezone.utc)),
    ("Julia White", "+15554445566", ["vip", "anniversary"],
     "Julia is a VIP, prefers the window table. Celebrating her anniversary "
     "on 20 May — surprise dessert was offered last time.",
     "en", 1, datetime(2026, 4, 15, 21, 0, tzinfo=timezone.utc)),
    ("Laura Bennett", "+15559991122", ["returning_patient", "crown"],
     "Laura had a porcelain crown fitted on her lower-right molar on 8 April "
     "by Dr. Patel. Sensitivity has settled; flag any looseness on the next visit.",
     "en", 1, datetime(2026, 4, 8, 9, 30, tzinfo=timezone.utc)),
    ("Andrew Green", "+15558883344", ["returning_customer", "out_of_pocket"],
     "Andrew drives a 2019 Fiat Panda (plate AB123CD). Pays out of pocket — "
     "no insurance claim. Last visit: rear bumper repair on 3 May, paid invoice INV-DEMO0012.",
     "en", 1, datetime(2026, 5, 3, 14, 0, tzinfo=timezone.utc)),
    ("Sophie Walker", "+15552223344", ["business", "regular"],
     "Sophie books business dinners, prefers a corner table, parties of 4-6. "
     "Last booked 13 May for a quarterly review.",
     "en", 1, datetime(2026, 5, 13, 19, 30, tzinfo=timezone.utc)),
    ("Tom Hughes", "+15557778899", ["new_patient"],
     "First-time patient, wisdom-tooth check requested. "
     "Anxious about extraction — handle gently.",
     "en", 1, datetime(2026, 5, 12, 11, 0, tzinfo=timezone.utc)),
]


async def seed():
    async with SessionLocal() as session:
        # Round 8 migration: if the DB still contains any ExecutedAction
        # with the legacy `appointment.*` namespace, the schema layout has
        # changed under it (booking.create now requires booking_date /
        # booking_time and Laura/Andrew payloads are reshaped). Demo DB is
        # disposable (`feedback_db_disposable.md`) — wipe the whole seed
        # state so the fresh seed below repopulates it on the same boot.
        # Customer-owned non-seed rows (anything is_seed=False) is left
        # untouched.
        legacy_count = await session.scalar(
            select(func.count(ExecutedAction.id)).where(
                ExecutedAction.action_type.like("appointment.%")
            )
        )
        if legacy_count:
            print(
                f"[seed] round-8 migration: {legacy_count} legacy "
                f"appointment.* rows found — wiping demo state for clean "
                f"re-emit."
            )
            # FK constraints:
            #   - Call.template_id has ondelete=RESTRICT so we can't drop
            #     Template seed rows while ANY Call (seed or demo-session)
            #     still references them. Demo DB is disposable
            #     (`feedback_db_disposable.md`), so wipe ALL Call rows
            #     unconditionally — both seed and demo-session.
            #   - ExtractedFields.call_id and ExecutedAction.call_id are
            #     ondelete=CASCADE, so they're cleaned automatically.
            #   - AuditLog.call_id is ondelete=SET NULL (logs survive but
            #     lose the link, which is fine for the demo).
            #   - Customer.id is referenced by ExecutedAction.customer_id
            #     with ondelete=SET NULL, no blocking.
            await session.execute(delete(Call))
            await session.execute(delete(Customer))
            await session.execute(
                delete(Template).where(Template.is_seed.is_(True))
            )
            await session.commit()
            # Fall through: `existing` query below will now return empty
            # for the seed templates and the main seed path runs.

        # Check seed templates only — user-custom templates from the
        # wizard live alongside but don't satisfy the "demo data is
        # already there" signal we use to short-circuit re-seeding.
        existing = (
            await session.execute(
                select(Template).where(Template.is_seed.is_(True))
            )
        ).scalars().all()
        if existing:
            print(
                f"[seed] {len(existing)} seed templates already present, "
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

        # Six known customers — one per (template, returning caller) so the
        # "Call from existing customer" button produces a coherent memory
        # card on every preset (restaurant ×2, dentist ×2, bodyshop ×1) and
        # the busy-week generator has enough variety to avoid same-customer
        # streaks in the Bookings sort. Source of truth lives in
        # `SEED_CUSTOMERS` at module level.
        created_by_name: dict[str, Customer] = {}
        for (name, phone, tags, memory, lang, total, last) in SEED_CUSTOMERS:
            created_by_name[name] = Customer(
                id=uuid.uuid4(),
                phone_e164=phone,
                display_name=name,
                preferred_language=lang,
                tags=tags,
                memory_summary=memory,
                total_calls=total,
                last_call_at=last,
                is_seed=True,
            )
        session.add_all(list(created_by_name.values()))
        mark = created_by_name["Mark Ross"]
        julia = created_by_name["Julia White"]
        laura = created_by_name["Laura Bennett"]
        andrew = created_by_name["Andrew Green"]
        sophie = created_by_name["Sophie Walker"]
        tom = created_by_name["Tom Hughes"]

        # Flush so the customer IDs are usable for the seeded Call rows.
        await session.flush()

        call_specs = list(
            _seed_call_specs(
                restaurant_id, dentist_id, bodyshop_id,
                mark.id, julia.id, laura.id, andrew.id,
                sophie.id, tom.id,
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
            f"[seed] Demo data inserted: 3 templates, {len(SEED_CUSTOMERS)} customers, "
            f"{len(call_specs)} seeded calls."
        )


# ---------------------------------------------------------------------------
# Seeded calls — one per (template, returning caller).
#   restaurant: Mark (×2), Julia (×1), Sophie (×1)
#   dentist:    Laura (×1), Tom (×1)
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
    sophie_id,
    tom_id,
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
            "booking_date": "2026-04-08",
            "booking_time": "10:00",
            "booking_notes": "morning slot",
        },
        "confidence": {
            "patient_name": 0.95,
            "is_new_patient": 0.92,
            "reason": 0.94,
            "urgency": 0.86,
            "booking_date": 0.96,
            "booking_time": 0.92,
            "booking_notes": 0.84,
        },
        "evidence": {
            "patient_name": "it's Laura Bennett",
            "is_new_patient": "Yes, ten o'clock with Dr. Patel",
            "reason": "crown fitting today",
            "urgency": "in twenty minutes",
            "booking_date": "today",
            "booking_time": "ten o'clock",
            "booking_notes": "ten o'clock",
        },
        "intent": "booking_confirm",
        "sentiment": "neutral",
        "urgency": "soon",
        "briefing": (
            "Laura had a porcelain crown fitted on her lower-right molar on 8 April. "
            "Sensitivity settled; flag any looseness on the next visit."
        ),
        "actions": [
            {
                "action_type": "booking.create",
                "title": "Confirm booking",
                "summary": "Crown fitting · 8 Apr · 10:00 with Dr. Patel",
                "payload": {
                    "patient_name": "Laura Bennett",
                    "is_new_patient": False,
                    "reason": "crown fitting on lower-right molar",
                    "urgency": "soon",
                    "booking_date": "2026-04-08",
                    "booking_time": "10:00",
                    "booking_notes": "morning slot",
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
            "booking_date": "2026-05-07",
            "booking_time": "14:00",
        },
        "confidence": {
            "customer_name": 0.94,
            "vehicle_make_model": 0.93,
            "license_plate": 0.90,
            "damage_type": 0.88,
            "insurance_involved": 0.96,
            "drivable": 0.80,
            "booking_date": 0.92,
            "booking_time": 0.92,
        },
        "evidence": {
            "customer_name": "it's Andrew",
            "vehicle_make_model": "The Panda",
            "license_plate": "AB123CD",
            "damage_type": "rear bumper repair",
            "insurance_involved": "no insurance",
            "drivable": "When can I bring it in?",
            "booking_date": "Thursday",
            "booking_time": "Thursday at two",
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
                "action_type": "booking.create",
                "title": "Create booking",
                "summary": "Rear bumper · Thursday 14:00",
                "payload": {
                    "customer_name": "Andrew Green",
                    "vehicle_make_model": "2019 Fiat Panda",
                    "license_plate": "AB123CD",
                    "damage_type": "rear bumper dent",
                    "drivable": True,
                    "booking_date": "2026-05-07",
                    "booking_time": "14:00",
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
    yield {
        "id": uuid.UUID("11111111-1111-4111-8111-000000000006"),
        "customer_id": sophie_id,
        "template_id": restaurant_template_id,
        "phone_e164": "+15552223344",
        "phone_display": "Sophie Walker",
        "language": "en",
        "created_at": datetime(2026, 5, 8, 19, 15, tzinfo=timezone.utc),
        "transcript": (
            "Operator: La Trattoria, good evening.\n"
            "Caller: Hi, Sophie Walker. Quarterly review dinner — "
            "party of six on Friday at half seven, corner table please.\n"
            "Operator: Of course Sophie. Same wine selection as last time?\n"
            "Caller: Yes please. We'll need the room a bit quieter, business chat."
        ),
        "fields": {
            "party_size": 6,
            "booking_date": "2026-05-08",
            "booking_time": "19:30",
            "customer_name": "Sophie Walker",
            "seating_preference": "corner table",
            "occasion": "business dinner",
            "callback_channel": "email",
        },
        "confidence": {
            "party_size": 0.96,
            "booking_date": 0.94,
            "booking_time": 0.95,
            "customer_name": 0.93,
            "seating_preference": 0.91,
            "occasion": 0.88,
            "callback_channel": 0.84,
        },
        "evidence": {
            "party_size": "party of six",
            "booking_date": "Friday",
            "booking_time": "half seven",
            "customer_name": "Sophie Walker",
            "seating_preference": "corner table please",
            "occasion": "Quarterly review dinner",
            "callback_channel": "email confirmation",
        },
        "intent": "booking_new",
        "sentiment": "positive",
        "urgency": "routine",
        "briefing": (
            "Sophie books business dinners, prefers a corner table, "
            "parties of 4-6. Quarterly review on 8 May."
        ),
        "actions": [
            {
                "action_type": "booking.create",
                "title": "Create booking",
                "summary": "Corner table for 6 on 8 May at 19:30, business dinner",
                "payload": {
                    "party_size": 6,
                    "booking_date": "2026-05-08",
                    "booking_time": "19:30",
                    "customer_name": "Sophie Walker",
                    "seating_preference": "corner table",
                    "occasion": "business dinner",
                },
                "confidence": 0.94,
                "evidence": ["party of six", "Friday at half seven"],
                "result": {
                    "booking_id": "BK-DEMO0006",
                    "status": "confirmed",
                    "mock": True,
                    "mutates": True,
                },
            },
        ],
    }
    yield {
        "id": uuid.UUID("11111111-1111-4111-8111-000000000007"),
        "customer_id": tom_id,
        "template_id": dentist_template_id,
        "phone_e164": "+15557778899",
        "phone_display": "Tom Hughes",
        "language": "en",
        "created_at": datetime(2026, 5, 7, 11, 0, tzinfo=timezone.utc),
        "transcript": (
            "Operator: Greenwood Dental, this is the front desk.\n"
            "Caller: Hi, my name's Tom Hughes. I'm a new patient — I'd "
            "like a wisdom-tooth check. I'm honestly quite anxious about it.\n"
            "Operator: I understand Tom. We can book a consultation, "
            "no procedure today. Thursday at eleven with Dr. Patel?\n"
            "Caller: Thursday at eleven works. Thank you."
        ),
        "fields": {
            "patient_name": "Tom Hughes",
            "is_new_patient": True,
            "reason": "wisdom-tooth check (consultation only)",
            "urgency": "soon",
            "booking_date": "2026-05-07",
            "booking_time": "11:00",
            "booking_notes": "anxious patient — handle gently",
        },
        "confidence": {
            "patient_name": 0.95,
            "is_new_patient": 0.96,
            "reason": 0.92,
            "urgency": 0.84,
            "booking_date": 0.93,
            "booking_time": 0.94,
            "booking_notes": 0.86,
        },
        "evidence": {
            "patient_name": "my name's Tom Hughes",
            "is_new_patient": "I'm a new patient",
            "reason": "wisdom-tooth check",
            "urgency": "quite anxious about it",
            "booking_date": "Thursday",
            "booking_time": "eleven",
            "booking_notes": "honestly quite anxious about it",
        },
        "intent": "booking_new",
        "sentiment": "anxious",
        "urgency": "soon",
        "briefing": (
            "Tom is a first-time patient, wisdom-tooth check requested. "
            "Anxious about extraction — handle gently."
        ),
        "actions": [
            {
                "action_type": "booking.create",
                "title": "Create booking",
                "summary": "Wisdom-tooth consultation · 7 May · 11:00 with Dr. Patel",
                "payload": {
                    "patient_name": "Tom Hughes",
                    "is_new_patient": True,
                    "reason": "wisdom-tooth check (consultation only)",
                    "urgency": "soon",
                    "booking_date": "2026-05-07",
                    "booking_time": "11:00",
                    "booking_notes": "anxious patient — handle gently",
                },
                "confidence": 0.91,
                "evidence": ["Thursday at eleven"],
                "result": {
                    "booking_id": "BK-DENT0002",
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
    been flushed by `_emit_seeded_call_core`, so the FK resolves now.

    Numbers are picked from realistic ranges for a Gemini 3.1 Flash-Lite call
    on a ~60-word transcript (latency in the low-seconds for LLM steps, tens
    of ms for deterministic ones) so the Audit log surfaces meaningful
    duration + token figures even when no live pipeline has run yet. Values
    are deterministic per seed call (Random seeded with the call UUID).
    """
    rng = random.Random(spec["id"].int)
    action_count = len(spec.get("actions", []) or [])

    audit_steps = [
        {
            "agent": "speechmatics",
            "step_type": "tool_call",
            "model": None,
            "duration_ms": rng.randint(1600, 2800),
            "input_tokens": None,
            "output_tokens": None,
            "payload": None,
        },
        {
            "agent": "call_analyzer",
            "step_type": "llm_call",
            "model": "gemini-3.1-flash-lite",
            "duration_ms": rng.randint(1700, 2600),
            "input_tokens": rng.randint(1800, 2600),
            "output_tokens": rng.randint(380, 620),
            "payload": None,
        },
        {
            "agent": "action_planner",
            "step_type": "agent_loop",
            "model": "gemini-3.1-flash-lite",
            "duration_ms": rng.randint(1200, 1900),
            "input_tokens": rng.randint(1100, 1700),
            "output_tokens": rng.randint(140, 280),
            "payload": {"mode": "auto", "count": action_count},
        },
        {
            "agent": "action_executor",
            "step_type": "action_exec",
            "model": None,
            "duration_ms": rng.randint(40, 160),
            "input_tokens": None,
            "output_tokens": None,
            "payload": None,
        },
        {
            "agent": "memory_updater",
            "step_type": "tool_call",
            "model": None,
            "duration_ms": rng.randint(90, 240),
            "input_tokens": None,
            "output_tokens": None,
            "payload": None,
        },
    ]
    cursor_offset = 10
    for step in audit_steps:
        session.add(
            AuditLog(
                id=uuid.uuid4(),
                call_id=spec["id"],
                agent_name=step["agent"],
                step_type=step["step_type"],
                model=step["model"],
                duration_ms=step["duration_ms"],
                input_tokens=step["input_tokens"],
                output_tokens=step["output_tokens"],
                payload=step["payload"],
                status="success",
                created_at=spec["created_at"] + timedelta(
                    seconds=cursor_offset,
                    milliseconds=step["duration_ms"],
                ),
            )
        )
        # Each subsequent step starts roughly when the previous one ended,
        # so the chronological view in the UI tells the same story as a live
        # pipeline run.
        cursor_offset += int(step["duration_ms"] / 1000) + 1


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
        "error": "empty_or_noise_audio",
        "created_at": datetime(2026, 5, 16, 9, 12, tzinfo=timezone.utc),
        "language": None,
    },
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000002"),
        "phone_e164": "+447911100004",  # Daniel Edwards
        "status": "failed",
        "error": "empty_or_noise_audio",
        "created_at": datetime(2026, 5, 15, 14, 47, tzinfo=timezone.utc),
        "language": None,
    },
    {
        "id": uuid.UUID("22222222-2222-4222-8222-000000000003"),
        "phone_e164": "+447911100009",  # Isla Johnson
        "status": "failed",
        "error": "empty_or_noise_audio",
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


# Phone numbers used by the "busy week" densification. Mix of known mock
# contacts (avatars resolve in the UI) and a few unknown numbers to keep
# the Unsaved filter populated. Customer-owned phones live in
# `_CUSTOMER_PHONES_BY_NAME` below; those calls get a customer_id linked
# at insert time so the customer detail "Calls (N)" shows real history.
_BUSY_MOCK_PHONES = [
    "+447911100001",  # Amelia Brooks
    "+447911100002",  # Benjamin Clark
    "+447911100005",  # Eleanor Foster
    "+447911100006",  # Finn Gallagher
    "+447911100010",  # Jack Kennedy
    "+447911100013",  # Mia Nguyen
    "+447911100015",  # Olivia Patel
    "+447911100017",  # Rosie Stewart
]

_BUSY_UNKNOWN_PHONES = [
    "+15550001234",
    "+447700900112",
    "+15558887766",
    "+447700901234",
]

# Names match the six seed Customer rows created in `seed()` /
# `_ensure_seed_customers` (Mark Ross, Julia White, Laura Bennett, Andrew
# Green, Sophie Walker, Tom Hughes). Lookup by display_name keeps the
# helper resilient to UUID changes — the customer IDs are random but the
# phones/names are stable. Single source of truth for the customer roster
# lives in `SEED_CUSTOMERS`.
_CUSTOMER_PHONES_BY_NAME = {
    "Mark Ross": "+15551112233",
    "Julia White": "+15554445566",
    "Laura Bennett": "+15559991122",
    "Andrew Green": "+15558883344",
    "Sophie Walker": "+15552223344",
    "Tom Hughes": "+15557778899",
}

# Hour slots that look like realistic restaurant traffic — lunch and dinner
# clusters on weekdays, broader spread on weekends. Used to scatter calls
# across the day rather than bunching them all at midnight.
_HOUR_SLOTS_WEEKDAY = [
    (12, 15), (12, 45), (13, 20), (13, 55),
    (19, 5), (19, 35), (20, 10), (20, 40), (21, 5),
]
_HOUR_SLOTS_WEEKEND = [
    (11, 30), (12, 10), (12, 50), (13, 25), (14, 5),
    (18, 45), (19, 15), (19, 50), (20, 25), (21, 0), (21, 30),
]


def _busy_week_specs() -> list[dict]:
    """Deterministic fixtures for the dense 9–17 May window. Returns ~43
    entries — combined with the 7 base fixtures we land at ~50 personal
    calls, exactly the Home `limit=50` cap. UUIDs are UUID5-derived from
    (phone, created_at) so re-running the seed is idempotent without
    requiring a separate IDs table.

    Kinds:
      - `completed` → human-handled personal call (Afterglow not engaged)
      - `missed`    → empty_or_noise_audio failure (Missed filter)
      - `pipeline_error` → simulated technical failure (Pipeline error badge)
      - `ai_booking` → AI-handled work call that yields a booking.create —
                       feeds the Bookings tab. Pool must be `customer:<name>`;
                       the helper resolves the customer's vertical (restaurant /
                       dentist / bodyshop) to pick the right template, but the
                       action namespace is the same across verticals.
    """
    rng = random.Random(20260518)  # date-of-write seed → stable output
    out: list[dict] = []

    # Per-day plan. Each entry: (date, list of (kind, phone_pool)) where
    # kind is one of completed / missed / pipeline_error / ai_booking, and
    # phone_pool is "mock" / "unknown" / "customer:<name>". Exactly one
    # pipeline_error is sprinkled in (11 May) so the failure-kind badge is
    # exercised. AI booking calls are sprinkled across the week so the
    # Bookings tab stays populated as the window scrolls forward.
    plan = [
        # 9 May (Friday)
        ("2026-05-09", [
            ("completed", "mock"),
            ("ai_booking", "customer:Andrew Green"),
            ("completed", "mock"), ("missed", "mock"),
        ]),
        # 10 May (Saturday, weekend peak) — Sophie business dinner
        ("2026-05-10", [
            ("ai_booking", "customer:Sophie Walker"),
            ("completed", "mock"), ("completed", "unknown"),
            ("completed", "mock"),
            ("missed", "unknown"), ("missed", "mock"),
        ]),
        # 11 May (Sunday) — pipeline_error lives here
        ("2026-05-11", [
            ("ai_booking", "customer:Mark Ross"),
            ("completed", "mock"), ("completed", "mock"),
            ("completed", "unknown"),
            ("missed", "mock"), ("pipeline_error", "unknown"),
        ]),
        # 12 May (Monday) — Tom new-patient check
        ("2026-05-12", [
            ("completed", "mock"),
            ("ai_booking", "customer:Tom Hughes"),
            ("completed", "mock"), ("missed", "mock"),
        ]),
        # 13 May (Tuesday)
        ("2026-05-13", [
            ("completed", "mock"),
            ("ai_booking", "customer:Laura Bennett"),
            ("completed", "mock"), ("missed", "unknown"),
        ]),
        # 14 May (Wednesday)
        ("2026-05-14", [
            ("ai_booking", "customer:Julia White"),
            ("completed", "mock"), ("completed", "mock"),
            ("missed", "mock"),
        ]),
        # 15 May (Thursday) — Sophie repeat business dinner
        ("2026-05-15", [
            ("completed", "mock"), ("completed", "mock"),
            ("ai_booking", "customer:Sophie Walker"),
            ("missed", "mock"),
        ]),
        # 16 May (Friday)
        ("2026-05-16", [
            ("completed", "mock"),
            ("ai_booking", "customer:Mark Ross"),
            ("completed", "mock"), ("completed", "unknown"),
            ("missed", "mock"),
        ]),
        # 17 May (Saturday weekend peak)
        ("2026-05-17", [
            ("ai_booking", "customer:Andrew Green"),
            ("completed", "mock"), ("completed", "mock"),
            ("completed", "unknown"),
            ("missed", "mock"), ("missed", "mock"),
        ]),
    ]

    for date_str, calls in plan:
        y, m, d = (int(x) for x in date_str.split("-"))
        day_dt = datetime(y, m, d, tzinfo=timezone.utc)
        weekend = day_dt.weekday() >= 5
        slots = list(_HOUR_SLOTS_WEEKEND if weekend else _HOUR_SLOTS_WEEKDAY)
        rng.shuffle(slots)
        for idx, (kind, pool) in enumerate(calls):
            hh, mm = slots[idx % len(slots)]
            created = datetime(y, m, d, hh, mm, tzinfo=timezone.utc)
            if pool == "mock":
                phone = rng.choice(_BUSY_MOCK_PHONES)
                customer_name = None
            elif pool == "unknown":
                phone = rng.choice(_BUSY_UNKNOWN_PHONES)
                customer_name = None
            elif pool.startswith("customer:"):
                customer_name = pool.split(":", 1)[1]
                phone = _CUSTOMER_PHONES_BY_NAME[customer_name]
            else:
                raise ValueError(f"unknown pool: {pool}")

            # Namespace varies per kind so re-seeding into a DB that
            # already contains the personal-only flavor (e.g. our first
            # round-7 deploy) doesn't silently skip the new AI bookings
            # via UUID5 collision. The namespace is fixed per kind so
            # the second run is still idempotent.
            namespace = (
                uuid.UUID("22222222-2222-5222-8222-aaaa00000000")
                if kind == "ai_booking"
                else uuid.UUID("22222222-2222-5222-8222-000000000000")
            )
            fixture_uuid = uuid.uuid5(namespace, f"{phone}@{created.isoformat()}")

            if kind == "completed":
                fixture = {
                    "id": fixture_uuid,
                    "phone_e164": phone,
                    "status": "completed",
                    "created_at": created,
                    "language": "en",
                }
            elif kind == "missed":
                fixture = {
                    "id": fixture_uuid,
                    "phone_e164": phone,
                    "status": "failed",
                    "error": "empty_or_noise_audio",
                    "created_at": created,
                    "language": None,
                }
            elif kind == "pipeline_error":
                fixture = {
                    "id": fixture_uuid,
                    "phone_e164": phone,
                    "status": "failed",
                    "error": "action_planner: simulated failure",
                    "created_at": created,
                    "language": "en",
                }
            elif kind == "ai_booking":
                # Real AI-handled work call. customer_name MUST be set —
                # the helper resolves the right vertical/template/action
                # downstream in `_ensure_personal_calls`.
                if not customer_name:
                    raise ValueError("ai_booking requires customer pool")
                fixture = {
                    "id": fixture_uuid,
                    "phone_e164": phone,
                    "status": "completed",
                    "created_at": created,
                    "language": "en",
                    "ai_booking": True,
                }
            else:
                raise ValueError(f"unknown kind: {kind}")

            if customer_name:
                fixture["customer_name"] = customer_name
            out.append(fixture)
    return out


# Per-customer AI booking scripts: short transcript + extracted fields +
# one action that lands in the Bookings tab. Keep these self-contained
# (no cross-reference to the big `_seed_call_specs` payloads) so the
# busy-week generator stays predictable and idempotent.
_AI_BOOKING_BLUEPRINTS: dict[str, dict] = {
    "Mark Ross": {
        "domain": "restaurant",
        "transcript_template": (
            "Operator: La Trattoria, how can I help?\n"
            "Caller: Hi, it's Mark Ross. I'd like to book a table for "
            "Friday at eight, party of four.\n"
            "Operator: Of course, any preference?\n"
            "Caller: A quiet table, please — and remember I'm "
            "gluten-intolerant. Confirm on WhatsApp."
        ),
        "fields": {
            "party_size": 4,
            "booking_time": "20:00",
            "customer_name": "Mark Ross",
            "allergies": ["gluten"],
            "seating_preference": "quiet table",
            "callback_channel": "whatsapp",
        },
        "intent": "booking_new",
        "action": {
            "type": "booking.create",
            "title": "Create booking",
            "summary_template": "Quiet table for 4 on {date} at 20:00, gluten-free menu",
            "payload_template": {
                "party_size": 4,
                "booking_time": "20:00",
                "customer_name": "Mark Ross",
                "seating_preference": "quiet table",
            },
        },
        "briefing": (
            "Mark is gluten-intolerant and prefers quiet tables. "
            "Always confirm the gluten-free menu."
        ),
    },
    "Julia White": {
        "domain": "restaurant",
        "transcript_template": (
            "Operator: La Trattoria, good evening.\n"
            "Caller: Hi, it's Julia White. Booking for two on Saturday at "
            "nine, window table if possible. It's an anniversary.\n"
            "Operator: Wonderful, we'll prepare the usual surprise dessert.\n"
            "Caller: Perfect, thank you."
        ),
        "fields": {
            "party_size": 2,
            "booking_time": "21:00",
            "customer_name": "Julia White",
            "seating_preference": "window table",
            "occasion": "anniversary",
            "callback_channel": "sms",
        },
        "intent": "booking_new",
        "action": {
            "type": "booking.create",
            "title": "Create booking",
            "summary_template": "Window table for 2 on {date} at 21:00, anniversary dinner",
            "payload_template": {
                "party_size": 2,
                "booking_time": "21:00",
                "customer_name": "Julia White",
                "seating_preference": "window table",
                "occasion": "anniversary",
            },
        },
        "briefing": (
            "Julia is a VIP, anniversary on 20 May. "
            "Window table + surprise dessert is the usual."
        ),
    },
    "Laura Bennett": {
        "domain": "dentist",
        "transcript_template": (
            "Operator: Smile Dental, how can I help?\n"
            "Caller: Hi, Laura Bennett. The crown Dr. Patel fitted last "
            "month feels a touch loose. Could I come in for a check?\n"
            "Operator: Sure, Tuesday at three with Dr. Patel?\n"
            "Caller: Tuesday at three works. Thanks."
        ),
        "fields": {
            "patient_name": "Laura Bennett",
            "booking_time": "15:00",
            "concern": "loose crown",
            "preferred_doctor": "Dr. Patel",
            "callback_channel": "phone",
        },
        "intent": "booking_new",
        "action": {
            "type": "booking.create",
            "title": "Create booking",
            "summary_template": "Crown follow-up with Dr. Patel on {date} at 15:00",
            "payload_template": {
                "patient_name": "Laura Bennett",
                "booking_time": "15:00",
                "concern": "loose crown",
                "preferred_doctor": "Dr. Patel",
            },
        },
        "briefing": (
            "Laura had a porcelain crown fitted on her lower-right molar. "
            "Reported looseness — flag for Dr. Patel."
        ),
    },
    "Andrew Green": {
        "domain": "bodyshop",
        "transcript_template": (
            "Operator: Greenline Body Shop, how can I help?\n"
            "Caller: Hi, Andrew Green. The Fiat Panda Bravo Romeo six six "
            "four Charlie Yankee — clipped a bollard, rear bumper needs "
            "checking. Pays out of pocket as usual.\n"
            "Operator: Bring it Thursday morning at ten?\n"
            "Caller: Thursday at ten, perfect."
        ),
        "fields": {
            "customer_name": "Andrew Green",
            "vehicle_plate": "BR664CY",
            "damage_area": "rear bumper",
            "booking_time": "10:00",
            "payment_method": "out_of_pocket",
            "callback_channel": "sms",
        },
        "intent": "booking_new",
        "action": {
            "type": "booking.create",
            "title": "Create booking",
            "summary_template": "Rear bumper inspection on {date} at 10:00, plate BR664CY",
            "payload_template": {
                "customer_name": "Andrew Green",
                "vehicle_plate": "BR664CY",
                "damage_area": "rear bumper",
                "booking_time": "10:00",
            },
        },
        "briefing": (
            "Andrew drives a 2019 Fiat Panda (plate BR664CY). "
            "Pays out of pocket — no insurance claim."
        ),
    },
    "Sophie Walker": {
        "domain": "restaurant",
        "transcript_template": (
            "Operator: La Trattoria, good evening.\n"
            "Caller: Hi, it's Sophie Walker. Business dinner, party of "
            "six, corner table at half seven if you have it.\n"
            "Operator: Of course Sophie. Same wine selection as last "
            "time?\n"
            "Caller: Yes please, and confirm by email."
        ),
        "fields": {
            "party_size": 6,
            "booking_time": "19:30",
            "customer_name": "Sophie Walker",
            "seating_preference": "corner table",
            "occasion": "business dinner",
            "callback_channel": "email",
        },
        "intent": "booking_new",
        "action": {
            "type": "booking.create",
            "title": "Create booking",
            "summary_template": "Corner table for 6 on {date} at 19:30, business dinner",
            "payload_template": {
                "party_size": 6,
                "booking_time": "19:30",
                "customer_name": "Sophie Walker",
                "seating_preference": "corner table",
                "occasion": "business dinner",
            },
        },
        "briefing": (
            "Sophie books business dinners, prefers a corner table, "
            "parties of 4-6. Reliable repeat customer."
        ),
    },
    "Tom Hughes": {
        "domain": "dentist",
        "transcript_template": (
            "Operator: Greenwood Dental, this is the front desk.\n"
            "Caller: Hi, my name's Tom Hughes — I'm a new patient. "
            "I'd like a wisdom-tooth check. I'm honestly quite anxious "
            "about it.\n"
            "Operator: We can book a consultation, no procedure today. "
            "Thursday at eleven with Dr. Patel?\n"
            "Caller: Thursday at eleven works. Thank you."
        ),
        "fields": {
            "patient_name": "Tom Hughes",
            "booking_time": "11:00",
            "concern": "wisdom-tooth check (consultation only)",
            "preferred_doctor": "Dr. Patel",
            "callback_channel": "phone",
        },
        "intent": "booking_new",
        "action": {
            "type": "booking.create",
            "title": "Create booking",
            "summary_template": "Wisdom-tooth consultation with Dr. Patel on {date} at 11:00",
            "payload_template": {
                "patient_name": "Tom Hughes",
                "booking_time": "11:00",
                "concern": "wisdom-tooth check (consultation only)",
                "preferred_doctor": "Dr. Patel",
            },
        },
        "briefing": (
            "Tom is a first-time patient — wisdom-tooth check requested. "
            "Anxious about extraction — handle gently."
        ),
    },
}


def _make_ai_booking_spec(
    *,
    fixture_uuid: uuid.UUID,
    customer_id: uuid.UUID,
    template_id: uuid.UUID,
    phone: str,
    created_at: datetime,
    customer_name: str,
) -> dict:
    """Materialize a `_emit_seeded_call_core`-compatible spec from a busy-
    week AI booking fixture. Templates are looked up per-customer via
    `_AI_BOOKING_BLUEPRINTS`; the booking_date is derived as
    `created_at + 2 days` so the slot looks future-dated relative to the
    call timestamp (operators usually book a few days out)."""
    bp = _AI_BOOKING_BLUEPRINTS[customer_name]
    booking_date = (created_at + timedelta(days=2)).date().isoformat()
    summary = bp["action"]["summary_template"].format(date=booking_date)
    action_payload = dict(bp["action"]["payload_template"])
    # Every blueprint produces `booking.create` since the round 8
    # unification — the action namespace is the same across verticals.
    action_payload["booking_date"] = booking_date

    extracted_fields = dict(bp["fields"])
    extracted_fields["booking_date"] = booking_date

    confidence = {k: 0.92 for k in extracted_fields}
    evidence = {
        k: ("see transcript" if not isinstance(v, list) else "see transcript")
        for k, v in extracted_fields.items()
    }

    return {
        "id": fixture_uuid,
        "customer_id": customer_id,
        "template_id": template_id,
        "phone_e164": phone,
        "language": "en",
        "created_at": created_at,
        "transcript": bp["transcript_template"],
        "fields": extracted_fields,
        "confidence": confidence,
        "evidence": evidence,
        "intent": bp["intent"],
        "sentiment": "positive",
        "urgency": "routine",
        "briefing": bp["briefing"],
        "actions": [
            {
                "action_type": bp["action"]["type"],
                "title": bp["action"]["title"],
                "summary": summary,
                "payload": action_payload,
                "confidence": 0.91,
                "evidence": ["see transcript"],
                "result": {
                    # Mirror the result shape stamped by the live executor
                    # so the Call detail's "Simulated" badge + Undo button
                    # render exactly as they would for a real run.
                    "status": "confirmed",
                    "mock": True,
                    "mutates": True,
                },
            }
        ],
    }


async def _ensure_seed_customers(session) -> None:
    """Idempotent upsert: insert any of SEED_CUSTOMERS that isn't already in
    the DB (matched by phone_e164 + is_seed=True). Safe to call on every boot.

    Called from `_ensure_personal_calls` so the busy-week generator can
    resolve customer_id for newly added seed customers (Sophie / Tom) even
    on a round-8-clean DB where the main seed path's customer-creation block
    no longer runs.
    """
    existing_phones = set(
        (
            await session.execute(
                select(Customer.phone_e164).where(Customer.is_seed.is_(True))
            )
        ).scalars().all()
    )
    inserted = 0
    for (name, phone, tags, memory, lang, total, last) in SEED_CUSTOMERS:
        if phone in existing_phones:
            continue
        session.add(
            Customer(
                id=uuid.uuid4(),
                phone_e164=phone,
                display_name=name,
                preferred_language=lang,
                tags=tags,
                memory_summary=memory,
                total_calls=total,
                last_call_at=last,
                is_seed=True,
            )
        )
        inserted += 1
    if inserted:
        await session.flush()
        print(f"[seed] upserted {inserted} missing seed customers.")


async def _ensure_personal_calls(session) -> None:
    """Insert missing personal phonebook calls plus a "busy week" densified
    history. Idempotent via fixed UUIDs (base fixtures) and UUID5-derived
    IDs (busy week).

    Call.template_id is non-nullable, so personal calls are attached to
    the first seed template we find — they carry no extracted fields and
    no executed actions, so the template choice is cosmetic. Customer
    calls (Mark Ross etc.) get `customer_id` resolved by phone lookup so
    the customer detail "Calls (N)" surfaces real repeat-caller history;
    `Customer.total_calls` and `last_call_at` are recomputed at the end
    so the Contacts ordering stays consistent with the inserted rows.
    """
    seed_template = (
        await session.execute(
            select(Template).where(Template.is_seed.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    if seed_template is None:
        print("[seed] no seed template found, skipping personal calls.")
        return

    # Backfill any seed customers added in later rounds (e.g. Sophie / Tom
    # in round 9). Idempotent: skips customers already present by phone.
    await _ensure_seed_customers(session)

    # Per-domain template lookup so AI booking calls land on the correct
    # vertical (Mark/Julia → restaurant, Laura → dentist, Andrew →
    # bodyshop). Falls back to the first seed template if a domain isn't
    # present (e.g. someone deleted a preset by hand).
    domain_template_ids: dict[str, uuid.UUID] = {}
    for dom in ("restaurant", "dentist", "bodyshop"):
        row = (
            await session.execute(
                select(Template.id).where(
                    Template.is_seed.is_(True),
                    Template.domain_hint == dom,
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            domain_template_ids[dom] = row

    # Resolve customer IDs by phone — keeps the helper independent of the
    # random UUIDs assigned in `seed()`. Customers absent from the DB
    # (e.g. running an older seed) silently drop to customer_id=None.
    customer_phones = list(_CUSTOMER_PHONES_BY_NAME.values())
    phone_to_customer_id: dict[str, uuid.UUID] = {}
    if customer_phones:
        rows = (
            await session.execute(
                select(Customer.id, Customer.phone_e164).where(
                    Customer.phone_e164.in_(customer_phones),
                    Customer.is_seed.is_(True),
                )
            )
        ).all()
        phone_to_customer_id = {phone: cid for cid, phone in rows}

    all_fixtures = list(_PERSONAL_CALL_FIXTURES) + _busy_week_specs()

    inserted = 0
    ai_specs: list[dict] = []  # deferred — emitted via _emit_seeded_call_core
    for fx in all_fixtures:
        present = await session.scalar(select(Call.id).where(Call.id == fx["id"]))
        if present is not None:
            continue
        customer_name = fx.get("customer_name")
        customer_id: uuid.UUID | None = None
        if customer_name:
            phone_for_lookup = _CUSTOMER_PHONES_BY_NAME.get(customer_name)
            if phone_for_lookup:
                customer_id = phone_to_customer_id.get(phone_for_lookup)

        if fx.get("ai_booking"):
            # An older deploy may have inserted a personal "completed
            # customer:X" call at the exact same (phone, slot) — under
            # the legacy namespace. The new AI booking uses a different
            # namespace so no UUID collision blocks the insert, but the
            # stale row is now a semantic duplicate (same slot, same
            # customer, no extracted/actions). Drop it before we emit the
            # AI version. Postgres cascades onto extracted_fields /
            # executed_actions / audit_log via the existing FKs.
            legacy_uuid = uuid.uuid5(
                uuid.UUID("22222222-2222-5222-8222-000000000000"),
                f"{fx['phone_e164']}@{fx['created_at'].isoformat()}",
            )
            if legacy_uuid != fx["id"]:
                legacy = await session.get(Call, legacy_uuid)
                if legacy is not None:
                    await session.delete(legacy)
                    await session.flush()

            # AI work call — vertical resolved from the blueprint's domain.
            blueprint = _AI_BOOKING_BLUEPRINTS.get(customer_name or "")
            if blueprint is None or customer_id is None:
                # Defensive: if the customer was renamed or the blueprint
                # is missing, fall back to a plain completed call instead
                # of crashing the whole seed. This keeps the demo bootable.
                session.add(
                    Call(
                        id=fx["id"],
                        template_id=seed_template.id,
                        customer_id=customer_id,
                        phone_e164=fx["phone_e164"],
                        audio_url=None,
                        detected_language=fx["language"],
                        raw_transcript=None,
                        status=fx["status"],
                        error=fx.get("error"),
                        started_at=fx["created_at"],
                        completed_at=fx["created_at"],
                        is_seed=True,
                        session_id=None,
                        created_at=fx["created_at"],
                    )
                )
                inserted += 1
                continue
            tpl_id = domain_template_ids.get(
                blueprint["domain"], seed_template.id
            )
            spec = _make_ai_booking_spec(
                fixture_uuid=fx["id"],
                customer_id=customer_id,
                template_id=tpl_id,
                phone=fx["phone_e164"],
                created_at=fx["created_at"],
                customer_name=customer_name or "",
            )
            ai_specs.append(spec)
            inserted += 1
            continue

        session.add(
            Call(
                id=fx["id"],
                template_id=seed_template.id,
                customer_id=customer_id,
                phone_e164=fx["phone_e164"],
                audio_url=None,
                detected_language=fx["language"],
                raw_transcript=None,
                status=fx["status"],
                error=fx.get("error"),
                started_at=fx["created_at"],
                completed_at=fx["created_at"] if fx["status"] != "failed" else None,
                is_seed=True,
                session_id=None,
                created_at=fx["created_at"],
            )
        )
        inserted += 1

    # Phase two: emit AI specs (Call + ExtractedFields + ExecutedAction +
    # AuditLog) using the same two-step flush pattern that `seed()` uses
    # for the original 5 seed calls. Order matters — see the comment in
    # `seed()` about the audit_log FK ordering.
    for spec in ai_specs:
        _emit_seeded_call_core(session, spec)
        await session.flush()
        _emit_seeded_call_audit(session, spec)
        await session.flush()

    if inserted:
        await session.flush()

        # Recompute total_calls and last_call_at for every seed Customer
        # we wired calls to. Contacts list ordering and customer detail
        # subtitle both depend on these — leaving them stale at "1 call"
        # while we insert 4 more would make the demo feel broken.
        touched_customer_ids = {
            cid for cid in phone_to_customer_id.values() if cid is not None
        }
        for cid in touched_customer_ids:
            row = (
                await session.execute(
                    select(
                        func.count(Call.id),
                        func.max(Call.created_at),
                    ).where(Call.customer_id == cid)
                )
            ).one()
            total, last_at = row
            cust = await session.get(Customer, cid)
            if cust is not None:
                cust.total_calls = int(total or 0)
                cust.last_call_at = last_at

        print(f"[seed] inserted {inserted} personal calls.")


if __name__ == "__main__":
    asyncio.run(seed())
