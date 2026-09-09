"""HA listener registry, metadata, and read-only presence runtime.

This module owns the existing registry reconciliation and snapshot projection
logic. Listener subscription registration and all device-effect execution remain
in the listener mixin and its controlled action path.
"""
from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from math import isfinite
from typing import Any

from .device_registry_identity import registry_metadata, registry_entry_matches

from homeassistant.helpers.event import async_call_later
from homeassistant.core import callback

from .const import DEVICE_CONTROL_MODES
from .sensor_event_filter import environment_sensor_kind


_LOGGER = logging.getLogger(__name__)

def listener_entity_metadata(
    self,
    entity_id: str,
    *,
    info: dict[str, Any] | None = None,
    state_obj: Any | None = None,
) -> dict[str, Any]:
    row = dict(info) if isinstance(info, dict) else {}
    if not row:
        device_info = getattr(self, "device_info", {})
        stored = device_info.get(entity_id) if isinstance(device_info, dict) else None
        if isinstance(stored, dict):
            row.update(stored)
    if state_obj is None:
        states = getattr(getattr(self, "hass", None), "states", None)
        get_state = getattr(states, "get", None)
        state_obj = get_state(entity_id) if callable(get_state) else None
    attributes = getattr(state_obj, "attributes", None)
    if isinstance(attributes, dict):
        for key in ("device_class", "friendly_name", "entity_category"):
            if not row.get(key) and attributes.get(key) not in (None, ""):
                row[key] = attributes.get(key)
    return row

def is_presence_listener_entity(self, entity_id: str, info: dict[str, Any] | None = None) -> bool:
    """Return True for managed entities that can represent human presence."""
    domain = str(entity_id or "").split(".", 1)[0]
    if domain != "binary_sensor":
        return False
    row = self._listener_entity_metadata(entity_id, info=info)
    sensor_type = str(row.get("sensor_type") or row.get("presence_sensor_type") or "").strip().lower()
    return sensor_type in self._ACTIONABLE_SENSOR_TYPES

