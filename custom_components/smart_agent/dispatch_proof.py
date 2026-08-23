"""Verify and durably consume one-time add-on to HA dispatch proofs."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import time
from typing import Any, Callable, Iterable


PROOF_VERSION = 1
PROOF_PURPOSE = "ha_execute_dispatch"
FIELD_CANARY_PROOF_VERSION = 2
FIELD_CANARY_PROOF_PURPOSE = "ha_execute_dispatch_field_canary"
FIELD_CANARY_PROOF_AUTHORITY = "field_canary_gateway_decision"
FIELD_DISPATCH_PERMIT_SCHEMA_VERSION = (
    "smartagent.field_canary_promotion_grant_dispatch_permit.v0.1"
)
PROOF_MAX_TTL_SECONDS = 30
PROOF_CLOCK_SKEW_SECONDS = 5
_KEY_DERIVATION_CONTEXT = b"smartagent/ha-dispatch-proof/v1"
_FIELD_CANARY_KEY_DERIVATION_CONTEXT = (
    b"smartagent/ha-dispatch-proof/v2/field-canary"
)
_TRANSPORT_FIELDS = frozenset({"_smartagent_transport", "_smartagent_dispatch_proof"})
_RUNTIME_KEY = "smart_agent_dispatch_proof_runtime"
_STORE_VERSION = 1
_STORE_PREFIX = "smart_agent.ha_dispatch_proofs"
_MAX_CONSUMED_PROOFS = 4096
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_V1_EXPECTED_KEYS = frozenset(
    {
        "v",
        "purpose",
        "kid",
        "authority",
        "execution_transaction_id",
        "request_id",
        "envelope_sha256",
        "commands_digest",
        "binding_digest",
        "reservation_digest",
        "dispatch_token_digest",
        "target",
        "jti",
        "iat",
        "exp",
        "signature",
    }
)
_V2_EXPECTED_KEYS = frozenset(
    {
        *_V1_EXPECTED_KEYS,
        "field_dispatch_permit_schema_version",
        "field_dispatch_permit_id",
        "field_dispatch_permit_digest",
        "field_dispatch_permit_exp",
    }
)
_FIELD_PERMIT_ID = re.compile(r"^fcdpmt_[0-9a-f]{32}$")


class DispatchProofError(ValueError):
    """Fail-closed proof validation or durable-consumption error."""


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_envelope_projection(envelope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise DispatchProofError("dispatch_proof_envelope_invalid")
    try:
        detached = json.loads(_stable_json(envelope))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise DispatchProofError("dispatch_proof_envelope_invalid") from exc
    if not isinstance(detached, dict):
        raise DispatchProofError("dispatch_proof_envelope_invalid")
    for field in _TRANSPORT_FIELDS:
        detached.pop(field, None)
    return detached


def envelope_digest(envelope: dict[str, Any]) -> str:
    return hashlib.sha256(
        _stable_json(canonical_envelope_projection(envelope)).encode("utf-8")
    ).hexdigest()


def _derived_key(secret: str, *, version: int = PROOF_VERSION) -> bytes:
    raw = str(secret or "").encode("utf-8")
    if len(raw) < 16:
        raise DispatchProofError("dispatch_proof_secret_unavailable")
    if version == PROOF_VERSION:
        context = _KEY_DERIVATION_CONTEXT
    elif version == FIELD_CANARY_PROOF_VERSION:
        context = _FIELD_CANARY_KEY_DERIVATION_CONTEXT
    else:
        raise DispatchProofError("dispatch_proof_version_invalid")
    return hmac.new(raw, context, hashlib.sha256).digest()


def key_id(secret: str, *, version: int = PROOF_VERSION) -> str:
    return hashlib.sha256(_derived_key(secret, version=version)).hexdigest()[:16]


def dispatch_proof_secret_for_clients(
    proof: Any,
    addon_clients: Iterable[Any],
) -> str:
    """Select one exact verification secret without crossing proof domains."""

    if type(proof) is not dict:
        return ""
    proof_kid = proof.get("kid")
    proof_version = proof.get("v")
    if (
        type(proof_kid) is not str
        or not proof_kid
        or proof_kid != proof_kid.strip()
        or type(proof_version) is not int
    ):
        return ""
    if proof_version not in {PROOF_VERSION, FIELD_CANARY_PROOF_VERSION}:
        return ""

    for addon_client in addon_clients:
        if proof_version == PROOF_VERSION:
            candidates = (getattr(addon_client, "_auth_token", ""),)
        elif (
            getattr(
                addon_client,
                "_field_canary_host_dispatch_proof_enabled",
                False,
            )
            is True
        ):
            candidates = (
                getattr(
                    addon_client,
                    "_field_canary_host_dispatch_proof_secret",
                    "",
                ),
                getattr(
                    addon_client,
                    "_field_canary_previous_host_dispatch_proof_secret",
                    "",
                ),
            )
        else:
            candidates = ()
        seen: set[str] = set()
        for candidate in candidates:
            if (
                type(candidate) is not str
                or not candidate
                or candidate != candidate.strip()
                or candidate in seen
            ):
                continue
            seen.add(candidate)
            try:
                if key_id(candidate, version=proof_version) == proof_kid:
                    return candidate
            except DispatchProofError:
                continue
    return ""


def _actual_target(envelope: dict[str, Any]) -> str:
    commands = (
        envelope.get("commands")
        if isinstance(envelope.get("commands"), list)
        else []
    )
    if len(commands) == 1 and isinstance(commands[0], dict):
        return str(commands[0].get("entity_id") or "").strip().lower()
    return ""


def verify_dispatch_proof(
    envelope: dict[str, Any],
    proof: Any,
    *,
    secret: str,
    now: int | None = None,
) -> dict[str, Any]:
    if not isinstance(proof, dict):
        raise DispatchProofError("dispatch_proof_schema_invalid")
    version = proof.get("v")
    if type(version) is not int or version not in {
        PROOF_VERSION,
        FIELD_CANARY_PROOF_VERSION,
    }:
        raise DispatchProofError("dispatch_proof_version_invalid")
    expected_keys = (
        _V1_EXPECTED_KEYS
        if version == PROOF_VERSION
        else _V2_EXPECTED_KEYS
    )
    if frozenset(proof) != expected_keys:
        raise DispatchProofError("dispatch_proof_schema_invalid")
    expected_purpose = (
        PROOF_PURPOSE
        if version == PROOF_VERSION
        else FIELD_CANARY_PROOF_PURPOSE
    )
    if proof.get("purpose") != expected_purpose:
        raise DispatchProofError("dispatch_proof_purpose_invalid")
    if type(proof.get("iat")) is not int or type(proof.get("exp")) is not int:
        raise DispatchProofError("dispatch_proof_time_invalid")
    issued_at = int(proof["iat"])
    expires_at = int(proof["exp"])
    evaluated_at = int(time.time() if now is None else now)
    if (
        expires_at <= issued_at
        or expires_at - issued_at > PROOF_MAX_TTL_SECONDS
        or issued_at > evaluated_at + PROOF_CLOCK_SKEW_SECONDS
        or evaluated_at >= expires_at
    ):
        raise DispatchProofError("dispatch_proof_expired_or_future")
    if str(proof.get("kid") or "") != key_id(secret, version=version):
        raise DispatchProofError("dispatch_proof_key_mismatch")
    if not _HEX_64.fullmatch(str(proof.get("jti") or "")):
        raise DispatchProofError("dispatch_proof_jti_invalid")
    signature = str(proof.get("signature") or "").strip().lower()
    unsigned = {key: value for key, value in proof.items() if key != "signature"}
    expected_signature = hmac.new(
        _derived_key(secret, version=version),
        _stable_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not _HEX_64.fullmatch(signature) or not hmac.compare_digest(
        signature,
        expected_signature,
    ):
        raise DispatchProofError("dispatch_proof_signature_invalid")
    request_id = str(envelope.get("request_id") or "").strip()
    if not request_id or str(proof.get("request_id") or "").strip() != request_id:
        raise DispatchProofError("dispatch_proof_request_mismatch")
    if str(proof.get("envelope_sha256") or "") != envelope_digest(envelope):
        raise DispatchProofError("dispatch_proof_envelope_mismatch")
    reference = envelope.get("authorization_ref")
    reference = reference if isinstance(reference, dict) else {}
    if str(proof.get("commands_digest") or "").strip().lower() != str(
        reference.get("commands_digest") or ""
    ).strip().lower():
        raise DispatchProofError("dispatch_proof_commands_mismatch")
    if str(proof.get("target") or "").strip().lower() != _actual_target(envelope):
        raise DispatchProofError("dispatch_proof_target_mismatch")
    transaction_id = str(proof.get("execution_transaction_id") or "").strip()
    authority = str(proof.get("authority") or "").strip().lower()
    v1_authorities = {
        "gateway_decision",
        "controlled_execution",
        "operations_patrol",
    }
    if not transaction_id or (
        version == PROOF_VERSION
        and authority not in v1_authorities
    ) or (
        version == FIELD_CANARY_PROOF_VERSION
        and authority != FIELD_CANARY_PROOF_AUTHORITY
    ):
        raise DispatchProofError("dispatch_proof_authority_invalid")
    if authority in {"gateway_decision", FIELD_CANARY_PROOF_AUTHORITY}:
        for field in (
            "commands_digest",
            "binding_digest",
            "reservation_digest",
            "dispatch_token_digest",
        ):
            if not _HEX_64.fullmatch(str(proof.get(field) or "")):
                raise DispatchProofError("dispatch_proof_gateway_binding_invalid")
    if version == FIELD_CANARY_PROOF_VERSION:
        permit_id = proof.get("field_dispatch_permit_id")
        permit_digest = proof.get("field_dispatch_permit_digest")
        permit_exp = proof.get("field_dispatch_permit_exp")
        if (
            proof.get("field_dispatch_permit_schema_version")
            != FIELD_DISPATCH_PERMIT_SCHEMA_VERSION
            or type(permit_id) is not str
            or not _FIELD_PERMIT_ID.fullmatch(permit_id)
            or type(permit_digest) is not str
            or not _HEX_64.fullmatch(permit_digest)
            or permit_id != "fcdpmt_" + permit_digest[:32]
            or type(permit_exp) is not int
            or permit_exp <= issued_at
            or expires_at != min(
                issued_at + PROOF_MAX_TTL_SECONDS,
                permit_exp,
            )
        ):
            raise DispatchProofError("dispatch_proof_field_permit_invalid")
    return dict(proof)


async def async_consume_dispatch_proof(
    hass: Any,
    claims: dict[str, Any],
    *,
    now: int | None = None,
    store_factory: Callable[[Any, int, str], Any] | None = None,
) -> None:
    evaluated_at = int(time.time() if now is None else now)
    expires_at = claims.get("exp")
    if type(expires_at) is not int or evaluated_at >= int(expires_at):
        raise DispatchProofError("dispatch_proof_expired_or_future")
    kid = str(claims.get("kid") or "").strip()
    jti = str(claims.get("jti") or "").strip().lower()
    if not kid or not _HEX_64.fullmatch(jti):
        raise DispatchProofError("dispatch_proof_consume_binding_invalid")
    if store_factory is None:
        try:
            from homeassistant.helpers.storage import Store
        except Exception as exc:
            raise DispatchProofError("dispatch_proof_store_unavailable") from exc
        store_factory = Store
    runtime = hass.data.setdefault(_RUNTIME_KEY, {})
    state = runtime.setdefault(kid, {})
    lock = state.get("lock")
    if not isinstance(lock, asyncio.Lock):
        lock = asyncio.Lock()
        state["lock"] = lock
    store = state.get("store")
    if store is None:
        store = store_factory(hass, _STORE_VERSION, f"{_STORE_PREFIX}.{kid}")
        state["store"] = store
    nonce_digest = hashlib.sha256(jti.encode("ascii")).hexdigest()
    async with lock:
        try:
            payload = await store.async_load()
        except Exception as exc:
            raise DispatchProofError("dispatch_proof_store_unavailable") from exc
        if payload is None:
            consumed: dict[str, int] = {}
        elif isinstance(payload, dict) and isinstance(payload.get("consumed"), dict):
            consumed = {}
            for raw_digest, raw_expiry in payload["consumed"].items():
                if (
                    _HEX_64.fullmatch(str(raw_digest or ""))
                    and type(raw_expiry) is int
                ):
                    consumed[str(raw_digest)] = int(raw_expiry)
                else:
                    raise DispatchProofError("dispatch_proof_store_corrupt")
        else:
            raise DispatchProofError("dispatch_proof_store_corrupt")
        live = {
            digest: expiry
            for digest, expiry in consumed.items()
            if expiry > evaluated_at
        }
        if nonce_digest in live:
            raise DispatchProofError("dispatch_proof_replayed")
        if len(live) >= _MAX_CONSUMED_PROOFS:
            raise DispatchProofError("dispatch_proof_store_capacity_exceeded")
        candidate = {**live, nonce_digest: int(expires_at)}
        try:
            await store.async_save({"consumed": candidate})
        except Exception as exc:
            raise DispatchProofError("dispatch_proof_store_unavailable") from exc


__all__ = [
    "DispatchProofError",
    "FIELD_CANARY_PROOF_AUTHORITY",
    "FIELD_CANARY_PROOF_PURPOSE",
    "FIELD_CANARY_PROOF_VERSION",
    "FIELD_DISPATCH_PERMIT_SCHEMA_VERSION",
    "async_consume_dispatch_proof",
    "canonical_envelope_projection",
    "dispatch_proof_secret_for_clients",
    "envelope_digest",
    "key_id",
    "verify_dispatch_proof",
]
