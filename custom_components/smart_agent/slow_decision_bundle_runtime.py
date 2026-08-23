"""Portable slow-decision bundle orchestration for the HA coordinator.

The coordinator retains the implementations that acquire HA state, construct
the admitted snapshot, resolve areas, and read its local clock.  This module
only orchestrates those injected/owner ports and projects the request bundle.
"""
from __future__ import annotations

import json
import logging
from typing import Any


_LOGGER = logging.getLogger(__name__)
_FAST_PATH_HANDOFF_SOURCES = frozenset(
    {
        "addon_fast_path_409",
        "addon_fast_path_disabled",
        "addon_fast_path_low_confidence",
        "addon_fast_path_no_match",
    }
)


def _source_trace_projection(
    owner: Any,
    raw_source_trace_context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    fast_path_execution_audit = owner._normalize_fast_path_execution_audit(
        raw_source_trace_context
    )
    if fast_path_execution_audit:
        return dict(fast_path_execution_audit), fast_path_execution_audit
    source = str(raw_source_trace_context.get("source") or "").strip()
    if source not in _FAST_PATH_HANDOFF_SOURCES:
        return {}, {}
    projected = {
        key: json.loads(json.dumps(value, ensure_ascii=False, default=str))
        if isinstance(value, (dict, list))
        else value
        for key in (
            "source",
            "transaction_id",
            "correlation_id",
            "world_snapshot_id",
            "occupancy_cycle_id",
            "reason",
            "decision_trace",
            "event_claim",
        )
        if (value := raw_source_trace_context.get(key)) not in (None, "")
    }
    return projected, {}


def _snapshot_projection(
    owner: Any,
    *,
    entity_id: str,
    normalized_source: str,
    state_get: Any,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    snapshot: dict[str, Any] = {}
    snapshot_builder = getattr(owner, "_build_addon_fast_path_snapshot", None)
    if callable(snapshot_builder):
        try:
            if normalized_source.startswith("patrol"):
                snapshot = snapshot_builder(
                    entity_id,
                    include_environment_devices=True,
                )
            else:
                snapshot = snapshot_builder(entity_id)
        except Exception as exc:
            _LOGGER.debug("[决策] 慢脑快照构建失败: %s", exc)
            snapshot = {}

    raw_device_info = (
        snapshot.get("device_info")
        if isinstance(snapshot.get("device_info"), dict)
        else getattr(owner, "device_info", {})
    )
    device_info = dict(raw_device_info or {}) if isinstance(raw_device_info, dict) else {}
    raw_states = snapshot.get("states") if isinstance(snapshot.get("states"), dict) else {}
    states = dict(raw_states or {}) if isinstance(raw_states, dict) else {}
    raw_state_observations = (
        snapshot.get("state_observations")
        if isinstance(snapshot.get("state_observations"), dict)
        else {}
    )
    state_observations = {
        str(managed_entity_id): dict(observation)
        for managed_entity_id, observation in raw_state_observations.items()
        if isinstance(observation, dict)
    }
    if callable(state_get):
        for managed_entity_id in device_info:
            if str(states.get(managed_entity_id) or "").strip():
                continue
            state_obj = state_get(managed_entity_id)
            if state_obj is not None:
                states[managed_entity_id] = str(
                    getattr(state_obj, "state", "") or ""
                )

    capability_snapshot = (
        snapshot.get("device_capability_snapshot")
        if isinstance(snapshot.get("device_capability_snapshot"), dict)
        else {}
    )
    if not capability_snapshot:
        getter = getattr(owner, "get_device_capability_snapshot", None)
        if callable(getter):
            try:
                candidate = getter()
                if isinstance(candidate, dict):
                    capability_snapshot = candidate
            except Exception as exc:
                _LOGGER.debug("[决策] 慢脑设备能力快照构建失败: %s", exc)
    raw_environment_context = (
        snapshot.get("environment_context")
        if isinstance(snapshot.get("environment_context"), dict)
        else {}
    )
    environment_context = (
        dict(raw_environment_context or {})
        if isinstance(raw_environment_context, dict)
        else {}
    )
    return (
        snapshot,
        device_info,
        states,
        state_observations,
        capability_snapshot,
        environment_context,
    )


def _trigger_scope(
    owner: Any,
    *,
    entity_id: str,
    snapshot: dict[str, Any],
    device_info: dict[str, Any],
    trigger_space_id: str,
) -> tuple[str, str, str]:
    trigger_info = device_info.get(entity_id, {}) if entity_id else {}
    if not isinstance(trigger_info, dict):
        trigger_info = {}
    trigger_room = str(
        trigger_info.get("room")
        or trigger_info.get("area")
        or snapshot.get("trigger_room")
        or ""
    ).strip()
    derived_trigger_space_id = str(
        trigger_info.get("space_id")
        or trigger_info.get("room_id")
        or trigger_info.get("area_id")
        or trigger_room
        or ""
    ).strip()
    requested_trigger_space_id = str(trigger_space_id or "").strip()
    canonical_space_id = requested_trigger_space_id or derived_trigger_space_id
    if requested_trigger_space_id and not trigger_room:
        trigger_room = requested_trigger_space_id
    if not trigger_room and entity_id:
        area_lookup = getattr(owner, "_get_entity_area", None)
        if callable(area_lookup):
            try:
                trigger_room = str(area_lookup(entity_id) or "").strip()
            except Exception:
                trigger_room = ""
    return trigger_room, canonical_space_id, requested_trigger_space_id


def _patrol_projection(
    owner: Any,
    *,
    normalized_source: str,
    requested_trigger_space_id: str,
    trigger_space_id: str,
    trigger_room: str,
    now: Any,
    device_info: dict[str, Any],
    states: dict[str, Any],
    state_observations: dict[str, Any],
    capability_snapshot: dict[str, Any],
    presence_snapshot: dict[str, Any],
    scope_patrol_snapshot: Any,
    build_patrol_environment: Any,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    if requested_trigger_space_id and normalized_source.startswith("patrol"):
        (
            device_info,
            states,
            state_observations,
            capability_snapshot,
        ) = scope_patrol_snapshot(
            requested_space_id=requested_trigger_space_id,
            device_info=device_info,
            states=states,
            state_observations=state_observations,
            capability_snapshot=capability_snapshot,
            low_risk_entity_ids=getattr(owner, "_patrol_low_risk_entity_ids", ()),
        )

    patrol_execution_policy: dict[str, Any] = {}
    stale_environment_entity_ids: list[str] = []
    if normalized_source.startswith("patrol"):
        quiet_start = str(
            getattr(owner, "_patrol_quiet_hours_start", "") or ""
        ).strip()
        quiet_end = str(
            getattr(owner, "_patrol_quiet_hours_end", "") or ""
        ).strip()
        (
            states,
            state_observations,
            patrol_execution_policy,
            stale_environment_entity_ids,
        ) = build_patrol_environment(
            now=now,
            device_info=device_info,
            states=states,
            state_observations=state_observations,
            presence_snapshot=presence_snapshot,
            trigger_space_id=trigger_space_id,
            trigger_room=trigger_room,
            interval_minutes=getattr(owner, "_patrol_interval_minutes", 15),
            quiet_start=quiet_start,
            quiet_end=quiet_end,
            low_risk_entity_ids=getattr(owner, "_patrol_low_risk_entity_ids", ()),
            quiet_hours_active=owner._patrol_quiet_hours_active,
        )
    return (
        device_info,
        states,
        state_observations,
        capability_snapshot,
        patrol_execution_policy,
        stale_environment_entity_ids,
    )


def _context_text(
    owner: Any,
    *,
    trigger: str,
    one_off_prompt: str,
    parsed: dict[str, Any],
    entity_id: str,
    trigger_room: str,
    trigger_space_id: str,
    normalized_source: str,
    audit_pending: bool,
    source_trace_context: dict[str, Any],
    fast_path_execution_audit: dict[str, Any],
    automation_policy_section: str,
    snapshot: dict[str, Any],
    stale_environment_entity_ids: list[str],
) -> str:
    context_parts = [
        str(one_off_prompt or "").strip(),
        f"触发事件：{trigger}",
    ]
    if audit_pending:
        context_parts.append(
            "[fast_path_audit] Fast path already executed a provisional low-risk action. "
            "Audit the action, do not repeat identical light actions, and return "
            "approve/adjust/observe_only."
        )
    if fast_path_execution_audit:
        context_parts.append(
            "[fast_path_execution_audit] "
            + json.dumps(
                fast_path_execution_audit,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    elif source_trace_context.get("source") == "addon_fast_path_409":
        context_parts.append(
            "[fast_path_409_trace] "
            f"transaction_id={source_trace_context.get('transaction_id') or '-'} "
            f"correlation_id={source_trace_context.get('correlation_id') or '-'} "
            f"world_snapshot_id={source_trace_context.get('world_snapshot_id') or '-'} "
            f"reason={source_trace_context.get('reason') or '-'}"
        )
    elif str(source_trace_context.get("source") or "").strip() in {
        "addon_fast_path_disabled",
        "addon_fast_path_low_confidence",
        "addon_fast_path_no_match",
    }:
        context_parts.append(
            "[fast_path_handoff] "
            f"correlation_id={source_trace_context.get('correlation_id') or '-'} "
            f"reason={source_trace_context.get('reason') or '-'}"
        )
    if automation_policy_section:
        context_parts.append(automation_policy_section)
    if entity_id:
        context_parts.append(f"触发实体：{entity_id}")
    if trigger_room:
        context_parts.append(f"触发空间：{trigger_room}")
    if trigger_space_id and trigger_space_id != trigger_room:
        context_parts.append(f"规范空间 ID：{trigger_space_id}")
    if normalized_source.startswith("patrol"):
        snapshot_time = str(snapshot.get("observed_at") or "").strip()
        if snapshot_time:
            context_parts.append(f"本轮绝对状态快照采集时间：{snapshot_time}")
        if stale_environment_entity_ids:
            context_parts.append(
                "以下环境传感器观测已陈旧，旧数值已从可决策状态中剔除，"
                "不得用于触发动作："
                + "、".join(stale_environment_entity_ids)
            )
    if parsed.get("old_state") or parsed.get("new_state"):
        context_parts.append(
            f"状态变化：{parsed.get('old_state') or '?'} -> "
            f"{parsed.get('new_state') or '?'}"
        )
    if owner._is_addon_presence_clear(parsed):
        context_parts.append(
            "触发约束：占用清除。binary_sensor on->off 只表示近期未检测到活动，"
            "不等于确认无人，不等于确认有人离开；没有 leave_qualified 或多源确认时，"
            "不要生成“有人离开，准备关闭灯光”的场景。"
        )
    return "\n".join(part for part in context_parts if part)


def build_addon_slow_decision_bundle(
    owner: Any,
    trigger: str,
    *,
    scope_patrol_snapshot: Any,
    build_patrol_environment: Any,
    state_get: Any = None,
    one_off_prompt: str = "",
    source: str = "listener",
    user_explicit_voice: bool = False,
    source_trace_context: dict[str, Any] | None = None,
    trigger_space_id: str = "",
    causal_events: list[dict[str, Any]] | None = None,
    task_occurrence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the rich bundle used by add-on slow decisions."""
    parsed = owner._parse_addon_decision_trigger(trigger)
    normalized_source = str(source or "").strip().lower()
    audit_pending = owner._is_fast_path_audit_prompt(one_off_prompt)
    raw_source_trace_context = (
        dict(source_trace_context) if isinstance(source_trace_context, dict) else {}
    )
    source_trace_context, fast_path_execution_audit = _source_trace_projection(
        owner,
        raw_source_trace_context,
    )
    entity_id = parsed.get("trigger_entity_id", "")
    (
        snapshot,
        device_info,
        states,
        state_observations,
        capability_snapshot,
        environment_context,
    ) = _snapshot_projection(
        owner,
        entity_id=entity_id,
        normalized_source=normalized_source,
        state_get=state_get,
    )
    trigger_room, trigger_space_id, requested_trigger_space_id = _trigger_scope(
        owner,
        entity_id=entity_id,
        snapshot=snapshot,
        device_info=device_info,
        trigger_space_id=trigger_space_id,
    )
    now = owner._ha_local_now()
    presence_snapshot = (
        snapshot.get("presence_snapshot")
        if isinstance(snapshot.get("presence_snapshot"), dict)
        else {}
    )
    (
        device_info,
        states,
        state_observations,
        capability_snapshot,
        patrol_execution_policy,
        stale_environment_entity_ids,
    ) = _patrol_projection(
        owner,
        normalized_source=normalized_source,
        requested_trigger_space_id=requested_trigger_space_id,
        trigger_space_id=trigger_space_id,
        trigger_room=trigger_room,
        now=now,
        device_info=device_info,
        states=states,
        state_observations=state_observations,
        capability_snapshot=capability_snapshot,
        presence_snapshot=presence_snapshot,
        scope_patrol_snapshot=scope_patrol_snapshot,
        build_patrol_environment=build_patrol_environment,
    )
    device_table = owner._render_addon_decision_device_table(
        device_info,
        states,
        state_observations=state_observations,
        trigger_room=trigger_room,
        trigger_space_id=trigger_space_id,
    )
    occupancy_section = owner._render_addon_decision_occupancy_section(
        presence_snapshot,
        trigger_room=trigger_space_id or trigger_room,
    )
    automation_policy_section = owner._render_addon_decision_automation_policy_section(
        getattr(owner, "_ai_scenes_cache", []),
        getattr(owner, "_ha_scenes", []),
        getattr(owner, "_ha_scripts", []),
        trigger_room=trigger_room,
    )
    context_text = _context_text(
        owner,
        trigger=trigger,
        one_off_prompt=one_off_prompt,
        parsed=parsed,
        entity_id=entity_id,
        trigger_room=trigger_room,
        trigger_space_id=trigger_space_id,
        normalized_source=normalized_source,
        audit_pending=audit_pending,
        source_trace_context=source_trace_context,
        fast_path_execution_audit=fast_path_execution_audit,
        automation_policy_section=automation_policy_section,
        snapshot=snapshot,
        stale_environment_entity_ids=stale_environment_entity_ids,
    )
    weekdays = (
        "星期一",
        "星期二",
        "星期三",
        "星期四",
        "星期五",
        "星期六",
        "星期日",
    )
    is_voice = normalized_source == "voice" or normalized_source.startswith("voice_")
    is_user_explicit = bool(is_voice and user_explicit_voice is True) or (
        normalized_source == "manual"
    )
    decision_objective = (
        "patrol_reconciliation"
        if normalized_source.startswith("patrol")
        else "fast_path_execution_audit"
        if audit_pending
        else ""
    )
    return {
        "trigger": str(trigger or ""),
        "context_text": context_text,
        "source": f"ha_bridge_{source}",
        "is_voice": is_voice,
        "cmd_source": "USER_EXPLICIT" if is_user_explicit else "SENSOR",
        "decision_objective": decision_objective,
        "time_str": now.strftime("%H:%M"),
        "day_str": f"{now.strftime('%Y-%m-%d')} {weekdays[now.weekday()]}",
        "mode": owner._mode,
        "engine": owner.engine,
        "confidence_auto": owner.confidence_auto,
        "confidence_notify": owner.confidence_notify,
        "trigger_entity_id": entity_id,
        "old_state": parsed.get("old_state", ""),
        "new_state": parsed.get("new_state", ""),
        "trigger_room": trigger_room,
        "trigger_space_id": trigger_space_id,
        "audit_pending": audit_pending,
        "provisional_execution": audit_pending,
        "audit_source": "fast_path" if audit_pending else "",
        "device_info": device_info,
        "states": states,
        "state_observations": state_observations,
        "observed_at": str(snapshot.get("observed_at") or ""),
        "created_at": str(snapshot.get("created_at") or ""),
        "environment_context": environment_context,
        "presence_snapshot": presence_snapshot,
        "space_snapshot": snapshot.get("space_snapshot")
        if isinstance(snapshot.get("space_snapshot"), dict)
        else {},
        "device_capability_snapshot": capability_snapshot,
        "room_topology": snapshot.get("room_topology")
        if isinstance(snapshot.get("room_topology"), dict)
        else {},
        "device_table": device_table,
        "occupancy_section": occupancy_section,
        "automation_policy_section": automation_policy_section,
        "patrol_execution_policy": patrol_execution_policy,
        "source_trace_context": source_trace_context,
        "fast_path_execution_audit": fast_path_execution_audit,
        "parent_transaction_id": str(
            source_trace_context.get("transaction_id") or ""
        ),
        "parent_execution_transaction_id": str(
            source_trace_context.get("execution_transaction_id") or ""
        ),
        "parent_decision_trace": source_trace_context.get("decision_trace")
        if isinstance(source_trace_context.get("decision_trace"), dict)
        else {},
        "parent_correlation_id": str(
            source_trace_context.get("correlation_id") or ""
        ),
        "parent_world_snapshot_id": str(
            source_trace_context.get("world_snapshot_id") or ""
        ),
        "event_claim_continuation": dict(source_trace_context.get("event_claim"))
        if isinstance(source_trace_context.get("event_claim"), dict)
        else {},
        "causal_events": [
            dict(item)
            for item in (causal_events or [])[:50]
            if isinstance(item, dict)
        ],
        "task_occurrence": dict(task_occurrence)
        if isinstance(task_occurrence, dict)
        else {},
        "occupancy_cycle_id": str(
            snapshot.get("occupancy_cycle_id")
            or source_trace_context.get("occupancy_cycle_id")
            or ""
        ).strip(),
    }


__all__ = ["build_addon_slow_decision_bundle"]
