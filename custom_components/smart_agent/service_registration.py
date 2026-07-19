"""HA service registration helpers for the SmartAgent host."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .const import DOMAIN


@dataclass(frozen=True, slots=True)
class ServiceRegistration:
    name: str
    handler: Any
    schema: Any | None = None


SERVICE_REGISTRATION_NAMES: tuple[str, ...] = (
    "discover_devices",
    "sync_rooms_to_ha",
    "save_room_topology",
    "batch_add_devices",
    "add_device",
    "delete_device",
    "update_device",
    "add_habit",
    "delete_habit",
    "toggle_habit_lock",
    "add_rule",
    "delete_rule",
    "toggle_rule_lock",
    "manual_inference",
    "clear_overrides",
    "report_correction",
    "delete_behavior_pattern",
    "set_mode",
    "set_showroom_scene",
    "approve_ai_scene",
    "reject_ai_scene",
    "delete_ai_scene",
    "trigger_ai_scene",
    "create_scene_from_text",
    "rollback_transaction",
    "refresh_transactions",
    "set_device_control_mode",
    "batch_set_control_mode",
    "update_showroom_scene_config",
    "update_config",
    "tts_test",
    "run_pattern_analysis",
    "verify_license",
    "voice_command",
)
SERVICE_UNLOAD_NAMES: tuple[str, ...] = (
    *SERVICE_REGISTRATION_NAMES,
    "dismiss_ai_action",
)


def validate_service_registration(registrations: Iterable[ServiceRegistration]) -> None:
    """Ensure the host registers exactly the declared service matrix."""
    names = tuple(registration.name for registration in registrations)
    if names != SERVICE_REGISTRATION_NAMES:
        raise RuntimeError(
            "SmartAgent service registration order drifted: "
            f"expected={SERVICE_REGISTRATION_NAMES!r} actual={names!r}"
        )


def register_smart_agent_services(
    hass: Any, registrations: Iterable[ServiceRegistration]
) -> None:
    """Register SmartAgent HA services in canonical host order."""
    registration_list = tuple(registrations)
    validate_service_registration(registration_list)
    for registration in registration_list:
        if registration.schema is None:
            hass.services.async_register(DOMAIN, registration.name, registration.handler)
        else:
            hass.services.async_register(
                DOMAIN,
                registration.name,
                registration.handler,
                schema=registration.schema,
            )


def remove_smart_agent_services(hass: Any) -> None:
    """Remove registered and legacy SmartAgent HA services."""
    for service_name in SERVICE_UNLOAD_NAMES:
        hass.services.async_remove(DOMAIN, service_name)
