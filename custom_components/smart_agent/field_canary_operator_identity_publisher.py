"""Current-session publisher for the dedicated Field Canary operator ingress.

The caller must pass the exact Home Assistant WebSocket connection that is
handling the current administrator gesture.  Identity attestation and explicit
approval publication are separate public functions.  A third explicit function
may request the exact server-owned Grant definition after approval; the returned
Grant remains non-executable and this module has no device command or background
retry loop.  Revocation remains a current-admin two-stage gesture: prepare first,
then submit the exact signed approval-bound terminal request.
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
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_SECRET,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_ENABLED,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_SECRET,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_PREVIOUS_ATTESTATION_SECRET,
    DEFAULT_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL,
)
from .field_canary_operator_identity_attestation import (
    FieldCanaryOperatorSessionAttestationError,
    async_attest_current_ha_admin_session,
    field_canary_operator_identity_attestation_key_id,
    sign_field_canary_operator_identity_challenge_request,
    sign_field_canary_operator_identity_commit_request,
    sign_field_canary_operator_approval_request,
    sign_field_canary_promotion_grant_operator_revocation_request,
    sign_field_canary_promotion_grant_revocation_proposal_request,
    sign_field_canary_promotion_grant_request,
    verify_field_canary_operator_identity_challenge_response,
    verify_field_canary_operator_identity_commit_response,
    verify_field_canary_operator_approval_response,
    verify_field_canary_promotion_grant_operator_revocation_response,
    verify_field_canary_promotion_grant_revocation_proposal_response,
    verify_field_canary_promotion_grant_response,
)
from .refresh_registry_snapshot import ha_installation_digest


CHALLENGE_PATH = "/api/v1/internal/field-canary/operator-identity/challenges"
COMMIT_PATH = "/api/v1/internal/field-canary/operator-identity/commits"
APPROVAL_PATH = "/api/v1/internal/field-canary/operator-approvals/commits"
PROMOTION_GRANT_ISSUE_PATH = "/api/v1/internal/field-canary/promotion-grants/issue"
PROMOTION_GRANT_REVOCATION_PROPOSAL_PATH = (
    "/api/v1/internal/field-canary/promotion-grants/revocation-proposals"
)
PROMOTION_GRANT_OPERATOR_REVOCATION_PATH = (
    "/api/v1/internal/field-canary/promotion-grants/revocations/commits"
)
_TIMEOUT = aiohttp.ClientTimeout(total=30)


class FieldCanaryOperatorIdentityPublisherError(RuntimeError):
    """The explicit current-session identity handshake did not complete."""


def _secret(value: Any, name: str, *, optional: bool = False) -> str:
    if optional and value == "":
        return ""
    if (
        type(value) is not str
        or len(value) < 32
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise FieldCanaryOperatorIdentityPublisherError(f"{name}_invalid")
    return value


def _url(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise FieldCanaryOperatorIdentityPublisherError(
            "field_canary_operator_identity_ingress_url_invalid"
        )
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
        raise FieldCanaryOperatorIdentityPublisherError(
            "field_canary_operator_identity_ingress_url_invalid"
        )
    return value.rstrip("/")


def _now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if type(value) is not datetime or value.tzinfo is None:
        raise FieldCanaryOperatorIdentityPublisherError(
            "field_canary_operator_identity_clock_invalid"
        )
    try:
        return value.astimezone(UTC)
    except (OverflowError, ValueError) as exc:
        raise FieldCanaryOperatorIdentityPublisherError(
            "field_canary_operator_identity_clock_invalid"
        ) from exc


@dataclass(frozen=True, slots=True)
class FieldCanaryOperatorIdentityPublisherConfig:
    enabled: bool
    ingress_url: str = DEFAULT_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL
    ingress_secret: str = ""
    attestation_secret: str = ""
    previous_attestation_secret: str = ""

    @classmethod
    def from_entry(cls, entry: Any) -> "FieldCanaryOperatorIdentityPublisherConfig":
        values = {
            **dict(getattr(entry, "data", {}) or {}),
            **dict(getattr(entry, "options", {}) or {}),
        }
        return cls(
            enabled=values.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_ENABLED, False
            ),
            ingress_url=values.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL,
                DEFAULT_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL,
            ),
            ingress_secret=values.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_SECRET, ""
            ),
            attestation_secret=values.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_SECRET, ""
            ),
            previous_attestation_secret=values.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_PREVIOUS_ATTESTATION_SECRET, ""
            ),
        ).validated()

    def validated(self) -> "FieldCanaryOperatorIdentityPublisherConfig":
        if type(self.enabled) is not bool:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_operator_identity_enabled_invalid"
            )
        if not self.enabled:
            return self
        _url(self.ingress_url)
        secrets_to_check = (
            _secret(self.ingress_secret, "field_canary_operator_identity_ingress_secret"),
            _secret(
                self.attestation_secret,
                "field_canary_operator_identity_attestation_secret",
            ),
        )
        previous = _secret(
            self.previous_attestation_secret,
            "field_canary_operator_identity_previous_attestation_secret",
            optional=True,
        )
        all_values = secrets_to_check + ((previous,) if previous else ())
        if len(set(all_values)) != len(all_values):
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_operator_identity_secret_reuse_forbidden"
            )
        return self


async def _post(
    session: aiohttp.ClientSession,
    *,
    url: str,
    body: dict[str, Any],
    accepted_statuses: set[int],
) -> dict[str, Any]:
    async with session.post(
        url,
        json=body,
        headers={"Content-Type": "application/json"},
        timeout=_TIMEOUT,
    ) as response:
        try:
            payload = await response.json(content_type=None)
        except Exception as exc:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_operator_identity_response_invalid"
            ) from exc
        if response.status not in accepted_statuses or type(payload) is not dict:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_operator_identity_request_rejected"
            )
        return payload


async def async_publish_current_operator_identity(
    hass: Any,
    entry: Any,
    connection: Any,
    *,
    approval_definition_id: str,
    config: FieldCanaryOperatorIdentityPublisherConfig | None = None,
    session: aiohttp.ClientSession | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Persist one current HA admin-session identity, and nothing else."""

    active = (config or FieldCanaryOperatorIdentityPublisherConfig.from_entry(entry)).validated()
    if not active.enabled:
        return {
            "ok": False,
            "disposition": "disabled",
            "canonical_operator_identity_verified": False,
            "approval_record_issued": False,
            "promotion_grant_issued": False,
            "execution_eligible": False,
            "execution_permitted": False,
            "field_accepted": False,
            "device_effect_authority": "none",
        }
    if type(approval_definition_id) is not str or not approval_definition_id.strip():
        raise FieldCanaryOperatorIdentityPublisherError(
            "field_canary_operator_approval_definition_invalid"
        )

    from homeassistant.helpers import instance_id

    installation_digest = ha_installation_digest(await instance_id.async_get(hass))
    base_url = _url(active.ingress_url)
    own_session = session is None
    client = session or aiohttp.ClientSession(timeout=_TIMEOUT)
    try:
        challenge_request_id = f"fcoicr_{secrets.token_hex(16)}"
        challenge_request = dict(
            sign_field_canary_operator_identity_challenge_request(
                request_id=challenge_request_id,
                approval_definition_id=approval_definition_id.strip(),
                requested_at=_now(clock),
                ingress_secret=active.ingress_secret,
            )
        )
        challenge_response = await _post(
            client,
            url=f"{base_url}{CHALLENGE_PATH}",
            body=challenge_request,
            accepted_statuses={201},
        )
        response_key_id = challenge_response.get("expected_attestation_key_id")
        attestation_by_key = {
            field_canary_operator_identity_attestation_key_id(secret): secret
            for secret in (active.attestation_secret, active.previous_attestation_secret)
            if secret
        }
        selected_attestation_secret = attestation_by_key.get(response_key_id)
        if selected_attestation_secret is None:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_operator_attestation_key_unavailable"
            )
        challenge = verify_field_canary_operator_identity_challenge_response(
            challenge_response,
            ingress_secret=active.ingress_secret,
            expected_request_id=challenge_request_id,
            expected_approval_definition_id=approval_definition_id.strip(),
            expected_ha_installation_digest=installation_digest,
            expected_bridge_config_entry_id=entry.entry_id,
            expected_attestation_key_id=response_key_id,
            evaluated_at=_now(clock),
        )
        attestation = await async_attest_current_ha_admin_session(
            hass,
            connection,
            challenge=challenge,
            attestation_secret=selected_attestation_secret,
            clock=clock,
        )
        commit_request_id = f"fcoicm_{secrets.token_hex(16)}"
        commit_request = dict(
            sign_field_canary_operator_identity_commit_request(
                request_id=commit_request_id,
                challenge_id=attestation["challenge_id"],
                attestation=attestation,
                requested_at=_now(clock),
                ingress_secret=active.ingress_secret,
            )
        )
        try:
            commit_response = await _post(
                client,
                url=f"{base_url}{COMMIT_PATH}",
                body=commit_request,
                accepted_statuses={200},
            )
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            # Only the exact same signed commit fact is retried.
            commit_response = await _post(
                client,
                url=f"{base_url}{COMMIT_PATH}",
                body=commit_request,
                accepted_statuses={200},
            )
        try:
            verified = verify_field_canary_operator_identity_commit_response(
                commit_response,
                ingress_secret=active.ingress_secret,
                expected_request_id=commit_request_id,
                expected_challenge_id=attestation["challenge_id"],
                expected_approval_definition_id=attestation["approval_definition_id"],
                expected_identity_record_id=attestation["attestation_id"],
            )
        except FieldCanaryOperatorSessionAttestationError as exc:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_operator_identity_response_invalid"
            ) from exc
        return dict(verified)
    finally:
        if own_session:
            await client.close()


