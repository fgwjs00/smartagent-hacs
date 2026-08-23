"""HA-host half of the dedicated RegistrySnapshot ingress proof.

This contract never uses the ordinary SmartAgent add-on bearer token and never
authorizes refresh dispatch or any device effect.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, datetime
from typing import Any


CHALLENGE_REQUEST_SCHEMA_VERSION = (
    "smartagent.observation_refresh_registry_challenge_request.v0.1"
)
CHALLENGE_RESPONSE_SCHEMA_VERSION = (
    "smartagent.observation_refresh_registry_challenge_response.v0.1"
)
COMMIT_REQUEST_SCHEMA_VERSION = (
    "smartagent.observation_refresh_registry_commit_request.v0.1"
)
COMMIT_RESPONSE_SCHEMA_VERSION = (
    "smartagent.observation_refresh_registry_commit_response.v0.1"
)
CHALLENGE_REQUEST_PURPOSE = "observation_refresh_registry_challenge"
CHALLENGE_RESPONSE_PURPOSE = "observation_refresh_registry_challenge_issued"
COMMIT_REQUEST_PURPOSE = "observation_refresh_registry_commit"
COMMIT_RESPONSE_PURPOSE = "observation_refresh_registry_commit_result"
CHALLENGE_PROOF_MAX_SKEW_SECONDS = 15

_SAFE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_RESPONSE_FIELDS = frozenset(
    {
        "schema_version",
        "purpose",
        "challenge_id",
        "ingress_key_id",
        "attestation_key_id",
        "site_id",
        "ha_installation_digest",
        "bridge_config_entry_id",
        "request_id",
        "request_nonce",
        "source_seq",
        "issued_at",
        "expires_at",
        "catalog_write_authorized",
        "refresh_dispatch_authorized",
        "execution_eligible",
        "device_effect_authority",
        "signature",
    }
)
_COMMIT_RESPONSE_FIELDS = frozenset(
    {
        "schema_version",
        "purpose",
        "ingress_key_id",
        "request_id",
        "challenge_id",
        "ok",
        "disposition",
        "source_commit_confirmed",
        "attestation_id",
        "attestation_envelope_digest",
        "source_receipt_id",
        "source_receipt_digest",
        "source_seq",
        "snapshot_id",
        "snapshot_digest",
        "catalog_write_receipt_id",
        "catalog_write_receipt_digest",
        "catalog_write_committed",
        "retryable",
        "catalog_write_authorized",
        "refresh_dispatch_authorized",
        "execution_eligible",
        "device_effect_authority",
        "signature",
    }
)


class RefreshRegistryIngressProofError(ValueError):
    """The dedicated add-on proof is not exact or authentic."""


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
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_projection_invalid"
        ) from exc


def _safe_id(value: Any, field_name: str) -> str:
    if type(value) is not str or _SAFE_ID_RE.fullmatch(value) is None:
        raise RefreshRegistryIngressProofError(f"{field_name}_invalid")
    return value


def _sha256(value: Any, field_name: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise RefreshRegistryIngressProofError(f"{field_name}_invalid")
    return value


def _utc(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str:
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise RefreshRegistryIngressProofError(f"{field_name}_invalid") from exc
    else:
        raise RefreshRegistryIngressProofError(f"{field_name}_invalid")
    if parsed.tzinfo is None:
        raise RefreshRegistryIngressProofError(f"{field_name}_invalid")
    try:
        return parsed.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise RefreshRegistryIngressProofError(f"{field_name}_invalid") from exc


def _root_secret(secret: Any) -> bytes:
    if type(secret) is not str or len(secret) < 32:
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_secret_invalid")
    return secret.encode("utf-8")


def _derived_key(secret: str, purpose: bytes) -> bytes:
    return hmac.new(
        _root_secret(secret),
        b"smartagent/observation-refresh-registry-ingress/v1\0" + purpose,
        hashlib.sha256,
    ).digest()


def registry_ingress_key_id(secret: str) -> str:
    return "refresh-registry-key-" + hashlib.sha256(
        _derived_key(secret, b"key-id")
    ).hexdigest()[:32]


def _signature(secret: str, purpose: bytes, projection: dict[str, Any]) -> str:
    return hmac.new(
        _derived_key(secret, purpose),
        _canonical_json(projection).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _zero_authority(row: dict[str, Any]) -> None:
    if (
        row.get("catalog_write_authorized") is not False
        or row.get("refresh_dispatch_authorized") is not False
        or row.get("execution_eligible") is not False
        or row.get("device_effect_authority") != "none"
    ):
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_authority_forbidden"
        )


def sign_registry_challenge_request(
    *, secret: str, request_id: str, requested_at: datetime
) -> dict[str, Any]:
    projection = {
        "schema_version": CHALLENGE_REQUEST_SCHEMA_VERSION,
        "purpose": CHALLENGE_REQUEST_PURPOSE,
        "ingress_key_id": registry_ingress_key_id(secret),
        "request_id": _safe_id(request_id, "refresh_registry_ingress_request_id"),
        "requested_at": _utc(
            requested_at, "refresh_registry_ingress_requested_at"
        ).isoformat(),
        "catalog_write_authorized": False,
        "refresh_dispatch_authorized": False,
        "execution_eligible": False,
        "device_effect_authority": "none",
    }
    return {
        **projection,
        "signature": _signature(secret, b"challenge-request", projection),
    }


def verify_registry_challenge_response(
    value: Any,
    *,
    secret: str,
    expected_request_id: str,
    expected_site_id: str,
    expected_ha_installation_digest: str,
    expected_bridge_config_entry_id: str,
    expected_attestation_key_id: str,
    evaluated_at: datetime,
) -> dict[str, Any]:
    if type(value) is not dict:
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_schema_invalid")
    try:
        row = json.loads(_canonical_json(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_schema_invalid"
        ) from exc
    if type(row) is not dict or frozenset(row) != _RESPONSE_FIELDS:
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_schema_invalid")
    if (
        row["schema_version"] != CHALLENGE_RESPONSE_SCHEMA_VERSION
        or row["purpose"] != CHALLENGE_RESPONSE_PURPOSE
        or row["ingress_key_id"] != registry_ingress_key_id(secret)
    ):
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_version_or_key_invalid")
    _zero_authority(row)
    expected = {
        "request_id": _safe_id(expected_request_id, "refresh_registry_ingress_request_id"),
        "site_id": _safe_id(expected_site_id, "refresh_registry_ingress_site_id"),
        "ha_installation_digest": _sha256(
            expected_ha_installation_digest, "refresh_registry_ingress_installation"
        ),
        "bridge_config_entry_id": _safe_id(
            expected_bridge_config_entry_id, "refresh_registry_ingress_bridge_entry"
        ),
        "attestation_key_id": _safe_id(
            expected_attestation_key_id, "refresh_registry_ingress_attestation_key_id"
        ),
    }
    if any(row.get(field_name) != fact for field_name, fact in expected.items()):
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_server_pin_mismatch")
    _safe_id(row["challenge_id"], "refresh_registry_ingress_challenge_id")
    _sha256(row["request_nonce"], "refresh_registry_ingress_request_nonce")
    if type(row["source_seq"]) is not int or row["source_seq"] <= 0:
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_source_seq_invalid")
    issued = _utc(row["issued_at"], "refresh_registry_ingress_issued_at")
    expires = _utc(row["expires_at"], "refresh_registry_ingress_expires_at")
    now = _utc(evaluated_at, "refresh_registry_ingress_evaluated_at")
    if (
        (issued - now).total_seconds() > CHALLENGE_PROOF_MAX_SKEW_SECONDS
        or now >= expires
        or expires <= issued
        or (expires - issued).total_seconds() > 300
    ):
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_challenge_not_live")
    signature = row.pop("signature")
    expected_signature = _signature(secret, b"challenge-response", row)
    if type(signature) is not str or not hmac.compare_digest(signature, expected_signature):
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_signature_invalid")
    return row


def sign_registry_commit_request(
    *,
    secret: str,
    request_id: str,
    requested_at: datetime,
    challenge_id: str,
    attestation: dict[str, Any],
) -> dict[str, Any]:
    if type(attestation) is not dict:
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_attestation_invalid"
        )
    detached_attestation = json.loads(_canonical_json(attestation))
    projection = {
        "schema_version": COMMIT_REQUEST_SCHEMA_VERSION,
        "purpose": COMMIT_REQUEST_PURPOSE,
        "ingress_key_id": registry_ingress_key_id(secret),
        "request_id": _safe_id(request_id, "refresh_registry_ingress_request_id"),
        "requested_at": _utc(
            requested_at, "refresh_registry_ingress_requested_at"
        ).isoformat(),
        "challenge_id": _safe_id(
            challenge_id, "refresh_registry_ingress_challenge_id"
        ),
        "attestation": detached_attestation,
        "catalog_write_authorized": False,
        "refresh_dispatch_authorized": False,
        "execution_eligible": False,
        "device_effect_authority": "none",
    }
    return {
        **projection,
        "signature": _signature(secret, b"commit-request", projection),
    }


def verify_registry_commit_response(
    value: Any,
    *,
    secret: str,
    expected_request_id: str,
    expected_challenge_id: str,
    expected_attestation_id: str,
    expected_attestation_envelope_digest: str,
    expected_source_seq: int,
    expected_snapshot_id: str,
    expected_snapshot_digest: str,
) -> dict[str, Any]:
    """Verify the add-on's durable result instead of trusting HTTP success."""

    if type(value) is not dict:
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_schema_invalid")
    try:
        row = json.loads(_canonical_json(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_schema_invalid"
        ) from exc
    if type(row) is not dict or frozenset(row) != _COMMIT_RESPONSE_FIELDS:
        raise RefreshRegistryIngressProofError("refresh_registry_ingress_schema_invalid")
    if (
        row["schema_version"] != COMMIT_RESPONSE_SCHEMA_VERSION
        or row["purpose"] != COMMIT_RESPONSE_PURPOSE
        or row["ingress_key_id"] != registry_ingress_key_id(secret)
    ):
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_version_or_key_invalid"
        )
    _zero_authority(row)
    expected = {
        "request_id": _safe_id(
            expected_request_id, "refresh_registry_ingress_request_id"
        ),
        "challenge_id": _safe_id(
            expected_challenge_id, "refresh_registry_ingress_challenge_id"
        ),
        "attestation_id": _safe_id(
            expected_attestation_id, "refresh_registry_attestation_id"
        ),
        "attestation_envelope_digest": _sha256(
            expected_attestation_envelope_digest,
            "refresh_registry_attestation_envelope_digest",
        ),
        "source_seq": expected_source_seq,
        "snapshot_id": _safe_id(
            expected_snapshot_id, "refresh_registry_snapshot_id"
        ),
        "snapshot_digest": _sha256(
            expected_snapshot_digest, "refresh_registry_snapshot_digest"
        ),
    }
    if any(row.get(field_name) != fact for field_name, fact in expected.items()):
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_result_binding_mismatch"
        )
    _safe_id(row["disposition"], "refresh_registry_ingress_disposition")
    _safe_id(row["source_receipt_id"], "refresh_registry_source_receipt_id")
    _sha256(row["source_receipt_digest"], "refresh_registry_source_receipt_digest")
    catalog_committed = row["catalog_write_committed"]
    if (
        type(row["ok"]) is not bool
        or row["source_commit_confirmed"] is not True
        or type(expected_source_seq) is not int
        or expected_source_seq <= 0
        or type(catalog_committed) is not bool
        or type(row["retryable"]) is not bool
        or row["ok"] is not catalog_committed
    ):
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_result_invalid"
        )
    if catalog_committed:
        _safe_id(
            row["catalog_write_receipt_id"], "refresh_registry_catalog_receipt_id"
        )
        _sha256(
            row["catalog_write_receipt_digest"],
            "refresh_registry_catalog_receipt_digest",
        )
    elif row["catalog_write_receipt_id"] != "" or row["catalog_write_receipt_digest"] != "":
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_result_invalid"
        )
    signature = row.pop("signature")
    expected_signature = _signature(secret, b"commit-response", row)
    if type(signature) is not str or not hmac.compare_digest(
        signature, expected_signature
    ):
        raise RefreshRegistryIngressProofError(
            "refresh_registry_ingress_signature_invalid"
        )
    return row


__all__: list[str] = []
