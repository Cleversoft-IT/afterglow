"""Pydantic schema for the read-only Integrations marketplace surface.

The Integrations drawer screen (`app/(drawer)/integrations.tsx`) consumes a
flat list of these summaries — one per `mock_target` / `internal_handler`
prefix — to render a consultative list of channels Afterglow can act on,
with a Simulated / Live badge. No drill-down, no detail, no actions.

The aggregation logic lives in `app.integrations.action_catalog.aggregate_integrations`
(pure function, no I/O). This module only describes the wire shape.
"""
from typing import Literal

from pydantic import BaseModel


class IntegrationSummary(BaseModel):
    key: str  # bucket identifier, e.g. "booking", "calendar", "customer_profile"
    label: str  # human-readable label rendered in the UI
    kind: Literal["simulated", "live"]
    action_count: int