async def async_publish_current_operator_approval(
    hass: Any,
    entry: Any,
    connection: Any,
    *,
    approval_definition_id: str,
    config: FieldCanaryOperatorIdentityPublisherConfig | None = None,
    session: aiohttp.ClientSession | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Attest the current session, then explicitly publish its exact approval."""

    active = (
        config or FieldCanaryOperatorIdentityPublisherConfig.from_entry(entry)
    ).validated()
    if not active.enabled:
        return {
            "ok": False,
            "disposition": "disabled",
            "canonical_operator_identity_verified": False,
            "approval_record_issued": False,
            "promotion_grant_issued": False,
            "execution_eligible": False,
            "execution_permitted": False,
            "field_accepted": False,
            "device_effect_authority": "none",
        }
    own_session = session is None
    client = session or aiohttp.ClientSession(timeout=_TIMEOUT)
    try:
        identity = await async_publish_current_operator_identity(
            hass,
            entry,
            connection,
            approval_definition_id=approval_definition_id,
            config=active,
            session=client,
            clock=clock,
        )
        request_id = f"fcoapr_{secrets.token_hex(16)}"
        request = dict(
            sign_field_canary_operator_approval_request(
                request_id=request_id,
                approval_definition_id=approval_definition_id.strip(),
                identity_record_id=identity["identity_record_id"],
                identity_record_digest=identity["identity_record_digest"],
                requested_at=_now(clock),
                ingress_secret=active.ingress_secret,
            )
        )
        try:
            response = await _post(
                client,
                url=f"{_url(active.ingress_url)}{APPROVAL_PATH}",
                body=request,
                accepted_statuses={200},
            )
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            response = await _post(
                client,
                url=f"{_url(active.ingress_url)}{APPROVAL_PATH}",
                body=request,
                accepted_statuses={200},
            )
        try:
            verified = verify_field_canary_operator_approval_response(
                response,
                ingress_secret=active.ingress_secret,
                expected_request_id=request_id,
                expected_approval_definition_id=approval_definition_id.strip(),
                expected_identity_record_id=identity["identity_record_id"],
                expected_identity_record_digest=identity["identity_record_digest"],
            )
        except FieldCanaryOperatorSessionAttestationError as exc:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_operator_approval_response_invalid"
            ) from exc
        return dict(verified)
    finally:
        if own_session:
            await client.close()


async def async_issue_current_operator_promotion_grant(
    hass: Any,
    entry: Any,
    connection: Any,
    *,
    approval_definition_id: str,
    grant_definition_id: str,
    materialization_id: str,
    config: FieldCanaryOperatorIdentityPublisherConfig | None = None,
    session: aiohttp.ClientSession | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Approve and issue one exact server proposal without execution authority."""

    active = (
        config or FieldCanaryOperatorIdentityPublisherConfig.from_entry(entry)
    ).validated()
    if not active.enabled:
        return {
            "ok": False,
            "disposition": "disabled",
            "canonical_operator_identity_verified": False,
            "approval_record_issued": False,
            "promotion_grant_issued": False,
            "execution_eligible": False,
            "execution_permitted": False,
            "field_accepted": False,
            "device_effect_authority": "none",
        }
    own_session = session is None
    client = session or aiohttp.ClientSession(timeout=_TIMEOUT)
    try:
        approval = await async_publish_current_operator_approval(
            hass,
            entry,
            connection,
            approval_definition_id=approval_definition_id,
            config=active,
            session=client,
            clock=clock,
        )
        request_id = f"fcpgrq_{secrets.token_hex(16)}"
        definition_id = grant_definition_id.strip()
        expected_materialization_id = materialization_id.strip()
        request = dict(
            sign_field_canary_promotion_grant_request(
                request_id=request_id,
                grant_definition_id=definition_id,
                materialization_id=expected_materialization_id,
                requested_at=_now(clock),
                ingress_secret=active.ingress_secret,
            )
        )
        try:
            response = await _post(
                client,
                url=f"{_url(active.ingress_url)}{PROMOTION_GRANT_ISSUE_PATH}",
                body=request,
                accepted_statuses={200},
            )
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            response = await _post(
                client,
                url=f"{_url(active.ingress_url)}{PROMOTION_GRANT_ISSUE_PATH}",
                body=request,
                accepted_statuses={200},
            )
        try:
            verified = verify_field_canary_promotion_grant_response(
                response,
                ingress_secret=active.ingress_secret,
                expected_request_id=request_id,
                expected_grant_definition_id=definition_id,
                expected_materialization_id=expected_materialization_id,
                expected_approval_record_id=approval["approval_record_id"],
            )
        except FieldCanaryOperatorSessionAttestationError as exc:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_promotion_grant_response_invalid"
            ) from exc
        return dict(verified)
    finally:
        if own_session:
            await client.close()


