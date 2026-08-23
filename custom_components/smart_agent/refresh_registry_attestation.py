"""Issue a short-lived host attestation for one detached registry snapshot.

The secret is deliberately separate from the add-on bearer token.  This pure
module performs no transport, persistence, catalog write, refresh, or device
operation.  Durable replay consumption belongs to the future catalog writer.
"""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import hmac
import json
import re
from typing import Any


ATTESTATION_SCHEMA_VERSION = "smartagent.ha_refresh_registry_attestation.v0.1"
ATTESTATION_PURPOSE = "observation_refresh_registry_snapshot"
ATTESTATION_ISSUER = "smartagent_ha_registry_snapshot_host_v0.1"
ATTESTATION_MAX_TTL_SECONDS = 300
ATTESTATION_CLOCK_SKEW_SECONDS = 15
SNAPSHOT_SCHEMA_VERSION = "smartagent.ha_refresh_registry_snapshot.v0.1"
_KEY_DERIVATION_CONTEXT = b"smartagent/observation-refresh-registry-attestation/v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:@/-]+$")
_SNAPSHOT_AUTHORITY_FIELDS = {
    "source_attestation_state": "not_materialized",
    "catalog_write_authorized": False,
    "refresh_dispatch_authorized": False,
    "execution_eligible": False,
    "device_effect_authority": "none",
}
_EXPECTED_SNAPSHOT_FIELDS = frozenset(
    {
        "schema_version",
        "ha_installation_digest",
        "bridge_config_entry_id",
        "request_nonce",
        "source_seq",
        "captured_at",
        "expires_at",
        "coverage_completeness",
        "registry_revision",
        "config_entry_count",
        "device_count",
        "entity_count",
        "quarantined_identity_count",
        "config_entries",
        "devices",
        "entities",
        "source_attestation_state",
        "catalog_write_authorized",
        "refresh_dispatch_authorized",
        "execution_eligible",
        "device_effect_authority",
        "snapshot_id",
        "snapshot_digest",
    }
)
_CONFIG_ENTRY_FIELDS = frozenset(
    {
        "entry_id",
        "domain",
        "state",
        "disabled_by",
        "version",
        "minor_version",
        "config_subentry_ids",
        "registry_identity_complete",
        "quarantine_reasons",
    }
)
_DEVICE_FIELDS = frozenset(
    {
        "device_id",
        "config_entry_ids",
        "config_subentry_ids_by_entry",
        "disabled_by",
        "identity_digest",
        "registry_identity_complete",
        "quarantine_reasons",
    }
)
_ENTITY_FIELDS = frozenset(
    {
        "registry_entry_id",
        "entity_id",
        "domain",
        "platform",
        "unique_id_digest",
        "config_entry_id",
        "config_subentry_id",
        "device_id",
        "disabled_by",
        "device_class",
        "original_device_class",
        "unit_of_measurement",
        "registry_identity_complete",
        "quarantine_reasons",
        "adapter_inference_authorized",
    }
)
_ENTITY_ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")


class RefreshRegistryAttestationError(ValueError):
    """Raised when an attestation cannot be issued without ambiguity."""


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
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_projection_invalid"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def attestation_envelope_digest(value: Any) -> str:
    """Return the canonical digest used to bind an issued envelope to a receipt."""

    if type(value) is not dict:
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_envelope_invalid"
        )
    return _digest(value)


def _identity_digest(namespace: str, *values: str) -> str:
    return hashlib.sha256("\0".join((namespace, *values)).encode("utf-8")).hexdigest()


def _identity(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 255
        or not _SAFE_ID_RE.fullmatch(value)
    ):
        raise RefreshRegistryAttestationError(f"{field_name}_invalid")
    return value


def _utc(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, bool) or not isinstance(value, (datetime, str)):
        raise RefreshRegistryAttestationError(f"{field_name}_invalid")
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("timezone_required")
        return parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RefreshRegistryAttestationError(f"{field_name}_invalid") from exc


def _derived_key(secret: str) -> bytes:
    if type(secret) is not str or len(secret.encode("utf-8")) < 32:
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_secret_unavailable"
        )
    return hmac.new(
        secret.encode("utf-8"),
        _KEY_DERIVATION_CONTEXT,
        hashlib.sha256,
    ).digest()


