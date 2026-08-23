"""One-shot HA RegistrySnapshot publisher for the dedicated add-on listener.

This module reads registries only.  It never calls an HA service, never invokes
``update_entity``, and never sends the ordinary add-on bearer token.
"""
from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from urllib.parse import urlsplit

import aiohttp

from .const import (
    CONF_REFRESH_REGISTRY_ATTESTATION_SECRET,
    CONF_REFRESH_REGISTRY_INGRESS_SECRET,
    CONF_REFRESH_REGISTRY_INGRESS_URL,
    CONF_REFRESH_REGISTRY_SITE_ID,
    CONF_REFRESH_REGISTRY_SOURCE_ENABLED,
    DEFAULT_REFRESH_REGISTRY_INGRESS_URL,
)
from .refresh_registry_attestation import (
    attestation_envelope_digest,
    attestation_key_id,
    issue_refresh_registry_attestation,
)
from .refresh_registry_ingress import (
    sign_registry_challenge_request,
    sign_registry_commit_request,
    verify_registry_challenge_response,
    verify_registry_commit_response,
)
from .refresh_registry_snapshot import (
    build_ha_refresh_registry_snapshot,
    ha_installation_digest,
)


REGISTRY_CHALLENGE_PATH = (
    "/api/v1/internal/observation-refresh/registry/challenges"
)
REGISTRY_COMMIT_PATH = "/api/v1/internal/observation-refresh/registry/commits"
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class RefreshRegistryPublisherError(RuntimeError):
    """The read-only publisher could not establish a durable source fact."""