async def async_prepare_current_operator_promotion_grant_revocation(
    hass: Any,
    entry: Any,
    connection: Any,
    *,
    grant_id: str,
    config: FieldCanaryOperatorIdentityPublisherConfig | None = None,
    session: aiohttp.ClientSession | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Persist a proposal and current-session approval, but never revoke."""

    active = (
        config or FieldCanaryOperatorIdentityPublisherConfig.from_entry(entry)
    ).validated()
    if not active.enabled:
        return {
            "ok": False,
            "disposition": "disabled",
            "canonical_operator_identity_verified": False,
            "canonical_revoker_identity_verified": False,
            "approval_record_issued": False,
            "grant_revocation_authorized": False,
            "grant_revoked": False,
            "positive_authority": False,
            "execution_eligible": False,
            "execution_permitted": False,
            "field_accepted": False,
            "runtime_consumer_enabled": False,
            "device_effect_authority": "none",
        }
    if type(grant_id) is not str or not grant_id or grant_id != grant_id.strip():
        raise FieldCanaryOperatorIdentityPublisherError(
            "field_canary_promotion_grant_revocation_grant_invalid"
        )
    own_session = session is None
    client = session or aiohttp.ClientSession(timeout=_TIMEOUT)
    try:
        request_id = f"fcpgrp_{secrets.token_hex(16)}"
        request = dict(
            sign_field_canary_promotion_grant_revocation_proposal_request(
                request_id=request_id,
                grant_id=grant_id,
                requested_at=_now(clock),
                ingress_secret=active.ingress_secret,
            )
        )
        try:
            response = await _post(
                client,
                url=(
                    f"{_url(active.ingress_url)}"
                    f"{PROMOTION_GRANT_REVOCATION_PROPOSAL_PATH}"
                ),
                body=request,
                accepted_statuses={201},
            )
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            response = await _post(
                client,
                url=(
                    f"{_url(active.ingress_url)}"
                    f"{PROMOTION_GRANT_REVOCATION_PROPOSAL_PATH}"
                ),
                body=request,
                accepted_statuses={201},
            )
        try:
            proposal = dict(
                verify_field_canary_promotion_grant_revocation_proposal_response(
                    response,
                    ingress_secret=active.ingress_secret,
                    expected_request_id=request_id,
                    expected_grant_id=grant_id,
                )
            )
        except FieldCanaryOperatorSessionAttestationError as exc:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_promotion_grant_revocation_proposal_response_invalid"
            ) from exc
        approval = await async_publish_current_operator_approval(
            hass,
            entry,
            connection,
            approval_definition_id=proposal["approval_definition_id"],
            config=active,
            session=client,
            clock=clock,
        )
        if (
            approval.get("approval_class") != "promotion_grant_revocation"
            or approval.get("subject_id") != proposal["revocation_definition_id"]
            or approval.get("subject_digest")
            != proposal["approval_subject_digest"]
        ):
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_promotion_grant_revocation_approval_binding_invalid"
            )
        return {
            "ok": True,
            "disposition": "revocation_approval_prepared",
            "proposal_id": proposal["proposal_id"],
            "proposal_digest": proposal["proposal_digest"],
            "grant_id": proposal["grant_id"],
            "grant_digest": proposal["grant_digest"],
            "revocation_definition_id": proposal["revocation_definition_id"],
            "approval_definition_id": proposal["approval_definition_id"],
            "approval_record_id": approval["approval_record_id"],
            "approval_record_digest": approval["approval_record_digest"],
            "canonical_operator_identity_verified": True,
            "canonical_revoker_identity_verified": True,
            "approval_record_issued": True,
            "grant_revocation_authorized": False,
            "grant_revoked": False,
            "positive_authority": False,
            "execution_eligible": False,
            "execution_permitted": False,
            "field_accepted": False,
            "runtime_consumer_enabled": False,
            "device_effect_authority": "none",
        }
    finally:
        if own_session:
            await client.close()


async def async_commit_current_operator_promotion_grant_revocation(
    hass: Any,
    entry: Any,
    connection: Any,
    *,
    grant_id: str,
    config: FieldCanaryOperatorIdentityPublisherConfig | None = None,
    session: aiohttp.ClientSession | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Prepare current-admin approval and atomically commit its exact revocation."""

    active = (
        config or FieldCanaryOperatorIdentityPublisherConfig.from_entry(entry)
    ).validated()
    if not active.enabled:
        return {
            "ok": False,
            "disposition": "disabled",
            "canonical_operator_identity_verified": False,
            "canonical_revoker_identity_verified": False,
            "approval_record_issued": False,
            "approval_consumed": False,
            "grant_revocation_authorized": False,
            "grant_revoked": False,
            "positive_authority": False,
            "execution_eligible": False,
            "execution_permitted": False,
            "field_accepted": False,
            "runtime_consumer_enabled": False,
            "device_effect_authority": "none",
        }
    own_session = session is None
    client = session or aiohttp.ClientSession(timeout=_TIMEOUT)
    try:
        prepared = await async_prepare_current_operator_promotion_grant_revocation(
            hass,
            entry,
            connection,
            grant_id=grant_id,
            config=active,
            session=client,
            clock=clock,
        )
        if (
            prepared.get("disposition") != "revocation_approval_prepared"
            or prepared.get("canonical_revoker_identity_verified") is not True
            or prepared.get("approval_record_issued") is not True
            or prepared.get("grant_revocation_authorized") is not False
            or prepared.get("grant_revoked") is not False
        ):
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_promotion_grant_revocation_prepare_invalid"
            )
        request_id = f"fcpgrc_{secrets.token_hex(16)}"
        request = dict(
            sign_field_canary_promotion_grant_operator_revocation_request(
                request_id=request_id,
                revocation_definition_id=prepared["revocation_definition_id"],
                approval_record_id=prepared["approval_record_id"],
                approval_record_digest=prepared["approval_record_digest"],
                requested_at=_now(clock),
                ingress_secret=active.ingress_secret,
            )
        )
        try:
            response = await _post(
                client,
                url=(
                    f"{_url(active.ingress_url)}"
                    f"{PROMOTION_GRANT_OPERATOR_REVOCATION_PATH}"
                ),
                body=request,
                accepted_statuses={200},
            )
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            # A transport ambiguity may resend only the exact same signed request.
            response = await _post(
                client,
                url=(
                    f"{_url(active.ingress_url)}"
                    f"{PROMOTION_GRANT_OPERATOR_REVOCATION_PATH}"
                ),
                body=request,
                accepted_statuses={200},
            )
        try:
            verified = dict(
                verify_field_canary_promotion_grant_operator_revocation_response(
                    response,
                    ingress_secret=active.ingress_secret,
                    expected_request_id=request_id,
                    expected_revocation_definition_id=(
                        prepared["revocation_definition_id"]
                    ),
                    expected_proposal_id=prepared["proposal_id"],
                    expected_proposal_digest=prepared["proposal_digest"],
                    expected_grant_id=prepared["grant_id"],
                    expected_grant_digest=prepared["grant_digest"],
                    expected_approval_record_id=prepared["approval_record_id"],
                    expected_approval_record_digest=(
                        prepared["approval_record_digest"]
                    ),
                )
            )
        except FieldCanaryOperatorSessionAttestationError as exc:
            raise FieldCanaryOperatorIdentityPublisherError(
                "field_canary_promotion_grant_operator_revocation_response_invalid"
            ) from exc
        return {"ok": True, **verified}
    finally:
        if own_session:
            await client.close()


__all__: list[str] = []
