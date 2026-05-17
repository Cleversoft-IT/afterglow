"""Integrations marketplace API — read-only consultative surface.

Returns the catalog grouped by bucket (`mock_target` for `mock_external`
actions, prefix of `internal_handler` for `internal_real`). Powers the
"Integrations" drawer screen on the Expo app.

No DB access, no lifespan dependency: the response is derived from the
in-memory `CATALOG` via the pure `aggregate_integrations()` helper. The
endpoint still hangs off `get_session_context` for CORS / demo session
plumbing consistency with the rest of the API.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.session_context import SessionContext, get_session_context
from app.integrations.action_catalog import aggregate_integrations
from app.schemas.integrations import IntegrationSummary

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.get("", response_model=list[IntegrationSummary])
async def list_integrations(
    ctx: SessionContext = Depends(get_session_context),
) -> list[IntegrationSummary]:
    """Return one entry per integration bucket (mock target or internal handler)."""
    return [IntegrationSummary(**bucket) for bucket in aggregate_integrations()]
