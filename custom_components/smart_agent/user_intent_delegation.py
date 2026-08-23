"""Issue short-lived user-intent delegations from the trusted HA integration.

This module deliberately does not accept a ``user_explicit`` boolean as
authority.  Callers must first establish a current authenticated HA user
session and pass that server-owned session identifier to the issuer.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any


DELEGATION_KIND = "smartagent.user_intent_delegation.v1"
DELEGATION_VERSION = 1
DEFAULT_TTL_SECONDS = 15
MAX_TTL_SECONDS = 30
TRANSPORT_FIELD = "_smartagent_user_intent_delegation"
_KEY_CONTEXT = b"smartagent.user_intent_delegation.signing.v1\x00"


class UserIntentDelegationError(ValueError):
    """Raised when a delegation cannot be issued or transported safely."""


@dataclass(frozen=True, slots=True)
class AuthenticatedUserIntentAuthority:
    """HA-owned identity/session fact carried inside one in-process request.

    This is intentionally not a token and cannot be constructed from a
    ``user_explicit`` flag or a transport header.  The conversation boundary
    creates it only after resolving the current HA auth user.
    """

    user_id: str
    session_id: str


def authenticated_user_intent_authority(
    *, user_id: str, session_id: str
) -> AuthenticatedUserIntentAuthority:
    """Create the typed authority fact after HA auth has succeeded."""

    normalized_user_id = user_id.strip() if type(user_id) is str else ""
    normalized_session_id = session_id.strip() if type(session_id) is str else ""
    if (
        not normalized_user_id
        or normalized_user_id != user_id
        or len(normalized_user_id) > 256
        or not normalized_session_id
        or normalized_session_id != session_id
        or len(normalized_session_id) < 8
        or len(normalized_session_id) > 256
        or any(
            ord(character) < 32 or ord(character) == 127
            for value in (normalized_user_id, normalized_session_id)
            for character in value
        )
    ):
        raise UserIntentDelegationError("user_intent_authority_invalid")
    return AuthenticatedUserIntentAuthority(
        user_id=normalized_user_id,
        session_id=normalized_session_id,
    )


def _fail(reason: str) -> None:
    raise UserIntentDelegationError(reason)


def _signing_key(secret: str) -> bytes:
    if type(secret) is not str or secret != secret.strip():
        _fail("user_intent_delegation_secret_invalid")
    raw = secret.encode("utf-8")
    if len(raw) < 32 or any(ord(char) < 32 or ord(char) == 127 for char in secret):
        _fail("user_intent_delegation_secret_invalid")
    return hmac.new(raw, _KEY_CONTEXT, hashlib.sha256).digest()


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise UserIntentDelegationError(
            "user_intent_delegation_payload_invalid"
        ) from exc


def canonical_command_projection(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the exact command projection covered by a delegation."""

    if type(envelope) is not dict:
        _fail("user_intent_delegation_envelope_invalid")
    raw_commands = envelope.get("commands")
    if type(raw_commands) is not list or not raw_commands:
        _fail("user_intent_delegation_commands_invalid")
    commands: list[dict[str, Any]] = []
    for raw_command in raw_commands:
        if type(raw_command) is not dict:
            _fail("user_intent_delegation_commands_invalid")
        entity_id = str(raw_command.get("entity_id") or "").strip()
        service = str(raw_command.get("service") or "").strip()
        if "." not in entity_id or not service:
            _fail("user_intent_delegation_commands_invalid")
        domain = (
            str(raw_command.get("domain") or "").strip()
            or entity_id.split(".", 1)[0]
        )
        raw_data = raw_command.get("data")
        if not isinstance(raw_data, dict):
            raw_data = raw_command.get("params")
        data = dict(raw_data) if isinstance(raw_data, dict) else {}
        commands.append(
            {
                "entity_id": entity_id,
                "domain": domain,
                "service": service,
                "data": data,
            }
        )
    # Reject values that cannot be represented by the signed wire contract.
    _canonical_json(commands)
    return commands


def command_digest(envelope: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(canonical_command_projection(envelope))).hexdigest()


def _request_id(envelope: dict[str, Any]) -> str:
    request_id = str(envelope.get("request_id") or "").strip()
    if not request_id or len(request_id) > 256:
        _fail("user_intent_delegation_request_id_invalid")
    return request_id


def issue_user_intent_delegation(
    envelope: dict[str, Any],
    *,
    secret: str,
    session_id: str,
    user_id: str = "",
    now_epoch: int | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    jti: str | None = None,
) -> dict[str, Any]:
    """Issue one delegation after the HA integration authenticates the user.

    ``session_id`` must identify the server-owned current HA user/voice session;
    a UI label or caller-provided source string is not sufficient.
    """

    key = _signing_key(secret)
    if type(session_id) is not str:
        _fail("user_intent_delegation_session_invalid")
    normalized_session_id = session_id.strip()
    if (
        session_id != normalized_session_id
        or len(normalized_session_id) < 8
        or len(normalized_session_id) > 256
    ):
        _fail("user_intent_delegation_session_invalid")
    normalized_user_id = user_id.strip() if type(user_id) is str else ""
    if normalized_user_id and (
        normalized_user_id != user_id
        or len(normalized_user_id) > 256
        or any(ord(character) < 32 or ord(character) == 127 for character in normalized_user_id)
    ):
        _fail("user_intent_delegation_user_invalid")
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        _fail("user_intent_delegation_ttl_invalid")
    issued_at = int(time.time()) if now_epoch is None else now_epoch
    if type(issued_at) is not int or issued_at < 0:
        _fail("user_intent_delegation_time_invalid")
    delegation_id = jti if jti is not None else secrets.token_urlsafe(18)
    if (
        type(delegation_id) is not str
        or delegation_id != delegation_id.strip()
        or not 16 <= len(delegation_id) <= 128
    ):
        _fail("user_intent_delegation_jti_invalid")

    payload: dict[str, Any] = {
        "v": DELEGATION_VERSION,
        "kind": DELEGATION_KIND,
        "issuer": "ha_integration",
        "execution_intent": "user_explicit",
        "actor_class": "authenticated_gateway_operator",
        "request_id": _request_id(envelope),
        "session_id": normalized_session_id,
        "commands_digest": command_digest(envelope),
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "jti": delegation_id,
        "kid": hashlib.sha256(key).hexdigest()[:16],
    }
    signature = hmac.new(key, _canonical_json(payload), hashlib.sha256).digest()
    payload["sig"] = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return payload


def validate_transport_binding(
    envelope: dict[str, Any], delegation: dict[str, Any]
) -> dict[str, Any]:
    """Fail before transport when the token is bound to another command."""

    if type(delegation) is not dict:
        _fail("user_intent_delegation_invalid")
    if delegation.get("request_id") != _request_id(envelope):
        _fail("user_intent_delegation_request_mismatch")
    if delegation.get("commands_digest") != command_digest(envelope):
        _fail("user_intent_delegation_commands_mismatch")
    return dict(delegation)


__all__ = [
    "AuthenticatedUserIntentAuthority",
    "DEFAULT_TTL_SECONDS",
    "DELEGATION_KIND",
    "DELEGATION_VERSION",
    "MAX_TTL_SECONDS",
    "TRANSPORT_FIELD",
    "UserIntentDelegationError",
    "authenticated_user_intent_authority",
    "canonical_command_projection",
    "command_digest",
    "issue_user_intent_delegation",
    "validate_transport_binding",
]
