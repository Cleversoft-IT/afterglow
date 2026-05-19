"""Mock external integrations — bookings, messaging, calendar, payment, review, CRM.

Each mock returns a deterministic-looking payload so the demo feels real
without touching live systems. The ActionExecutor stamps `mock: True` on the
resulting `ExecutedAction.result` so the UI can render a "Simulated external
call" badge — judges see the boundary between real AI work and stubbed
integrations.

Dispatch is per `action_key`, NOT per bucket: every entry in `CATALOG` with
`integration_kind="mock_external"` must have its own row below, even if it
shares the underlying handler with another action (the executor looks up by
the literal action_key — see `executors/action_executor.py`).
"""
from app.integrations.mocks.booking import (
    cancel_booking_mock,
    create_booking_mock,
    reschedule_booking_mock,
)
from app.integrations.mocks.calendar import (
    add_calendar_event_mock,
    block_calendar_slot_mock,
    send_calendar_invite_mock,
)
from app.integrations.mocks.crm import (
    create_lead_mock,
    create_ticket_mock,
    update_customer_mock,
)
from app.integrations.mocks.email import send_email_mock, send_quote_email_mock
from app.integrations.mocks.payment import (
    create_payment_link_mock,
    request_deposit_mock,
    send_invoice_mock,
)
from app.integrations.mocks.review import (
    publish_review_response_mock,
    request_review_feedback_mock,
)
from app.integrations.mocks.sms import send_sms_mock
from app.integrations.mocks.whatsapp import request_photos_mock, send_whatsapp_mock

MOCK_REGISTRY = {
    # Booking bucket — single namespace covers every vertical (restaurant /
    # dentist / bodyshop / salon / gym / hotel / events / clinic).
    "booking.create": create_booking_mock,
    "booking.cancel": cancel_booking_mock,
    "booking.reschedule": reschedule_booking_mock,
    # WhatsApp bucket
    "whatsapp.send_confirmation": send_whatsapp_mock,
    "whatsapp.request_photos": request_photos_mock,
    # SMS bucket (sms.send_reminder used to dispatch to WhatsApp — fixed 2026-05-18)
    "sms.send_reminder": send_sms_mock,
    "sms.send_confirmation": send_sms_mock,
    "sms.send_link": send_sms_mock,
    # Email bucket
    "email.send": send_email_mock,
    "email.send_quote": send_quote_email_mock,
    # Calendar bucket
    "calendar.add_event": add_calendar_event_mock,
    "calendar.send_invite": send_calendar_invite_mock,
    "calendar.block_slot": block_calendar_slot_mock,
    # Payment bucket
    "payment.create_link": create_payment_link_mock,
    "payment.request_deposit": request_deposit_mock,
    "payment.send_invoice": send_invoice_mock,
    # Review bucket
    "review.request_feedback": request_review_feedback_mock,
    "review.publish_response": publish_review_response_mock,
    # CRM bucket
    "case.open_insurance": update_customer_mock,
    "crm.create_lead": create_lead_mock,
    "crm.create_ticket": create_ticket_mock,
    # internal_real action keys below are NOT dispatched here (the executor
    # branches by integration_kind), but kept for back-compat in case any
    # downstream still calls `MOCK_REGISTRY.get(key)` defensively.
    "customer.update_profile": update_customer_mock,
    "patient.update_profile": update_customer_mock,
}


def available_keys() -> list[str]:
    """List the action_type keys backed by a registered mock target.

    Used by the template_validator's deterministic step to flag action_types
    in a generated template that would land as `status='failed'` because
    nothing in MOCK_REGISTRY knows how to handle them.
    """
    return sorted(MOCK_REGISTRY.keys())


__all__ = ["MOCK_REGISTRY", "available_keys"]