def get_live_presence_occupancy_map(self) -> dict[str, list[tuple[str, str]]]:
    """Read current HA states for Core-authorized, fresh guard evidence."""
    self._last_live_presence_guard_status = {
        "ok": False,
        "reason": "presence_snapshot_unavailable",
    }
    snapshot_getter = getattr(self, "get_presence_snapshot", None)
    if not callable(snapshot_getter):
        return {}
    try:
        snapshot = snapshot_getter()
    except Exception:
        return {}
    rooms = snapshot.get("rooms") if isinstance(snapshot, dict) else None
    if not isinstance(rooms, dict):
        self._last_live_presence_guard_status["reason"] = "presence_rooms_unavailable"
        return {}
    states = getattr(getattr(self, "hass", None), "states", None)
    get_state = getattr(states, "get", None)
    if not callable(get_state):
        self._last_live_presence_guard_status["reason"] = "ha_states_unavailable"
        return {}

    now = datetime.now(timezone.utc)
    occupancy: dict[str, list[tuple[str, str]]] = {}

    def _append_entry(
        room_candidates: list[str],
        entity_id: str,
        state: str,
    ) -> None:
        entry = (entity_id, state)
        for room in room_candidates:
            room_entries = occupancy.setdefault(room, [])
            if entry not in room_entries:
                room_entries.append(entry)

    for room_id, payload in rooms.items():
        if not isinstance(payload, dict):
            continue
        room_candidates: list[str] = []
        for raw_value in (room_id, payload.get("localized_spaces")):
            values = (
                raw_value
                if isinstance(raw_value, (list, tuple, set))
                else (raw_value,)
            )
            for value in values:
                room = str(value or "").strip()
                if room and room not in room_candidates:
                    room_candidates.append(room)

        evidence_rows = payload.get("presence_evidence")
        if not isinstance(evidence_rows, (list, tuple)):
            continue
        for evidence in evidence_rows:
            if not isinstance(evidence, dict) or evidence.get("stale") is True:
                continue
            use_for_raw = evidence.get("use_for")
            if isinstance(use_for_raw, str):
                use_for = {
                    item.strip()
                    for item in use_for_raw.split(",")
                    if item.strip()
                }
            elif isinstance(use_for_raw, (list, tuple, set)):
                use_for = {
                    str(item or "").strip()
                    for item in use_for_raw
                    if str(item or "").strip()
                }
            else:
                use_for = set()
            if "guard" not in use_for:
                continue

            entity_id = str(
                evidence.get("entity_id")
                or evidence.get("id")
                or ""
            ).strip()
            sensor_type = str(
                evidence.get("sensor_type")
                or evidence.get("presence_sensor_type")
                or ""
            ).strip().lower()
            if not entity_id or sensor_type in self._ACTIONABLE_CONTACT_SENSOR_TYPES:
                continue
            if sensor_type not in self._ACTIONABLE_SENSOR_TYPES:
                continue

            ttl_invalid = False
            try:
                freshness_ttl_secs = float(
                    evidence.get("freshness_ttl_secs") or 0
                )
            except (TypeError, ValueError):
                freshness_ttl_secs = 0.0
                ttl_invalid = True
            if not isfinite(freshness_ttl_secs) or freshness_ttl_secs < 0:
                ttl_invalid = True
            if ttl_invalid:
                _append_entry(room_candidates, entity_id, "unknown")
                continue
            if freshness_ttl_secs > 0:
                observed_text = str(
                    evidence.get("last_observed_at")
                    or evidence.get("observed_at")
                    or ""
                ).strip()
                try:
                    observed_at = datetime.fromisoformat(
                        observed_text.replace("Z", "+00:00")
                    )
                    if observed_at.tzinfo is None:
                        observed_at = observed_at.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    observed_at = None
                if observed_at is None:
                    _append_entry(room_candidates, entity_id, "unknown")
                    continue
                age_secs = (
                    now - observed_at.astimezone(timezone.utc)
                ).total_seconds()
                if age_secs < -60:
                    _append_entry(room_candidates, entity_id, "unknown")
                    continue
                if age_secs > freshness_ttl_secs:
                    continue
            try:
                state_obj = get_state(entity_id)
            except Exception:
                state_obj = None
            raw_state = str(
                getattr(state_obj, "state", "") or ""
            ).strip().lower()
            if raw_state in {
                "on",
                "occupied",
                "present",
                "home",
                "motion",
                "person",
            }:
                state = "on"
            elif raw_state in {
                "off",
                "vacant",
                "clear",
                "away",
                "none",
                "idle",
                "empty",
            }:
                state = "off"
            elif raw_state in {"unknown", "unavailable"}:
                state = raw_state
            elif sensor_type in {"person_count", "object_count", "frigate"}:
                try:
                    numeric_state = float(raw_state)
                except (TypeError, ValueError):
                    state = "unknown"
                else:
                    if not isfinite(numeric_state) or numeric_state < 0:
                        state = "unknown"
                    else:
                        state = "on" if numeric_state > 0 else "off"
            else:
                state = "unknown"

            _append_entry(room_candidates, entity_id, state)
    self._last_live_presence_guard_status = {"ok": True, "reason": ""}
    return occupancy

def reconcile_active_listener_states(
    self,
    entity_ids: list[str],
    *,
    schedule: Any = async_call_later,
) -> None:
    """Wake the shared room loop on inventory/startup, including vacant rooms."""
    if not entity_ids or not self._is_enabled() or getattr(self, "_sensors_muted", False):
        return
    previous = getattr(self, "_room_lighting_startup_cancel", None)
    if callable(previous):
        previous()
    @callback
    def wake(now: Any) -> None:
        from .room_lighting_runtime import reconcile_rooms
        self._room_lighting_startup_cancel = None
        self.hass.async_create_task(reconcile_rooms(self, now))
    self._room_lighting_startup_cancel = schedule(self.hass, 0.2, wake)


