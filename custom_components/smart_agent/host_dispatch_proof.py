"""Home Assistant adapter for selecting the exact dispatch-proof secret."""
from __future__ import annotations

from typing import Any

from .const import DOMAIN
from .dispatch_proof import dispatch_proof_secret_for_clients


def dispatch_proof_secret_for_ha_request(
    hass: Any,
    proof: Any,
) -> str:
    """Select an exact key from the HA-side dedicated proof keyrings."""

    coordinators = hass.data.get(DOMAIN, {})
    values = coordinators.values() if isinstance(coordinators, dict) else ()
    clients = tuple(
        addon_client
        for coordinator in values
        if (addon_client := getattr(coordinator, "_addon_client", None))
        is not None
    )
    return dispatch_proof_secret_for_clients(proof, clients)


__all__ = ["dispatch_proof_secret_for_ha_request"]
