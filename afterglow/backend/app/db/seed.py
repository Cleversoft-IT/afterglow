"""Seed demo data: 1 restaurant + 1 dentist + 1 bodyshop + sample customers + templates."""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.engine import SessionLocal
from app.db.models import Business, Customer, Template


RESTAURANT_TEMPLATE = {
    "name": "Standard booking",
    "description": "Phone bookings for an Italian restaurant.",
    "fields_schema": [
        {"key": "party_size", "type": "integer", "label": "Number of guests", "required": True},
        {"key": "booking_date", "type": "date", "label": "Date", "required": True},
        {"key": "booking_time", "type": "time", "label": "Time", "required": True},
        {"key": "customer_name", "type": "string", "label": "Name", "required": True},
        {"key": "allergies", "type": "string_list", "label": "Allergies", "required": False, "sensitive": True},
        {"key": "seating_preference", "type": "string", "label": "Seating preference", "required": False},
        {"key": "occasion", "type": "string", "label": "Special occasion", "required": False},
        {"key": "callback_channel", "type": "enum", "label": "Confirmation channel", "options": ["whatsapp", "sms", "email", "none"]},
    ],
    "action_types": [
        {"key": "booking.create", "label": "Create booking", "execution_mode": "auto", "mock_target": "booking"},
        {"key": "whatsapp.send_confirmation", "label": "Send WhatsApp confirmation", "execution_mode": "auto", "mock_target": "whatsapp"},
        {"key": "customer.update_profile", "label": "Update customer profile", "execution_mode": "auto", "mock_target": "crm"},
        {"key": "booking.cancel", "label": "Cancel booking", "execution_mode": "manual-only", "mock_target": "booking"},
    ],
    "custom_dictionary": [
        "celiachia", "glutine", "lattosio", "intolleranza", "Nebbiolo", "Barolo",
        "tavolo", "coperti", "menu degustazione", "vegano", "vegetariano",
    ],
    "prompt_hints": "When in doubt, extract field values literally from the conversation. Mark 'allergies' as sensitive — confidence below 0.8 must include human review.",
}

DENTIST_TEMPLATE = {
    "name": "Appointment intake",
    "description": "Phone intake for a dental clinic — handle existing patients, new requests and emergencies.",
    "fields_schema": [
        {"key": "patient_name", "type": "string", "label": "Patient name", "required": True},
        {"key": "is_new_patient", "type": "boolean", "label": "New patient?", "required": True},
        {"key": "reason", "type": "string", "label": "Reason for visit", "required": True, "sensitive": True},
        {"key": "urgency", "type": "enum", "label": "Urgency", "options": ["routine", "soon", "urgent", "emergency"]},
        {"key": "preferred_date", "type": "date", "label": "Preferred date"},
        {"key": "preferred_time_window", "type": "string", "label": "Preferred time window"},
    ],
    "action_types": [
        {"key": "appointment.create", "label": "Create appointment", "execution_mode": "auto", "mock_target": "booking"},
        {"key": "patient.update_profile", "label": "Update patient profile", "execution_mode": "manual-only", "mock_target": "crm"},
        {"key": "sms.send_reminder", "label": "Send SMS reminder", "execution_mode": "auto", "mock_target": "whatsapp"},
    ],
    "custom_dictionary": ["igiene dentale", "carie", "estrazione", "implantologia", "ortodonzia"],
    "prompt_hints": "Health-related fields are sensitive. If urgency is 'emergency', escalate via callback.",
}

BODYSHOP_TEMPLATE = {
    "name": "Damage quote intake",
    "description": "Phone intake for a body shop — quotes, inspections, insurance claims.",
    "fields_schema": [
        {"key": "customer_name", "type": "string", "label": "Customer name", "required": True},
        {"key": "vehicle_make_model", "type": "string", "label": "Vehicle make/model", "required": True},
        {"key": "license_plate", "type": "string", "label": "License plate"},
        {"key": "damage_type", "type": "string", "label": "Damage description"},
        {"key": "insurance_involved", "type": "boolean", "label": "Insurance claim?"},
        {"key": "drivable", "type": "boolean", "label": "Vehicle drivable?"},
    ],
    "action_types": [
        {"key": "appointment.create_inspection", "label": "Schedule inspection", "execution_mode": "auto", "mock_target": "booking"},
        {"key": "whatsapp.request_photos", "label": "Request damage photos", "execution_mode": "auto", "mock_target": "whatsapp"},
        {"key": "case.open_insurance", "label": "Open insurance case", "execution_mode": "manual-only", "mock_target": "crm"},
    ],
    "custom_dictionary": ["paraurti", "carrozzeria", "sinistro", "perito", "franchigia", "targa"],
    "prompt_hints": "If license plate is missing, queue an action to request it.",
}


async def seed():
    async with SessionLocal() as session:
        existing = (await session.execute(select(Business))).scalars().all()
        if existing:
            print(f"[seed] {len(existing)} businesses already present, skipping.")
            return

        # Restaurant
        restaurant = Business(
            id=uuid.uuid4(),
            name="Trattoria Demo",
            domain="restaurant",
            default_language="it",
            settings={"opening_hours": {"mon_sat": "18:30-23:00", "sun": "closed"}},
        )
        session.add(restaurant)

        dentist = Business(
            id=uuid.uuid4(),
            name="Studio Dentistico Demo",
            domain="dentist",
            default_language="it",
        )
        session.add(dentist)

        bodyshop = Business(
            id=uuid.uuid4(),
            name="Carrozzeria Demo",
            domain="bodyshop",
            default_language="it",
        )
        session.add(bodyshop)

        await session.flush()

        for biz, tpl in (
            (restaurant, RESTAURANT_TEMPLATE),
            (dentist, DENTIST_TEMPLATE),
            (bodyshop, BODYSHOP_TEMPLATE),
        ):
            session.add(
                Template(
                    id=uuid.uuid4(),
                    business_id=biz.id,
                    name=tpl["name"],
                    version=1,
                    description=tpl["description"],
                    fields_schema=tpl["fields_schema"],
                    action_types=tpl["action_types"],
                    custom_dictionary=tpl["custom_dictionary"],
                    prompt_hints=tpl["prompt_hints"],
                    is_active=True,
                )
            )

        # Two known customers on the restaurant for cross-call demo
        session.add(
            Customer(
                id=uuid.uuid4(),
                business_id=restaurant.id,
                phone_e164="+393331112233",
                display_name="Marco Rossi",
                preferred_language="it",
                tags=["repeat", "gluten_free"],
                memory_summary="Cliente abituale, intollerante al glutine. Ultima prenotazione: 4 persone, tavolo tranquillo.",
                total_calls=2,
                last_call_at=datetime(2026, 5, 7, 20, 30, tzinfo=timezone.utc),
            )
        )
        session.add(
            Customer(
                id=uuid.uuid4(),
                business_id=restaurant.id,
                phone_e164="+393334445566",
                display_name="Giulia Bianchi",
                preferred_language="it",
                tags=["vip", "anniversary"],
                memory_summary="Cliente VIP, ama il tavolo vicino alla finestra. Festeggerà anniversario il 20 maggio.",
                total_calls=1,
                last_call_at=datetime(2026, 4, 15, 21, 0, tzinfo=timezone.utc),
            )
        )

        await session.commit()
        print("[seed] Demo data inserted.")


if __name__ == "__main__":
    asyncio.run(seed())
