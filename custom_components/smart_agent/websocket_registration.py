"""HA WebSocket command registration helpers for the SmartAgent host."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components import websocket_api


WEBSOCKET_COMMAND_NAMES: tuple[str, ...] = (
    "ws_get_devices",
    "ws_get_habits",
    "ws_get_rules",
    "ws_get_ai_scenes",
    "ws_get_energy_stats",
    "ws_get_transactions",
    "ws_get_decision_stats",
    "ws_get_behavior_patterns",
    "ws_get_ai_actions",
    "ws_get_sys_log",
    "ws_get_terminal_log",
    "ws_get_frigate_cameras",
    "ws_get_learning_stats",
    "ws_get_frigate_zones",
    "ws_save_frigate_zone",
    "ws_get_presence_sensors",
    "ws_save_sensor_type",
    "ws_get_room_topology",
    "ws_list_backups",
    "ws_attest_field_canary_operator_identity",
    "ws_publish_field_canary_operator_approval",
    "ws_issue_field_canary_promotion_grant",
    "ws_prepare_field_canary_promotion_grant_revocation",
    "ws_commit_field_canary_promotion_grant_revocation",
)


def validate_websocket_registration(commands: Iterable[Any]) -> None:
    """Ensure the host registers exactly the declared WebSocket matrix."""
    names = tuple(getattr(command, "__name__", "") for command in commands)
    if names != WEBSOCKET_COMMAND_NAMES:
        raise RuntimeError(
            "SmartAgent WebSocket registration order drifted: "
            f"expected={WEBSOCKET_COMMAND_NAMES!r} actual={names!r}"
        )


def register_smart_agent_websocket_commands(
    hass: Any, commands: Iterable[Any]
) -> None:
    """Register SmartAgent HA WebSocket commands in canonical host order."""
    command_list = tuple(commands)
    validate_websocket_registration(command_list)
    for command in command_list:
        websocket_api.async_register_command(hass, command)
