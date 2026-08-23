"""Current-HA-WebSocket-session attestor for Field Canary provisioning.

This module is deliberately transport-free.  It verifies one add-on-signed
proposal challenge, re-reads the exact Home Assistant refresh token backing the
current WebSocket connection, and emits the v0.2 operator-identity attestation
accepted by the add-on persistence source.  It does not publish an approval,
PromotionGrant, or any device/runtime authority.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any, Callable, Mapping


FIELD_CANARY_OPERATOR_CHALLENGE_RESPONSE_VERSION = (
    "smartagent.field_canary_operator_identity_challenge_response.v0.1"
)
FIELD_CANARY_OPERATOR_CHALLENGE_REQUEST_VERSION = (
    "smartagent.field_canary_operator_identity_challenge_request.v0.1"
)
FIELD_CANARY_OPERATOR_COMMIT_REQUEST_VERSION = (
    "smartagent.field_canary_operator_identity_commit_request.v0.1"
)
FIELD_CANARY_OPERATOR_COMMIT_RESPONSE_VERSION = (
    "smartagent.field_canary_operator_identity_commit_response.v0.1"
)
FIELD_CANARY_OPERATOR_APPROVAL_REQUEST_VERSION = (
    "smartagent.field_canary_operator_approval_publish_request.v0.1"
)
FIELD_CANARY_OPERATOR_APPROVAL_RESPONSE_VERSION = (
    "smartagent.field_canary_operator_approval_publish_response.v0.1"
)
FIELD_CANARY_PROMOTION_GRANT_REQUEST_VERSION = (
    "smartagent.field_canary_promotion_grant_issue_request.v0.1"
)
FIELD_CANARY_PROMOTION_GRANT_RESPONSE_VERSION = (
    "smartagent.field_canary_promotion_grant_issue_response.v0.1"
)
FIELD_CANARY_PROMOTION_GRANT_REVOCATION_REQUEST_VERSION = (
    "smartagent.field_canary_promotion_grant_revocation_request.v0.1"
)
FIELD_CANARY_PROMOTION_GRANT_REVOCATION_RESPONSE_VERSION = (
    "smartagent.field_canary_promotion_grant_revocation_response.v0.1"
)
FIELD_CANARY_PROMOTION_GRANT_OPERATOR_REVOCATION_REQUEST_VERSION = (
    "smartagent.field_canary_promotion_grant_operator_revocation_request.v0.1"
)
FIELD_CANARY_PROMOTION_GRANT_OPERATOR_REVOCATION_RESPONSE_VERSION = (
    "smartagent.field_canary_promotion_grant_operator_revocation_response.v0.1"
)
FIELD_CANARY_PROMOTION_GRANT_REVOCATION_PROPOSAL_REQUEST_VERSION = (
    "smartagent.field_canary_promotion_grant_revocation_proposal_request.v0.1"
)
FIELD_CANARY_PROMOTION_GRANT_REVOCATION_PROPOSAL_RESPONSE_VERSION = (
    "smartagent.field_canary_promotion_grant_revocation_proposal_response.v0.1"
)
FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_VERSION = (
    "smartagent.field_canary_operator_identity_attestation.v0.2"
)
FIELD_CANARY_OPERATOR_CHALLENGE_RESPONSE_PURPOSE = (
    "field_canary_operator_identity_challenge_issued"
)
FIELD_CANARY_OPERATOR_CHALLENGE_REQUEST_PURPOSE = (
    "field_canary_operator_identity_challenge_requested"
)
FIELD_CANARY_OPERATOR_COMMIT_REQUEST_PURPOSE = (
    "field_canary_operator_identity_commit_requested"
)
FIELD_CANARY_OPERATOR_COMMIT_RESPONSE_PURPOSE = (
    "field_canary_operator_identity_committed"
)
FIELD_CANARY_OPERATOR_APPROVAL_REQUEST_PURPOSE = (
    "field_canary_operator_approval_publish_requested"
)
FIELD_CANARY_OPERATOR_APPROVAL_RESPONSE_PURPOSE = (
    "field_canary_operator_approval_published"
)
FIELD_CANARY_PROMOTION_GRANT_REQUEST_PURPOSE = (
    "field_canary_promotion_grant_issue_requested"
)
FIELD_CANARY_PROMOTION_GRANT_RESPONSE_PURPOSE = (
    "field_canary_promotion_grant_issued"
)
FIELD_CANARY_PROMOTION_GRANT_REVOCATION_REQUEST_PURPOSE = (
    "field_canary_promotion_grant_revocation_requested"
)
FIELD_CANARY_PROMOTION_GRANT_REVOCATION_RESPONSE_PURPOSE = (
    "field_canary_promotion_grant_revoked"
)
FIELD_CANARY_PROMOTION_GRANT_OPERATOR_REVOCATION_REQUEST_PURPOSE = (
    "field_canary_promotion_grant_operator_revocation_requested"
)
FIELD_CANARY_PROMOTION_GRANT_OPERATOR_REVOCATION_RESPONSE_PURPOSE = (
    "field_canary_promotion_grant_operator_revocation_committed"
)
FIELD_CANARY_PROMOTION_GRANT_REVOCATION_PROPOSAL_REQUEST_PURPOSE = (
    "field_canary_promotion_grant_revocation_proposal_requested"
)
FIELD_CANARY_PROMOTION_GRANT_REVOCATION_PROPOSAL_RESPONSE_PURPOSE = (
    "field_canary_promotion_grant_revocation_proposal_committed"
)
MAX_OPERATOR_IDENTITY_WINDOW_SECONDS = 15 * 60
MAX_OPERATOR_IDENTITY_CLOCK_SKEW_SECONDS = 15

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_APPROVAL_CLASSES = frozenset(
    {
        "issuer_policy_provisioning",
        "acceptance_profile_authority_provisioning",
        "readiness_selection_provisioning",
        "policy_assignment_authority_provisioning",
        "device_binding_authority_provisioning",
        "capability_manifest_authority_provisioning",
        "provider_binding_authority_provisioning",
        "promotion_grant_issuance",
        "promotion_grant_revocation",
    }
)
_FACTORY_TOKEN = object()
_AUTHORITY = {
    "host_attestation_verified": True,
    "canonical_operator_identity_verified": True,
    "promotion_grant_issued": False,
    "execution_eligible": False,
    "execution_permitted": False,
    "field_accepted": False,
    "device_effect_authority": "none",
}
_CHALLENGE_AUTHORITY = {
    "challenge_consumed": False,
    "canonical_operator_identity_verified": False,
    "promotion_grant_issued": False,
    "execution_eligible": False,
    "execution_permitted": False,
    "field_accepted": False,
    "device_effect_authority": "none",
}
_CHALLENGE_FIELDS = frozenset(
    {
        "schema_version",
        "purpose",
        "ingress_key_id",
        "request_id",
        "challenge_id",
        "approval_definition_id",
        "approval_class",
        "subject_id",
        "subject_digest",
        "request_nonce",
        "request_nonce_digest",
        "expected_attestation_key_id",
        "ha_installation_digest",
        "bridge_config_entry_id",
        "issued_at",
        "expires_at",
        *_CHALLENGE_AUTHORITY,
        "signature",
    }
)
_REQUEST_AUTHORITY = {
    "promotion_grant_issued": False,
    "execution_eligible": False,
    "execution_permitted": False,
    "field_accepted": False,
    "device_effect_authority": "none",
}
_COMMIT_RESPONSE_AUTHORITY = {
    "canonical_operator_identity_verified": True,
    "approval_record_issued": False,
    **_REQUEST_AUTHORITY,
}
_APPROVAL_REQUEST_AUTHORITY = {
    "canonical_operator_identity_verified": True,
    "approval_record_issued": False,
    **_REQUEST_AUTHORITY,
}
_APPROVAL_RESPONSE_AUTHORITY = {
    "canonical_operator_identity_verified": True,
    "approval_record_issued": True,
    **_REQUEST_AUTHORITY,
}
_GRANT_REQUEST_AUTHORITY = {
    "canonical_operator_identity_verified": True,
    "approval_record_issued": True,
    **_REQUEST_AUTHORITY,
}
_GRANT_RESPONSE_AUTHORITY = {
    "canonical_operator_identity_verified": True,
    "approval_record_issued": True,
    "positive_authority": True,
    "promotion_grant_issued": True,
    "promotion_eligible": True,
    "execution_eligible": False,
    "execution_permitted": False,
    "field_accepted": False,
    "runtime_consumer_enabled": False,
    "device_effect_authority": "none",
}
_GRANT_REVOCATION_REQUEST_AUTHORITY = {
    "canonical_operator_identity_verified": False,
    "approval_record_issued": False,
    "grant_origin_identity_bound": True,
    "revoker_identity_verified": False,
    "positive_authority": False,
    "promotion_grant_issued": False,
    "promotion_eligible": False,
    "execution_eligible": False,
    "execution_permitted": False,
    "field_accepted": False,
    "runtime_consumer_enabled": False,
    "device_effect_authority": "none",
}
_GRANT_REVOCATION_RESPONSE_AUTHORITY = {
    "canonical_operator_identity_verified": False,
    "approval_record_issued": False,
    "grant_origin_identity_bound": True,
    "revoker_identity_verified": False,
    "positive_authority": False,
    "promotion_grant_issued": True,
    "promotion_eligible": False,
    "grant_revoked": True,
    "execution_eligible": False,
    "execution_permitted": False,
    "field_accepted": False,
    "runtime_consumer_enabled": False,
    "device_effect_authority": "none",
}
_GRANT_REVOCATION_PROPOSAL_AUTHORITY = {
    "canonical_revoker_identity_verified": False,
    "approval_record_issued": False,
    "grant_revocation_authorized": False,
    "grant_revoked": False,
    "positive_authority": False,
    "runtime_consumer_enabled": False,
    **_REQUEST_AUTHORITY,
}
_GRANT_OPERATOR_REVOCATION_REQUEST_AUTHORITY = {
    "canonical_revoker_identity_verified": True,
    "approval_record_issued": True,
    "approval_consumed": False,
    "grant_revocation_authorized": False,
    "grant_revoked": False,
    "positive_authority": False,
    "runtime_consumer_enabled": False,
    **_REQUEST_AUTHORITY,
}
_GRANT_OPERATOR_REVOCATION_RESPONSE_AUTHORITY = {
    "canonical_revoker_identity_verified": True,
    "approval_record_issued": True,
    "approval_consumed": True,
    "grant_revocation_authorized": True,
    "grant_revoked": True,
    "positive_authority": False,
    "promotion_grant_issued": True,
    "execution_eligible": False,
    "execution_permitted": False,
    "field_accepted": False,
    "runtime_consumer_enabled": False,
    "device_effect_authority": "none",
}


class FieldCanaryOperatorSessionAttestationError(RuntimeError):
    """The challenge or current authenticated HA session is not admissible."""


def _identifier(value: Any, code: str) -> str:
    if (
        type(value) is not str
        or value != value.strip()
        or _IDENTIFIER_RE.fullmatch(value) is None
    ):
        raise FieldCanaryOperatorSessionAttestationError(code)
    return value


def _hex(value: Any, code: str) -> str:
    if type(value) is not str or _HEX_RE.fullmatch(value) is None:
        raise FieldCanaryOperatorSessionAttestationError(code)
    return value


def _utc(value: Any, code: str) -> datetime:
    try:
        if type(value) is datetime:
            parsed = value
        elif type(value) is str:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            raise ValueError(code)
        if parsed.tzinfo is None:
            raise ValueError(code)
        return parsed.astimezone(UTC)
    except (OverflowError, TypeError, ValueError) as exc:
        raise FieldCanaryOperatorSessionAttestationError(code) from exc


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (OverflowError, TypeError, ValueError) as exc:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_session_projection_invalid"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _secret(value: Any, code: str) -> bytes:
    if type(value) is str:
        if value != value.strip():
            raise FieldCanaryOperatorSessionAttestationError(code)
        raw = value.encode("utf-8")
    elif type(value) is bytes:
        raw = value
    else:
        raise FieldCanaryOperatorSessionAttestationError(code)
    if len(raw) < 32:
        raise FieldCanaryOperatorSessionAttestationError(code)
    return raw


def _ingress_key(secret: bytes) -> bytes:
    return hashlib.sha256(
        b"smartagent.field_canary_operator_identity_ingress.v0.1\x00" + secret
    ).digest()


def field_canary_operator_identity_ingress_key_id(secret: str | bytes) -> str:
    raw = _secret(secret, "field_canary_operator_ingress_secret_invalid")
    return "fcoigk_" + hashlib.sha256(_ingress_key(raw)).hexdigest()[:32]


def _challenge_signature(secret: bytes, unsigned: Mapping[str, Any]) -> str:
    return hmac.new(
        _ingress_key(secret),
        b"challenge-response\x00" + _json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _ingress_signature(secret: bytes, domain: bytes, unsigned: Mapping[str, Any]) -> str:
    return hmac.new(
        _ingress_key(secret),
        domain + b"\x00" + _json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _attestation_key(secret: bytes) -> bytes:
    return hashlib.sha256(
        b"smartagent.field_canary_operator_identity_attestation.v0.2\x00" + secret
    ).digest()


def field_canary_operator_identity_attestation_key_id(
    secret: str | bytes,
) -> str:
    raw = _secret(secret, "field_canary_operator_identity_secret_invalid")
    return "fcoik_" + hashlib.sha256(_attestation_key(raw)).hexdigest()[:32]


def _attestation_signature(secret: bytes, unsigned: Mapping[str, Any]) -> str:
    return hmac.new(
        _attestation_key(secret),
        _json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class VerifiedFieldCanaryOperatorIdentityChallenge:
    """Detached challenge facts admitted by the host verifier."""

    projection: Mapping[str, Any]
    _factory_token: object

    def __post_init__(self) -> None:
        if self._factory_token is not _FACTORY_TOKEN:
            raise TypeError("field_canary_operator_challenge_factory_required")


def sign_field_canary_operator_identity_challenge_request(
    *,
    request_id: str,
    approval_definition_id: str,
    requested_at: datetime,
    ingress_secret: str | bytes,
) -> Mapping[str, Any]:
    """Sign one bounded request for a server-owned proposal challenge."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    unsigned = {
        "schema_version": FIELD_CANARY_OPERATOR_CHALLENGE_REQUEST_VERSION,
        "purpose": FIELD_CANARY_OPERATOR_CHALLENGE_REQUEST_PURPOSE,
        "ingress_key_id": field_canary_operator_identity_ingress_key_id(secret),
        "request_id": _identifier(
            request_id, "field_canary_operator_challenge_request_invalid"
        ),
        "approval_definition_id": _identifier(
            approval_definition_id,
            "field_canary_operator_challenge_request_invalid",
        ),
        "requested_at": _iso(
            _utc(requested_at, "field_canary_operator_challenge_request_invalid")
        ),
        **_REQUEST_AUTHORITY,
    }
    return MappingProxyType(
        {
            **unsigned,
            "signature": _ingress_signature(
                secret, b"challenge-request", unsigned
            ),
        }
    )