async def async_refresh_device_info_from_addon_devices(
    self, *, reason: str = "", registry_event: dict[str, Any] | None = None,
) -> bool:
    """Refresh runtime listener device_info from the add-on device projection."""
    status = {
        "ok": False,
        "source": "addon_devices",
        "reason": str(reason or "manual"),
        "count": 0,
    }
    client = getattr(self, "_addon_client", None)
    get_devices = getattr(client, "get_devices", None)
    if not callable(get_devices):
        status["reason"] = "addon_client_unavailable"
        self._last_addon_device_sync_status = status
        return False

    try:
        rows = await get_devices()
        reconcile_ids = getattr(self, "_async_reconcile_ha_registry_entity_ids", None)
        if isinstance(rows, list) and callable(reconcile_ids) and await reconcile_ids(rows, registry_event=registry_event):
            rows = await get_devices()
        reconcile = getattr(self, "_reconcile_device_runtime_capabilities", None)
        if isinstance(rows, list) and callable(reconcile) and await reconcile(rows):
            # Read the confirmed projection back through Gateway capability binding.
            rows = await get_devices()
    except Exception as exc:
        status["reason"] = "addon_exception"
        status["error"] = str(exc)
        self._last_addon_device_sync_status = status
        return False

    if rows is None:
        status["reason"] = "addon_not_available"
        self._last_addon_device_sync_status = status
        return False
    if isinstance(rows, dict):
        status["reason"] = "addon_error"
        if rows.get("__status") is not None:
            status["status"] = rows.get("__status")
        if rows.get("error") is not None:
            status["error"] = str(rows.get("error"))
        self._last_addon_device_sync_status = status
        return False
    if not isinstance(rows, list):
        status["reason"] = "invalid_payload"
        status["payload_type"] = type(rows).__name__
        self._last_addon_device_sync_status = status
        return False

    self._managed_registry_entity_ids = {
        str(row["entity_id"]) for row in rows
        if isinstance(row, dict) and row.get("entity_id") and row.get("managed") is True
    }
    next_device_info: dict[str, dict[str, Any]] = {}
    next_environment_context_info: dict[str, dict[str, Any]] = {}
    skipped = 0
    for row in rows:
        if not isinstance(row, dict):
            skipped += 1
            continue
        mapped = self._managed_device_info_row_from_addon_device(row)
        if mapped is None:
            skipped += 1
            continue
        entity_id, info = mapped
        listener_runtime_entity = self._is_listener_runtime_entity(
            entity_id,
            info,
        )
        environment_kind = environment_sensor_kind(entity_id, info)
        if listener_runtime_entity:
            next_device_info[entity_id] = info
        if environment_kind:
            next_environment_context_info[entity_id] = info
        if not listener_runtime_entity and not environment_kind:
            skipped += 1

    current = getattr(self, "device_info", {}) or {}
    if not isinstance(current, dict):
        current = {}
    current_environment = getattr(self, "_environment_context_device_info", {}) or {}
    if not isinstance(current_environment, dict):
        current_environment = {}
    changed = current != next_device_info or current_environment != next_environment_context_info
    self.device_info = next_device_info
    self._environment_context_device_info = next_environment_context_info
    if changed:
        reconciled = getattr(self, "_listener_active_state_reconciled", None)
        if isinstance(reconciled, dict):
            for entity_id in list(reconciled):
                if (
                    entity_id not in next_device_info
                    and entity_id not in next_environment_context_info
                ):
                    reconciled.pop(entity_id, None)
        presence_inference = getattr(self, "_presence_inference", None)
        if presence_inference is not None and hasattr(presence_inference, "device_info"):
            try:
                presence_inference.device_info = self.device_info
            except Exception:
                pass
        updater = getattr(self, "async_set_updated_data", None)
        if callable(updater):
            try:
                updater({})
            except Exception:
                pass

    status.update(
        {
            "ok": True,
            "reason": str(reason or "manual"),
            "count": len(next_device_info),
            "environment_context_count": len(next_environment_context_info),
            "skipped": skipped,
            "changed": changed,
        }
    )
    self._device_info_source = "addon_devices"
    self._last_addon_device_sync_status = status
    return changed