def attestation_key_id(secret: str) -> str:
    return hashlib.sha256(_derived_key(secret)).hexdigest()[:16]


def _string(value: Any, field_name: str, *, allow_empty: bool = True) -> str:
    if (
        type(value) is not str
        or value != value.strip()
        or len(value) > 255
        or (not allow_empty and not value)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise RefreshRegistryAttestationError(f"{field_name}_invalid")
    return value


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        raise RefreshRegistryAttestationError(f"{field_name}_invalid")
    if value != sorted(set(value)) or any(
        not item or item != item.strip() or not _SAFE_ID_RE.fullmatch(item)
        for item in value
    ):
        raise RefreshRegistryAttestationError(f"{field_name}_invalid")
    return value


def _validate_registry_rows(detached: dict[str, Any]) -> None:
    config_by_id: dict[str, dict[str, Any]] = {}
    for row in detached["config_entries"]:
        if not isinstance(row, dict) or frozenset(row) != _CONFIG_ENTRY_FIELDS:
            raise RefreshRegistryAttestationError(
                "refresh_registry_attestation_config_row_invalid"
            )
        entry_id = _identity(row.get("entry_id"), "refresh_registry_config_entry_id")
        if entry_id in config_by_id:
            raise RefreshRegistryAttestationError(
                "refresh_registry_attestation_config_duplicate"
            )
        for name in ("domain", "state", "disabled_by"):
            _string(row.get(name), f"refresh_registry_config_{name}")
        if row["domain"] and not _SAFE_ID_RE.fullmatch(row["domain"]):
            raise RefreshRegistryAttestationError("refresh_registry_config_domain_invalid")
        if row["state"] and not _SAFE_ID_RE.fullmatch(row["state"]):
            raise RefreshRegistryAttestationError("refresh_registry_config_state_invalid")
        if row["disabled_by"] and not _SAFE_ID_RE.fullmatch(row["disabled_by"]):
            raise RefreshRegistryAttestationError("refresh_registry_config_disabled_by_invalid")
        if type(row.get("version")) is not int or not 0 <= row["version"] <= 1_000_000:
            raise RefreshRegistryAttestationError("refresh_registry_config_version_invalid")
        if type(row.get("minor_version")) is not int or not 0 <= row["minor_version"] <= 1_000_000:
            raise RefreshRegistryAttestationError("refresh_registry_config_minor_version_invalid")
        _string_list(row.get("config_subentry_ids"), "refresh_registry_config_subentries")
        reasons = _string_list(row.get("quarantine_reasons"), "refresh_registry_config_reasons")
        if type(row.get("registry_identity_complete")) is not bool or row["registry_identity_complete"] != (not reasons):
            raise RefreshRegistryAttestationError("refresh_registry_config_completion_mismatch")
        if row["registry_identity_complete"] and (
            not row["domain"]
            or row["state"].lower() != "loaded"
            or row["disabled_by"]
            or row["version"] <= 0
        ):
            raise RefreshRegistryAttestationError("refresh_registry_config_complete_fact_invalid")
        config_by_id[entry_id] = row

    device_by_id: dict[str, dict[str, Any]] = {}
    for row in detached["devices"]:
        if not isinstance(row, dict) or frozenset(row) != _DEVICE_FIELDS:
            raise RefreshRegistryAttestationError(
                "refresh_registry_attestation_device_row_invalid"
            )
        device_id = _identity(row.get("device_id"), "refresh_registry_device_id")
        if device_id in device_by_id:
            raise RefreshRegistryAttestationError(
                "refresh_registry_attestation_device_duplicate"
            )
        owner_ids = _string_list(row.get("config_entry_ids"), "refresh_registry_device_owners")
        subentries = row.get("config_subentry_ids_by_entry")
        if not isinstance(subentries, dict) or set(subentries) != set(owner_ids):
            raise RefreshRegistryAttestationError("refresh_registry_device_subentries_invalid")
        for owner_id, values in subentries.items():
            _identity(owner_id, "refresh_registry_device_owner")
            _string_list(values, "refresh_registry_device_subentry_values")
        _string(row.get("disabled_by"), "refresh_registry_device_disabled_by")
        identity_digest = _string(row.get("identity_digest"), "refresh_registry_device_digest")
        if not _SHA256_RE.fullmatch(identity_digest):
            raise RefreshRegistryAttestationError("refresh_registry_device_digest_invalid")
        expected_identity_digest = _identity_digest(
            "smartagent.ha_device_registry_identity.v0.1",
            device_id,
            *owner_ids,
            _canonical_json(subentries),
        )
        if identity_digest != expected_identity_digest:
            raise RefreshRegistryAttestationError("refresh_registry_device_digest_mismatch")
        reasons = _string_list(row.get("quarantine_reasons"), "refresh_registry_device_reasons")
        if type(row.get("registry_identity_complete")) is not bool or row["registry_identity_complete"] != (not reasons):
            raise RefreshRegistryAttestationError("refresh_registry_device_completion_mismatch")
        expected_relational_reasons: set[str] = set()
        for owner_id in owner_ids:
            owner = config_by_id.get(owner_id)
            if owner is None:
                expected_relational_reasons.add("device_config_entry_not_in_registry")
                continue
            if owner["registry_identity_complete"] is not True:
                expected_relational_reasons.add("device_config_entry_quarantined")
            if not set(subentries[owner_id]).issubset(set(owner["config_subentry_ids"])):
                expected_relational_reasons.add("device_config_subentry_not_in_registry")
        if not expected_relational_reasons.issubset(set(reasons)):
            raise RefreshRegistryAttestationError("refresh_registry_device_relation_mismatch")
        if row["registry_identity_complete"] and (
            not owner_ids or row["disabled_by"] or expected_relational_reasons
        ):
            raise RefreshRegistryAttestationError("refresh_registry_device_complete_fact_invalid")
        device_by_id[device_id] = row

    registry_entry_ids: set[str] = set()
    entity_ids: set[str] = set()
    logical_entity_ids: set[tuple[str, str, str]] = set()
    for row in detached["entities"]:
        if not isinstance(row, dict) or frozenset(row) != _ENTITY_FIELDS:
            raise RefreshRegistryAttestationError(
                "refresh_registry_attestation_entity_row_invalid"
            )
        registry_entry_id = _identity(
            row.get("registry_entry_id"), "refresh_registry_entity_registry_id"
        )
        if registry_entry_id in registry_entry_ids:
            raise RefreshRegistryAttestationError(
                "refresh_registry_attestation_entity_duplicate"
            )
        registry_entry_ids.add(registry_entry_id)
        entity_id = _string(row.get("entity_id"), "refresh_registry_entity_id", allow_empty=False)
        if not _ENTITY_ID_RE.fullmatch(entity_id):
            raise RefreshRegistryAttestationError("refresh_registry_entity_id_invalid")
        if entity_id in entity_ids:
            raise RefreshRegistryAttestationError("refresh_registry_entity_id_duplicate")
        entity_ids.add(entity_id)
        domain = _string(row.get("domain"), "refresh_registry_entity_domain", allow_empty=False)
        if entity_id.split(".", 1)[0] != domain:
            raise RefreshRegistryAttestationError("refresh_registry_entity_domain_mismatch")
        for name in (
            "platform",
            "unique_id_digest",
            "config_entry_id",
            "config_subentry_id",
            "device_id",
            "disabled_by",
            "device_class",
            "original_device_class",
            "unit_of_measurement",
        ):
            _string(row.get(name), f"refresh_registry_entity_{name}")
        for name in ("platform", "config_entry_id", "config_subentry_id", "device_id", "disabled_by", "device_class", "original_device_class"):
            if row[name] and not _SAFE_ID_RE.fullmatch(row[name]):
                raise RefreshRegistryAttestationError(f"refresh_registry_entity_{name}_invalid")
        unique_digest = row["unique_id_digest"]
        if unique_digest and not _SHA256_RE.fullmatch(unique_digest):
            raise RefreshRegistryAttestationError("refresh_registry_entity_unique_digest_invalid")
        logical_identity = (domain, row["platform"], unique_digest)
        if unique_digest and logical_identity in logical_entity_ids:
            raise RefreshRegistryAttestationError("refresh_registry_entity_logical_duplicate")
        if unique_digest:
            logical_entity_ids.add(logical_identity)
        reasons = _string_list(row.get("quarantine_reasons"), "refresh_registry_entity_reasons")
        if type(row.get("registry_identity_complete")) is not bool or row["registry_identity_complete"] != (not reasons):
            raise RefreshRegistryAttestationError("refresh_registry_entity_completion_mismatch")
        if row.get("adapter_inference_authorized") is not False:
            raise RefreshRegistryAttestationError("refresh_registry_entity_adapter_authority_forbidden")
        expected_relational_reasons: set[str] = set()
        config_entry = config_by_id.get(row["config_entry_id"])
        if config_entry is None:
            expected_relational_reasons.add("config_entry_not_in_registry")
        elif config_entry["registry_identity_complete"] is not True:
            expected_relational_reasons.add("config_entry_quarantined")
        device = device_by_id.get(row["device_id"])
        if device is None:
            expected_relational_reasons.add("device_not_in_registry")
        else:
            if device["registry_identity_complete"] is not True:
                expected_relational_reasons.add("device_quarantined")
            if row["config_entry_id"] not in device["config_entry_ids"]:
                expected_relational_reasons.add("entity_device_config_entry_mismatch")
            device_subentries = device["config_subentry_ids_by_entry"].get(row["config_entry_id"], [])
            if row["config_subentry_id"] and row["config_subentry_id"] not in device_subentries:
                expected_relational_reasons.add("entity_device_config_subentry_mismatch")
            if not row["config_subentry_id"] and device_subentries:
                expected_relational_reasons.add("entity_device_config_subentry_missing")
            if (
                config_entry is not None
                and row["config_subentry_id"]
                and row["config_subentry_id"] not in config_entry["config_subentry_ids"]
            ):
                expected_relational_reasons.add("entity_config_subentry_not_in_registry")
        if not expected_relational_reasons.issubset(set(reasons)):
            raise RefreshRegistryAttestationError("refresh_registry_entity_relation_mismatch")
        if row["registry_identity_complete"] and (
            not row["platform"]
            or not unique_digest
            or not row["config_entry_id"]
            or not row["device_id"]
            or row["disabled_by"]
            or expected_relational_reasons
        ):
            raise RefreshRegistryAttestationError("refresh_registry_entity_complete_fact_invalid")

    bridge = config_by_id.get(detached["bridge_config_entry_id"])
    if (
        bridge is None
        or bridge["registry_identity_complete"] is not True
        or bridge["domain"] != "smart_agent"
    ):
        raise RefreshRegistryAttestationError("refresh_registry_bridge_entry_invalid")


def _validated_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_invalid"
        )
    try:
        detached = json.loads(_canonical_json(snapshot))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_invalid"
        ) from exc
    if not isinstance(detached, dict):
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_invalid"
        )
    if frozenset(detached) != _EXPECTED_SNAPSHOT_FIELDS:
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_fields_invalid"
        )
    if detached.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_version_unknown"
        )
    for field_name, expected in _SNAPSHOT_AUTHORITY_FIELDS.items():
        if detached.get(field_name) != expected:
            raise RefreshRegistryAttestationError(
                "refresh_registry_attestation_snapshot_authority_invalid"
            )
    snapshot_digest = str(detached.get("snapshot_digest") or "")
    snapshot_id = str(detached.get("snapshot_id") or "")
    if not _SHA256_RE.fullmatch(snapshot_digest):
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_digest_invalid"
        )
    projection = {
        key: value
        for key, value in detached.items()
        if key not in {"snapshot_id", "snapshot_digest"}
    }
    if _digest(projection) != snapshot_digest or snapshot_id != f"harrs_{snapshot_digest[:32]}":
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_digest_mismatch"
        )
    if detached.get("coverage_completeness") != "complete":
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_incomplete"
        )
    if type(detached.get("source_seq")) is not int or detached["source_seq"] <= 0:
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_source_seq_invalid"
        )
    _identity(detached.get("request_nonce"), "refresh_registry_attestation_nonce")
    _identity(
        detached.get("bridge_config_entry_id"),
        "refresh_registry_attestation_bridge_config_entry_id",
    )
    _identity(
        detached.get("ha_installation_digest"),
        "refresh_registry_attestation_installation",
    )
    if not _SHA256_RE.fullmatch(str(detached["ha_installation_digest"])):
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_installation_invalid"
        )
    if not _SHA256_RE.fullmatch(str(detached.get("registry_revision") or "")):
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_registry_revision_invalid"
        )
    expected_registry_revision = _digest(
        {
            "config_entries": detached.get("config_entries"),
            "devices": detached.get("devices"),
            "entities": detached.get("entities"),
        }
    )
    if detached["registry_revision"] != expected_registry_revision:
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_registry_revision_mismatch"
        )
    _utc(detached.get("captured_at"), "refresh_registry_attestation_captured_at")
    _utc(detached.get("expires_at"), "refresh_registry_attestation_snapshot_expires_at")
    for field_name, rows_name in (
        ("config_entry_count", "config_entries"),
        ("device_count", "devices"),
        ("entity_count", "entities"),
    ):
        rows = detached.get(rows_name)
        if (
            type(detached.get(field_name)) is not int
            or detached[field_name] < 0
            or not isinstance(rows, list)
            or detached[field_name] != len(rows)
        ):
            raise RefreshRegistryAttestationError(
                "refresh_registry_attestation_snapshot_count_mismatch"
            )
    rows = (*detached["config_entries"], *detached["devices"], *detached["entities"])
    if any(not isinstance(row, dict) for row in rows):
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_snapshot_row_invalid"
        )
    quarantined_count = detached.get("quarantined_identity_count")
    if (
        type(quarantined_count) is not int
        or quarantined_count < 0
        or quarantined_count
        != sum(row.get("registry_identity_complete") is not True for row in rows)
    ):
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_quarantine_count_mismatch"
        )
    _validate_registry_rows(detached)
    return detached