def sign_field_canary_operator_identity_commit_request(
    *,
    request_id: str,
    challenge_id: str,
    attestation: Mapping[str, Any],
    requested_at: datetime,
    ingress_secret: str | bytes,
) -> Mapping[str, Any]:
    """Sign one exact attestation commit request for the dedicated ingress."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    if type(attestation) is not dict:
        try:
            attestation = dict(attestation)
        except (TypeError, ValueError) as exc:
            raise FieldCanaryOperatorSessionAttestationError(
                "field_canary_operator_commit_request_invalid"
            ) from exc
    if attestation.get("challenge_id") != challenge_id:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_commit_request_invalid"
        )
    unsigned = {
        "schema_version": FIELD_CANARY_OPERATOR_COMMIT_REQUEST_VERSION,
        "purpose": FIELD_CANARY_OPERATOR_COMMIT_REQUEST_PURPOSE,
        "ingress_key_id": field_canary_operator_identity_ingress_key_id(secret),
        "request_id": _identifier(
            request_id, "field_canary_operator_commit_request_invalid"
        ),
        "challenge_id": _identifier(
            challenge_id, "field_canary_operator_commit_request_invalid"
        ),
        "requested_at": _iso(
            _utc(requested_at, "field_canary_operator_commit_request_invalid")
        ),
        "attestation": json.loads(_json(attestation)),
        **_REQUEST_AUTHORITY,
    }
    return MappingProxyType(
        {
            **unsigned,
            "signature": _ingress_signature(secret, b"commit-request", unsigned),
        }
    )


def sign_field_canary_operator_approval_request(
    *,
    request_id: str,
    approval_definition_id: str,
    identity_record_id: str,
    identity_record_digest: str,
    requested_at: datetime,
    ingress_secret: str | bytes,
) -> Mapping[str, Any]:
    """Sign one distinct explicit approval publication request."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    unsigned = {
        "schema_version": FIELD_CANARY_OPERATOR_APPROVAL_REQUEST_VERSION,
        "purpose": FIELD_CANARY_OPERATOR_APPROVAL_REQUEST_PURPOSE,
        "ingress_key_id": field_canary_operator_identity_ingress_key_id(secret),
        "request_id": _identifier(
            request_id, "field_canary_operator_approval_request_invalid"
        ),
        "approval_definition_id": _identifier(
            approval_definition_id,
            "field_canary_operator_approval_request_invalid",
        ),
        "identity_record_id": _identifier(
            identity_record_id, "field_canary_operator_approval_request_invalid"
        ),
        "identity_record_digest": _hex(
            identity_record_digest,
            "field_canary_operator_approval_request_invalid",
        ),
        "requested_at": _iso(
            _utc(requested_at, "field_canary_operator_approval_request_invalid")
        ),
        **_APPROVAL_REQUEST_AUTHORITY,
    }
    return MappingProxyType(
        {
            **unsigned,
            "signature": _ingress_signature(secret, b"approval-request", unsigned),
        }
    )


