"""Pure secret-domain validation for SmartAgent's dedicated HA channels."""
from __future__ import annotations

from collections.abc import Iterable, Mapping


MIN_DEDICATED_SECRET_LENGTH = 32

ADDON_AUTH_TOKEN_KEY = "addon_auth_token"
DEDICATED_SECURITY_CHANNEL_SECRET_KEYS = (
    "refresh_registry_ingress_secret",
    "refresh_registry_attestation_secret",
    "observation_refresh_provider_request_secret",
    "observation_refresh_provider_previous_request_secret",
    "observation_refresh_provider_replay_integrity_secret",
    "output_ledger_ingress_secret",
    "output_ledger_attestation_secret",
    "maintenance_change_ingress_secret",
    "maintenance_delegation_attestation_secret",
    "field_canary_operator_identity_ingress_secret",
    "field_canary_operator_identity_attestation_secret",
    "field_canary_operator_identity_previous_attestation_secret",
    "field_canary_host_dispatch_proof_secret",
    "field_canary_previous_host_dispatch_proof_secret",
    "user_intent_delegation_secret",
)


def security_channel_secret_domains_are_valid(
    *,
    addon_auth_token: object,
    dedicated_secrets: Iterable[object],
) -> bool:
    """Return whether persisted channel secrets are strict and domain-separated.

    Empty dedicated values are allowed so a channel can remain disabled.  Any
    non-empty dedicated value is still validated because OptionsFlow persists
    it and a later enable operation must not silently activate a reused key.
    """

    if type(addon_auth_token) is not str:
        return False
    normalized_addon_token = addon_auth_token.strip()
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in normalized_addon_token
    ):
        return False

    nonempty_dedicated: list[str] = []
    for value in dedicated_secrets:
        if type(value) is not str:
            return False
        if not value:
            continue
        if (
            len(value) < MIN_DEDICATED_SECRET_LENGTH
            or value != value.strip()
            or any(
                ord(character) < 32 or ord(character) == 127
                for character in value
            )
        ):
            return False
        nonempty_dedicated.append(value)

    all_nonempty = [*nonempty_dedicated]
    if normalized_addon_token:
        all_nonempty.append(normalized_addon_token)
    return len(set(all_nonempty)) == len(all_nonempty)


def security_channel_secret_mapping_is_valid(values: Mapping[str, object]) -> bool:
    """Validate all persisted HA channel secret domains from one config view."""

    if not isinstance(values, Mapping):
        return False
    return security_channel_secret_domains_are_valid(
        addon_auth_token=values.get(ADDON_AUTH_TOKEN_KEY, ""),
        dedicated_secrets=tuple(
            values.get(key, "") for key in DEDICATED_SECURITY_CHANNEL_SECRET_KEYS
        ),
    )


__all__ = [
    "DEDICATED_SECURITY_CHANNEL_SECRET_KEYS",
    "security_channel_secret_domains_are_valid",
    "security_channel_secret_mapping_is_valid",
]
