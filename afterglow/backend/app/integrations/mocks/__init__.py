"""Mock external integrations — bookings, WhatsApp, email, CRM.

Each mock returns a deterministic-looking payload so the demo feels real
without touching live systems. Wired into the deterministic ActionExecutor.
"""
from app.integrations.mocks.booking import create_booking_mock, cancel_booking_mock
from app.integrations.mocks.whatsapp import send_whatsapp_mock, request_photos_mock
from app.integrations.mocks.email import send_email_mock
from app.integrations.mocks.crm import update_customer_mock

MOCK_REGISTRY = {
    "booking.create": create_booking_mock,
    "booking.cancel": cancel_booking_mock,
    "appointment.create": create_booking_mock,
    "appointment.create_inspection": create_booking_mock,
    "whatsapp.send_confirmation": send_whatsapp_mock,
    "whatsapp.request_photos": request_photos_mock,
    "sms.send_reminder": send_whatsapp_mock,
    "email.send": send_email_mock,
    "customer.update_profile": update_customer_mock,
    "patient.update_profile": update_customer_mock,
    "case.open_insurance": update_customer_mock,
}

__all__ = ["MOCK_REGISTRY"]