def sign_field_canary_promotion_grant_request(
    *,
    request_id: str,
    grant_definition_id: str,
    materialization_id: str,
    requested_at: datetime,
    ingress_secret: str | bytes,
) -> Mapping[str, Any]:
    """Sign one explicit request to consume approval and persist a Grant."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    unsigned = {
        "schema_version": FIELD_CANARY_PROMOTION_GRANT_REQUEST_VERSION,
        "purpose": FIELD_CANARY_PROMOTION_GRANT_REQUEST_PURPOSE,
        "ingress_key_id": field_canary_operator_identity_ingress_key_id(secret),
        "request_id": _identifier(
            request_id, "field_canary_promotion_grant_request_invalid"
        ),
        "grant_definition_id": _identifier(
            grant_definition_id, "field_canary_promotion_grant_request_invalid"
        ),
        "materialization_id": _identifier(
            materialization_id, "field_canary_promotion_grant_request_invalid"
        ),
        "requested_at": _iso(
            _utc(requested_at, "field_canary_promotion_grant_request_invalid")
        ),
        **_GRANT_REQUEST_AUTHORITY,
    }
    return MappingProxyType(
        {
            **unsigned,
            "signature": _ingress_signature(
                secret, b"promotion-grant-request", unsigned
            ),
        }
    )


def sign_field_canary_promotion_grant_revocation_request(
    *,
    request_id: str,
    grant_id: str,
    grant_digest: str,
    operator_identity_record_id: str,
    operator_identity_record_digest: str,
    requested_at: datetime,
    ingress_secret: str | bytes,
) -> Mapping[str, Any]:
    """Sign an exact deny-only request to revoke one durable Grant."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    unsigned = {
        "schema_version": FIELD_CANARY_PROMOTION_GRANT_REVOCATION_REQUEST_VERSION,
        "purpose": FIELD_CANARY_PROMOTION_GRANT_REVOCATION_REQUEST_PURPOSE,
        "ingress_key_id": field_canary_operator_identity_ingress_key_id(secret),
        "request_id": _identifier(
            request_id, "field_canary_promotion_grant_revocation_request_invalid"
        ),
        "grant_id": _identifier(
            grant_id, "field_canary_promotion_grant_revocation_request_invalid"
        ),
        "grant_digest": _hex(
            grant_digest, "field_canary_promotion_grant_revocation_request_invalid"
        ),
        "operator_identity_record_id": _identifier(
            operator_identity_record_id,
            "field_canary_promotion_grant_revocation_request_invalid",
        ),
        "operator_identity_record_digest": _hex(
            operator_identity_record_digest,
            "field_canary_promotion_grant_revocation_request_invalid",
        ),
        "reason_code": "operator_revoked",
        "requested_at": _iso(
            _utc(
                requested_at,
                "field_canary_promotion_grant_revocation_request_invalid",
            )
        ),
        **_GRANT_REVOCATION_REQUEST_AUTHORITY,
    }
    return MappingProxyType(
        {
            **unsigned,
            "signature": _ingress_signature(
                secret, b"promotion-grant-revocation-request", unsigned
            ),
        }
    )


