"""Existing device/script routing without changing execution authorization."""

from __future__ import annotations
from typing import Any
from .action_execution_context import ActionCall, ActionGuardContext, ActionGuardOutcome
from .action_execution_diagnostics import action_predispatch_failure
from .const import ACTION_PARAM_KEYS_LIGHT_SCENE


def _can_route(call: ActionCall, control_mode: str, direct_entity_only: bool) -> bool:
    off_with_params = call.service in ("turn_off", "close") and call.params
    precise_light = (
        call.domain == "light"
        and call.service == "turn_on"
        and any(
            key in call.params
            for key in (
                "brightness_pct",
                "brightness",
                "color_temp",
                "color_temp_kelvin",
                "rgb_color",
                "hs_color",
                "xy_color",
                "effect",
            )
        )
    )
    return bool(
        not direct_entity_only
        and control_mode == "shared"
        and call.domain in ("light", "switch", "cover", "fan", "climate")
        and call.service in ("turn_on", "turn_off", "open", "close", "toggle")
        and not off_with_params
        and not precise_light
        and not (call.domain in ("light", "switch") and call.service == "turn_off")
    )


def _associated_script(host: Any, call: ActionCall) -> str | None:
    script = host._find_associated_script(call.entity_id, call.service)
    if script:
        local = script.split(".", 1)[-1].lower()
        turnoff_script = any(
            key in local for key in ("turn_off", "guan_deng", "guan_bi", "all_off", "quan_guan")
        )
        if call.service == "turn_off" and turnoff_script:
            entity_local = call.entity_id.split(".", 1)[-1].lower()
            script_parts = set(local.replace("turn_off_", "").replace("_lights", "").split("_"))
            entity_parts = set(entity_local.split("_"))
            overlap = len(script_parts & entity_parts) / max(len(entity_parts), 1)
            if overlap < 0.8:
                host._sys_log(
                    "INFO",
                    f"[Action Router] 跳过路由 {call.entity_id} → {script}"
                    f"（turn_off 全关脚本保护，重叠率={overlap:.0%} < 80%，直接控制单个设备）",
                )
                script = None
    return script


def _apply_script_route(host: Any, call: ActionCall, script: str) -> None:
    domain = script.split(".")[0]
    had_params = bool(call.params)
    keep_precise = domain == "scene" and call.domain == "light" and call.service == "turn_on"
    host._sys_log(
        "INFO",
        f"[Action Router] {call.entity_id} → 路由至 {domain}: {script}"
        f"（优先使用脚本/场景"
        f"{', 保留灯光精细参数' if (had_params and keep_precise) else (', 丢弃 AI params' if had_params else '')}）",
    )
    call.params = (
        {key: value for key, value in call.params.items() if key in ACTION_PARAM_KEYS_LIGHT_SCENE}
        if keep_precise
        else {}
    )
    call.domain, call.entity_id, call.service = domain, script, "turn_on"


def _route_action(host: Any, call: ActionCall, *, direct_entity_only: bool) -> dict[str, Any] | None:
    if call.domain in ("script", "scene"):
        return None
    control_mode = host.device_info.get(call.entity_id, {}).get("control_mode", "shared")
    if control_mode == "ha":
        host._sys_log(
            "INFO",
            f"[管辖域] {call.entity_id} 为 HA优先模式，AI 跳过直接操作（建议: {call.service}）",
        )
        return {
            "entity_id": call.entity_id,
            "service": call.service,
            "status": "skip",
            "msg": "ha_control_mode",
        }
    if control_mode in ("ai", "shared") and _can_route(call, control_mode, direct_entity_only):
        script = _associated_script(host, call)
        if script:
            _apply_script_route(host, call, script)
    return None


def route_action(
    host: Any, context: ActionGuardContext, *, direct_entity_only: bool,
) -> ActionGuardOutcome | None:
    """Routing only reads evidence and changes the planned target; no device I/O."""
    try:
        result = _route_action(host, context.call, direct_entity_only=direct_entity_only)
    except Exception as exc:
        return action_predispatch_failure(context, exc, operation="action_route", code="action_route_failed")
    return ActionGuardOutcome(result) if result is not None else None
