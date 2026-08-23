"""Pure HA registry projection for future observation-refresh materialization.

This module only copies detached identity facts from Home Assistant-owned
registries.  It does not prove who transported the snapshot, choose a refresh
adapter, write the add-on catalog, or authorize any Provider/HA operation.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any


REFRESH_REGISTRY_SNAPSHOT_VERSION = "smartagent.ha_refresh_registry_snapshot.v0.1"
_ENTITY_ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:@/-]+$")


class RefreshRegistrySnapshotError(ValueError):
    """Raised when the HA registry projection is not deterministic and exact."""


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
        raise RefreshRegistrySnapshotError("refresh_registry_projection_invalid") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _identity_digest(namespace: str, *values: str) -> str:
    payload = "\0".join((namespace, *values))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ha_installation_digest(ha_instance_id: str) -> str:
    """Return the privacy-preserving installation pin used by the add-on."""

    normalized = _safe_id(
        ha_instance_id, "refresh_registry_ha_instance_id"
    )
    return _identity_digest("smartagent.ha_installation.v0.1", normalized)


def _utc_value(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise RefreshRegistrySnapshotError(f"{field_name}_timezone_required")
    try:
        return value.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise RefreshRegistrySnapshotError(f"{field_name}_invalid") from exc


def _optional_utc_text(value: Any, field_name: str) -> tuple[str, str | None]:
    if value is None:
        return "", None
    try:
        return _utc_value(value, field_name).isoformat(), None
    except RefreshRegistrySnapshotError:
        return "", f"{field_name}_invalid"


def _safe_id(value: Any, field_name: str, *, required: bool = True) -> str:
    if type(value) is not str:
        if required:
            raise RefreshRegistrySnapshotError(f"{field_name}_invalid")
        return ""
    normalized = value.strip()
    if not normalized:
        if required:
            raise RefreshRegistrySnapshotError(f"{field_name}_missing")
        return ""
    if len(normalized) > 255 or not _SAFE_ID_RE.fullmatch(normalized):
        raise RefreshRegistrySnapshotError(f"{field_name}_invalid")
    return normalized


def _optional_id(value: Any, field_name: str) -> tuple[str, str | None]:
    if value is None or value == "":
        return "", None
    try:
        return _safe_id(value, field_name), None
    except RefreshRegistrySnapshotError:
        return "", f"{field_name}_invalid"


def _required_id(value: Any, field_name: str) -> tuple[str, str | None]:
    try:
        return _safe_id(value, field_name), None
    except RefreshRegistrySnapshotError:
        return "", f"{field_name}_missing_or_invalid"


def _enum_text(value: Any, field_name: str) -> tuple[str, str | None]:
    raw = getattr(value, "value", value)
    if raw is None:
        return "", None
    if type(raw) is not str:
        return "", f"{field_name}_invalid"
    normalized = raw.strip()
    if len(normalized) > 64 or any(ord(char) < 32 for char in normalized):
        return "", f"{field_name}_invalid"
    return normalized, None


def _unique_id_digest(
    *, namespace: str, owner: str, value: Any, required: bool
) -> tuple[str, str | None]:
    if value is None and not required:
        return "", None
    if type(value) is not str:
        return "", "unique_id_missing_or_invalid"
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > 512
        or any(ord(char) < 32 for char in normalized)
    ):
        return "", "unique_id_missing_or_invalid"
    return _identity_digest(namespace, owner, normalized), None


def _registry_values(registry: Any, attribute: str) -> tuple[Any, ...]:
    raw = getattr(registry, attribute, None)
    if isinstance(raw, Mapping):
        return tuple(raw.values())
    values = getattr(raw, "values", None)
    if callable(values):
        try:
            return tuple(values())
        except Exception as exc:
            raise RefreshRegistrySnapshotError(
                f"refresh_registry_{attribute}_read_failed"
            ) from exc
    if isinstance(raw, (list, tuple, set, frozenset)):
        return tuple(raw)
    raise RefreshRegistrySnapshotError(f"refresh_registry_{attribute}_unavailable")


def _config_entry_values(config_entries: Any) -> tuple[Any, ...]:
    getter = getattr(config_entries, "async_entries", None)
    if callable(getter):
        try:
            values = getter()
        except Exception as exc:
            raise RefreshRegistrySnapshotError(
                "refresh_registry_config_entries_read_failed"
            ) from exc
        if isinstance(values, Iterable) and not isinstance(
            values, (str, bytes, Mapping)
        ):
            return tuple(values)
    raw = getattr(config_entries, "entries", None)
    if isinstance(raw, Mapping):
        return tuple(raw.values())
    if isinstance(raw, (list, tuple, set, frozenset)):
        return tuple(raw)
    raise RefreshRegistrySnapshotError("refresh_registry_config_entries_unavailable")


def _register_exact_row(
    rows: dict[str, Any], *, row_id: str, row: Any, kind: str
) -> None:
    if row_id in rows:
        raise RefreshRegistrySnapshotError(
            f"refresh_registry_{kind}_identity_duplicate"
        )
    rows[row_id] = row


def _normalized_device_config_entries(device: Any) -> tuple[tuple[str, ...], list[str]]:
    reasons: list[str] = []
    singular = getattr(device, "config_entry_id", None)
    if singular not in (None, ""):
        entry_id, error = _required_id(singular, "ha_device_config_entry_id")
        if error:
            return (), [error]
        return (entry_id,), reasons
    legacy = getattr(device, "config_entries", None)
    if legacy is None:
        return (), ["device_config_entries_missing"]
    try:
        normalized = tuple(
            sorted({_safe_id(item, "ha_device_config_entry_id") for item in legacy})
        )
    except (TypeError, RefreshRegistrySnapshotError):
        return (), ["device_config_entries_invalid"]
    if not normalized:
        reasons.append("device_config_entries_missing")
    return normalized, reasons


def _normalized_device_subentries(
    device: Any, config_entry_ids: tuple[str, ...]
) -> dict[str, list[str]]:
    singular = getattr(device, "config_subentry_id", None)
    if singular not in (None, "") and len(config_entry_ids) == 1:
        return {
            config_entry_ids[0]: [
                _safe_id(singular, "ha_device_config_subentry_id")
            ]
        }
    legacy = getattr(device, "config_entries_subentries", None)
    if not isinstance(legacy, Mapping):
        return {entry_id: [] for entry_id in config_entry_ids}
    try:
        legacy_entry_ids = {
            _safe_id(key, "ha_device_config_entry_id") for key in legacy
        }
    except RefreshRegistrySnapshotError as exc:
        raise RefreshRegistrySnapshotError(
            "refresh_registry_device_subentries_invalid"
        ) from exc
    if legacy_entry_ids != set(config_entry_ids):
        raise RefreshRegistrySnapshotError(
            "refresh_registry_device_subentry_owner_mismatch"
        )
    projection: dict[str, list[str]] = {}
    for entry_id in config_entry_ids:
        raw_values = legacy.get(entry_id, ()) or ()
        try:
            values = sorted(
                {
                    _safe_id(value, "ha_device_config_subentry_id")
                    for value in raw_values
                    if value not in (None, "")
                }
            )
        except (TypeError, RefreshRegistrySnapshotError) as exc:
            raise RefreshRegistrySnapshotError(
                "refresh_registry_device_subentries_invalid"
            ) from exc
        projection[entry_id] = values
    return projection


def _config_entry_subentries(entry: Any) -> tuple[str, ...]:
    raw = getattr(entry, "subentries", None)
    if raw is None:
        return ()
    if not isinstance(raw, Mapping):
        raise RefreshRegistrySnapshotError(
            "refresh_registry_config_entry_subentries_invalid"
        )
    try:
        return tuple(
            sorted(
                {
                    _safe_id(key, "ha_config_subentry_id")
                    for key in raw
                }
            )
        )
    except RefreshRegistrySnapshotError as exc:
        raise RefreshRegistrySnapshotError(
            "refresh_registry_config_entry_subentries_invalid"
        ) from exc


def _config_entry_projection(entry: Any) -> tuple[str, dict[str, Any]]:
    entry_id = _safe_id(getattr(entry, "entry_id", None), "ha_config_entry_id")
    reasons: list[str] = []
    domain, error = _required_id(
        getattr(entry, "domain", None), "ha_config_entry_domain"
    )
    if error:
        reasons.append(error)
    state, error = _enum_text(getattr(entry, "state", None), "config_entry_state")
    if error:
        reasons.append(error)
    disabled_by, error = _enum_text(
        getattr(entry, "disabled_by", None), "config_entry_disabled_by"
    )
    if error:
        reasons.append(error)
    version = getattr(entry, "version", 0)
    minor_version = getattr(entry, "minor_version", 0)
    if type(version) is not int or version <= 0 or version > 1_000_000:
        version = 0
        reasons.append("config_entry_version_invalid")
    if type(minor_version) is not int or minor_version < 0 or minor_version > 1_000_000:
        minor_version = 0
        reasons.append("config_entry_minor_version_invalid")
    try:
        config_subentry_ids = _config_entry_subentries(entry)
    except RefreshRegistrySnapshotError:
        config_subentry_ids = ()
        reasons.append("config_entry_subentries_invalid")
    if state.lower() != "loaded":
        reasons.append("config_entry_not_loaded")
    if disabled_by:
        reasons.append("config_entry_disabled")
    return entry_id, {
        "entry_id": entry_id,
        "domain": domain,
        "state": state,
        "disabled_by": disabled_by,
        "version": version,
        "minor_version": minor_version,
        "config_subentry_ids": list(config_subentry_ids),
        "registry_identity_complete": not reasons,
        "quarantine_reasons": sorted(set(reasons)),
    }


def _device_projection(
    device: Any, *, config_entries: Mapping[str, dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    device_id = _safe_id(getattr(device, "id", None), "ha_device_id")
    config_entry_ids, reasons = _normalized_device_config_entries(device)
    try:
        subentries = _normalized_device_subentries(device, config_entry_ids)
    except RefreshRegistrySnapshotError:
        subentries = {}
        reasons.append("device_config_subentries_invalid")
    for config_entry_id in config_entry_ids:
        owner = config_entries.get(config_entry_id)
        if owner is None:
            reasons.append("device_config_entry_not_in_registry")
            continue
        if not owner["registry_identity_complete"]:
            reasons.append("device_config_entry_quarantined")
        declared_subentries = set(subentries.get(config_entry_id, ()))
        owner_subentries = set(owner["config_subentry_ids"])
        if not declared_subentries.issubset(owner_subentries):
            reasons.append("device_config_subentry_not_in_registry")
    disabled_by, error = _enum_text(
        getattr(device, "disabled_by", None), "device_disabled_by"
    )
    if error:
        reasons.append(error)
    if disabled_by:
        reasons.append("device_disabled")
    identity_digest = _identity_digest(
        "smartagent.ha_device_registry_identity.v0.1",
        device_id,
        *config_entry_ids,
        _canonical_json(subentries),
    )
    return device_id, {
        "device_id": device_id,
        "config_entry_ids": list(config_entry_ids),
        "config_subentry_ids_by_entry": subentries,
        "disabled_by": disabled_by,
        "identity_digest": identity_digest,
        "registry_identity_complete": not reasons,
        "quarantine_reasons": sorted(set(reasons)),
    }


def _entity_projection(
    entity: Any,
    *,
    config_entries: Mapping[str, dict[str, Any]],
    devices: Mapping[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    registry_entry_id = _safe_id(
        getattr(entity, "id", None), "ha_entity_registry_entry_id"
    )
    raw_entity_id = getattr(entity, "entity_id", None)
    if type(raw_entity_id) is not str:
        raise RefreshRegistrySnapshotError("refresh_registry_entity_identity_invalid")
    entity_id = raw_entity_id.strip()
    if not _ENTITY_ID_RE.fullmatch(entity_id):
        raise RefreshRegistrySnapshotError("refresh_registry_entity_identity_invalid")
    reasons: list[str] = []
    entity_domain = entity_id.split(".", 1)[0]
    declared_domain, error = _optional_id(
        getattr(entity, "domain", None), "ha_entity_domain"
    )
    if error:
        reasons.append(error)
    if declared_domain and declared_domain != entity_domain:
        reasons.append("entity_domain_mismatch")
    platform, error = _required_id(getattr(entity, "platform", None), "ha_platform")
    if error:
        reasons.append(error)
    config_entry_id, error = _required_id(
        getattr(entity, "config_entry_id", None), "ha_config_entry_id"
    )
    if error:
        reasons.append(error)
    config_subentry_id, error = _optional_id(
        getattr(entity, "config_subentry_id", None), "ha_config_subentry_id"
    )
    if error:
        reasons.append(error)
    device_id, error = _required_id(getattr(entity, "device_id", None), "ha_device_id")
    if error:
        reasons.append(error)
    disabled_by, error = _enum_text(
        getattr(entity, "disabled_by", None), "entity_disabled_by"
    )
    if error:
        reasons.append(error)
    if disabled_by:
        reasons.append("entity_disabled")
    unique_id_digest, error = _unique_id_digest(
        namespace="smartagent.ha_entity_unique_id.v0.1",
        owner=f"{entity_domain}:{platform}",
        value=getattr(entity, "unique_id", None),
        required=True,
    )
    if error:
        reasons.append(error)
    config_entry = config_entries.get(config_entry_id)
    if config_entry is None:
        reasons.append("config_entry_not_in_registry")
    elif not config_entry["registry_identity_complete"]:
        reasons.append("config_entry_quarantined")
    device = devices.get(device_id)
    if device is None:
        reasons.append("device_not_in_registry")
    else:
        if not device["registry_identity_complete"]:
            reasons.append("device_quarantined")
        if config_entry_id not in device["config_entry_ids"]:
            reasons.append("entity_device_config_entry_mismatch")
        device_subentries = device["config_subentry_ids_by_entry"].get(
            config_entry_id, []
        )
        if config_subentry_id and config_subentry_id not in device_subentries:
            reasons.append("entity_device_config_subentry_mismatch")
        if not config_subentry_id and device_subentries:
            reasons.append("entity_device_config_subentry_missing")
        if (
            config_entry is not None
            and config_subentry_id
            and config_subentry_id not in config_entry["config_subentry_ids"]
        ):
            reasons.append("entity_config_subentry_not_in_registry")
    device_class, error = _enum_text(
        getattr(entity, "device_class", None), "entity_device_class"
    )
    if error:
        reasons.append(error)
    original_device_class, error = _enum_text(
        getattr(entity, "original_device_class", None),
        "entity_original_device_class",
    )
    if error:
        reasons.append(error)
    unit, error = _enum_text(
        getattr(entity, "unit_of_measurement", None),
        "entity_unit_of_measurement",
    )
    if error:
        reasons.append(error)
    return registry_entry_id, {
        "registry_entry_id": registry_entry_id,
        "entity_id": entity_id,
        "domain": entity_domain,
        "platform": platform,
        "unique_id_digest": unique_id_digest,
        "config_entry_id": config_entry_id,
        "config_subentry_id": config_subentry_id,
        "device_id": device_id,
        "disabled_by": disabled_by,
        "device_class": device_class,
        "original_device_class": original_device_class,
        "unit_of_measurement": unit,
        "registry_identity_complete": not reasons,
        "quarantine_reasons": sorted(set(reasons)),
        "adapter_inference_authorized": False,
    }


def build_ha_refresh_registry_snapshot(
    *,
    entity_registry: Any,
    device_registry: Any,
    config_entries: Any,
    ha_instance_id: str,
    bridge_config_entry_id: str,
    request_nonce: str,
    source_seq: int,
    captured_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    """Build one detached snapshot in a single no-await HA event-loop slice."""

    ha_instance_id = _safe_id(ha_instance_id, "refresh_registry_ha_instance_id")
    bridge_config_entry_id = _safe_id(
        bridge_config_entry_id, "refresh_registry_bridge_config_entry_id"
    )
    request_nonce = _safe_id(request_nonce, "refresh_registry_request_nonce")
    if type(source_seq) is not int or source_seq <= 0:
        raise RefreshRegistrySnapshotError("refresh_registry_source_seq_invalid")
    captured_value = _utc_value(captured_at, "refresh_registry_captured_at")
    expires_value = _utc_value(expires_at, "refresh_registry_expires_at")
    if expires_value <= captured_value:
        raise RefreshRegistrySnapshotError("refresh_registry_expiry_invalid")

    config_source_rows = _config_entry_values(config_entries)
    config_by_id: dict[str, dict[str, Any]] = {}
    for source in config_source_rows:
        entry_id, projection = _config_entry_projection(source)
        _register_exact_row(
            config_by_id, row_id=entry_id, row=projection, kind="config_entry"
        )
    bridge_entry = config_by_id.get(bridge_config_entry_id)
    if bridge_entry is None or bridge_entry["domain"] != "smart_agent":
        raise RefreshRegistrySnapshotError(
            "refresh_registry_bridge_config_entry_not_in_registry"
        )
    if not bridge_entry["registry_identity_complete"]:
        raise RefreshRegistrySnapshotError(
            "refresh_registry_bridge_config_entry_quarantined"
        )

    device_source_rows = _registry_values(device_registry, "devices")
    devices_by_id: dict[str, dict[str, Any]] = {}
    for source in device_source_rows:
        device_id, projection = _device_projection(
            source, config_entries=config_by_id
        )
        _register_exact_row(devices_by_id, row_id=device_id, row=projection, kind="device")

    entity_source_rows = _registry_values(entity_registry, "entities")
    entities_by_registry_id: dict[str, dict[str, Any]] = {}
    entity_ids: set[str] = set()
    entity_registry_identities: set[tuple[str, str, str]] = set()
    for source in entity_source_rows:
        registry_id, projection = _entity_projection(
            source,
            config_entries=config_by_id,
            devices=devices_by_id,
        )
        if projection["entity_id"] in entity_ids:
            raise RefreshRegistrySnapshotError(
                "refresh_registry_entity_identity_duplicate"
            )
        entity_ids.add(projection["entity_id"])
        logical_identity = (
            projection["domain"],
            projection["platform"],
            projection["unique_id_digest"],
        )
        if logical_identity in entity_registry_identities:
            raise RefreshRegistrySnapshotError(
                "refresh_registry_entity_logical_identity_duplicate"
            )
        entity_registry_identities.add(logical_identity)
        _register_exact_row(
            entities_by_registry_id,
            row_id=registry_id,
            row=projection,
            kind="entity_registry_entry",
        )

    config_rows = sorted(config_by_id.values(), key=lambda row: row["entry_id"])
    device_rows = sorted(devices_by_id.values(), key=lambda row: row["device_id"])
    entity_rows = sorted(
        entities_by_registry_id.values(),
        key=lambda row: (row["entity_id"], row["registry_entry_id"]),
    )
    registry_projection = {
        "config_entries": config_rows,
        "devices": device_rows,
        "entities": entity_rows,
    }
    registry_revision = _digest(registry_projection)
    quarantined_count = sum(
        1 for row in (*config_rows, *device_rows, *entity_rows)
        if not row["registry_identity_complete"]
    )
    projection = {
        "schema_version": REFRESH_REGISTRY_SNAPSHOT_VERSION,
        "ha_installation_digest": ha_installation_digest(ha_instance_id),
        "bridge_config_entry_id": bridge_config_entry_id,
        "request_nonce": request_nonce,
        "source_seq": source_seq,
        "captured_at": captured_value.isoformat(),
        "expires_at": expires_value.isoformat(),
        "coverage_completeness": "complete",
        "registry_revision": registry_revision,
        "config_entry_count": len(config_rows),
        "device_count": len(device_rows),
        "entity_count": len(entity_rows),
        "quarantined_identity_count": quarantined_count,
        **registry_projection,
        "source_attestation_state": "not_materialized",
        "catalog_write_authorized": False,
        "refresh_dispatch_authorized": False,
        "execution_eligible": False,
        "device_effect_authority": "none",
    }
    snapshot_digest = _digest(projection)
    return {
        **projection,
        "snapshot_id": f"harrs_{snapshot_digest[:32]}",
        "snapshot_digest": snapshot_digest,
    }


__all__: list[str] = []