def sign_field_canary_promotion_grant_operator_revocation_request(
    *,
    request_id: str,
    revocation_definition_id: str,
    approval_record_id: str,
    approval_record_digest: str,
    requested_at: datetime,
    ingress_secret: str | bytes,
) -> Mapping[str, Any]:
    """Sign an approval-bound current-session Grant revocation request."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    unsigned = {
        "schema_version": FIELD_CANARY_PROMOTION_GRANT_OPERATOR_REVOCATION_REQUEST_VERSION,
        "purpose": FIELD_CANARY_PROMOTION_GRANT_OPERATOR_REVOCATION_REQUEST_PURPOSE,
        "ingress_key_id": field_canary_operator_identity_ingress_key_id(secret),
        "request_id": _identifier(
            request_id,
            "field_canary_promotion_grant_operator_revocation_request_invalid",
        ),
        "revocation_definition_id": _identifier(
            revocation_definition_id,
            "field_canary_promotion_grant_operator_revocation_request_invalid",
        ),
        "approval_record_id": _identifier(
            approval_record_id,
            "field_canary_promotion_grant_operator_revocation_request_invalid",
        ),
        "approval_record_digest": _hex(
            approval_record_digest,
            "field_canary_promotion_grant_operator_revocation_request_invalid",
        ),
        "requested_at": _iso(
            _utc(
                requested_at,
                "field_canary_promotion_grant_operator_revocation_request_invalid",
            )
        ),
        **_GRANT_OPERATOR_REVOCATION_REQUEST_AUTHORITY,
    }
    return MappingProxyType(
        {
            **unsigned,
            "signature": _ingress_signature(
                secret,
                b"promotion-grant-operator-revocation-request",
                unsigned,
            ),
        }
    )


def sign_field_canary_promotion_grant_revocation_proposal_request(
    *,
    request_id: str,
    grant_id: str,
    requested_at: datetime,
    ingress_secret: str | bytes,
) -> Mapping[str, Any]:
    """Sign a prepare-only request for a server-derived revocation proposal."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    unsigned = {
        "schema_version": (
            FIELD_CANARY_PROMOTION_GRANT_REVOCATION_PROPOSAL_REQUEST_VERSION
        ),
        "purpose": (
            FIELD_CANARY_PROMOTION_GRANT_REVOCATION_PROPOSAL_REQUEST_PURPOSE
        ),
        "ingress_key_id": field_canary_operator_identity_ingress_key_id(secret),
        "request_id": _identifier(
            request_id,
            "field_canary_promotion_grant_revocation_proposal_request_invalid",
        ),
        "grant_id": _identifier(
            grant_id,
            "field_canary_promotion_grant_revocation_proposal_request_invalid",
        ),
        "requested_at": _iso(
            _utc(
                requested_at,
                "field_canary_promotion_grant_revocation_proposal_request_invalid",
            )
        ),
        **_GRANT_REVOCATION_PROPOSAL_AUTHORITY,
    }
    return MappingProxyType(
        {
            **unsigned,
            "signature": _ingress_signature(
                secret,
                b"promotion-grant-revocation-proposal-request",
                unsigned,
            ),
        }
    )


def verify_field_canary_operator_identity_commit_response(
    response: Mapping[str, Any],
    *,
    ingress_secret: str | bytes,
    expected_request_id: str,
    expected_challenge_id: str,
    expected_approval_definition_id: str,
    expected_identity_record_id: str,
) -> Mapping[str, Any]:
    """Verify the add-on's signed durable-identity acknowledgement."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    if type(response) is not dict:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_commit_response_invalid"
        )
    row = json.loads(_json(response))
    expected_fields = frozenset(
        {
            "schema_version",
            "purpose",
            "ingress_key_id",
            "request_id",
            "disposition",
            "challenge_id",
            "approval_definition_id",
            "identity_record_id",
            "identity_record_digest",
            "valid_until",
            *_COMMIT_RESPONSE_AUTHORITY,
            "signature",
        }
    )
    if frozenset(row) != expected_fields:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_commit_response_invalid"
        )
    signature = row.pop("signature")
    if (
        type(signature) is not str
        or not hmac.compare_digest(
            signature,
            _ingress_signature(secret, b"commit-response", row),
        )
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_commit_response_signature_invalid"
        )
    if (
        row["schema_version"] != FIELD_CANARY_OPERATOR_COMMIT_RESPONSE_VERSION
        or row["purpose"] != FIELD_CANARY_OPERATOR_COMMIT_RESPONSE_PURPOSE
        or row["ingress_key_id"]
        != field_canary_operator_identity_ingress_key_id(secret)
        or row["disposition"] != "identity_committed_or_replayed"
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_commit_response_invalid"
        )
    for name, expected in (
        ("request_id", expected_request_id),
        ("challenge_id", expected_challenge_id),
        ("approval_definition_id", expected_approval_definition_id),
        ("identity_record_id", expected_identity_record_id),
    ):
        if row.get(name) != expected:
            raise FieldCanaryOperatorSessionAttestationError(
                "field_canary_operator_commit_response_binding_invalid"
            )
    _hex(
        row["identity_record_digest"],
        "field_canary_operator_commit_response_invalid",
    )
    _utc(row["valid_until"], "field_canary_operator_commit_response_invalid")
    if any(
        type(row.get(name)) is not type(expected) or row.get(name) != expected
        for name, expected in _COMMIT_RESPONSE_AUTHORITY.items()
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_commit_response_authority_invalid"
        )
    return MappingProxyType({**row, "signature": signature})


def verify_field_canary_operator_approval_response(
    response: Mapping[str, Any],
    *,
    ingress_secret: str | bytes,
    expected_request_id: str,
    expected_approval_definition_id: str,
    expected_identity_record_id: str,
    expected_identity_record_digest: str,
) -> Mapping[str, Any]:
    """Verify a durable approval acknowledgement and its exact identity bind."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    if type(response) is not dict:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_approval_response_invalid"
        )
    row = json.loads(_json(response))
    expected_fields = frozenset(
        {
            "schema_version",
            "purpose",
            "ingress_key_id",
            "request_id",
            "disposition",
            "approval_definition_id",
            "approval_class",
            "subject_id",
            "subject_digest",
            "identity_record_id",
            "identity_record_digest",
            "approval_record_id",
            "approval_record_digest",
            "valid_until",
            *_APPROVAL_RESPONSE_AUTHORITY,
            "signature",
        }
    )
    if frozenset(row) != expected_fields:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_approval_response_invalid"
        )
    signature = row.pop("signature")
    if (
        type(signature) is not str
        or not hmac.compare_digest(
            signature,
            _ingress_signature(secret, b"approval-response", row),
        )
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_approval_response_signature_invalid"
        )
    if (
        row["schema_version"] != FIELD_CANARY_OPERATOR_APPROVAL_RESPONSE_VERSION
        or row["purpose"] != FIELD_CANARY_OPERATOR_APPROVAL_RESPONSE_PURPOSE
        or row["ingress_key_id"]
        != field_canary_operator_identity_ingress_key_id(secret)
        or row["disposition"] != "approval_committed_or_replayed"
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_approval_response_invalid"
        )
    for name, expected in (
        ("request_id", expected_request_id),
        ("approval_definition_id", expected_approval_definition_id),
        ("identity_record_id", expected_identity_record_id),
        ("identity_record_digest", expected_identity_record_digest),
    ):
        if row.get(name) != expected:
            raise FieldCanaryOperatorSessionAttestationError(
                "field_canary_operator_approval_response_binding_invalid"
            )
    for name in (
        "approval_class",
        "subject_id",
        "approval_record_id",
    ):
        _identifier(row.get(name), "field_canary_operator_approval_response_invalid")
    for name in ("subject_digest", "identity_record_digest", "approval_record_digest"):
        _hex(row.get(name), "field_canary_operator_approval_response_invalid")
    _utc(row.get("valid_until"), "field_canary_operator_approval_response_invalid")
    if any(
        type(row.get(name)) is not type(expected) or row.get(name) != expected
        for name, expected in _APPROVAL_RESPONSE_AUTHORITY.items()
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_approval_response_authority_invalid"
        )
    return MappingProxyType({**row, "signature": signature})


