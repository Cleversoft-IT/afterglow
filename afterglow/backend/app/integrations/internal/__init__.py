"""Internal-real action handlers — mutate Postgres for actual.

Unlike the mocks in `app/integrations/mocks/`, these functions persist
changes to live Customer / Memory rows. The executor stamps the resulting
ExecutedAction with `mock=False` so the UI does not show a "Simulated"
badge — the operator (and the judges) can trust that the side-effect
happened.
"""
from app.integrations.internal.customer_profile import (
    apply_customer_update,
    revert_customer_update,
)


INTERNAL_HANDLERS = {
    "customer_profile.apply_update": apply_customer_update,
    # The revert side stays out of MOCK_REGISTRY-style invocation; the
    # action_executor invokes it directly when /actions/{id}/undo lands
    # on an internal_real entry.
}

INTERNAL_REVERTERS = {
    "customer_profile.apply_update": revert_customer_update,
}


__all__ = [
    "INTERNAL_HANDLERS",
    "INTERNAL_REVERTERS",
    "apply_customer_update",
    "revert_customer_update",
]
