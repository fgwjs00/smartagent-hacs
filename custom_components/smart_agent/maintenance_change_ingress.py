"""HA-host HMAC contract for the dedicated maintenance ledger ingress."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping


MAINTENANCE_CHANGE_INGRESS_REQUEST_SCHEMA_VERSION = (
    "smartagent.maintenance_change_ingress_request.v0.1"
)
MAINTENANCE_CHANGE_INGRESS_RESPONSE_SCHEMA_VERSION = (
    "smartagent.maintenance_change_ingress_response.v0.1"
)
_RESPONSE_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "kind",
        "ingress_key_id",
        "server_at",
        "result",
        "result_digest",
        "signature",
        "response_digest",
    }
)


class MaintenanceChangeIngressContractError(ValueError):
    """A dedicated maintenance-ledger transport fact is invalid."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_projection_invalid"
        ) from exc


def _detach(value: Any) -> Any:
    try:
        return json.loads(_canonical(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_projection_invalid"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _secret(value: Any) -> bytes:
    if type(value) is str:
        result = value.encode("utf-8")
    elif type(value) is bytes:
        result = value
    else:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_secret_invalid"
        )
    if len(result) < 32:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_secret_invalid"
        )
    return result


def maintenance_change_ingress_key_id(secret: str | bytes) -> str:
    key = _secret(secret)
    return "mcik_" + hashlib.sha256(
        b"smartagent.maintenance-change-ingress.key-id.v1\x00" + key
    ).hexdigest()[:24]


def _utc_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_time_invalid"
        )
    try:
        normalized = value.astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_time_invalid"
        ) from exc
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _utc(value: Any) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_time_invalid"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00").astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_time_invalid"
        ) from exc
    if _utc_text(parsed) != value:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_time_invalid"
        )
    return parsed


def _request_id(value: str | None) -> str:
    result = value if value is not None else f"mcirq_{secrets.token_hex(16)}"
    if (
        type(result) is not str
        or not result.startswith("mcirq_")
        or len(result) != 38
        or any(character not in "0123456789abcdef" for character in result[6:])
    ):
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_request_id_invalid"
        )
    return result