def verify_field_canary_promotion_grant_response(
    response: Mapping[str, Any],
    *,
    ingress_secret: str | bytes,
    expected_request_id: str,
    expected_grant_definition_id: str,
    expected_materialization_id: str,
    expected_approval_record_id: str,
) -> Mapping[str, Any]:
    """Verify a durable Grant acknowledgement and all zero-execution flags."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    if type(response) is not dict:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_response_invalid"
        )
    row = json.loads(_json(response))
    expected_fields = frozenset(
        {
            "schema_version",
            "purpose",
            "ingress_key_id",
            "request_id",
            "disposition",
            "grant_definition_id",
            "grant_id",
            "grant_digest",
            "materialization_id",
            "materialization_record_digest",
            "exact_target_set_digest",
            "target_count",
            "max_dispatch_count",
            "approval_record_id",
            "approval_record_digest",
            "approval_consumption_id",
            "approval_consumption_digest",
            "valid_until",
            "field_authority",
            *_GRANT_RESPONSE_AUTHORITY,
            "signature",
        }
    )
    if frozenset(row) != expected_fields:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_response_invalid"
        )
    signature = row.pop("signature")
    if (
        type(signature) is not str
        or not hmac.compare_digest(
            signature,
            _ingress_signature(secret, b"promotion-grant-response", row),
        )
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_response_signature_invalid"
        )
    if (
        row["schema_version"] != FIELD_CANARY_PROMOTION_GRANT_RESPONSE_VERSION
        or row["purpose"] != FIELD_CANARY_PROMOTION_GRANT_RESPONSE_PURPOSE
        or row["ingress_key_id"]
        != field_canary_operator_identity_ingress_key_id(secret)
        or row["disposition"] != "promotion_grant_committed_or_replayed"
        or row["field_authority"] != "operator_approved_exact_canary"
        or type(row["target_count"]) is not int
        or row["target_count"] < 1
        or type(row["max_dispatch_count"]) is not int
        or row["max_dispatch_count"] != 1
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_response_invalid"
        )
    for name, expected in (
        ("request_id", expected_request_id),
        ("grant_definition_id", expected_grant_definition_id),
        ("materialization_id", expected_materialization_id),
        ("approval_record_id", expected_approval_record_id),
    ):
        if row.get(name) != expected:
            raise FieldCanaryOperatorSessionAttestationError(
                "field_canary_promotion_grant_response_binding_invalid"
            )
    for name in (
        "grant_id",
        "materialization_id",
        "approval_record_id",
        "approval_consumption_id",
    ):
        _identifier(row.get(name), "field_canary_promotion_grant_response_invalid")
    for name in (
        "grant_digest",
        "materialization_record_digest",
        "exact_target_set_digest",
        "approval_record_digest",
        "approval_consumption_digest",
    ):
        _hex(row.get(name), "field_canary_promotion_grant_response_invalid")
    _utc(row.get("valid_until"), "field_canary_promotion_grant_response_invalid")
    if any(
        type(row.get(name)) is not type(expected) or row.get(name) != expected
        for name, expected in _GRANT_RESPONSE_AUTHORITY.items()
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_response_authority_invalid"
        )
    return MappingProxyType({**row, "signature": signature})


def verify_field_canary_promotion_grant_revocation_response(
    response: Mapping[str, Any],
    *,
    ingress_secret: str | bytes,
    expected_request_id: str,
    expected_grant_id: str,
    expected_grant_digest: str,
    expected_operator_identity_record_id: str,
    expected_operator_identity_record_digest: str,
) -> Mapping[str, Any]:
    """Verify an exact, durable, deny-only Grant revocation acknowledgement."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    if type(response) is not dict:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_response_invalid"
        )
    row = json.loads(_json(response))
    expected_fields = frozenset(
        {
            "schema_version",
            "purpose",
            "ingress_key_id",
            "request_id",
            "disposition",
            "grant_id",
            "grant_digest",
            "operator_identity_record_id",
            "operator_identity_record_digest",
            "revocation_id",
            "revocation_digest",
            "reason_code",
            "revoked_at",
            "promotion_grant_state",
            *_GRANT_REVOCATION_RESPONSE_AUTHORITY,
            "signature",
        }
    )
    if frozenset(row) != expected_fields:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_response_invalid"
        )
    signature = row.pop("signature")
    if (
        type(signature) is not str
        or not hmac.compare_digest(
            signature,
            _ingress_signature(
                secret, b"promotion-grant-revocation-response", row
            ),
        )
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_response_signature_invalid"
        )
    if (
        row["schema_version"]
        != FIELD_CANARY_PROMOTION_GRANT_REVOCATION_RESPONSE_VERSION
        or row["purpose"] != FIELD_CANARY_PROMOTION_GRANT_REVOCATION_RESPONSE_PURPOSE
        or row["ingress_key_id"]
        != field_canary_operator_identity_ingress_key_id(secret)
        or row["disposition"] != "promotion_grant_revoked_or_replayed"
        or row["reason_code"] != "operator_revoked"
        or row["promotion_grant_state"] != "revoked"
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_response_invalid"
        )
    for name, expected in (
        ("request_id", expected_request_id),
        ("grant_id", expected_grant_id),
        ("grant_digest", expected_grant_digest),
        ("operator_identity_record_id", expected_operator_identity_record_id),
        (
            "operator_identity_record_digest",
            expected_operator_identity_record_digest,
        ),
    ):
        if row.get(name) != expected:
            raise FieldCanaryOperatorSessionAttestationError(
                "field_canary_promotion_grant_revocation_response_binding_invalid"
            )
    for name in ("grant_id", "operator_identity_record_id", "revocation_id"):
        _identifier(
            row.get(name), "field_canary_promotion_grant_revocation_response_invalid"
        )
    for name in (
        "grant_digest",
        "operator_identity_record_digest",
        "revocation_digest",
    ):
        _hex(
            row.get(name), "field_canary_promotion_grant_revocation_response_invalid"
        )
    _utc(row.get("revoked_at"), "field_canary_promotion_grant_revocation_response_invalid")
    if any(
        type(row.get(name)) is not type(expected) or row.get(name) != expected
        for name, expected in _GRANT_REVOCATION_RESPONSE_AUTHORITY.items()
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_response_authority_invalid"
        )
    return MappingProxyType({**row, "signature": signature})


