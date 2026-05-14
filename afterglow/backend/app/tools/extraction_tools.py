"""ADK tools for Extraction Agent — tool-state pattern.

Same shape as the lablab baseline (`tool_context.state[...]`). All
list params are typed as `list[str]` to avoid the Gemini INVALID_ARGUMENT
gotcha on generic `list` (see hackathon-docs/14-... r. 143-148).
"""
from __future__ import annotations

from typing import Optional

from google.adk.tools.tool_context import ToolContext


def save_restaurant_booking(
    tool_context: ToolContext,
    customer_name: Optional[str] = None,
    party_size: Optional[int] = None,
    booking_date: Optional[str] = None,
    booking_time: Optional[str] = None,
    allergies: Optional[list[str]] = None,
    seating_preference: Optional[str] = None,
    occasion: Optional[str] = None,
    callback_channel: Optional[str] = None,
    confidence: Optional[float] = None,
    evidence_quotes: Optional[list[str]] = None,
) -> str:
    """Save fields extracted from a restaurant booking call.

    Args:
        customer_name: Caller name as said on the call.
        party_size: Number of guests.
        booking_date: ISO date YYYY-MM-DD (resolve relative dates like "venerdi prossimo").
        booking_time: 24h HH:MM.
        allergies: Allergies or food intolerances (sensitive — flag for review).
        seating_preference: Free text (e.g. "tavolo tranquillo").
        occasion: Special occasion ("anniversary", "birthday", ...).
        callback_channel: One of "whatsapp", "sms", "email", "none".
        confidence: Overall confidence 0..1.
        evidence_quotes: Verbatim transcript fragments supporting the extraction.

    Returns:
        Confirmation string.
    """
    tool_context.state["extraction_result"] = {
        "template_key": "restaurant",
        "fields": {
            "customer_name": customer_name,
            "party_size": party_size,
            "booking_date": booking_date,
            "booking_time": booking_time,
            "allergies": allergies or [],
            "seating_preference": seating_preference,
            "occasion": occasion,
            "callback_channel": callback_channel,
        },
        "confidence_overall": confidence,
        "evidence_quotes": evidence_quotes or [],
    }
    return "Restaurant booking extraction saved."


def save_dentist_appointment(
    tool_context: ToolContext,
    patient_name: Optional[str] = None,
    is_new_patient: Optional[bool] = None,
    reason: Optional[str] = None,
    urgency: Optional[str] = None,
    preferred_date: Optional[str] = None,
    preferred_time_window: Optional[str] = None,
    confidence: Optional[float] = None,
    evidence_quotes: Optional[list[str]] = None,
) -> str:
    """Save fields extracted from a dental clinic call. Health data is sensitive."""
    tool_context.state["extraction_result"] = {
        "template_key": "dentist",
        "fields": {
            "patient_name": patient_name,
            "is_new_patient": is_new_patient,
            "reason": reason,
            "urgency": urgency,
            "preferred_date": preferred_date,
            "preferred_time_window": preferred_time_window,
        },
        "confidence_overall": confidence,
        "evidence_quotes": evidence_quotes or [],
    }
    return "Dentist appointment extraction saved."


def save_bodyshop_quote(
    tool_context: ToolContext,
    customer_name: Optional[str] = None,
    vehicle_make_model: Optional[str] = None,
    license_plate: Optional[str] = None,
    damage_type: Optional[str] = None,
    insurance_involved: Optional[bool] = None,
    drivable: Optional[bool] = None,
    confidence: Optional[float] = None,
    evidence_quotes: Optional[list[str]] = None,
) -> str:
    """Save fields extracted from a body shop quote/inspection call."""
    tool_context.state["extraction_result"] = {
        "template_key": "bodyshop",
        "fields": {
            "customer_name": customer_name,
            "vehicle_make_model": vehicle_make_model,
            "license_plate": license_plate,
            "damage_type": damage_type,
            "insurance_involved": insurance_involved,
            "drivable": drivable,
        },
        "confidence_overall": confidence,
        "evidence_quotes": evidence_quotes or [],
    }
    return "Body shop quote extraction saved."
