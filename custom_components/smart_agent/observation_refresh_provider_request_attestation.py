"""Verify an add-on observation-refresh request without calling a Provider.

Verification proves an exact short-lived request signature.  It does not
consume replay state, select an HA adapter, call ``update_entity``, prove fresh
evidence, or authorize a device effect.  Those remain separate future gates.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import re
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Iterable, Mapping, Protocol


PROVIDER_REQUEST_ATTESTATION_SCHEMA_VERSION = (
    "smartagent.observation_refresh_provider_request_attestation.v0.1"
)
PROVIDER_REQUEST_SCHEMA_VERSION = (
    "smartagent.observation_refresh_provider_request.v0.1"
)
DISPATCH_BOUNDARY_SCHEMA_VERSION = "smartagent.refresh_dispatch_boundary.v0.1"
PROVIDER_REQUEST_ATTESTATION_PURPOSE = "observation_refresh_provider_request"
PROVIDER_REQUEST_ATTESTATION_ISSUER = "smartagent_addon_refresh_runtime_v0.1"
PROVIDER_REQUEST_ATTESTATION_MAX_TTL_SECONDS = 30
PROVIDER_REQUEST_ATTESTATION_CLOCK_SKEW_SECONDS = 15
_KEY_CONTEXT = b"smartagent/observation-refresh-provider-request/v1"
PROVIDER_RESPONSE_ATTESTATION_SCHEMA_VERSION = (
    "smartagent.observation_refresh_provider_response_attestation.v0.1"
)
PROVIDER_RESPONSE_ATTESTATION_PURPOSE = "observation_refresh_provider_response"
PROVIDER_RESPONSE_ATTESTATION_ISSUER = "smartagent_ha_refresh_host_v0.1"
_RESPONSE_KEY_CONTEXT = b"smartagent/observation-refresh-provider-response/v1"
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+-]{0,254}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERIFIED_FACTORY_TOKEN = object()
_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "dispatch_boundary",
        "dispatch_boundary_digest",
        "parameters",
        "refresh_dispatch_authorized",
        "execution_eligible",
        "device_effect_authority",
    }
)
_BOUNDARY_FIELDS = frozenset(
    {
        "schema_version",
        "authority_id",
        "authority_digest",
        "source_record_digest",
        "runtime_adapter_id",
        "runtime_adapter_version",
        "runtime_adapter_digest",
        "claim_id",
        "claim_fingerprint",
        "attempt_id",
        "attempt_fingerprint",
        "attempt_no",
        "materialization_id",
        "materialization_digest",
        "site_id",
        "physical_lane_key",
        "binding_id",
        "binding_digest",
        "provider_id",
        "provider_binding_id",
        "provider_binding_digest",
        "provider_operation_id",
        "provider_operation_contract_digest",
        "exact_target_ref",
        "credential_scope_ref",
        "dispatch_started_at",
        "evidence_deadline_at",
        "not_before_at",
        "provider_call_may_start",
        "refresh_dispatch_authorized",
        "execution_eligible",
        "device_effect_authority",
    }
)
_ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        "purpose",
        "issuer",
        "key_id",
        "request",
        "request_digest",
        "claim_id",
        "attempt_id",
        "materialization_id",
        "dispatch_boundary_digest",
        "issued_at",
        "expires_at",
        "provider_request_signature_verified",
        "provider_call_authorized",
        "execution_eligible",
        "device_effect_authority",
        "attestation_id",
        "signature",
    }
)
_RESPONSE_RESULT_FIELDS = frozenset(
    {
        "ok",
        "schema_version",
        "disposition",
        "transport_state",
        "provider_io_performed",
        "provider_call_authorized",
        "replayed",
        "fresh_evidence_verified",
        "reconciliation_required",
        "execution_eligible",
        "device_effect_authority",
    }
)
_RESPONSE_DISPOSITIONS = frozenset(
    {
        "host_provider_runtime_disabled",
        "provider_request_rejected",
        "host_provider_adapter_unavailable",
        "host_provider_adapter_binding_mismatch",
        "provider_replay_reservation_uncertain",
        "provider_transport_replayed",
        "provider_transport_pending",
        "provider_transport_persistence_uncertain",
        "provider_transport_recorded",
    }
)


class ObservationRefreshProviderRequestVerificationError(ValueError):
    """Raised when a signed Provider request is malformed or untrusted."""


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
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_projection_invalid"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _identity(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or not _SAFE_ID_RE.fullmatch(value)
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            f"{field_name}_invalid"
        )
    return value


def _sha256(value: Any, field_name: str) -> str:
    if type(value) is not str or not _SHA256_RE.fullmatch(value):
        raise ObservationRefreshProviderRequestVerificationError(
            f"{field_name}_invalid"
        )
    return value


def _utc(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, bool) or not isinstance(value, (datetime, str)):
        raise ObservationRefreshProviderRequestVerificationError(
            f"{field_name}_invalid"
        )
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("timezone_required")
        return parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ObservationRefreshProviderRequestVerificationError(
            f"{field_name}_invalid"
        ) from exc


def _derived_key(secret: str) -> bytes:
    if type(secret) is not str or len(secret.encode("utf-8")) < 32:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_secret_invalid"
        )
    return hmac.new(secret.encode("utf-8"), _KEY_CONTEXT, hashlib.sha256).digest()


def provider_request_attestation_key_id(secret: str) -> str:
    return hashlib.sha256(_derived_key(secret)).hexdigest()[:16]


def _response_key(secret: str) -> bytes:
    if type(secret) is not str or len(secret.encode("utf-8")) < 32:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_response_secret_invalid"
        )
    return hmac.new(
        secret.encode("utf-8"), _RESPONSE_KEY_CONTEXT, hashlib.sha256
    ).digest()


def provider_response_attestation_key_id(secret: str) -> str:
    return hashlib.sha256(_response_key(secret)).hexdigest()[:16]


def _validated_response_result(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_response_result_invalid"
        )
    result = json.loads(_canonical_json(value))
    if (
        type(result) is not dict
        or set(result) != _RESPONSE_RESULT_FIELDS
        or result.get("schema_version")
        != "smartagent.observation_refresh_host_provider_result.v0.1"
        or result.get("disposition") not in _RESPONSE_DISPOSITIONS
        or type(result.get("ok")) is not bool
        or type(result.get("provider_io_performed")) is not bool
        or type(result.get("provider_call_authorized")) is not bool
        or type(result.get("replayed")) is not bool
        or result.get("fresh_evidence_verified") is not False
        or type(result.get("reconciliation_required")) is not bool
        or result.get("execution_eligible") is not False
        or result.get("device_effect_authority") != "none"
        or result.get("transport_state")
        not in {"", "provider_accepted", "ack_lost", "transport_failed"}
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_response_result_invalid"
        )
    if (
        result["provider_io_performed"]
        and not result["provider_call_authorized"]
    ) or (
        not result["provider_call_authorized"]
        and (
            result["transport_state"] != ""
            or result["replayed"]
            or result["ok"]
        )
    ) or (
        result["transport_state"] == "provider_accepted"
        and result["ok"] is not True
    ) or (
        result["transport_state"] != "provider_accepted"
        and result["ok"] is not False
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_response_authority_invalid"
        )
    return result


def _validated_request(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_invalid"
        )
    request = json.loads(_canonical_json(value))
    if type(request) is not dict or set(request) != _REQUEST_FIELDS:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_invalid"
        )
    boundary = request.get("dispatch_boundary")
    if type(boundary) is not dict or set(boundary) != _BOUNDARY_FIELDS:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_boundary_invalid"
        )
    if (
        request.get("schema_version") != PROVIDER_REQUEST_SCHEMA_VERSION
        or request.get("parameters") != {}
        or request.get("refresh_dispatch_authorized") is not True
        or request.get("execution_eligible") is not False
        or request.get("device_effect_authority") != "none"
        or boundary.get("schema_version") != DISPATCH_BOUNDARY_SCHEMA_VERSION
        or boundary.get("provider_call_may_start") is not True
        or boundary.get("refresh_dispatch_authorized") is not True
        or boundary.get("execution_eligible") is not False
        or boundary.get("device_effect_authority") != "none"
        or type(boundary.get("attempt_no")) is not int
        or int(boundary["attempt_no"]) < 1
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_authority_invalid"
        )
    for field_name in (
        "authority_id",
        "runtime_adapter_id",
        "runtime_adapter_version",
        "claim_id",
        "attempt_id",
        "materialization_id",
        "site_id",
        "binding_id",
        "provider_id",
        "provider_binding_id",
        "provider_operation_id",
        "exact_target_ref",
        "credential_scope_ref",
    ):
        _identity(boundary.get(field_name), f"refresh_provider_request_{field_name}")
    for field_name in (
        "authority_digest",
        "source_record_digest",
        "runtime_adapter_digest",
        "claim_fingerprint",
        "attempt_fingerprint",
        "materialization_digest",
        "physical_lane_key",
        "binding_digest",
        "provider_binding_digest",
        "provider_operation_contract_digest",
    ):
        _sha256(boundary.get(field_name), f"refresh_provider_request_{field_name}")
    boundary_digest = _digest(boundary)
    if request.get("dispatch_boundary_digest") != boundary_digest:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_boundary_digest_mismatch"
        )
    return request


@dataclass(frozen=True, slots=True, init=False)
class VerifiedObservationRefreshProviderRequest:
    attestation_id: str
    key_id: str
    request_digest: str
    claim_id: str
    attempt_id: str
    materialization_id: str
    dispatch_boundary_digest: str
    issued_at: str
    expires_at: str
    envelope_digest: str
    request: Mapping[str, Any]
    provider_request_signature_verified: bool
    provider_call_authorized: bool
    execution_eligible: bool
    device_effect_authority: str

    def __init__(
        self,
        *,
        _factory_token: object | None = None,
        **_values: Any,
    ) -> None:
        if _factory_token is not _VERIFIED_FACTORY_TOKEN:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_request_verified_factory_required"
            )


def verify_observation_refresh_provider_request(
    envelope: Mapping[str, Any],
    *,
    keyring: Mapping[str, str],
    evaluated_at: datetime,
) -> VerifiedObservationRefreshProviderRequest:
    """Verify one detached request; replay consumption remains not implemented."""

    if type(envelope) is not dict or type(keyring) is not dict:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_envelope_invalid"
        )
    detached = json.loads(_canonical_json(envelope))
    if type(detached) is not dict or set(detached) != _ENVELOPE_FIELDS:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_envelope_invalid"
        )
    if (
        detached.get("schema_version")
        != PROVIDER_REQUEST_ATTESTATION_SCHEMA_VERSION
        or detached.get("purpose") != PROVIDER_REQUEST_ATTESTATION_PURPOSE
        or detached.get("issuer") != PROVIDER_REQUEST_ATTESTATION_ISSUER
        or detached.get("provider_request_signature_verified") is not False
        or detached.get("provider_call_authorized") is not False
        or detached.get("execution_eligible") is not False
        or detached.get("device_effect_authority") != "none"
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_envelope_authority_invalid"
        )
    key_id = _identity(detached.get("key_id"), "refresh_provider_request_key_id")
    secret = keyring.get(key_id)
    if type(secret) is not str or provider_request_attestation_key_id(secret) != key_id:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_key_unknown"
        )
    signature = _sha256(
        detached.get("signature"), "refresh_provider_request_signature"
    )
    signed = {key: value for key, value in detached.items() if key != "signature"}
    expected_signature = hmac.new(
        _derived_key(secret),
        _canonical_json(signed).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_signature_invalid"
        )
    request = _validated_request(detached.get("request"))
    request_digest = _digest(request)
    boundary = request["dispatch_boundary"]
    if (
        detached.get("request_digest") != request_digest
        or detached.get("claim_id") != boundary["claim_id"]
        or detached.get("attempt_id") != boundary["attempt_id"]
        or detached.get("materialization_id") != boundary["materialization_id"]
        or detached.get("dispatch_boundary_digest")
        != request["dispatch_boundary_digest"]
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_lineage_mismatch"
        )
    _sha256(request_digest, "refresh_provider_request_digest")
    issued = _utc(detached.get("issued_at"), "refresh_provider_request_issued_at")
    expires = _utc(
        detached.get("expires_at"), "refresh_provider_request_expires_at"
    )
    evaluated = _utc(evaluated_at, "refresh_provider_request_evaluated_at")
    dispatch_started = _utc(
        boundary["dispatch_started_at"], "refresh_provider_request_dispatch_started_at"
    )
    evidence_deadline = _utc(
        boundary["evidence_deadline_at"],
        "refresh_provider_request_evidence_deadline_at",
    )
    if (
        issued < dispatch_started
        or issued >= expires
        or expires > evidence_deadline
        or expires - issued
        > timedelta(seconds=PROVIDER_REQUEST_ATTESTATION_MAX_TTL_SECONDS)
        or issued
        > evaluated
        + timedelta(seconds=PROVIDER_REQUEST_ATTESTATION_CLOCK_SKEW_SECONDS)
        or evaluated >= expires
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_attestation_window_invalid"
        )
    attestation_id = _identity(
        detached.get("attestation_id"), "refresh_provider_request_attestation_id"
    )
    unsigned = {
        key: value
        for key, value in detached.items()
        if key not in {"attestation_id", "signature"}
    }
    if attestation_id != "rfrpa_" + _digest(unsigned)[:40]:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_request_attestation_id_invalid"
        )
    frozen_request = _freeze(json.loads(_canonical_json(request)))
    instance = object.__new__(VerifiedObservationRefreshProviderRequest)
    values = {
        "attestation_id": attestation_id,
        "key_id": key_id,
        "request_digest": request_digest,
        "claim_id": boundary["claim_id"],
        "attempt_id": boundary["attempt_id"],
        "materialization_id": boundary["materialization_id"],
        "dispatch_boundary_digest": request["dispatch_boundary_digest"],
        "issued_at": issued.isoformat(),
        "expires_at": expires.isoformat(),
        "envelope_digest": _digest(detached),
        "request": frozen_request,
        "provider_request_signature_verified": True,
        "provider_call_authorized": False,
        "execution_eligible": False,
        "device_effect_authority": "none",
    }
    for field_name, value in values.items():
        object.__setattr__(instance, field_name, value)
    return instance


def sign_observation_refresh_provider_response(
    verified_request: VerifiedObservationRefreshProviderRequest,
    result: Mapping[str, Any],
    *,
    secret: str,
    responded_at: datetime,
) -> dict[str, Any]:
    """Sign one exact host transport fact; it never proves fresh evidence."""

    if type(verified_request) is not VerifiedObservationRefreshProviderRequest:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_response_verified_request_required"
        )
    validated_result = _validated_response_result(result)
    responded = _utc(responded_at, "refresh_provider_response_at")
    request_issued = _utc(
        verified_request.issued_at, "refresh_provider_request_issued_at"
    )
    boundary = verified_request.request["dispatch_boundary"]
    evidence_deadline = _utc(
        boundary["evidence_deadline_at"],
        "refresh_provider_request_evidence_deadline_at",
    )
    if responded < request_issued or responded > evidence_deadline:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_response_window_invalid"
        )
    unsigned = {
        "schema_version": PROVIDER_RESPONSE_ATTESTATION_SCHEMA_VERSION,
        "purpose": PROVIDER_RESPONSE_ATTESTATION_PURPOSE,
        "issuer": PROVIDER_RESPONSE_ATTESTATION_ISSUER,
        "key_id": provider_response_attestation_key_id(secret),
        "request_attestation_id": verified_request.attestation_id,
        "request_digest": verified_request.request_digest,
        "claim_id": verified_request.claim_id,
        "attempt_id": verified_request.attempt_id,
        "materialization_id": verified_request.materialization_id,
        "dispatch_boundary_digest": verified_request.dispatch_boundary_digest,
        "result": validated_result,
        "result_digest": _digest(validated_result),
        "responded_at": responded.isoformat(),
        "fresh_evidence_verified": False,
        "execution_eligible": False,
        "device_effect_authority": "none",
    }
    response_id = "rfrpr_" + _digest(unsigned)[:40]
    signed = {**unsigned, "response_id": response_id}
    signature = hmac.new(
        _response_key(secret),
        _canonical_json(signed).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {**signed, "signature": signature}


class ObservationRefreshHostReplayLedger(Protocol):
    """Durably reserve/finalize one signed attempt before any Provider I/O."""

    async def reserve_once(
        self,
        *,
        attestation_id: str,
        attempt_id: str,
        request_digest: str,
        expires_at: str,
    ) -> "ObservationRefreshHostReplayReservation":
        """Return the exact durable reservation state."""

    async def finalize_transport(
        self,
        *,
        attestation_id: str,
        attempt_id: str,
        request_digest: str,
        transport_state: str,
    ) -> None:
        """Persist the conservative transport fact for exact replay."""


class ObservationRefreshHostReplayStorage(Protocol):
    """Minimal HA Store-shaped persistence port used by the replay ledger."""

    async def async_load(self) -> object | None:
        """Load the last complete JSON-compatible document."""

    async def async_save(self, value: Mapping[str, Any]) -> None:
        """Atomically replace the persisted document or raise."""


@dataclass(frozen=True, slots=True)
class ObservationRefreshHostReplayReservation:
    state: str
    transport_state: str = ""

    def __post_init__(self) -> None:
        if self.state not in {"reserved", "existing_pending", "existing_terminal"}:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_state_invalid"
            )
        if self.state == "existing_terminal":
            if self.transport_state not in {
                "provider_accepted",
                "ack_lost",
                "transport_failed",
            }:
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_provider_replay_transport_invalid"
                )
        elif self.transport_state:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_transport_invalid"
            )


_REPLAY_LEDGER_SCHEMA_VERSION = (
    "smartagent.observation_refresh_host_replay_ledger.v0.1"
)
_REPLAY_LEDGER_KEY_CONTEXT = b"smartagent/observation-refresh-host-replay-ledger/v1"


def _replay_ledger_key(secret: str) -> bytes:
    if type(secret) is not str or len(secret.encode("utf-8")) < 32:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_replay_secret_invalid"
        )
    return hmac.new(
        secret.encode("utf-8"), _REPLAY_LEDGER_KEY_CONTEXT, hashlib.sha256
    ).digest()


class ObservationRefreshHostJsonReplayLedger:
    """Single-runtime durable replay fence; no Provider or HA service access."""

    def __init__(
        self,
        *,
        storage: ObservationRefreshHostReplayStorage,
        integrity_secret: str,
        clock: Callable[[], datetime],
    ) -> None:
        if not callable(getattr(storage, "async_load", None)) or not callable(
            getattr(storage, "async_save", None)
        ):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_storage_invalid"
            )
        if not callable(clock):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_clock_invalid"
            )
        self._storage = storage
        self._key = _replay_ledger_key(integrity_secret)
        self._key_id = hashlib.sha256(self._key).hexdigest()[:16]
        self._clock = clock
        self._lock = asyncio.Lock()

    def _row(self, facts: Mapping[str, Any]) -> dict[str, Any]:
        base = {
            "attestation_id": _identity(
                facts.get("attestation_id"), "refresh_provider_replay_attestation_id"
            ),
            "attempt_id": _identity(
                facts.get("attempt_id"), "refresh_provider_replay_attempt_id"
            ),
            "request_digest": _sha256(
                facts.get("request_digest"), "refresh_provider_replay_request_digest"
            ),
            "expires_at": _utc(
                facts.get("expires_at"), "refresh_provider_replay_expires_at"
            ).isoformat(),
            "state": facts.get("state"),
            "transport_state": facts.get("transport_state"),
            "created_at": _utc(
                facts.get("created_at"), "refresh_provider_replay_created_at"
            ).isoformat(),
            "updated_at": _utc(
                facts.get("updated_at"), "refresh_provider_replay_updated_at"
            ).isoformat(),
            "provider_call_authorized": facts.get("provider_call_authorized"),
            "fresh_evidence_verified": facts.get("fresh_evidence_verified"),
            "execution_eligible": facts.get("execution_eligible"),
            "device_effect_authority": facts.get("device_effect_authority"),
        }
        if (
            base["state"] not in {"pending", "terminal"}
            or base["provider_call_authorized"] is not True
            or base["fresh_evidence_verified"] is not False
            or base["execution_eligible"] is not False
            or base["device_effect_authority"] != "none"
            or _utc(base["created_at"], "refresh_provider_replay_created_at")
            > _utc(base["updated_at"], "refresh_provider_replay_updated_at")
        ):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_row_invalid"
            )
        if base["state"] == "pending":
            if base["transport_state"] != "":
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_provider_replay_row_invalid"
                )
        elif base["transport_state"] not in {
            "provider_accepted",
            "ack_lost",
            "transport_failed",
        }:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_row_invalid"
            )
        row_digest = _digest(base)
        signed = {**base, "row_digest": row_digest, "integrity_key_id": self._key_id}
        row_tag = hmac.new(
            self._key,
            b"refresh-provider-replay-row\x00"
            + _canonical_json(signed).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {**signed, "row_integrity_tag": row_tag}

    def _validated_row(self, value: Any) -> dict[str, Any]:
        if type(value) is not dict:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_row_invalid"
            )
        expected = {
            "attestation_id",
            "attempt_id",
            "request_digest",
            "expires_at",
            "state",
            "transport_state",
            "created_at",
            "updated_at",
            "provider_call_authorized",
            "fresh_evidence_verified",
            "execution_eligible",
            "device_effect_authority",
            "row_digest",
            "integrity_key_id",
            "row_integrity_tag",
        }
        if set(value) != expected:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_row_invalid"
            )
        rebuilt = self._row(value)
        if rebuilt != value:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_row_integrity_invalid"
            )
        return rebuilt

    def _document(self, rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        ordered = [rows[key] for key in sorted(rows)]
        base = {
            "schema_version": _REPLAY_LEDGER_SCHEMA_VERSION,
            "rows": ordered,
            "row_count": len(ordered),
            "provider_call_authority": "single_use_only",
            "fresh_evidence_verified": False,
            "execution_eligible": False,
            "device_effect_authority": "none",
        }
        document_digest = _digest(base)
        signed = {
            **base,
            "document_digest": document_digest,
            "integrity_key_id": self._key_id,
        }
        document_tag = hmac.new(
            self._key,
            b"refresh-provider-replay-document\x00"
            + _canonical_json(signed).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {**signed, "document_integrity_tag": document_tag}

    async def _load_rows(self) -> dict[str, dict[str, Any]]:
        raw = await self._storage.async_load()
        if raw is None:
            return {}
        if type(raw) is not dict:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_document_invalid"
            )
        expected = {
            "schema_version",
            "rows",
            "row_count",
            "provider_call_authority",
            "fresh_evidence_verified",
            "execution_eligible",
            "device_effect_authority",
            "document_digest",
            "integrity_key_id",
            "document_integrity_tag",
        }
        if (
            set(raw) != expected
            or raw.get("schema_version") != _REPLAY_LEDGER_SCHEMA_VERSION
            or type(raw.get("rows")) is not list
            or type(raw.get("row_count")) is not int
            or raw.get("row_count") != len(raw["rows"])
            or raw.get("provider_call_authority") != "single_use_only"
            or raw.get("fresh_evidence_verified") is not False
            or raw.get("execution_eligible") is not False
            or raw.get("device_effect_authority") != "none"
        ):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_document_invalid"
            )
        rows: dict[str, dict[str, Any]] = {}
        for item in raw["rows"]:
            row = self._validated_row(item)
            if row["attempt_id"] in rows:
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_provider_replay_attempt_duplicate"
                )
            rows[row["attempt_id"]] = row
        if self._document(rows) != raw:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_document_integrity_invalid"
            )
        return rows

    async def _save_rows(self, rows: Mapping[str, Mapping[str, Any]]) -> None:
        document = self._document(rows)
        await self._storage.async_save(document)
        persisted = await self._load_rows()
        if self._document(persisted) != document:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_post_write_mismatch"
            )

    async def reserve_once(
        self,
        *,
        attestation_id: str,
        attempt_id: str,
        request_digest: str,
        expires_at: str,
    ) -> ObservationRefreshHostReplayReservation:
        async with self._lock:
            current = _utc(self._clock(), "refresh_provider_replay_evaluated_at")
            expiry = _utc(expires_at, "refresh_provider_replay_expires_at")
            rows = await self._load_rows()
            existing = rows.get(attempt_id)
            if existing is not None:
                if (
                    existing["attestation_id"] != attestation_id
                    or existing["request_digest"] != request_digest
                    or existing["expires_at"] != expiry.isoformat()
                ):
                    raise ObservationRefreshProviderRequestVerificationError(
                        "refresh_provider_replay_conflict"
                    )
                if existing["state"] == "terminal":
                    return ObservationRefreshHostReplayReservation(
                        "existing_terminal", existing["transport_state"]
                    )
                return ObservationRefreshHostReplayReservation("existing_pending")
            if current >= expiry:
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_provider_replay_expired"
                )
            current_text = current.isoformat()
            row = self._row(
                {
                    "attestation_id": attestation_id,
                    "attempt_id": attempt_id,
                    "request_digest": request_digest,
                    "expires_at": expiry.isoformat(),
                    "state": "pending",
                    "transport_state": "",
                    "created_at": current_text,
                    "updated_at": current_text,
                    "provider_call_authorized": True,
                    "fresh_evidence_verified": False,
                    "execution_eligible": False,
                    "device_effect_authority": "none",
                }
            )
            await self._save_rows({**rows, attempt_id: row})
            return ObservationRefreshHostReplayReservation("reserved")

    async def finalize_transport(
        self,
        *,
        attestation_id: str,
        attempt_id: str,
        request_digest: str,
        transport_state: str,
    ) -> None:
        if transport_state not in {
            "provider_accepted",
            "ack_lost",
            "transport_failed",
        }:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_replay_transport_invalid"
            )
        async with self._lock:
            current = _utc(self._clock(), "refresh_provider_replay_evaluated_at")
            rows = await self._load_rows()
            existing = rows.get(attempt_id)
            if existing is None:
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_provider_replay_missing"
                )
            if (
                existing["attestation_id"] != attestation_id
                or existing["request_digest"] != request_digest
            ):
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_provider_replay_conflict"
                )
            if existing["state"] == "terminal":
                if existing["transport_state"] != transport_state:
                    raise ObservationRefreshProviderRequestVerificationError(
                        "refresh_provider_replay_terminal_conflict"
                    )
                return
            if current < _utc(
                existing["created_at"], "refresh_provider_replay_created_at"
            ):
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_provider_replay_clock_regression"
                )
            updated = self._row(
                {
                    **existing,
                    "state": "terminal",
                    "transport_state": transport_state,
                    "updated_at": current.isoformat(),
                }
            )
            await self._save_rows({**rows, attempt_id: updated})


@dataclass(frozen=True, slots=True)
class ObservationRefreshHostTransportFact:
    transport_state: str

    def __post_init__(self) -> None:
        if self.transport_state not in {
            "provider_accepted",
            "ack_lost",
            "transport_failed",
        }:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_transport_state_invalid"
            )


@dataclass(frozen=True, slots=True)
class ObservationRefreshHostProviderAdapter:
    """Compile-time exact adapter descriptor plus an observation-only callable."""

    runtime_adapter_id: str
    runtime_adapter_version: str
    runtime_adapter_digest: str
    provider_id: str
    provider_operation_id: str
    exact_target_prefix: str
    credential_scope_prefix: str
    request_observation: Callable[
        [Mapping[str, Any]], Awaitable[ObservationRefreshHostTransportFact]
    ]

    def __post_init__(self) -> None:
        for field_name in (
            "runtime_adapter_id",
            "runtime_adapter_version",
            "provider_id",
            "provider_operation_id",
            "exact_target_prefix",
            "credential_scope_prefix",
        ):
            _identity(getattr(self, field_name), f"refresh_host_adapter_{field_name}")
        _sha256(self.runtime_adapter_digest, "refresh_host_adapter_digest")
        if (
            not self.exact_target_prefix.endswith(":")
            or not self.credential_scope_prefix.endswith(":")
            or not callable(self.request_observation)
        ):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_host_adapter_invalid"
            )


class ObservationRefreshHostProviderAdapterRegistry:
    """Static exact-digest registry; the production built-in registry is empty."""

    def __init__(
        self, adapters: Iterable[ObservationRefreshHostProviderAdapter]
    ) -> None:
        rows = tuple(adapters)
        by_digest: dict[str, ObservationRefreshHostProviderAdapter] = {}
        identities: set[tuple[str, str]] = set()
        for row in rows:
            if type(row) is not ObservationRefreshHostProviderAdapter:
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_host_adapter_invalid"
                )
            identity = (row.runtime_adapter_id, row.runtime_adapter_version)
            if identity in identities or row.runtime_adapter_digest in by_digest:
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_host_adapter_ambiguous"
                )
            identities.add(identity)
            by_digest[row.runtime_adapter_digest] = row
        self._rows = tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.runtime_adapter_digest,
                    row.runtime_adapter_id,
                    row.runtime_adapter_version,
                ),
            )
        )
        self._by_digest = MappingProxyType(dict(by_digest))

    @property
    def adapters(self) -> tuple[ObservationRefreshHostProviderAdapter, ...]:
        return self._rows

    def get(self, digest: str) -> ObservationRefreshHostProviderAdapter | None:
        return self._by_digest.get(digest)


BUILTIN_OBSERVATION_REFRESH_HOST_PROVIDER_ADAPTER_REGISTRY = (
    ObservationRefreshHostProviderAdapterRegistry(())
)


@dataclass(frozen=True, slots=True)
class ObservationRefreshHostProviderRuntimeConfig:
    enabled: bool = False

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_host_runtime_enabled_invalid"
            )


class ObservationRefreshHostProviderRuntime:
    """Verify, reserve, and invoke one exact observation-only adapter."""

    def __init__(
        self,
        *,
        keyring: Mapping[str, str],
        adapter_registry: ObservationRefreshHostProviderAdapterRegistry,
        replay_ledger: ObservationRefreshHostReplayLedger,
        clock: Callable[[], datetime],
        config: ObservationRefreshHostProviderRuntimeConfig,
    ) -> None:
        if type(keyring) is not dict or not keyring:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_host_runtime_keyring_invalid"
            )
        if type(adapter_registry) is not ObservationRefreshHostProviderAdapterRegistry:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_host_runtime_registry_invalid"
            )
        if not callable(getattr(replay_ledger, "reserve_once", None)) or not callable(
            getattr(replay_ledger, "finalize_transport", None)
        ):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_host_runtime_replay_ledger_invalid"
            )
        if not callable(clock) or type(config) is not ObservationRefreshHostProviderRuntimeConfig:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_host_runtime_configuration_invalid"
            )
        self._keyring = dict(keyring)
        self._adapters = adapter_registry
        self._replay_ledger = replay_ledger
        self._clock = clock
        self._config = config

    @staticmethod
    def _result(
        disposition: str,
        *,
        transport_state: str = "",
        provider_io_performed: bool = False,
        provider_call_authorized: bool = False,
        replayed: bool = False,
        reconciliation_required: bool = False,
    ) -> dict[str, Any]:
        return {
            "ok": transport_state == "provider_accepted",
            "schema_version": "smartagent.observation_refresh_host_provider_result.v0.1",
            "disposition": disposition,
            "transport_state": transport_state,
            "provider_io_performed": provider_io_performed,
            "provider_call_authorized": provider_call_authorized,
            "replayed": replayed,
            "fresh_evidence_verified": False,
            "reconciliation_required": reconciliation_required,
            "execution_eligible": False,
            "device_effect_authority": "none",
        }

    async def handle(self, envelope: Mapping[str, Any]) -> dict[str, Any]:
        if not self._config.enabled:
            return self._result("host_provider_runtime_disabled")
        try:
            verified = verify_observation_refresh_provider_request(
                envelope,
                keyring=self._keyring,
                evaluated_at=self._clock(),
            )
        except ObservationRefreshProviderRequestVerificationError:
            return self._result("provider_request_rejected")
        boundary = verified.request["dispatch_boundary"]
        if not isinstance(boundary, Mapping):
            return self._result("provider_request_rejected")
        adapter = self._adapters.get(str(boundary["runtime_adapter_digest"]))
        if adapter is None:
            return self._result("host_provider_adapter_unavailable")
        if (
            adapter.runtime_adapter_id != boundary["runtime_adapter_id"]
            or adapter.runtime_adapter_version != boundary["runtime_adapter_version"]
            or adapter.runtime_adapter_digest != boundary["runtime_adapter_digest"]
            or adapter.provider_id != boundary["provider_id"]
            or adapter.provider_operation_id != boundary["provider_operation_id"]
            or not str(boundary["exact_target_ref"]).startswith(
                adapter.exact_target_prefix
            )
            or not str(boundary["credential_scope_ref"]).startswith(
                adapter.credential_scope_prefix
            )
        ):
            return self._result("host_provider_adapter_binding_mismatch")
        try:
            reservation = await self._replay_ledger.reserve_once(
                attestation_id=verified.attestation_id,
                attempt_id=verified.attempt_id,
                request_digest=verified.request_digest,
                expires_at=verified.expires_at,
            )
        except Exception:
            return self._result(
                "provider_replay_reservation_uncertain",
                reconciliation_required=True,
            )
        if type(reservation) is not ObservationRefreshHostReplayReservation:
            return self._result(
                "provider_replay_reservation_uncertain",
                reconciliation_required=True,
            )
        if reservation.state == "existing_terminal":
            return self._result(
                "provider_transport_replayed",
                transport_state=reservation.transport_state,
                provider_call_authorized=True,
                replayed=True,
                reconciliation_required=reservation.transport_state != "provider_accepted",
            )
        if reservation.state == "existing_pending":
            return self._result(
                "provider_transport_pending",
                transport_state="ack_lost",
                provider_call_authorized=True,
                replayed=True,
                reconciliation_required=True,
            )
        provider_io_performed = True
        try:
            fact = await adapter.request_observation(verified.request)
            if type(fact) is not ObservationRefreshHostTransportFact:
                transport_state = "ack_lost"
            else:
                transport_state = fact.transport_state
        except Exception:
            transport_state = "ack_lost"
        try:
            await self._replay_ledger.finalize_transport(
                attestation_id=verified.attestation_id,
                attempt_id=verified.attempt_id,
                request_digest=verified.request_digest,
                transport_state=transport_state,
            )
        except Exception:
            return self._result(
                "provider_transport_persistence_uncertain",
                transport_state="ack_lost",
                provider_io_performed=provider_io_performed,
                provider_call_authorized=True,
                reconciliation_required=True,
            )
        return self._result(
            "provider_transport_recorded",
            transport_state=transport_state,
            provider_io_performed=provider_io_performed,
            provider_call_authorized=True,
            reconciliation_required=transport_state != "provider_accepted",
        )


__all__: list[str] = []