def verify_field_canary_promotion_grant_operator_revocation_response(
    response: Mapping[str, Any],
    *,
    ingress_secret: str | bytes,
    expected_request_id: str,
    expected_revocation_definition_id: str,
    expected_proposal_id: str,
    expected_proposal_digest: str,
    expected_grant_id: str,
    expected_grant_digest: str,
    expected_approval_record_id: str,
    expected_approval_record_digest: str,
) -> Mapping[str, Any]:
    """Verify the atomic current-session operator revocation acknowledgement."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    if type(response) is not dict:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_operator_revocation_response_invalid"
        )
    row = json.loads(_json(response))
    identity_fields = {
        "receipt_id",
        "revocation_definition_id",
        "proposal_id",
        "grant_id",
        "grant_origin_identity_record_id",
        "approval_record_id",
        "approval_consumption_id",
        "revoker_identity_record_id",
        "generic_revocation_id",
    }
    digest_fields = {
        "receipt_digest",
        "revocation_definition_digest",
        "proposal_digest",
        "grant_digest",
        "grant_origin_identity_record_digest",
        "approval_record_digest",
        "approval_consumption_digest",
        "revoker_identity_record_digest",
        "generic_revocation_digest",
    }
    expected_fields = frozenset(
        {
            "schema_version",
            "purpose",
            "ingress_key_id",
            "request_id",
            "disposition",
            *identity_fields,
            *digest_fields,
            "reason_code",
            "revoked_at",
            *_GRANT_OPERATOR_REVOCATION_RESPONSE_AUTHORITY,
            "signature",
        }
    )
    if frozenset(row) != expected_fields:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_operator_revocation_response_invalid"
        )
    signature = row.pop("signature")
    if (
        type(signature) is not str
        or not hmac.compare_digest(
            signature,
            _ingress_signature(
                secret,
                b"promotion-grant-operator-revocation-response",
                row,
            ),
        )
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_operator_revocation_response_signature_invalid"
        )
    if (
        row.get("schema_version")
        != FIELD_CANARY_PROMOTION_GRANT_OPERATOR_REVOCATION_RESPONSE_VERSION
        or row.get("purpose")
        != FIELD_CANARY_PROMOTION_GRANT_OPERATOR_REVOCATION_RESPONSE_PURPOSE
        or row.get("ingress_key_id")
        != field_canary_operator_identity_ingress_key_id(secret)
        or row.get("disposition")
        != "promotion_grant_operator_revoked_or_replayed"
        or row.get("reason_code") != "operator_revoked"
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_operator_revocation_response_invalid"
        )
    for name, expected in (
        ("request_id", expected_request_id),
        ("revocation_definition_id", expected_revocation_definition_id),
        ("proposal_id", expected_proposal_id),
        ("proposal_digest", expected_proposal_digest),
        ("grant_id", expected_grant_id),
        ("grant_digest", expected_grant_digest),
        ("approval_record_id", expected_approval_record_id),
        ("approval_record_digest", expected_approval_record_digest),
    ):
        if row.get(name) != expected:
            raise FieldCanaryOperatorSessionAttestationError(
                "field_canary_promotion_grant_operator_revocation_response_binding_invalid"
            )
    for name in identity_fields:
        _identifier(
            row.get(name),
            "field_canary_promotion_grant_operator_revocation_response_invalid",
        )
    for name in digest_fields:
        _hex(
            row.get(name),
            "field_canary_promotion_grant_operator_revocation_response_invalid",
        )
    _utc(
        row.get("revoked_at"),
        "field_canary_promotion_grant_operator_revocation_response_invalid",
    )
    if any(
        type(row.get(name)) is not type(expected) or row.get(name) != expected
        for name, expected in _GRANT_OPERATOR_REVOCATION_RESPONSE_AUTHORITY.items()
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_operator_revocation_response_authority_invalid"
        )
    return MappingProxyType({**row, "signature": signature})


def verify_field_canary_promotion_grant_revocation_proposal_response(
    response: Mapping[str, Any],
    *,
    ingress_secret: str | bytes,
    expected_request_id: str,
    expected_grant_id: str,
) -> Mapping[str, Any]:
    """Verify one prepare-only proposal receipt without granting revoke authority."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    if type(response) is not dict:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_proposal_response_invalid"
        )
    row = json.loads(_json(response))
    expected_fields = frozenset(
        {
            "schema_version",
            "purpose",
            "ingress_key_id",
            "request_id",
            "disposition",
            "proposal_id",
            "proposal_digest",
            "grant_id",
            "grant_digest",
            "revocation_definition_id",
            "approval_definition_id",
            "approval_class",
            "approval_subject_digest",
            "reason_code",
            "valid_until",
            *_GRANT_REVOCATION_PROPOSAL_AUTHORITY,
            "signature",
        }
    )
    if frozenset(row) != expected_fields:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_proposal_response_invalid"
        )
    signature = row.pop("signature")
    if (
        type(signature) is not str
        or not hmac.compare_digest(
            signature,
            _ingress_signature(
                secret,
                b"promotion-grant-revocation-proposal-response",
                row,
            ),
        )
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_proposal_response_signature_invalid"
        )
    if (
        row.get("schema_version")
        != FIELD_CANARY_PROMOTION_GRANT_REVOCATION_PROPOSAL_RESPONSE_VERSION
        or row.get("purpose")
        != FIELD_CANARY_PROMOTION_GRANT_REVOCATION_PROPOSAL_RESPONSE_PURPOSE
        or row.get("ingress_key_id")
        != field_canary_operator_identity_ingress_key_id(secret)
        or row.get("request_id") != expected_request_id
        or row.get("grant_id") != expected_grant_id
        or row.get("disposition")
        != "revocation_proposal_committed_or_replayed"
        or row.get("approval_class") != "promotion_grant_revocation"
        or row.get("reason_code") != "operator_revoked"
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_proposal_response_binding_invalid"
        )
    for name in (
        "proposal_id",
        "grant_id",
        "revocation_definition_id",
        "approval_definition_id",
    ):
        _identifier(
            row.get(name),
            "field_canary_promotion_grant_revocation_proposal_response_invalid",
        )
    for name in (
        "proposal_digest",
        "grant_digest",
        "approval_subject_digest",
    ):
        _hex(
            row.get(name),
            "field_canary_promotion_grant_revocation_proposal_response_invalid",
        )
    _utc(
        row.get("valid_until"),
        "field_canary_promotion_grant_revocation_proposal_response_invalid",
    )
    if any(
        type(row.get(name)) is not type(expected)
        or row.get(name) != expected
        for name, expected in _GRANT_REVOCATION_PROPOSAL_AUTHORITY.items()
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_promotion_grant_revocation_proposal_response_authority_invalid"
        )
    return MappingProxyType({**row, "signature": signature})


