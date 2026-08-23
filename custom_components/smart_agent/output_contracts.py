"""Pure, deny-only receipt contracts for non-device HA output calls.

The receipt records what the HA service boundary accepted.  It never proves
that a person saw a notification or heard TTS, and it never grants device
execution authority.  Persistence and independent delivery/readback are
deliberately outside this structural slice.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


OUTPUT_ATTEMPT_SCHEMA_VERSION = "smartagent.output_attempt.v0.1"
OUTPUT_RECEIPT_SCHEMA_VERSION = "smartagent.output_receipt.v0.1"
OUTPUT_ATTESTATION_SCHEMA_VERSION = "smartagent.output_attestation.v0.1"
_ATTEMPT_SEAL = object()
_RECEIPT_SEAL = object()
_OUTPUT_CLASSES = frozenset({"notification", "user_explicit_output"})
_AUTHORITY_BY_CLASS = {
    "notification": "system_health",
    "user_explicit_output": "authenticated_user_current_gesture",
}
_SERVICES_BY_CLASS = {
    "notification": frozenset(
        {"persistent_notification.create", "persistent_notification.dismiss"}
    ),
    "user_explicit_output": frozenset({"tts.speak"}),
}


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
        raise ValueError("output_projection_invalid") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _attestation_secret(value: Any) -> bytes:
    if type(value) is str:
        secret = value.encode("utf-8")
    elif type(value) is bytes:
        secret = value
    else:
        raise ValueError("output_attestation_secret_invalid")
    if len(secret) < 32:
        raise ValueError("output_attestation_secret_invalid")
    return secret


def output_attestation_key_id(secret: str | bytes) -> str:
    key = _attestation_secret(secret)
    return "outak_" + hashlib.sha256(
        b"smartagent.output-attestation.key-id.v1\x00" + key
    ).hexdigest()[:24]


def _hex_digest(value: Any, *, reason: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(reason)
    return value


def _utc_text(value: datetime | None = None) -> str:
    current = value if value is not None else datetime.now(timezone.utc)
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise ValueError("output_time_invalid")
    try:
        normalized = current.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("output_time_invalid") from exc
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _text(value: Any, *, reason: str, maximum: int = 255) -> str:
    if type(value) is not str:
        raise ValueError(reason)
    normalized = value.strip()
    if not normalized or len(normalized) > maximum or any(ord(ch) < 32 for ch in normalized):
        raise ValueError(reason)
    return normalized


@dataclass(frozen=True, slots=True, init=False)
class OutputAttempt:
    schema_version: str
    attempt_id: str
    attempt_digest: str
    execution_class: str
    authority_class: str
    authority_ref_digest: str
    service_key: str
    target_ref_digest: str
    content_digest: str
    audience_ref_digest: str
    ttl_seconds: int
    dedupe_key_digest: str
    requested_at: str
    execution_eligible: bool
    device_effect_authority: str

    def __init__(self, projection: Mapping[str, Any], *, seal: object) -> None:
        if seal is not _ATTEMPT_SEAL or type(projection) is not dict:
            raise ValueError("output_attempt_constructor_forbidden")
        for key, value in projection.items():
            object.__setattr__(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }


@dataclass(frozen=True, slots=True, init=False)
class OutputReceipt:
    schema_version: str
    receipt_id: str
    receipt_digest: str
    attempt_id: str
    attempt_digest: str
    execution_class: str
    authority_class: str
    service_key: str
    transport_state: str
    outcome: str
    delivery_state: str
    accepted_by_ha: bool
    delivered: bool
    read_by_user: bool
    played: bool
    requested_at: str
    completed_at: str
    persistence_state: str
    execution_eligible: bool
    execution_permitted: bool
    device_effect_authority: str

    def __init__(self, projection: Mapping[str, Any], *, seal: object) -> None:
        if seal is not _RECEIPT_SEAL or type(projection) is not dict:
            raise ValueError("output_receipt_constructor_forbidden")
        for key, value in projection.items():
            object.__setattr__(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }


def begin_output_attempt(
    *,
    execution_class: str,
    authority_ref: str,
    service_key: str,
    target_ref: str,
    payload: Mapping[str, Any],
    audience_ref: str,
    ttl_seconds: int,
    requested_at: datetime | None = None,
) -> OutputAttempt:
    """Create one content-redacted structural output attempt."""
    class_text = _text(execution_class, reason="output_execution_class_invalid").lower()
    service_text = _text(service_key, reason="output_service_invalid").lower()
    if class_text not in _OUTPUT_CLASSES or service_text not in _SERVICES_BY_CLASS[class_text]:
        raise ValueError("output_class_service_binding_invalid")
    authority_text = _text(authority_ref, reason="output_authority_ref_invalid")
    target_text = _text(target_ref, reason="output_target_ref_invalid")
    audience_text = _text(audience_ref, reason="output_audience_ref_invalid")
    if type(payload) is not dict:
        raise ValueError("output_payload_invalid")
    if type(ttl_seconds) is not int or isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= 86_400:
        raise ValueError("output_ttl_invalid")
    requested_text = _utc_text(requested_at)
    content_digest = _digest(payload)
    seed = {
        "schema_version": OUTPUT_ATTEMPT_SCHEMA_VERSION,
        "nonce": secrets.token_hex(16),
        "execution_class": class_text,
        "authority_class": _AUTHORITY_BY_CLASS[class_text],
        "authority_ref_digest": _digest(authority_text),
        "service_key": service_text,
        "target_ref_digest": _digest(target_text),
        "content_digest": content_digest,
        "audience_ref_digest": _digest(audience_text),
        "ttl_seconds": ttl_seconds,
        "dedupe_key_digest": _digest(
            {
                "service_key": service_text,
                "target_ref_digest": _digest(target_text),
                "audience_ref_digest": _digest(audience_text),
                "content_digest": content_digest,
            }
        ),
        "requested_at": requested_text,
        "execution_eligible": False,
        "device_effect_authority": "none",
    }
    attempt_id = f"outa_{_digest(seed)[:32]}"
    projection = {key: value for key, value in seed.items() if key != "nonce"}
    projection["attempt_id"] = attempt_id
    projection["attempt_digest"] = _digest(projection)
    return OutputAttempt(projection, seal=_ATTEMPT_SEAL)


def finalize_output_attempt(
    attempt: OutputAttempt,
    *,
    accepted_by_ha: bool,
    completed_at: datetime | None = None,
) -> OutputReceipt:
    """Finalize the structural result without claiming delivery or playback."""
    if type(attempt) is not OutputAttempt:
        raise ValueError("output_attempt_required")
    if type(accepted_by_ha) is not bool:
        raise ValueError("output_transport_state_invalid")
    completed_text = _utc_text(completed_at)
    if completed_text < attempt.requested_at:
        raise ValueError("output_time_regression")
    if accepted_by_ha and attempt.execution_class == "notification":
        transport_state = "provider_accepted"
        outcome = "recorded_in_ha"
    elif accepted_by_ha:
        transport_state = "provider_accepted"
        outcome = "effect_unknown"
    else:
        transport_state = "transport_unknown"
        outcome = "effect_unknown"
    facts = {
        "schema_version": OUTPUT_RECEIPT_SCHEMA_VERSION,
        "attempt_id": attempt.attempt_id,
        "attempt_digest": attempt.attempt_digest,
        "execution_class": attempt.execution_class,
        "authority_class": attempt.authority_class,
        "service_key": attempt.service_key,
        "transport_state": transport_state,
        "outcome": outcome,
        "delivery_state": "not_verified",
        "accepted_by_ha": accepted_by_ha,
        "delivered": False,
        "read_by_user": False,
        "played": False,
        "requested_at": attempt.requested_at,
        "completed_at": completed_text,
        "persistence_state": "not_persisted",
        "execution_eligible": False,
        "execution_permitted": False,
        "device_effect_authority": "none",
    }
    receipt_id = f"outr_{_digest(facts)[:32]}"
    projection = dict(facts, receipt_id=receipt_id)
    projection["receipt_digest"] = _digest(projection)
    return OutputReceipt(projection, seal=_RECEIPT_SEAL)


def _sign_output_attestation(
    projection: Mapping[str, Any],
    *,
    kind: str,
    principal_kind: str,
    parent_attestation_id: str,
    parent_attestation_digest: str,
    secret: str | bytes,
    ha_installation_digest: str,
    bridge_config_entry_id: str,
    issued_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    key = _attestation_secret(secret)
    installation = _hex_digest(
        ha_installation_digest,
        reason="output_attestation_installation_digest_invalid",
    )
    bridge_entry = _text(
        bridge_config_entry_id,
        reason="output_attestation_bridge_entry_invalid",
    )
    issued_text = _utc_text(issued_at)
    expires_text = _utc_text(expires_at)
    try:
        issued = datetime.fromisoformat(issued_text[:-1] + "+00:00")
        expires = datetime.fromisoformat(expires_text[:-1] + "+00:00")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("output_attestation_time_invalid") from exc
    try:
        ttl_limit = issued + timedelta(seconds=120)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("output_attestation_time_invalid") from exc
    if not issued < expires <= ttl_limit:
        raise ValueError("output_attestation_time_invalid")
    if kind == "attempt":
        if parent_attestation_id or parent_attestation_digest:
            raise ValueError("output_attestation_parent_invalid")
    elif kind == "receipt":
        if (
            type(parent_attestation_id) is not str
            or not parent_attestation_id.startswith("outat_")
            or len(parent_attestation_id) != 38
        ):
            raise ValueError("output_attestation_parent_invalid")
        _hex_digest(
            parent_attestation_digest,
            reason="output_attestation_parent_invalid",
        )
    else:
        raise ValueError("output_attestation_kind_invalid")
    body = json.loads(_canonical_json(dict(projection)))
    body_digest = _digest(body)
    facts = {
        "schema_version": OUTPUT_ATTESTATION_SCHEMA_VERSION,
        "kind": kind,
        "key_id": output_attestation_key_id(key),
        "ha_installation_digest": installation,
        "bridge_config_entry_id": bridge_entry,
        "principal_kind": principal_kind,
        "parent_attestation_id": parent_attestation_id,
        "parent_attestation_digest": parent_attestation_digest,
        "issued_at": issued_text,
        "expires_at": expires_text,
        "body": body,
        "body_digest": body_digest,
    }
    attestation_id = "outat_" + _digest(facts)[:32]
    signed = dict(facts, attestation_id=attestation_id)
    signature = hmac.new(
        key,
        b"smartagent.output-attestation.signature.v1\x00"
        + _canonical_json(signed).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    envelope = dict(signed, signature=signature)
    envelope["attestation_digest"] = _digest(envelope)
    return envelope


def sign_output_attempt_attestation(
    attempt: OutputAttempt,
    *,
    secret: str | bytes,
    ha_installation_digest: str,
    bridge_config_entry_id: str,
    issued_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    """Sign one redacted attempt for the dedicated output-ledger ingress."""
    if type(attempt) is not OutputAttempt:
        raise ValueError("output_attempt_required")
    principal_kind = (
        "system_health"
        if attempt.execution_class == "notification"
        else "ha_current_user"
    )
    return _sign_output_attestation(
        attempt.to_dict(),
        kind="attempt",
        principal_kind=principal_kind,
        parent_attestation_id="",
        parent_attestation_digest="",
        secret=secret,
        ha_installation_digest=ha_installation_digest,
        bridge_config_entry_id=bridge_config_entry_id,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def sign_output_receipt_attestation(
    receipt: OutputReceipt,
    *,
    parent_attestation: Mapping[str, Any],
    secret: str | bytes,
    ha_installation_digest: str,
    bridge_config_entry_id: str,
    issued_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    """Sign one conservative Receipt and bind it to its attempt attestation."""
    if type(receipt) is not OutputReceipt or type(parent_attestation) is not dict:
        raise ValueError("output_receipt_required")
    parent_body = parent_attestation.get("body")
    if (
        parent_attestation.get("kind") != "attempt"
        or type(parent_body) is not dict
        or parent_body.get("attempt_id") != receipt.attempt_id
        or parent_body.get("attempt_digest") != receipt.attempt_digest
    ):
        raise ValueError("output_attestation_parent_invalid")
    principal_kind = (
        "system_health"
        if receipt.execution_class == "notification"
        else "ha_current_user"
    )
    return _sign_output_attestation(
        receipt.to_dict(),
        kind="receipt",
        principal_kind=principal_kind,
        parent_attestation_id=str(parent_attestation.get("attestation_id") or ""),
        parent_attestation_digest=str(
            parent_attestation.get("attestation_digest") or ""
        ),
        secret=secret,
        ha_installation_digest=ha_installation_digest,
        bridge_config_entry_id=bridge_config_entry_id,
        issued_at=issued_at,
        expires_at=expires_at,
    )


__all__: list[str] = []
