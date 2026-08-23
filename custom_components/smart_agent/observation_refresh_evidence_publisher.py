"""Explicit host port for submitting one signed observation-evidence fact.

This module is deliberately not registered as a listener or background task.
Its caller must already possess an exact materialization ID, a canonical value
from an integration-specific observation source, and a dedicated issuer key.
It never calls an HA service and never treats a Provider ACK as fresh evidence.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

import aiohttp


EVIDENCE_CONTEXT_PATH = "/api/v1/internal/observation-refresh/evidence/contexts"
EVIDENCE_COMMIT_PATH = "/api/v1/internal/observation-refresh/evidence/commits"
EVIDENCE_CONTEXT_REQUEST_VERSION = (
    "smartagent.observation_refresh_evidence_context_request.v0.1"
)
EVIDENCE_CONTEXT_RESPONSE_VERSION = (
    "smartagent.observation_refresh_evidence_context_response.v0.1"
)
EVIDENCE_COMMIT_REQUEST_VERSION = (
    "smartagent.observation_refresh_evidence_commit_request.v0.1"
)
EVIDENCE_COMMIT_RESPONSE_VERSION = (
    "smartagent.observation_refresh_evidence_commit_response.v0.1"
)
EVIDENCE_INGRESS_KEY_ID_HEADER = "X-SA-Observation-Evidence-Key-Id"
EVIDENCE_INGRESS_TOKEN_HEADER = "X-SA-Observation-Evidence-Token"
EVIDENCE_ATTESTATION_SCHEMA_VERSION = (
    "smartagent.observation_refresh_evidence_attestation.v0.1"
)
EVIDENCE_ATTESTATION_CONTEXT_VERSION = (
    "smartagent.observation_refresh_evidence_attestation_context.v0.1"
)
EVIDENCE_ATTESTATION_ISSUER_VERSION = (
    "smartagent.observation_refresh_evidence_issuer.v0.1"
)
EVIDENCE_ATTESTATION_PURPOSE = "canonical_observation_evidence"
EVIDENCE_ATTESTATION_MAX_TTL_SECONDS = 60
EVIDENCE_ATTESTATION_CLOCK_SKEW_SECONDS = 15
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
_KEY_CONTEXT = b"smartagent/observation-refresh-evidence-attestation/v1"
_CONTEXT_FIELDS = (
    "site_id",
    "materialization_id",
    "materialization_digest",
    "binding_id",
    "binding_digest",
    "provider_id",
    "provider_binding_id",
    "provider_binding_digest",
    "source_entity_id",
    "source_stream_id",
    "signal_manifest_id",
    "signal_manifest_version",
    "signal_manifest_digest",
    "freshness_contract_digest",
    "runtime_adapter_digest",
    "canonical_value_kind",
    "canonical_unit",
)
_ATTESTATION_AUTHORITY_FIELDS = {
    "source_attestation_state": "signed_not_consumed",
    "canonical_evidence_authority_verified": False,
    "refresh_dispatch_authorized": False,
    "execution_eligible": False,
    "execution_permitted": False,
    "device_effect_authority": "none",
}
_INGRESS_AUTHORITY_FIELDS = {
    "refresh_dispatch_authorized": False,
    "execution_eligible": False,
    "execution_permitted": False,
    "device_effect_authority": "none",
}


class ObservationRefreshEvidencePublisherError(RuntimeError):
    """The explicit evidence publisher could not establish a canonical fact."""


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_publisher_projection_invalid"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _secret(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value.encode("utf-8")) < 32
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ObservationRefreshEvidencePublisherError(f"{field_name}_invalid")
    return value


def _identity(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ObservationRefreshEvidencePublisherError(f"{field_name}_invalid")
    return value


def _sha256(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ObservationRefreshEvidencePublisherError(f"{field_name}_invalid")
    return value


def _utc(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, bool) or not isinstance(value, (datetime, str)):
        raise ObservationRefreshEvidencePublisherError(f"{field_name}_invalid")
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("timezone_required")
        return parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ObservationRefreshEvidencePublisherError(f"{field_name}_invalid") from exc


def _safe_shift(value: datetime, *, seconds: int) -> datetime:
    try:
        return value + timedelta(seconds=seconds)
    except OverflowError as exc:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_publisher_time_invalid"
        ) from exc


def _url(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_ingress_url_invalid"
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
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_ingress_url_invalid"
        )
    return value.rstrip("/")


def _now(clock: Callable[[], datetime]) -> datetime:
    try:
        value = clock()
    except Exception as exc:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_publisher_clock_invalid"
        ) from exc
    return _utc(value, "refresh_evidence_publisher_clock")


def _ingress_key(secret: str) -> bytes:
    return hmac.new(
        _secret(secret, "refresh_evidence_ingress_secret").encode("utf-8"),
        b"smartagent/observation-refresh-evidence-ingress/v1",
        hashlib.sha256,
    ).digest()


def evidence_ingress_key_id(secret: str) -> str:
    return hashlib.sha256(_ingress_key(secret)).hexdigest()[:16]


def _verify_response(
    envelope: Any,
    *,
    secret: str,
    expected_schema_version: str,
    expected_purpose: str,
) -> dict[str, Any]:
    if type(envelope) is not dict:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_ingress_response_invalid"
        )
    detached = json.loads(_canonical_json(envelope))
    if frozenset(detached) != {
        "schema_version",
        "purpose",
        "key_id",
        "result",
        "refresh_dispatch_authorized",
        "execution_eligible",
        "execution_permitted",
        "device_effect_authority",
        "signature",
    }:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_ingress_response_invalid"
        )
    if (
        detached["schema_version"] != expected_schema_version
        or detached["purpose"] != expected_purpose
        or detached["key_id"] != evidence_ingress_key_id(secret)
        or type(detached.get("result")) is not dict
        or any(detached.get(key) != value for key, value in _INGRESS_AUTHORITY_FIELDS.items())
    ):
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_ingress_response_invalid"
        )
    unsigned = {key: value for key, value in detached.items() if key != "signature"}
    response_key = hmac.new(
        _secret(secret, "refresh_evidence_ingress_secret").encode("utf-8"),
        b"smartagent/observation-refresh-evidence-response/v1",
        hashlib.sha256,
    ).digest()
    expected = hmac.new(
        response_key,
        _canonical_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(str(detached.get("signature") or ""), expected):
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_ingress_signature_invalid"
        )
    return json.loads(_canonical_json(detached["result"]))


def _validate_submission_context(
    payload: Any,
    *,
    issuer_secret: str,
    expected_materialization_id: str,
    evaluated_at: datetime,
) -> dict[str, Any]:
    if type(payload) is not dict:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_submission_context_invalid"
        )
    detached = json.loads(_canonical_json(payload))
    required = {
        "schema_version",
        "materialization_id",
        "materialization_digest",
        "binding_context",
        "binding_context_digest",
        "expected_source_seq",
        "previous_source_event_id",
        "previous_observed_at",
        "issuer",
        "issuer_registry_digest",
        "issued_at",
        "expires_at",
        "evidence_write_authorized",
        "canonical_evidence_authority_verified",
        "refresh_dispatch_authorized",
        "execution_eligible",
        "execution_permitted",
        "device_effect_authority",
        "submission_context_id",
        "submission_context_digest",
    }
    if frozenset(detached) != required:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_submission_context_invalid"
        )
    unsigned = {
        key: value
        for key, value in detached.items()
        if key not in {"submission_context_id", "submission_context_digest"}
    }
    expected_digest = _digest(unsigned)
    if (
        detached["schema_version"]
        != "smartagent.observation_refresh_evidence_submission_context.v0.1"
        or detached["materialization_id"] != expected_materialization_id
        or detached["submission_context_digest"] != expected_digest
        or detached["submission_context_id"]
        != f"oref-evidence-context-{expected_digest[:32]}"
        or detached["evidence_write_authorized"] is not False
        or detached["canonical_evidence_authority_verified"] is not False
        or any(detached.get(key) != value for key, value in _INGRESS_AUTHORITY_FIELDS.items())
    ):
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_submission_context_invalid"
        )
    context = detached["binding_context"]
    issuer = detached["issuer"]
    if type(context) is not dict or type(issuer) is not dict:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_submission_context_invalid"
        )
    if (
        context.get("schema_version") != EVIDENCE_ATTESTATION_CONTEXT_VERSION
        or _digest(context) != detached["binding_context_digest"]
        or context.get("materialization_id") != detached["materialization_id"]
        or context.get("materialization_digest") != detached["materialization_digest"]
        or issuer.get("schema_version") != EVIDENCE_ATTESTATION_ISSUER_VERSION
        or issuer.get("key_id") != evidence_attestation_key_id(issuer_secret)
        or issuer.get("site_id") != context.get("site_id")
        or issuer.get("provider_id") != context.get("provider_id")
        or issuer.get("runtime_adapter_digest") != context.get("runtime_adapter_digest")
    ):
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_submission_context_binding_invalid"
        )
    issued = _utc(detached["issued_at"], "refresh_evidence_submission_context_issued_at")
    expires = _utc(detached["expires_at"], "refresh_evidence_submission_context_expires_at")
    if issued > _safe_shift(evaluated_at, seconds=15) or evaluated_at >= expires:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_submission_context_not_live"
        )
    if (
        _utc(issuer.get("valid_from"), "refresh_evidence_issuer_valid_from") > evaluated_at
        or evaluated_at
        >= _utc(issuer.get("valid_until"), "refresh_evidence_issuer_valid_until")
    ):
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_submission_context_issuer_not_live"
        )
    source_seq = detached["expected_source_seq"]
    if type(source_seq) is not int or source_seq < 1:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_submission_context_source_seq_invalid"
        )
    return detached


def _derived_evidence_key(secret: str) -> bytes:
    return hmac.new(
        _secret(secret, "refresh_evidence_attestation_secret").encode("utf-8"),
        _KEY_CONTEXT,
        hashlib.sha256,
    ).digest()


def evidence_attestation_key_id(secret: str) -> str:
    return hashlib.sha256(_derived_evidence_key(secret)).hexdigest()[:16]


def _canonical_value(value_kind: str, value: Any) -> bool | int | float | str:
    if value_kind == "boolean" and type(value) is bool:
        return value
    if value_kind == "integer" and type(value) is int:
        return value
    if value_kind == "number" and type(value) is float and math.isfinite(value):
        return value
    if (
        value_kind == "string"
        and type(value) is str
        and len(value) <= 4096
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        return value
    raise ObservationRefreshEvidencePublisherError(
        "refresh_evidence_attestation_value_invalid"
    )


def _sign_evidence(
    submission: Mapping[str, Any],
    *,
    issuer_secret: str,
    canonical_value: Any,
    quality: str,
    source_event_id: str,
    observed_at: datetime,
    issued_at: datetime,
) -> dict[str, Any]:
    context = dict(submission["binding_context"])
    issuer = dict(submission["issuer"])
    value = _canonical_value(str(context.get("canonical_value_kind")), canonical_value)
    accepted_qualities = context.get("accepted_qualities")
    if type(accepted_qualities) is not list or quality not in accepted_qualities:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_attestation_quality_rejected"
        )
    event_id = _identity(source_event_id, "refresh_evidence_attestation_event_id")
    observed = _utc(observed_at, "refresh_evidence_attestation_observed_at")
    expires = min(
        _safe_shift(issued_at, seconds=EVIDENCE_ATTESTATION_MAX_TTL_SECONDS),
        _utc(submission["expires_at"], "refresh_evidence_submission_context_expires_at"),
        _utc(context["binding_valid_until"], "refresh_evidence_binding_valid_until"),
        _utc(issuer["valid_until"], "refresh_evidence_issuer_valid_until"),
    )
    if issued_at >= expires or observed > _safe_shift(
        issued_at, seconds=EVIDENCE_ATTESTATION_CLOCK_SKEW_SECONDS
    ):
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_attestation_time_invalid"
        )
    value_digest = _digest(
        {
            "value_kind": context["canonical_value_kind"],
            "canonical_value": value,
            "canonical_unit": context["canonical_unit"],
        }
    )
    unsigned = {
        "schema_version": EVIDENCE_ATTESTATION_SCHEMA_VERSION,
        "purpose": EVIDENCE_ATTESTATION_PURPOSE,
        "issuer_id": issuer["issuer_id"],
        "issuer_version": issuer["schema_version"],
        "key_id": evidence_attestation_key_id(issuer_secret),
        **{field: context[field] for field in _CONTEXT_FIELDS},
        "canonical_value": value,
        "value_digest": value_digest,
        "quality": quality,
        "source_event_id": event_id,
        "source_seq": submission["expected_source_seq"],
        "observed_at": observed.isoformat(),
        "issued_at": issued_at.isoformat(),
        "expires_at": expires.isoformat(),
        **_ATTESTATION_AUTHORITY_FIELDS,
    }
    unsigned["attestation_id"] = (
        f"oref-evidence-attestation-{_digest(unsigned)[:32]}"
    )
    signature = hmac.new(
        _derived_evidence_key(issuer_secret),
        _canonical_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {**unsigned, "signature": signature}


@dataclass(frozen=True, slots=True)
class ObservationRefreshEvidencePublisherConfig:
    enabled: bool
    ingress_url: str = ""
    ingress_secret: str = ""
    issuer_secret: str = ""

    def validated(self) -> "ObservationRefreshEvidencePublisherConfig":
        if type(self.enabled) is not bool:
            raise ObservationRefreshEvidencePublisherError(
                "refresh_evidence_publisher_enabled_invalid"
            )
        if not self.enabled:
            return self
        _url(self.ingress_url)
        ingress = _secret(self.ingress_secret, "refresh_evidence_ingress_secret")
        issuer = _secret(self.issuer_secret, "refresh_evidence_attestation_secret")
        if hmac.compare_digest(ingress, issuer):
            raise ObservationRefreshEvidencePublisherError(
                "refresh_evidence_publisher_secret_reuse_forbidden"
            )
        return self


async def _post_json(
    session: aiohttp.ClientSession,
    *,
    url: str,
    payload: dict[str, Any],
    secret: str,
) -> dict[str, Any]:
    async with session.post(
        url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            EVIDENCE_INGRESS_KEY_ID_HEADER: evidence_ingress_key_id(secret),
            EVIDENCE_INGRESS_TOKEN_HEADER: secret,
        },
        timeout=_REQUEST_TIMEOUT,
    ) as response:
        try:
            body = await response.json(content_type=None)
        except Exception as exc:
            raise ObservationRefreshEvidencePublisherError(
                "refresh_evidence_ingress_response_invalid"
            ) from exc
        if response.status != 200 or type(body) is not dict:
            raise ObservationRefreshEvidencePublisherError(
                "refresh_evidence_ingress_request_rejected"
            )
        return body


async def async_publish_observation_refresh_evidence_once(
    *,
    config: ObservationRefreshEvidencePublisherConfig,
    materialization_id: str,
    canonical_value: Any,
    quality: str,
    source_event_id: str,
    observed_at: datetime,
    session: aiohttp.ClientSession | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Submit one caller-observed fact; no Provider ACK is accepted here."""

    active = config.validated()
    if not active.enabled:
        return {
            "status": "disabled",
            "canonical_evidence_authority_verified": False,
            "decision_eligible": False,
            **_INGRESS_AUTHORITY_FIELDS,
        }
    materialization = _identity(
        materialization_id, "refresh_evidence_ingress_materialization_id"
    )
    base_url = _url(active.ingress_url)
    own_session = session is None
    active_session = session or aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT)
    try:
        context_envelope = await _post_json(
            active_session,
            url=f"{base_url}{EVIDENCE_CONTEXT_PATH}",
            payload={
                "schema_version": EVIDENCE_CONTEXT_REQUEST_VERSION,
                "materialization_id": materialization,
            },
            secret=active.ingress_secret,
        )
        context_result = _verify_response(
            context_envelope,
            secret=active.ingress_secret,
            expected_schema_version=EVIDENCE_CONTEXT_RESPONSE_VERSION,
            expected_purpose="observation_refresh_evidence_context",
        )
        submission = _validate_submission_context(
            context_result,
            issuer_secret=active.issuer_secret,
            expected_materialization_id=materialization,
            evaluated_at=_now(clock),
        )
        issued_at = _now(clock)
        attestation = _sign_evidence(
            submission,
            issuer_secret=active.issuer_secret,
            canonical_value=canonical_value,
            quality=_identity(quality, "refresh_evidence_attestation_quality"),
            source_event_id=source_event_id,
            observed_at=observed_at,
            issued_at=issued_at,
        )
        commit_payload = {
            "schema_version": EVIDENCE_COMMIT_REQUEST_VERSION,
            "materialization_id": materialization,
            "attestation": attestation,
        }
        try:
            commit_envelope = await _post_json(
                active_session,
                url=f"{base_url}{EVIDENCE_COMMIT_PATH}",
                payload=commit_payload,
                secret=active.ingress_secret,
            )
        except (aiohttp.ClientError, asyncio.TimeoutError):
            # A lost response may follow a durable commit.  Retry only the exact
            # same signed evidence envelope; never mint a new seq/event fact.
            commit_envelope = await _post_json(
                active_session,
                url=f"{base_url}{EVIDENCE_COMMIT_PATH}",
                payload=commit_payload,
                secret=active.ingress_secret,
            )
        result = _verify_response(
            commit_envelope,
            secret=active.ingress_secret,
            expected_schema_version=EVIDENCE_COMMIT_RESPONSE_VERSION,
            expected_purpose="observation_refresh_evidence_commit",
        )
        if (
            result.get("status") != "canonical_evidence_committed"
            or result.get("materialization_id") != materialization
            or result.get("attestation_id") != attestation["attestation_id"]
            or result.get("attestation_envelope_digest") != _digest(attestation)
            or result.get("source_event_id") != source_event_id
            or result.get("source_seq") != submission["expected_source_seq"]
            or result.get("canonical_evidence_authority_verified") is not True
            or result.get("decision_eligible") is not True
            or any(result.get(key) != value for key, value in _INGRESS_AUTHORITY_FIELDS.items())
        ):
            raise ObservationRefreshEvidencePublisherError(
                "refresh_evidence_ingress_commit_result_invalid"
            )
        return result
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise ObservationRefreshEvidencePublisherError(
            "refresh_evidence_ingress_transport_unknown"
        ) from exc
    finally:
        if own_session:
            await active_session.close()


__all__: list[str] = []