def sign_field_canary_operator_identity_challenge_response(
    *,
    request_id: str,
    challenge: Mapping[str, Any],
    ha_installation_digest: str,
    bridge_config_entry_id: str,
    ingress_secret: str | bytes,
) -> Mapping[str, Any]:
    """Pure add-on-side response signer used by the future dedicated ingress."""

    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    if type(challenge) is not dict:
        try:
            challenge = dict(challenge)
        except (TypeError, ValueError) as exc:
            raise FieldCanaryOperatorSessionAttestationError(
                "field_canary_operator_challenge_invalid"
            ) from exc
    nonce = _hex(challenge.get("request_nonce"), "field_canary_operator_challenge_invalid")
    if hashlib.sha256(nonce.encode("ascii")).hexdigest() != _hex(
        challenge.get("request_nonce_digest"),
        "field_canary_operator_challenge_invalid",
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_nonce_invalid"
        )
    approval_class = _identifier(
        challenge.get("approval_class"), "field_canary_operator_challenge_invalid"
    )
    if approval_class not in _APPROVAL_CLASSES:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_class_invalid"
        )
    unsigned = {
        "schema_version": FIELD_CANARY_OPERATOR_CHALLENGE_RESPONSE_VERSION,
        "purpose": FIELD_CANARY_OPERATOR_CHALLENGE_RESPONSE_PURPOSE,
        "ingress_key_id": field_canary_operator_identity_ingress_key_id(secret),
        "request_id": _identifier(request_id, "field_canary_operator_request_id_invalid"),
        "challenge_id": _identifier(
            challenge.get("challenge_id"), "field_canary_operator_challenge_invalid"
        ),
        "approval_definition_id": _identifier(
            challenge.get("approval_definition_id"),
            "field_canary_operator_challenge_invalid",
        ),
        "approval_class": approval_class,
        "subject_id": _identifier(
            challenge.get("subject_id"), "field_canary_operator_challenge_invalid"
        ),
        "subject_digest": _hex(
            challenge.get("subject_digest"), "field_canary_operator_challenge_invalid"
        ),
        "request_nonce": nonce,
        "request_nonce_digest": challenge["request_nonce_digest"],
        "expected_attestation_key_id": _identifier(
            challenge.get("expected_attestation_key_id"),
            "field_canary_operator_challenge_invalid",
        ),
        "ha_installation_digest": _hex(
            ha_installation_digest,
            "field_canary_operator_installation_digest_invalid",
        ),
        "bridge_config_entry_id": _identifier(
            bridge_config_entry_id, "field_canary_operator_entry_id_invalid"
        ),
        "issued_at": _iso(
            _utc(challenge.get("issued_at"), "field_canary_operator_challenge_invalid")
        ),
        "expires_at": _iso(
            _utc(challenge.get("expires_at"), "field_canary_operator_challenge_invalid")
        ),
        **_CHALLENGE_AUTHORITY,
    }
    return MappingProxyType(
        {**unsigned, "signature": _challenge_signature(secret, unsigned)}
    )


