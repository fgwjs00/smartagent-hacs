"""Thin, allowlisted MQTT-to-HA bridge for LD2410 maintenance snapshots."""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any


_LOGGER = logging.getLogger(__name__)
_TOPIC_RE = re.compile(r"^zigbee2mqtt/(0x[0-9a-f]{16})$", re.IGNORECASE)
_BRIDGE_VERSION = 1

# This list mirrors the public 0xFC10 maintenance contract. Password material
# and arbitrary Zigbee2MQTT state never cross this boundary.
_ALLOWED_FIELDS = frozenset({
    "target_state", "moving_distance_cm", "moving_energy", "still_distance_cm", "still_energy",
    "detection_distance_cm", "max_moving_gate", "max_still_gate", "no_target_delay_s",
    "distance_resolution", "bluetooth_desired_state", "password_configured", "light_control_mode",
    "light_threshold", "out_default_level", "maintenance_contract_version", "config_revision",
    "config_hash", "module_firmware_version", "module_mac", "noise_calibration_state",
    "diagnostic_session_state", "diagnostic_expires_at", "last_command_correlation",
    "last_command_status", "product_id", "hardware_revision", "protocol", "firmware_version",
    "bootselect_version", "schema_version", "firmware_update_transaction_id", "firmware_update_phase",
    "moving_gate_energy", "still_gate_energy", "ld_light_value", "out_state", "raw_temperature",
    "raw_humidity", "temperature_offset", "humidity_residual", "calibration_version",
    "calibrated_at_epoch_s", "calibration_status", "calibration_source", "calibration_quality",
    "sensor_error_count",
    *{f"moving_sensitivity_{gate}" for gate in range(9)},
    *{f"still_sensitivity_{gate}" for gate in range(9)},
})


def maintenance_bridge_entity_id(ieee_address: str) -> str:
    """Return the deterministic internal HA state entity for one Zigbee IEEE address."""
    normalized = str(ieee_address or "").lower()
    if not re.fullmatch(r"0x[0-9a-f]{16}", normalized):
        raise ValueError("invalid_zigbee_ieee_address")
    return f"sensor.smartagent_ld2410_maintenance_{normalized}"


def _json_safe(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_json_safe(item) for item in value)
    return False


def build_maintenance_snapshot(topic: str, payload: Any) -> tuple[str, str, dict[str, Any]] | None:
    """Normalize one Zigbee2MQTT state message without inventing maintenance capability."""
    match = _TOPIC_RE.fullmatch(str(topic or ""))
    if match is None or not isinstance(payload, dict):
        return None
    ieee_address = match.group(1).lower()
    contract_value = payload.get("maintenance_contract_version")
    if isinstance(contract_value, bool):
        return None
    try:
        contract_version = int(contract_value)
    except (TypeError, ValueError):
        return None
    if contract_version < 1:
        return None

    attributes = {
        key: value
        for key, value in payload.items()
        if key in _ALLOWED_FIELDS and _json_safe(value)
    }
    attributes["maintenance_contract_version"] = contract_version
    attributes["zigbee_ieee_address"] = ieee_address
    attributes["smartagent_maintenance_bridge_version"] = _BRIDGE_VERSION
    return maintenance_bridge_entity_id(ieee_address), "ready", attributes


class LD2410MaintenanceMQTTBridge:
    """Keep a private HA state mirror for raw Zigbee2MQTT maintenance snapshots."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass
        self._unsubscribe: Callable[[], None] | None = None

    async def async_start(self) -> None:
        try:
            from homeassistant.components.mqtt import async_subscribe
        except ImportError:
            _LOGGER.warning("LD2410 maintenance bridge is unavailable because MQTT is not loaded")
            return
        try:
            self._unsubscribe = await async_subscribe(
                self._hass,
                "zigbee2mqtt/+",
                self._async_handle_message,
            )
        except Exception:
            _LOGGER.exception("LD2410 maintenance MQTT bridge subscription failed")
            return
        _LOGGER.info("LD2410 maintenance MQTT bridge subscribed to Zigbee2MQTT state topics")

    def stop(self) -> None:
        unsubscribe, self._unsubscribe = self._unsubscribe, None
        if unsubscribe is not None:
            unsubscribe()

    async def _async_handle_message(self, message: Any) -> None:
        try:
            raw = getattr(message, "payload", b"")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            payload = json.loads(raw) if isinstance(raw, str) else raw
            snapshot = build_maintenance_snapshot(getattr(message, "topic", ""), payload)
        except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError):
            return
        if snapshot is None:
            return
        entity_id, state, attributes = snapshot
        self._hass.states.async_set(entity_id, state, attributes)