def issue_refresh_registry_attestation(
    snapshot: dict[str, Any],
    *,
    secret: str,
    site_id: str,
    issued_at: datetime,
) -> dict[str, Any]:
    """Sign one exact snapshot without granting catalog or execution authority."""

    detached = _validated_snapshot(snapshot)
    normalized_site_id = _identity(site_id, "refresh_registry_attestation_site_id")
    issued = _utc(issued_at, "refresh_registry_attestation_issued_at")
    captured = _utc(
        detached["captured_at"], "refresh_registry_attestation_captured_at"
    )
    expires = _utc(
        detached["expires_at"], "refresh_registry_attestation_snapshot_expires_at"
    )
    if (
        captured > issued
        or (issued - captured).total_seconds() > ATTESTATION_CLOCK_SKEW_SECONDS
        or issued >= expires
        or (expires - captured).total_seconds() > ATTESTATION_MAX_TTL_SECONDS
    ):
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_time_invalid"
        )
    ttl = int((expires - issued).total_seconds())
    if ttl <= 0 or ttl > ATTESTATION_MAX_TTL_SECONDS:
        raise RefreshRegistryAttestationError(
            "refresh_registry_attestation_ttl_invalid"
        )
    unsigned = {
        "schema_version": ATTESTATION_SCHEMA_VERSION,
        "purpose": ATTESTATION_PURPOSE,
        "issuer": ATTESTATION_ISSUER,
        "key_id": attestation_key_id(secret),
        "site_id": normalized_site_id,
        "snapshot_id": detached["snapshot_id"],
        "snapshot_digest": detached["snapshot_digest"],
        "ha_installation_digest": detached["ha_installation_digest"],
        "source_seq": detached["source_seq"],
        "request_nonce": detached["request_nonce"],
        "registry_revision": detached["registry_revision"],
        "captured_at": captured.isoformat(),
        "issued_at": issued.isoformat(),
        "expires_at": expires.isoformat(),
        "snapshot": detached,
        "source_attestation_state": "signed_not_consumed",
        "catalog_write_authorized": False,
        "refresh_dispatch_authorized": False,
        "execution_eligible": False,
        "device_effect_authority": "none",
    }
    attestation_id = f"harra_{_digest(unsigned)[:32]}"
    signed_projection = {**unsigned, "attestation_id": attestation_id}
    signature = hmac.new(
        _derived_key(secret),
        _canonical_json(signed_projection).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {**signed_projection, "signature": signature}


__all__: list[str] = []