def verify_field_canary_operator_identity_challenge_response(
    value: Any,
    *,
    ingress_secret: str | bytes,
    expected_request_id: str,
    expected_approval_definition_id: str,
    expected_ha_installation_digest: str,
    expected_bridge_config_entry_id: str,
    expected_attestation_key_id: str,
    evaluated_at: datetime,
) -> VerifiedFieldCanaryOperatorIdentityChallenge:
    """Verify and detach one exact add-on challenge response."""

    if type(value) is not dict:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_schema_invalid"
        )
    row = json.loads(_json(value))
    if type(row) is not dict or frozenset(row) != _CHALLENGE_FIELDS:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_schema_invalid"
        )
    secret = _secret(ingress_secret, "field_canary_operator_ingress_secret_invalid")
    signature = row.pop("signature")
    if (
        type(signature) is not str
        or not hmac.compare_digest(signature, _challenge_signature(secret, row))
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_signature_invalid"
        )
    if (
        row["schema_version"] != FIELD_CANARY_OPERATOR_CHALLENGE_RESPONSE_VERSION
        or row["purpose"] != FIELD_CANARY_OPERATOR_CHALLENGE_RESPONSE_PURPOSE
        or row["ingress_key_id"]
        != field_canary_operator_identity_ingress_key_id(secret)
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_contract_invalid"
        )
    _identifier(row["request_id"], "field_canary_operator_challenge_identity_invalid")
    _identifier(row["challenge_id"], "field_canary_operator_challenge_identity_invalid")
    _identifier(
        row["approval_definition_id"],
        "field_canary_operator_challenge_identity_invalid",
    )
    approval_class = _identifier(
        row["approval_class"], "field_canary_operator_challenge_identity_invalid"
    )
    if approval_class not in _APPROVAL_CLASSES:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_class_invalid"
        )
    _identifier(row["subject_id"], "field_canary_operator_challenge_identity_invalid")
    _hex(row["subject_digest"], "field_canary_operator_challenge_digest_invalid")
    _identifier(
        row["expected_attestation_key_id"],
        "field_canary_operator_challenge_identity_invalid",
    )
    _hex(
        row["ha_installation_digest"],
        "field_canary_operator_challenge_digest_invalid",
    )
    _identifier(
        row["bridge_config_entry_id"],
        "field_canary_operator_challenge_identity_invalid",
    )
    for name, expected in (
        ("request_id", expected_request_id),
        ("approval_definition_id", expected_approval_definition_id),
        ("ha_installation_digest", expected_ha_installation_digest),
        ("bridge_config_entry_id", expected_bridge_config_entry_id),
        ("expected_attestation_key_id", expected_attestation_key_id),
    ):
        if row.get(name) != expected:
            raise FieldCanaryOperatorSessionAttestationError(
                "field_canary_operator_challenge_pin_mismatch"
            )
    if any(
        type(row.get(name)) is not type(expected) or row.get(name) != expected
        for name, expected in _CHALLENGE_AUTHORITY.items()
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_authority_invalid"
        )
    nonce = _hex(row["request_nonce"], "field_canary_operator_challenge_nonce_invalid")
    if hashlib.sha256(nonce.encode("ascii")).hexdigest() != _hex(
        row["request_nonce_digest"], "field_canary_operator_challenge_nonce_invalid"
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_nonce_invalid"
        )
    now = _utc(evaluated_at, "field_canary_operator_challenge_time_invalid")
    issued = _utc(row["issued_at"], "field_canary_operator_challenge_time_invalid")
    expires = _utc(row["expires_at"], "field_canary_operator_challenge_time_invalid")
    if (
        (issued - now).total_seconds() > MAX_OPERATOR_IDENTITY_CLOCK_SKEW_SECONDS
        or now >= expires
        or expires <= issued
        or (expires - issued).total_seconds() > MAX_OPERATOR_IDENTITY_WINDOW_SECONDS
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_not_live"
        )
    detached = MappingProxyType({**row, "signature": signature})
    return VerifiedFieldCanaryOperatorIdentityChallenge(detached, _FACTORY_TOKEN)


def _pseudonymous_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


async def async_attest_current_ha_admin_session(
    hass: Any,
    connection: Any,
    *,
    challenge: VerifiedFieldCanaryOperatorIdentityChallenge,
    attestation_secret: str | bytes,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Mapping[str, Any]:
    """Bind the verified challenge to the exact current HA WebSocket session."""

    if type(challenge) is not VerifiedFieldCanaryOperatorIdentityChallenge:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_challenge_factory_required"
        )
    facts = dict(challenge.projection)
    user = getattr(connection, "user", None)
    refresh_token_id = getattr(connection, "refresh_token_id", None)
    if (
        user is None
        or getattr(user, "is_active", None) is not True
        or getattr(user, "is_admin", None) is not True
        or getattr(user, "system_generated", None) is not False
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_current_admin_required"
        )
    user_id = _identifier(
        getattr(user, "id", None), "field_canary_operator_user_id_invalid"
    )
    token_id = _identifier(
        refresh_token_id, "field_canary_operator_refresh_token_required"
    )
    auth = getattr(hass, "auth", None)
    get_token = getattr(auth, "async_get_refresh_token", None)
    if not callable(get_token):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_auth_store_unavailable"
        )
    token = get_token(token_id)
    if token is None or getattr(token, "id", None) != token_id:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_refresh_token_not_live"
        )
    if getattr(token, "user", None) is not user:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_session_user_mismatch"
        )
    if getattr(token, "token_type", None) != "normal":
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_interactive_session_required"
        )
    now = _utc(clock(), "field_canary_operator_session_clock_invalid")
    created = _utc(
        getattr(token, "created_at", None),
        "field_canary_operator_refresh_token_time_invalid",
    )
    if (created - now).total_seconds() > MAX_OPERATOR_IDENTITY_CLOCK_SKEW_SECONDS:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_refresh_token_time_invalid"
        )
    expire_at = getattr(token, "expire_at", None)
    if type(expire_at) not in {int, float} or not math.isfinite(float(expire_at)):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_refresh_token_expiry_invalid"
        )
    try:
        now_timestamp = now.timestamp()
        token_expires = datetime.fromtimestamp(float(expire_at), tz=UTC)
    except (OSError, OverflowError, ValueError) as exc:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_refresh_token_expiry_invalid"
        ) from exc
    if not float(expire_at) > now_timestamp:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_refresh_token_not_live"
        )
    challenge_expires = _utc(
        facts["expires_at"], "field_canary_operator_challenge_time_invalid"
    )
    valid_until = min(
        challenge_expires,
        token_expires,
        now + timedelta(seconds=MAX_OPERATOR_IDENTITY_WINDOW_SECONDS),
    )
    if valid_until <= now:
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_session_not_live"
        )
    secret = _secret(
        attestation_secret, "field_canary_operator_identity_secret_invalid"
    )
    if facts["expected_attestation_key_id"] != field_canary_operator_identity_attestation_key_id(
        secret
    ):
        raise FieldCanaryOperatorSessionAttestationError(
            "field_canary_operator_attestation_key_mismatch"
        )
    installation = facts["ha_installation_digest"]
    entry_id = facts["bridge_config_entry_id"]
    base = {
        "schema_version": FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_VERSION,
        "challenge_id": facts["challenge_id"],
        "challenge_nonce_digest": facts["request_nonce_digest"],
        "approval_definition_id": facts["approval_definition_id"],
        "approval_class": facts["approval_class"],
        "subject_id": facts["subject_id"],
        "subject_digest": facts["subject_digest"],
        "operator_principal_id": _pseudonymous_id(
            "ha-user", installation, user_id
        ),
        "operator_authority_ref": _pseudonymous_id(
            "ha-auth-session", installation, entry_id, user_id, token_id
        ),
        "ha_installation_digest": installation,
        "bridge_config_entry_id": entry_id,
        "session_id": _pseudonymous_id("ha-session", installation, token_id),
        "authentication_method": "ha_auth_session",
        "is_admin": True,
        "is_active": True,
        "issued_at": _iso(now),
        "valid_until": _iso(valid_until),
        "attestation_key_id": facts["expected_attestation_key_id"],
        **_AUTHORITY,
    }
    attestation_id = "fcoia_" + _digest(base)
    unsigned = {**base, "attestation_id": attestation_id}
    return MappingProxyType(
        {**unsigned, "signature": _attestation_signature(secret, unsigned)}
    )


__all__: list[str] = []