def _text(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise RefreshRegistryPublisherError(f"{field_name}_invalid")
    return value


def _secret(value: Any, field_name: str) -> str:
    if type(value) is not str or len(value) < 32:
        raise RefreshRegistryPublisherError(f"{field_name}_invalid")
    return value


def _url(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise RefreshRegistryPublisherError("refresh_registry_ingress_url_invalid")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise RefreshRegistryPublisherError("refresh_registry_ingress_url_invalid")
    return value.rstrip("/")


def _utc_now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise RefreshRegistryPublisherError("refresh_registry_publisher_clock_invalid")
    try:
        return value.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise RefreshRegistryPublisherError(
            "refresh_registry_publisher_clock_invalid"
        ) from exc


@dataclass(frozen=True, slots=True)
class RefreshRegistryPublisherConfig:
    enabled: bool
    ingress_url: str = DEFAULT_REFRESH_REGISTRY_INGRESS_URL
    site_id: str = ""
    ingress_secret: str = ""
    attestation_secret: str = ""

    @classmethod
    def from_entry(cls, entry: Any) -> "RefreshRegistryPublisherConfig":
        values = {**dict(getattr(entry, "data", {}) or {}), **dict(getattr(entry, "options", {}) or {})}
        config = cls(
            enabled=values.get(CONF_REFRESH_REGISTRY_SOURCE_ENABLED, False),
            ingress_url=values.get(
                CONF_REFRESH_REGISTRY_INGRESS_URL,
                DEFAULT_REFRESH_REGISTRY_INGRESS_URL,
            ),
            site_id=values.get(CONF_REFRESH_REGISTRY_SITE_ID, ""),
            ingress_secret=values.get(CONF_REFRESH_REGISTRY_INGRESS_SECRET, ""),
            attestation_secret=values.get(
                CONF_REFRESH_REGISTRY_ATTESTATION_SECRET, ""
            ),
        )
        return config.validated()

    def validated(self) -> "RefreshRegistryPublisherConfig":
        if type(self.enabled) is not bool:
            raise RefreshRegistryPublisherError(
                "refresh_registry_source_enabled_invalid"
            )
        if not self.enabled:
            return self
        _url(self.ingress_url)
        _text(self.site_id, "refresh_registry_site_id")
        ingress_secret = _secret(
            self.ingress_secret, "refresh_registry_ingress_secret"
        )
        attestation_secret = _secret(
            self.attestation_secret, "refresh_registry_attestation_secret"
        )
        if ingress_secret == attestation_secret:
            raise RefreshRegistryPublisherError(
                "refresh_registry_secret_reuse_forbidden"
            )
        return self


async def _post_json(
    session: aiohttp.ClientSession,
    *,
    url: str,
    payload: dict[str, Any],
    accepted_statuses: set[int],
) -> dict[str, Any]:
    async with session.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=_REQUEST_TIMEOUT,
    ) as response:
        try:
            body = await response.json(content_type=None)
        except Exception as exc:
            raise RefreshRegistryPublisherError(
                "refresh_registry_ingress_response_invalid"
            ) from exc
        if response.status not in accepted_statuses or type(body) is not dict:
            raise RefreshRegistryPublisherError(
                "refresh_registry_ingress_request_rejected"
            )
        return body


async def async_publish_refresh_registry_snapshot_once(
    hass: Any,
    entry: Any,
    *,
    config: RefreshRegistryPublisherConfig | None = None,
    session: aiohttp.ClientSession | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Publish one complete HA registry snapshot with no HA/device mutation."""

    active_config = (config or RefreshRegistryPublisherConfig.from_entry(entry)).validated()
    if not active_config.enabled:
        return {
            "ok": False,
            "disposition": "disabled",
            "catalog_write_committed": False,
            "refresh_dispatch_authorized": False,
            "execution_eligible": False,
            "device_effect_authority": "none",
        }

    from homeassistant.helpers import device_registry, entity_registry, instance_id

    installation_id = await instance_id.async_get(hass)
    installation_digest = ha_installation_digest(installation_id)
    base_url = _url(active_config.ingress_url)
    own_session = session is None
    active_session = session or aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT)
    try:
        # If the challenge ACK is lost, issue one new request-id.  The add-on
        # atomically supersedes the unknown earlier challenge, so no nonce is
        # reused and no unsigned client-side recovery fact is invented.
        challenge_response: dict[str, Any] | None = None
        challenge_request_id = ""
        for attempt_index in range(2):
            challenge_request_id = f"ha-refresh-challenge-{secrets.token_hex(12)}"
            challenge_request = sign_registry_challenge_request(
                secret=active_config.ingress_secret,
                request_id=challenge_request_id,
                requested_at=_utc_now(clock),
            )
            try:
                challenge_response = await _post_json(
                    active_session,
                    url=f"{base_url}{REGISTRY_CHALLENGE_PATH}",
                    payload=challenge_request,
                    accepted_statuses={201},
                )
                break
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
                if attempt_index:
                    raise
        if challenge_response is None:
            raise RefreshRegistryPublisherError(
                "refresh_registry_challenge_unavailable"
            )
        challenge = verify_registry_challenge_response(
            challenge_response,
            secret=active_config.ingress_secret,
            expected_request_id=challenge_request_id,
            expected_site_id=active_config.site_id,
            expected_ha_installation_digest=installation_digest,
            expected_bridge_config_entry_id=entry.entry_id,
            expected_attestation_key_id=attestation_key_id(
                active_config.attestation_secret
            ),
            evaluated_at=_utc_now(clock),
        )

        # Deliberately no await in this registry capture slice.
        captured_at = _utc_now(clock)
        snapshot = build_ha_refresh_registry_snapshot(
            entity_registry=entity_registry.async_get(hass),
            device_registry=device_registry.async_get(hass),
            config_entries=hass.config_entries,
            ha_instance_id=installation_id,
            bridge_config_entry_id=entry.entry_id,
            request_nonce=challenge["request_nonce"],
            source_seq=challenge["source_seq"],
            captured_at=captured_at,
            expires_at=datetime.fromisoformat(challenge["expires_at"]),
        )
        attestation = issue_refresh_registry_attestation(
            snapshot,
            secret=active_config.attestation_secret,
            site_id=active_config.site_id,
            issued_at=_utc_now(clock),
        )
        commit_request_id = f"ha-refresh-commit-{secrets.token_hex(12)}"
        commit_request = sign_registry_commit_request(
            secret=active_config.ingress_secret,
            request_id=commit_request_id,
            requested_at=_utc_now(clock),
            challenge_id=challenge["challenge_id"],
            attestation=attestation,
        )

        # A transport ambiguity retries the exact same signed body once.
        try:
            result = await _post_json(
                active_session,
                url=f"{base_url}{REGISTRY_COMMIT_PATH}",
                payload=commit_request,
                accepted_statuses={200, 202, 409, 500, 503},
            )
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            result = await _post_json(
                active_session,
                url=f"{base_url}{REGISTRY_COMMIT_PATH}",
                payload=commit_request,
                accepted_statuses={200, 202, 409, 500, 503},
            )
        try:
            return verify_registry_commit_response(
                result,
                secret=active_config.ingress_secret,
                expected_request_id=commit_request_id,
                expected_challenge_id=challenge["challenge_id"],
                expected_attestation_id=attestation["attestation_id"],
                expected_attestation_envelope_digest=attestation_envelope_digest(
                    attestation
                ),
                expected_source_seq=attestation["source_seq"],
                expected_snapshot_id=attestation["snapshot_id"],
                expected_snapshot_digest=attestation["snapshot_digest"],
            )
        except Exception as exc:
            raise RefreshRegistryPublisherError(
                "refresh_registry_ingress_result_invalid"
            ) from exc
    finally:
        if own_session:
            await active_session.close()


__all__: list[str] = []
