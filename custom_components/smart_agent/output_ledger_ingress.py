"""Pure HMAC transport contracts for the dedicated output-ledger ingress.

This channel is deliberately separate from the ordinary add-on bearer.  It
only transports redacted output attempt/receipt attestations and signed ledger
results; it cannot dispatch a Home Assistant service by itself.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping


OUTPUT_INGRESS_REQUEST_SCHEMA_VERSION = (
    "smartagent.output_ledger_ingress_request.v0.1"
)
OUTPUT_INGRESS_RESPONSE_SCHEMA_VERSION = (
    "smartagent.output_ledger_ingress_response.v0.1"
)
_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "kind",
        "ingress_key_id",
        "requested_at",
        "payload",
        "payload_digest",
        "signature",
        "request_digest",
    }
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


class OutputLedgerIngressContractError(ValueError):
    """The dedicated output-ledger transport fact is invalid."""


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
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_projection_invalid"
        ) from exc


def _detach(value: Any) -> Any:
    try:
        return json.loads(_canonical(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_projection_invalid"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _secret(value: Any) -> bytes:
    if type(value) is str:
        result = value.encode("utf-8")
    elif type(value) is bytes:
        result = value
    else:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_secret_invalid"
        )
    if len(result) < 32:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_secret_invalid"
        )
    return result


def output_ledger_ingress_key_id(secret: str | bytes) -> str:
    key = _secret(secret)
    return "outik_" + hashlib.sha256(
        b"smartagent.output-ledger-ingress.key-id.v1\x00" + key
    ).hexdigest()[:24]


def _utc_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_time_invalid"
        )
    try:
        normalized = value.astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_time_invalid"
        ) from exc
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _utc(value: Any) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_time_invalid"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00").astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_time_invalid"
        ) from exc
    if _utc_text(parsed) != value:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_time_invalid"
        )
    return parsed


def _request_id(value: str | None) -> str:
    result = value if value is not None else f"outirq_{secrets.token_hex(16)}"
    if (
        type(result) is not str
        or not result.startswith("outirq_")
        or len(result) != 39
        or any(character not in "0123456789abcdef" for character in result[7:])
    ):
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_request_id_invalid"
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
    if kind not in {"claim", "finalize"} or type(payload) is not dict:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_request_invalid"
        )
    detached_payload = _detach(payload)
    facts = {
        "schema_version": OUTPUT_INGRESS_REQUEST_SCHEMA_VERSION,
        "request_id": _request_id(request_id),
        "kind": kind,
        "ingress_key_id": output_ledger_ingress_key_id(key),
        "requested_at": _utc_text(requested_at),
        "payload": detached_payload,
        "payload_digest": _digest(detached_payload),
    }
    signature = hmac.new(
        key,
        b"smartagent.output-ledger-ingress.request.v1\x00"
        + _canonical(facts).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    signed = dict(facts, signature=signature)
    signed["request_digest"] = _digest(signed)
    return signed


def sign_output_ledger_claim_request(
    attempt_attestation: Mapping[str, Any],
    *,
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    if type(attempt_attestation) is not dict:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_attestation_invalid"
        )
    return _sign_request(
        kind="claim",
        payload={"attempt_attestation": dict(attempt_attestation)},
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def sign_output_ledger_finalize_request(
    *,
    attempt_id: str,
    attempt_digest: str,
    dispatch_token: str,
    receipt_attestation: Mapping[str, Any],
    secret: str | bytes,
    requested_at: datetime,
    request_id: str | None = None,
) -> dict[str, Any]:
    if type(receipt_attestation) is not dict:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_attestation_invalid"
        )
    return _sign_request(
        kind="finalize",
        payload={
            "attempt_id": attempt_id,
            "attempt_digest": attempt_digest,
            "dispatch_token": dispatch_token,
            "receipt_attestation": dict(receipt_attestation),
        },
        secret=secret,
        requested_at=requested_at,
        request_id=request_id,
    )


def verify_output_ledger_ingress_response(
    envelope: Mapping[str, Any],
    *,
    keyring: Mapping[str, str | bytes],
    expected_request_id: str,
    expected_kind: str,
    evaluated_at: datetime,
    max_clock_skew_seconds: int = 15,
) -> dict[str, Any]:
    """Verify one exact add-on response and return its detached result."""
    if type(envelope) is not dict or type(keyring) is not dict:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_invalid"
        )
    detached = _detach(envelope)
    if type(detached) is not dict or set(detached) != _RESPONSE_FIELDS:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_invalid"
        )
    if detached["schema_version"] != OUTPUT_INGRESS_RESPONSE_SCHEMA_VERSION:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_schema_invalid"
        )
    if (
        detached["request_id"] != _request_id(expected_request_id)
        or detached["kind"] != expected_kind
        or expected_kind not in {"claim", "finalize"}
    ):
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_binding_invalid"
        )
    key_id = detached["ingress_key_id"]
    if type(key_id) is not str or key_id not in keyring:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_key_invalid"
        )
    key = _secret(keyring[key_id])
    if output_ledger_ingress_key_id(key) != key_id:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_key_invalid"
        )
    if type(detached["result"]) is not dict or detached["result_digest"] != _digest(
        detached["result"]
    ):
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_result_invalid"
        )
    facts = {
        field: detached[field]
        for field in _RESPONSE_FIELDS
        if field not in {"signature", "response_digest"}
    }
    expected_signature = hmac.new(
        key,
        b"smartagent.output-ledger-ingress.response.v1\x00"
        + _canonical(facts).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if (
        type(detached["signature"]) is not str
        or not hmac.compare_digest(detached["signature"], expected_signature)
        or detached["response_digest"]
        != _digest(dict(facts, signature=detached["signature"]))
    ):
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_signature_invalid"
        )
    if (
        type(max_clock_skew_seconds) is not int
        or isinstance(max_clock_skew_seconds, bool)
        or not 0 <= max_clock_skew_seconds <= 60
    ):
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_time_invalid"
        )
    server_at = _utc(detached["server_at"])
    current = _utc_text(evaluated_at)
    current_dt = _utc(current)
    try:
        earliest = current_dt - timedelta(seconds=max_clock_skew_seconds)
        latest = current_dt + timedelta(seconds=max_clock_skew_seconds)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_time_invalid"
        ) from exc
    if not earliest <= server_at <= latest:
        raise OutputLedgerIngressContractError(
            "output_ledger_ingress_response_time_invalid"
        )
    return _detach(detached["result"])


__all__: list[str] = []
