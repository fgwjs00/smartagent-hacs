"""Pure action-shape helpers shared by fast-path and HA execution."""

from __future__ import annotations

from typing import Any


def action_entity_id(action: Any) -> str:
    """Return the effective entity id for supported planner action shapes."""
    if not isinstance(action, dict):
        return ""
    target = action.get("target")
    target_entity_id = (
        target.get("entity_id", "")
        if isinstance(target, dict)
        else ""
    )
    return str(
        action.get("entity_id")
        or action.get("entity")
        or target_entity_id
        or ""
    ).strip()


def action_domain(action: Any) -> str:
    """Return the effective HA domain for supported planner action shapes."""
    if not isinstance(action, dict):
        return ""
    entity_id = action_entity_id(action)
    service_raw = str(
        action.get("service")
        or action.get("action")
        or action.get("command")
        or ""
    ).strip()
    if "." in service_raw and not action.get("domain"):
        return service_raw.split(".", 1)[0].strip().lower()
    return str(
        action.get("domain")
        or (entity_id.split(".", 1)[0] if "." in entity_id else "")
    ).strip().lower()


def action_requires_presence_refresh(
    action: Any,
    *,
    dim_to_off_brightness_pct: int = 5,
) -> bool:
    """Return whether execution will apply the light/switch turn-off guard."""
    if not isinstance(action, dict):
        return False

    service_raw = str(
        action.get("service")
        or action.get("action")
        or action.get("command")
        or ""
    ).strip()
    if "." in service_raw and not action.get("domain"):
        _domain, service = service_raw.split(".", 1)
    else:
        service = service_raw
    domain = action_domain(action)

    params = (
        action.get("params")
        or action.get("data")
        or action.get("service_data")
        or {}
    )
    if (
        service == "turn_on"
        and domain == "light"
        and isinstance(params, dict)
        and "brightness_pct" in params
    ):
        try:
            brightness_pct = int(float(params.get("brightness_pct")))
        except (TypeError, ValueError):
            brightness_pct = None
        if (
            brightness_pct is not None
            and 0 <= brightness_pct <= dim_to_off_brightness_pct
        ):
            service = "turn_off"

    return domain in {"light", "switch"} and service == "turn_off"