def is_actionable_sensor_runtime_entity(self, entity_id: str, info: dict[str, Any]) -> bool:
    sensor_type = str((info or {}).get("sensor_type") or "").strip().lower()
    if sensor_type in self._ACTIONABLE_SENSOR_TYPES:
        return True
    text = " ".join(
        str((info or {}).get(key) or "")
        for key in ("name", "type", "capability", "device_class")
    ).lower()
    text = f"{entity_id.lower()} {text}"
    return any(str(kw).lower() in text for kw in (*self._PRESENCE_KW, *self._PERSON_COUNT_KW))

def is_listener_runtime_entity(self, entity_id: str, info: dict[str, Any]) -> bool:
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    if domain not in self._LISTENER_DOMAINS:
        return False
    if domain != "sensor":
        return True
    return self._is_actionable_sensor_runtime_entity(entity_id, info)


def is_explicitly_managed_device_row(row: dict[str, Any]) -> bool:
    """Resolve managed membership without making legacy aliases a second veto.

    ``managed`` is the current add-on-owned contract.  ``in_sa`` and
    ``in_smartagent`` are accepted only for rows that predate that field.  The
    exact-bool checks keep missing or stringly-typed inventory rows from being
    promoted into the listener set.
    """

    if not isinstance(row, dict):
        return False
    if "managed" in row:
        return row.get("managed") is True
    return row.get("in_sa") is True or row.get("in_smartagent") is True