def _sign_request(
    *,
    kind: str,
    payload: Mapping[str, Any],
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None,
) -> dict[str, Any]:
    key = _secret(secret)
    if kind not in {
        "prepare_learning_mode_disable",
        "prepare_ai_management_enable",
        "reserve",
        "finalize",
        "apply_learning_mode_disable",
        "permit_ai_management_enable",
        "finalize_ai_management_enable",
        "reconcile_ai_management_enable",
    } or type(payload) is not dict:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_request_invalid"
        )
    detached_payload = _detach(payload)
    facts = {
        "schema_version": MAINTENANCE_CHANGE_INGRESS_REQUEST_SCHEMA_VERSION,
        "request_id": _request_id(request_id),
        "kind": kind,
        "ingress_key_id": maintenance_change_ingress_key_id(key),
        "requested_at": _utc_text(requested_at),
        "payload": detached_payload,
        "payload_digest": _digest(detached_payload),
    }
    signature = hmac.new(
        key,
        b"smartagent.maintenance-change-ingress.request.v1\x00"
        + _canonical(facts).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    signed = dict(facts, signature=signature)
    signed["request_digest"] = _digest(signed)
    return signed


def sign_maintenance_prepare_learning_mode_disable_request(
    *,
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    return _sign_request(
        kind="prepare_learning_mode_disable",
        payload={},
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def sign_maintenance_prepare_ai_management_enable_request(
    *,
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    return _sign_request(
        kind="prepare_ai_management_enable",
        payload={},
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def sign_maintenance_reserve_request(
    delegation_attestation: Mapping[str, Any],
    *,
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    if type(delegation_attestation) is not dict:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_attestation_invalid"
        )
    return _sign_request(
        kind="reserve",
        payload={"delegation_attestation": dict(delegation_attestation)},
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def sign_maintenance_finalize_request(
    *,
    attempt_id: str,
    attempt_digest: str,
    outcome: str,
    reason_digest: str,
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    return _sign_request(
        kind="finalize",
        payload={
            "attempt_id": attempt_id,
            "attempt_digest": attempt_digest,
            "outcome": outcome,
            "reason_digest": reason_digest,
        },
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def sign_maintenance_learning_mode_disable_request(
    *,
    attempt_id: str,
    attempt_digest: str,
    resource_ref: Mapping[str, Any],
    payload: Mapping[str, Any],
    before_state: Mapping[str, Any],
    expected_after_state: Mapping[str, Any],
    backup_ref: Mapping[str, Any],
    rollback_plan: Mapping[str, Any],
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    exact = {
        "attempt_id": attempt_id,
        "attempt_digest": attempt_digest,
        "resource_ref": resource_ref,
        "payload": payload,
        "before_state": before_state,
        "expected_after_state": expected_after_state,
        "backup_ref": backup_ref,
        "rollback_plan": rollback_plan,
    }
    if any(type(value) is not dict for value in tuple(exact.values())[2:]):
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_apply_projection_invalid"
        )
    return _sign_request(
        kind="apply_learning_mode_disable",
        payload=exact,
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def sign_maintenance_ai_management_enable_permit_request(
    *,
    attempt_id: str,
    attempt_digest: str,
    resource_ref: Mapping[str, Any],
    payload: Mapping[str, Any],
    before_state: Mapping[str, Any],
    expected_after_state: Mapping[str, Any],
    backup_ref: Mapping[str, Any],
    rollback_plan: Mapping[str, Any],
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    exact = {
        "attempt_id": attempt_id,
        "attempt_digest": attempt_digest,
        "resource_ref": resource_ref,
        "payload": payload,
        "before_state": before_state,
        "expected_after_state": expected_after_state,
        "backup_ref": backup_ref,
        "rollback_plan": rollback_plan,
    }
    if any(type(value) is not dict for value in tuple(exact.values())[2:]):
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_permit_projection_invalid"
        )
    return _sign_request(
        kind="permit_ai_management_enable",
        payload=exact,
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def sign_maintenance_ai_management_enable_finalize_request(
    *,
    permit_id: str,
    permit_digest: str,
    attempt_id: str,
    attempt_digest: str,
    observed_before_state: Mapping[str, Any],
    observed_after_state: Mapping[str, Any],
    reason_digest: str,
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    if type(observed_before_state) is not dict or type(observed_after_state) is not dict:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_host_readback_invalid"
        )
    return _sign_request(
        kind="finalize_ai_management_enable",
        payload={
            "permit_id": permit_id,
            "permit_digest": permit_digest,
            "attempt_id": attempt_id,
            "attempt_digest": attempt_digest,
            "observed_before_state": observed_before_state,
            "observed_after_state": observed_after_state,
            "reason_digest": reason_digest,
        },
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def sign_maintenance_ai_management_enable_reconcile_request(
    *,
    attempt_id: str,
    attempt_digest: str,
    blocked_receipt_id: str,
    blocked_receipt_digest: str,
    observed_state: Mapping[str, Any],
    reason_digest: str,
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    if type(observed_state) is not dict:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_host_readback_invalid"
        )
    return _sign_request(
        kind="reconcile_ai_management_enable",
        payload={
            "attempt_id": attempt_id,
            "attempt_digest": attempt_digest,
            "blocked_receipt_id": blocked_receipt_id,
            "blocked_receipt_digest": blocked_receipt_digest,
            "observed_state": observed_state,
            "reason_digest": reason_digest,
        },
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def verify_maintenance_change_ingress_response(
    envelope: Mapping[str, Any],
    *,
    keyring: Mapping[str, str | bytes],
    expected_request_id: str,
    expected_kind: str,
    evaluated_at: datetime,
    max_clock_skew_seconds: int = 15,
) -> dict[str, Any]:
    if type(envelope) is not dict or type(keyring) is not dict:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_invalid"
        )
    detached = _detach(envelope)
    if type(detached) is not dict or set(detached) != _RESPONSE_FIELDS:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_invalid"
        )
    if detached["schema_version"] != MAINTENANCE_CHANGE_INGRESS_RESPONSE_SCHEMA_VERSION:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_schema_invalid"
        )
    if (
        detached["request_id"] != _request_id(expected_request_id)
        or detached["kind"] != expected_kind
        or expected_kind not in {
            "prepare_learning_mode_disable",
            "prepare_ai_management_enable",
            "reserve",
            "finalize",
            "apply_learning_mode_disable",
            "permit_ai_management_enable",
            "finalize_ai_management_enable",
            "reconcile_ai_management_enable",
        }
    ):
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_binding_invalid"
        )
    key_id = detached["ingress_key_id"]
    if type(key_id) is not str or key_id not in keyring:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_key_invalid"
        )
    key = _secret(keyring[key_id])
    if maintenance_change_ingress_key_id(key) != key_id:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_key_invalid"
        )
    if type(detached["result"]) is not dict or detached["result_digest"] != _digest(
        detached["result"]
    ):
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_result_invalid"
        )
    facts = {
        field: detached[field]
        for field in _RESPONSE_FIELDS
        if field not in {"signature", "response_digest"}
    }
    expected_signature = hmac.new(
        key,
        b"smartagent.maintenance-change-ingress.response.v1\x00"
        + _canonical(facts).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if (
        type(detached["signature"]) is not str
        or not hmac.compare_digest(detached["signature"], expected_signature)
        or detached["response_digest"]
        != _digest(dict(facts, signature=detached["signature"]))
    ):
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_signature_invalid"
        )
    if (
        type(max_clock_skew_seconds) is not int
        or isinstance(max_clock_skew_seconds, bool)
        or not 0 <= max_clock_skew_seconds <= 60
    ):
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_time_invalid"
        )
    server_at = _utc(detached["server_at"])
    current = _utc(_utc_text(evaluated_at))
    try:
        earliest = current - timedelta(seconds=max_clock_skew_seconds)
        latest = current + timedelta(seconds=max_clock_skew_seconds)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_time_invalid"
        ) from exc
    if not earliest <= server_at <= latest:
        raise MaintenanceChangeIngressContractError(
            "maintenance_change_ingress_response_time_invalid"
        )
    return _detach(detached["result"])


__all__: list[str] = []
