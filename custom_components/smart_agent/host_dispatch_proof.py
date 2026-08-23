"""Home Assistant adapter for selecting the exact dispatch-proof secret."""
from __future__ import annotations

from typing import Any

from .const import DOMAIN
from .dispatch_proof import (
    PROOF_VERSION,
    DispatchProofError,
    dispatch_proof_secret_for_clients,
    key_id,
)


def dispatch_proof_secret_for_ha_request(
    hass: Any,
    proof: Any,
    *,
    request_bearer: str = "",
) -> str:
    """Select the authenticated v1 bridge bearer or an exact legacy client key.

    Field-canary v2 remains in its independently provisioned client-key domain.
    """

    if type(proof) is dict and proof.get("v") == PROOF_VERSION:
        proof_kid = proof.get("kid")
        if type(proof_kid) is str and proof_kid and type(request_bearer) is str:
            try:
                if key_id(request_bearer, version=PROOF_VERSION) == proof_kid:
                    return request_bearer
            except DispatchProofError:
                pass

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