def managed_device_info_row_from_addon_device(
    self,
    row: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    if not is_explicitly_managed_device_row(row):
        return None
    entity_id = str(row.get("entity_id") or row.get("id") or "").strip()
    if "." not in entity_id:
        return None
    ops = str(row.get("ops") or "").strip()
    if ops == "__smartagent_deleted__":
        return None
    domain = entity_id.split(".", 1)[0]
    if domain not in self._LISTENER_DOMAINS:
        return None

    mode = str(row.get("control_mode") or row.get("policy") or "shared").strip() or "shared"
    valid_modes = DEVICE_CONTROL_MODES
    if mode not in valid_modes:
        mode = "shared"

    room = (
        row.get("room")
        or row.get("area")
        or row.get("space_id")
        or row.get("space")
        or ""
    )
    if isinstance(room, (list, tuple)):
        room = next((str(item).strip() for item in room if str(item).strip()), "")
    space_id = row.get("space_id") or row.get("space") or ""
    if isinstance(space_id, (list, tuple)):
        space_id = next((str(item).strip() for item in space_id if str(item).strip()), "")
    name = (
        row.get("name")
        or row.get("friendly_name")
        or row.get("display_name")
        or entity_id
    )
    dev_type = (
        row.get("type")
        or row.get("dev_type")
        or row.get("capability")
        or row.get("domain")
        or domain
    )
    vacant_action = str(row.get("vacant_action") or "preserve").strip().lower()
    info = {
        "name": str(name or entity_id),
        "room": str(room or ""),
        "space_id": str(space_id or ""),
        "type": str(dev_type or domain),
        "capability": str(row.get("capability") or dev_type or domain),
        "ops": ops,
        "control_mode": mode,
        "managed": True,
        "vacant_action": vacant_action,
        "sensor_type": str(row.get("sensor_type") or ""),
        "device_class": str(row.get("device_class") or ""),
        "unit_of_measurement": str(row.get("unit_of_measurement") or row.get("unit") or ""),
        "ha_unique_id": str(row.get("ha_unique_id") or row.get("unique_id") or ""),
        "ha_device_id": str(row.get("ha_device_id") or row.get("device_id") or ""),
        "ha_entity_registry_id": str(row.get("ha_entity_registry_id") or ""),
        "ha_platform": str(row.get("ha_platform") or ""),
        **{key: row[key] for key in ("ha_area_id", "ha_entity_area_id", "ha_device_area_id", "area_source") if key in row},
    }
    raw_metadata = row.get("metadata")
    if isinstance(raw_metadata, dict):
        policy_source = str(
            raw_metadata.get("policy_source")
            or raw_metadata.get("management_source")
            or ""
        ).strip()
        if (
            raw_metadata.get("managed_policy_explicit") is True
            and policy_source
            in {
                "device_management_sync",
                "config_migration",
                "legacy_explicit_management",
            }
        ):
            # Only the canonical governance proof crosses into the decision
            # snapshot.  Runtime facts and bridge payloads cannot synthesize
            # management authority or carry arbitrary nested metadata.
            info["metadata"] = {
                "managed_policy_explicit": True,
                "policy_source": policy_source,
            }
    sampling_contract = row.get("signal_sampling_contract")
    if isinstance(sampling_contract, dict):
        info["signal_sampling_contract"] = copy.deepcopy(sampling_contract)
    if "supported_services" in row:
        supported_services = row.get("supported_services")
        info["supported_services"] = (
            copy.deepcopy(supported_services)
            if isinstance(supported_services, (list, tuple))
            else []
        )
    for key in (
        "behavior_dims",
        "capability_snapshot",
        "runtime_capability_binding",
        "runtime_capability_facts",
        "runtime_capability_live",
        "service_selection",
        "ha_control_policy",
        "learning_policy",
    ):
        value = row.get(key)
        if isinstance(value, (dict, list, tuple)):
            info[key] = copy.deepcopy(value)
    # Presence of a configured value matters: false, zero and an empty scope
    # are user choices, not requests to restore role/domain defaults.
    for key in (
        "roles", "disturbance", "disturbance_level", "sleep_safe", "shared_fixture",
        "shared_space_ids", "coverage_space_ids", "coverage_spaces", "control_zone",
        "energy_level", "risk_level", "can_trigger_enter", "can_confirm_leave",
        "can_block_turn_off", "can_localize_zone",
        "learnable", "season_sensitive", "ha_entity_category",
    ):
        if key in row:
            info[key] = copy.deepcopy(row[key])
    return entity_id, info

def device_info_row_from_addon_device(self, row: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    mapped = self._managed_device_info_row_from_addon_device(row)
    if mapped is None:
        return None
    entity_id, info = mapped
    if not self._is_listener_runtime_entity(entity_id, info):
        return None
    return entity_id, info

def managed_listener_entity_ids(self) -> list[str]:
    """Return managed entity ids that should receive HA state listeners."""
    try:
        self._reconcile_device_info_entity_ids_from_ha_registry()
    except Exception as exc:
        _LOGGER.debug("[Listeners] entity registry reconciliation failed: %s", exc)
    device_info = getattr(self, "device_info", {}) or {}
    if not isinstance(device_info, dict):
        device_info = {}
    listener_entity_ids = [
        eid
        for eid in device_info
        if isinstance(eid, str)
        and self._is_listener_runtime_entity(eid, device_info.get(eid) if isinstance(device_info.get(eid), dict) else {})
    ]
    environment_device_info = (
        getattr(self, "_environment_context_device_info", {}) or {}
    )
    if isinstance(environment_device_info, dict):
        # The gateway checks room occupancy and lighting need before lux can
        # request planning. Existing telemetry sampling still coalesces updates.
        listener_entity_ids.extend(
            entity_id
            for entity_id, raw_info in environment_device_info.items()
            if isinstance(entity_id, str)
            and environment_sensor_kind(
                entity_id,
                raw_info if isinstance(raw_info, dict) else {},
            ) in {"temperature", "humidity", "illuminance"}
        )
    return list(dict.fromkeys(listener_entity_ids))

def reconcile_device_info_entity_ids_from_ha_registry(self) -> bool:
    """Refresh identity metadata; renames await the Add-on lifecycle commit."""
    try:
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self.hass)
    except Exception as exc:
        _LOGGER.debug("[Listeners] entity registry unavailable: %s", exc)
        return False
    for entity_id, info in (getattr(self, "device_info", {}) or {}).items():
        if isinstance(info, dict):
            self._persist_ha_registry_metadata(entity_id, info, registry.async_get(entity_id))
    return False


def persist_ha_registry_metadata(self, entity_id: str, info: dict[str, Any], entry: Any) -> None:
    """Remember HA registry identity metadata so future HA-side renames can be reconciled."""
    if not isinstance(info, dict) or entry is None:
        return
    # A deleted/recreated registry entry is a different device, even if its
    # entity_id was reused. Keep the original binding for explicit reconciliation.
    if info.get("ha_entity_registry_id") and not registry_entry_matches(entity_id, info, entry):
        return
    metadata = registry_metadata(entry)
    updates = {key: value for key, value in metadata.items() if value and info.get(key) != value}
    if updates:
        info.update(updates)
        self._persist_device_registry_metadata(entity_id, info)

def persist_device_registry_metadata(self, entity_id: str, info: dict[str, Any]) -> None:
    if not callable(getattr(self, "_db_exec", None)):
        return
    now = self._listener_db_now_text()
    try:
        self._db_exec(
            "UPDATE devices SET ha_unique_id=?, ha_device_id=?, ha_entity_registry_id=?, ha_platform=?, updated=? WHERE entity_id=?",
            (
                str(info.get("ha_unique_id") or ""),
                str(info.get("ha_device_id") or ""),
                str(info.get("ha_entity_registry_id") or ""),
                str(info.get("ha_platform") or ""),
                now,
                entity_id,
            ),
        )
    except Exception as exc:
        _LOGGER.debug("[Listeners] device registry metadata persist skipped for %s: %s", entity_id, exc)

def persist_device_entity_id_migration(self, old_entity_id: str, new_entity_id: str, info: dict[str, Any]) -> None:
    if not callable(getattr(self, "_db_exec", None)):
        return
    now = self._listener_db_now_text()
    try:
        self._db_exec(
            "UPDATE devices SET entity_id=?, updated=? WHERE entity_id=?",
            (new_entity_id, now, old_entity_id),
        )
    except Exception as exc:
        _LOGGER.warning("[Listeners] device entity_id migration persist failed %s -> %s: %s", old_entity_id, new_entity_id, exc)
        return
    try:
        self._db_exec(
            "UPDATE devices SET ha_unique_id=?, ha_device_id=?, ha_entity_registry_id=?, ha_platform=?, updated=? WHERE entity_id=?",
            (
                str(info.get("ha_unique_id") or ""),
                str(info.get("ha_device_id") or ""),
                str(info.get("ha_entity_registry_id") or ""),
                str(info.get("ha_platform") or ""),
                now,
                new_entity_id,
            ),
        )
    except Exception as exc:
        _LOGGER.debug("[Listeners] migrated registry metadata persist skipped for %s: %s", new_entity_id, exc)

def refresh_listeners_if_entity_set_changed(self) -> bool:
    """Refresh HA state listeners when the managed entity id set drifts."""
    next_ids = set(self._managed_listener_entity_ids())
    current_ids = set(getattr(self, "_listener_entity_ids", set()) or set())
    if next_ids == current_ids:
        self._reconcile_active_listener_states(sorted(next_ids))
        return False
    self._refresh_listeners()
    return True


__all__ = [
    "listener_entity_metadata",
    "is_presence_listener_entity",
    "get_live_presence_occupancy_map",
    "reconcile_active_listener_states",
    "async_refresh_device_info_from_addon_devices",
    "is_actionable_sensor_runtime_entity",
    "is_listener_runtime_entity",
    "is_explicitly_managed_device_row",
    "managed_device_info_row_from_addon_device",
    "device_info_row_from_addon_device",
    "managed_listener_entity_ids",
    "reconcile_device_info_entity_ids_from_ha_registry",
    "persist_ha_registry_metadata",
    "persist_device_registry_metadata",
    "persist_device_entity_id_migration",
    "refresh_listeners_if_entity_set_changed",
]
