"""The existing showroom tier policy and its per-batch evidence snapshot."""

from __future__ import annotations
from typing import Any
from .action_execution_context import (
    ActionCall,
    ActionGuardContext,
    ActionGuardOutcome,
    ShowroomBatchEvidence,
)
from .const import (
    MODE_SHOWROOM,
    SHOWROOM_DISPLAY_DIM_PCT,
    SHOWROOM_OCCUPIED_PCT,
    SHOWROOM_CORE_MIN_PCT,
)


def _showroom_occupied(sensors: list[Any]) -> bool:
    if not sensors:
        return True
    occupied = any(state == "on" for _, state in sensors)
    if not occupied and all(state in ("unknown", "unavailable") for _, state in sensors):
        return True
    return occupied


async def collect_showroom_evidence(host: Any) -> ShowroomBatchEvidence:
    # Contract: legacy_presence_evidence_only; canonical guards use _room_occupancy_entries().
    legacy_map = host._get_room_occupancy_map()
    counts = host._get_room_person_counts() if hasattr(host, "_get_room_person_counts") else {}
    rules = host._build_locked_people_rules() if hasattr(host, "_build_locked_people_rules") else []
    minute = host._ha_local_minute_of_day()
    working = (
        minute is not None and host.showroom_biz_start_min <= minute < host.showroom_biz_end_min
    )
    occupied, tiers = False, {}
    if host._mode == MODE_SHOWROOM:
        area = host.showroom_area_name
        sensors = legacy_map.get(area, []) if area else []
        occupied = _showroom_occupied(sensors)
        for entity, info in host.device_info.items():
            if not entity.startswith("light."):
                continue
            room = info.get("room", "")
            if area and room == area and room not in host.showroom_excluded_subareas:
                tiers[entity] = await host.hass.async_add_executor_job(
                    host._get_showroom_light_tier_v2, entity
                )
    return ShowroomBatchEvidence(counts, rules, working, occupied, tiers)


def evaluate_people_rule(
    host: Any, context: ActionGuardContext, evidence: ShowroomBatchEvidence
) -> ActionGuardOutcome | None:
    call = context.call
    if (
        call.domain == "light"
        and call.service == "turn_on"
        and context.batch.cmd_source != "USER_EXPLICIT"
    ):
        room = ((host.device_info.get(call.entity_id) or {}).get("room") or "").strip()
        if not room and hasattr(host, "_get_entity_area"):
            room = (host._get_entity_area(call.entity_id) or "").strip()
        if room:
            count = int((evidence.people_counts or {}).get(room, 0) or 0)
            blocked, rule = host._is_light_blocked_by_people_rule(
                entity_id=call.entity_id,
                room=room,
                person_count=count,
                parsed_rules=evidence.people_rules,
            )
            if blocked:
                host._sys_log(
                    "WARN",
                    f"[P1人数阈值] 阻止 turn_on({call.entity_id})：{room} 当前人数={count}，未满足锁定规则({rule}人)",
                )
                return ActionGuardOutcome(
                    {
                        "entity_id": call.entity_id,
                        "service": call.service,
                        "status": "blocked_p1_people",
                        "msg": f"{room}人数{count}未满足锁定阈值",
                    },
                    blocked=1,
                )
    return None


def _apply_occupied_tier(host: Any, call: ActionCall, tier: str) -> None:
    if call.service == "turn_off":
        if tier in ("core", "display"):
            host._sys_log(
                "INFO",
                f"[展厅P1] {call.entity_id}({tier}) 展厅有人，turn_off 转为 turn_on {SHOWROOM_OCCUPIED_PCT}%",
            )
            call.service, call.params = "turn_on", {"brightness_pct": SHOWROOM_OCCUPIED_PCT}
    elif call.service == "turn_on":
        brightness = call.params.get("brightness_pct")
        if tier == "core" and brightness is not None and brightness < SHOWROOM_CORE_MIN_PCT:
            host._sys_log(
                "INFO",
                f"[展厅P1] {call.entity_id}(core) 亮度下限保护：{brightness}% → {SHOWROOM_CORE_MIN_PCT}%",
            )
            call.params["brightness_pct"] = SHOWROOM_CORE_MIN_PCT
        elif brightness is None:
            call.params["brightness_pct"] = SHOWROOM_OCCUPIED_PCT


def _apply_vacant_core_tier(host: Any, call: ActionCall) -> ActionGuardOutcome | None:
    if call.service == "turn_off":
        host._sys_log(
            "WARN", f"[展厅P1] 阻止 turn_off({call.entity_id})：Core 层在营业时间内禁止关闭"
        )
        return ActionGuardOutcome(
            {
                "entity_id": call.entity_id,
                "service": call.service,
                "status": "blocked_p1",
                "msg": "P1 core",
            },
            blocked=1,
        )
    if (
        call.service == "turn_on"
        and call.params.get("brightness_pct") is not None
        and call.params["brightness_pct"] < SHOWROOM_CORE_MIN_PCT
    ):
        host._sys_log(
            "INFO",
            f"[展厅P1] {call.entity_id}(core) 无人亮度下限：{call.params['brightness_pct']}% → {SHOWROOM_CORE_MIN_PCT}%",
        )
        call.params["brightness_pct"] = SHOWROOM_CORE_MIN_PCT
    return None


def _apply_vacant_display_tier(host: Any, call: ActionCall) -> None:
    if call.service == "turn_off":
        host._sys_log(
            "INFO",
            f"[展厅分层] {call.entity_id}(display) 无人节能：turn_off → turn_on {SHOWROOM_DISPLAY_DIM_PCT}%",
        )
        call.service, call.params = "turn_on", {"brightness_pct": SHOWROOM_DISPLAY_DIM_PCT}
    elif (
        call.service == "turn_on"
        and call.params.get("brightness_pct") is not None
        and call.params["brightness_pct"] < SHOWROOM_DISPLAY_DIM_PCT
    ):
        host._sys_log(
            "INFO",
            f"[展厅分层] {call.entity_id}(display) 无人节能：亮度限制至 {SHOWROOM_DISPLAY_DIM_PCT}%",
        )
        call.params["brightness_pct"] = SHOWROOM_DISPLAY_DIM_PCT


async def evaluate_showroom_tier(
    host: Any, context: ActionGuardContext, evidence: ShowroomBatchEvidence
) -> ActionGuardOutcome | None:
    call = context.call
    if host._mode == MODE_SHOWROOM and call.domain == "light":
        info = host.device_info.get(call.entity_id, {})
        room = (info.get("room") or "").strip()
        area = host.showroom_area_name
        showroom_light = bool(area) and room == area and room not in host.showroom_excluded_subareas
        authenticated_turnon = context.batch.authenticated_user_intent and call.service == "turn_on"
        if showroom_light and not authenticated_turnon:
            tier = evidence.light_tiers.get(
                call.entity_id
            ) or await host.hass.async_add_executor_job(
                host._get_showroom_light_tier_v2, call.entity_id
            )
            if evidence.occupied:
                _apply_occupied_tier(host, call, tier)
            elif evidence.working_hour:
                if tier == "core":
                    return _apply_vacant_core_tier(host, call)
                if tier == "display":
                    _apply_vacant_display_tier(host, call)
            else:
                host._sys_log(
                    "INFO", f"[展厅下班] 非营业时间且无人，放行对 {call.entity_id} 的操作"
                )
    return None
