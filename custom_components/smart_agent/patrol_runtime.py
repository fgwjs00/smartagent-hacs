"""Portable patrol scheduling and add-on orchestration for the HA coordinator.

The coordinator retains HA snapshot acquisition and lifecycle ownership.  This
module only consumes the owner's already-admitted snapshots and add-on client;
it does not import Home Assistant, call HA services, or mint execution authority.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable


PatrolOccurrenceBuilder = Callable[..., dict[str, str]]


def filter_patrol_reconciliation_actions(
    actions: list[dict[str, Any]],
    bundle: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply deterministic patrol evidence and disturbance gates after inference."""

    policy = (
        bundle.get("patrol_execution_policy")
        if isinstance(bundle.get("patrol_execution_policy"), dict)
        else {}
    )
    if not policy:
        return list(actions), []

    allowlist = {
        str(value or "").strip().lower()
        for value in policy.get("low_risk_entity_ids", ())
        if str(value or "").strip()
    }
    quiet_hours_active = bool(policy.get("quiet_hours_active"))
    presence_state = str(policy.get("presence_state") or "").strip().lower()
    fresh_environment_entity_ids = {
        str(value or "").strip().lower()
        for value in policy.get("fresh_environment_entity_ids", ())
        if str(value or "").strip()
    }
    device_info = (
        bundle.get("device_info")
        if isinstance(bundle.get("device_info"), dict)
        else {}
    )
    scoped_entity_ids = {
        str(managed_entity_id or "").strip().lower()
        for managed_entity_id in device_info
        if str(managed_entity_id or "").strip()
    }
    capability_snapshot = (
        bundle.get("device_capability_snapshot")
        if isinstance(bundle.get("device_capability_snapshot"), dict)
        else {}
    )

    authorized: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for action in actions:
        entity_id = str(
            action.get("entity_id")
            or action.get("entity")
            or (
                action.get("target", {}).get("entity_id")
                if isinstance(action.get("target"), dict)
                else ""
            )
            or ""
        ).strip().lower()
        domain = str(
            action.get("domain")
            or (entity_id.split(".", 1)[0] if "." in entity_id else "")
            or ""
        ).strip().lower()
        service = str(action.get("service") or "").strip().lower()
        info = (
            device_info.get(entity_id)
            if isinstance(device_info.get(entity_id), dict)
            else {}
        )
        capability = (
            capability_snapshot.get(entity_id)
            if isinstance(capability_snapshot.get(entity_id), dict)
            else {}
        )
        comfort_capability = str(
            info.get("capability")
            or info.get("type")
            or capability.get("capability")
            or capability.get("type")
            or ""
        ).strip().lower()
        is_comfort_actuator = domain in {"fan", "climate"} or comfort_capability in {
            "fan",
            "climate",
            "air_conditioner",
            "air-conditioning",
            "hvac",
        }
        blocked_reason = ""
        if not entity_id or entity_id not in scoped_entity_ids:
            blocked_reason = "patrol_entity_outside_scoped_snapshot"
        elif allowlist and entity_id not in allowlist:
            blocked_reason = "patrol_low_risk_entity_not_allowed"
        elif quiet_hours_active and not allowlist:
            blocked_reason = "patrol_quiet_hours_requires_low_risk_allowlist"
        elif is_comfort_actuator and service != "turn_off":
            if presence_state != "occupied":
                blocked_reason = "patrol_presence_not_occupied"
            elif not fresh_environment_entity_ids:
                blocked_reason = "patrol_environment_evidence_stale_or_missing"

        if blocked_reason:
            blocked.append(
                {
                    **action,
                    "status": "blocked_by_patrol_policy",
                    "reason": blocked_reason,
                }
            )
            continue
        authorized.append(action)
    return authorized, blocked


def _ordered_text_tuple(values: Any) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value or "").strip()
            for value in (values or ())
            if str(value or "").strip()
        )
    )


def _discover_patrol_spaces(
    owner: Any,
    configured_scope: tuple[str, ...],
    excluded_scope: set[str],
) -> tuple[str, ...]:
    discovered_spaces: list[str] = []

    def _add_space(value: Any) -> None:
        space_id = str(value or "").strip()
        if (
            space_id
            and space_id not in excluded_scope
            and space_id not in discovered_spaces
        ):
            discovered_spaces.append(space_id)

    if configured_scope:
        for space_id in configured_scope:
            _add_space(space_id)
        return tuple(discovered_spaces)

    presence_getter = getattr(owner, "get_presence_snapshot", None)
    if callable(presence_getter):
        try:
            presence_snapshot = presence_getter()
        except Exception:
            presence_snapshot = {}
        rooms = (
            presence_snapshot.get("rooms")
            if isinstance(presence_snapshot, dict)
            and isinstance(presence_snapshot.get("rooms"), dict)
            else {}
        )
        for space_id in rooms:
            _add_space(space_id)

    capability_getter = getattr(owner, "get_device_capability_snapshot", None)
    if callable(capability_getter):
        try:
            capability_snapshot = capability_getter()
        except Exception:
            capability_snapshot = {}
        if isinstance(capability_snapshot, dict):
            for raw_capability in capability_snapshot.values():
                capability = raw_capability if isinstance(raw_capability, dict) else {}
                _add_space(
                    capability.get("space_id")
                    or capability.get("room_id")
                    or capability.get("area_id")
                    or capability.get("room")
                    or capability.get("area")
                )
                for key in (
                    "coverage_spaces",
                    "target_space_ids",
                    "coverage_space_ids",
                ):
                    raw_values = capability.get(key)
                    if isinstance(raw_values, (list, tuple, set)):
                        for value in raw_values:
                            _add_space(value)

    for info_source in (
        getattr(owner, "device_info", {}) or {},
        getattr(owner, "_environment_context_device_info", {}) or {},
    ):
        if not isinstance(info_source, dict):
            continue
        for raw_info in info_source.values():
            info = raw_info if isinstance(raw_info, dict) else {}
            _add_space(
                info.get("space_id")
                or info.get("room_id")
                or info.get("area_id")
                or info.get("room")
                or info.get("area")
            )
    return tuple(discovered_spaces)


def _select_automatic_patrol_spaces(
    owner: Any,
    *,
    source: str,
    patrol_spaces: tuple[str, ...],
) -> tuple[tuple[str, ...], float | None, bool] | None:
    if source != "ha_low_frequency_patrol":
        return patrol_spaces, None, False

    automatic_submit_at = time.monotonic()
    interval_seconds = max(
        60.0,
        float(getattr(owner, "_patrol_interval_minutes", 15) or 15) * 60.0,
    )
    previous_submit_at = float(
        getattr(owner, "_ai_patrol_last_automatic_submit_monotonic", 0.0) or 0.0
    )
    if (
        previous_submit_at > 0.0
        and automatic_submit_at - previous_submit_at < interval_seconds
    ):
        retry_space_ids = set(
            _ordered_text_tuple(getattr(owner, "_ai_patrol_retry_space_ids", ()))
        )
        retry_not_before = float(
            getattr(owner, "_ai_patrol_retry_not_before_monotonic", 0.0) or 0.0
        )
        if not retry_space_ids or automatic_submit_at < retry_not_before:
            return None
        retry_spaces = tuple(
            space_id for space_id in patrol_spaces if space_id in retry_space_ids
        )
        if not retry_spaces:
            owner._ai_patrol_retry_space_ids = ()
            owner._ai_patrol_retry_not_before_monotonic = 0.0
            return None
        return retry_spaces, automatic_submit_at, True

    owner._ai_patrol_last_automatic_submit_monotonic = automatic_submit_at
    owner._ai_patrol_retry_space_ids = ()
    owner._ai_patrol_retry_not_before_monotonic = 0.0
    return patrol_spaces, automatic_submit_at, False


def _patrol_prompt_contract(
    owner: Any,
    *,
    configured_scope: tuple[str, ...],
    excluded_scope: set[str],
) -> tuple[str, str, int, dict[str, Any]]:
    low_risk_entity_ids = _ordered_text_tuple(
        getattr(owner, "_patrol_low_risk_entity_ids", ())
    )
    quiet_start = str(getattr(owner, "_patrol_quiet_hours_start", "") or "").strip()
    quiet_end = str(getattr(owner, "_patrol_quiet_hours_end", "") or "").strip()
    quiet_policy = (
        f"配置的安静时段为 {quiet_start}-{quiet_end}；它是动作扰动约束，不是跳过巡检的理由。"
        if quiet_start and quiet_end
        else "当前未配置安静时段。"
    )
    low_risk_policy = (
        "本轮允许规划的低风险执行实体仅限："
        + "、".join(low_risk_entity_ids)
        + "。环境和在场传感器只作为只读证据。"
        if low_risk_entity_ids
        else "本轮未配置额外低风险实体白名单，最终动作仍必须通过现有风险与灰度门禁。"
    )
    try:
        interval_minutes = max(
            1,
            min(1440, int(getattr(owner, "_patrol_interval_minutes", 15) or 15)),
        )
    except (TypeError, ValueError, OverflowError):
        interval_minutes = 15
    policy = {
        "quiet_hours": {"start": quiet_start, "end": quiet_end},
        "low_risk_entity_ids": sorted(low_risk_entity_ids),
        "configured_scope_space_ids": sorted(configured_scope),
        "excluded_space_ids": sorted(excluded_scope),
    }
    return quiet_policy, low_risk_policy, interval_minutes, policy


async def _run_patrol_decisions(
    owner: Any,
    *,
    patrol_spaces: tuple[str, ...],
    source: str,
    quiet_policy: str,
    low_risk_policy: str,
    occurrence_interval_minutes: int,
    occurrence_policy: dict[str, Any],
    build_task_occurrence: PatrolOccurrenceBuilder,
) -> list[dict[str, Any]]:
    occurrence_now = owner._ha_local_now()
    occurrence_job_id = (
        "ha_low_frequency_patrol"
        if source == "ha_low_frequency_patrol"
        else "ha_manual_patrol"
    )
    decisions: list[dict[str, Any]] = []
    for space_id in patrol_spaces:
        scope_label = space_id or "全部纳管空间"
        one_off_prompt = (
            "这是主动式 AI 管家的周期巡检补漏，不是增量状态事件。"
            "请忽略监听事件是否曾被 deadband 过滤，仅依据本次快照里的当前绝对状态、"
            "数据新鲜度、占用证据、设备能力、近期人工操作和现有安全策略做决定。"
            f"本轮只巡检 {scope_label}。重点复核有人/占用时的温度与舒适设备状态："
            "若现场明显不舒适且低风险风扇可用但关闭，应主动生成补偿目标；"
            "不要因为状态变化量小或本轮没有新事件而忽略。"
            "优先选择可逆、低风险动作；空调、扫地机等较高风险设备仍必须服从"
            "现有确认、人工保护、安静时段、冷却时间和主动 AI 灰度门禁。"
            f"{quiet_policy}{low_risk_policy}"
            "证据不足、占用未知或设备不可用时保持不动作。"
        )
        trigger = f"主动式 AI 管家周期巡检：复核 {scope_label} 当前绝对状态并补偿遗漏动作"
        try:
            result = await owner._run_addon_decision(
                trigger,
                one_off_prompt=one_off_prompt,
                source="patrol_reconciliation",
                trigger_space_id=space_id,
                task_occurrence=build_task_occurrence(
                    now=occurrence_now,
                    interval_minutes=occurrence_interval_minutes,
                    scope_id=space_id,
                    policy=occurrence_policy,
                    job_id=occurrence_job_id,
                ),
            )
        except Exception as exc:
            owner._sys_log(
                "WARN",
                "[AIPatrol] room reconciliation failed | "
                f"space={space_id} error={type(exc).__name__}",
            )
            result = {
                "status": "error",
                "matched": False,
                "executed_count": 0,
                "reason": "patrol_decision_exception",
            }
        decisions.append(
            {
                "space_id": space_id,
                "result": result if isinstance(result, dict) else {},
            }
        )
    return decisions


def _decision_failed(decision_result: dict[str, Any]) -> bool:
    status_text = str(decision_result.get("status") or "").strip().lower()
    try:
        http_status = int(decision_result.get("__status", 200) or 200)
    except (TypeError, ValueError, OverflowError):
        http_status = 500
    try:
        authorized_count = int(decision_result.get("authorized_action_count", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        authorized_count = 0
    try:
        executed_count = int(decision_result.get("executed_count", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        executed_count = 0
    final_outcome = str(
        decision_result.get("final_outcome")
        or decision_result.get("execution_status")
        or ""
    ).strip().lower()
    execution_attempted = (
        decision_result.get("auto_execute") is True
        or final_outcome in {"succeeded", "partial", "failed"}
    )
    execution_failed = (
        authorized_count > 0
        and execution_attempted
        and (
            final_outcome in {"partial", "failed"}
            or executed_count < authorized_count
        )
    )
    return (
        status_text == "error"
        or decision_result.get("ok") is False
        or http_status >= 400
        or execution_failed
    )


def _summarize_decisions(
    decisions: list[dict[str, Any]],
) -> tuple[str, int, int, int, tuple[str, ...]]:
    matched_count = sum(
        1
        for item in decisions
        if isinstance(item.get("result"), dict)
        and item["result"].get("matched") is True
    )
    executed_count = sum(
        int(item["result"].get("executed_count") or 0)
        for item in decisions
        if isinstance(item.get("result"), dict)
    )
    failed_space_ids = tuple(
        str(item.get("space_id") or "").strip()
        for item in decisions
        if _decision_failed(
            item.get("result") if isinstance(item.get("result"), dict) else {}
        )
    )
    failed_count = len(failed_space_ids)
    status = (
        "error"
        if failed_count == len(decisions)
        else "partial"
        if failed_count
        else "ok"
    )
    return status, failed_count, matched_count, executed_count, failed_space_ids


async def run_ai_patrol(
    owner: Any,
    *,
    source: str = "ha_low_frequency_patrol",
    build_task_occurrence: PatrolOccurrenceBuilder,
) -> dict[str, Any] | None:
    """Reconcile current absolute state through the add-on decision path."""

    if not owner._is_enabled():
        return None
    if bool(getattr(owner, "_learning_mode", False)):
        return None
    if not bool(getattr(owner, "_patrol_enabled", False)):
        return None

    configured_scope = _ordered_text_tuple(
        getattr(owner, "_patrol_scope_space_ids", ())
    )
    excluded_scope = set(
        _ordered_text_tuple(getattr(owner, "_patrol_excluded_space_ids", ()))
    )
    patrol_spaces = _discover_patrol_spaces(owner, configured_scope, excluded_scope)
    if not patrol_spaces:
        return {
            "status": "skipped",
            "reason": (
                "patrol_scope_fully_excluded"
                if configured_scope
                else "patrol_scope_unavailable"
            ),
            "run_count": 0,
            "results": [],
        }

    selected = _select_automatic_patrol_spaces(
        owner,
        source=source,
        patrol_spaces=patrol_spaces,
    )
    if selected is None:
        return None
    patrol_spaces, automatic_submit_at, automatic_retry_run = selected
    quiet_policy, low_risk_policy, interval_minutes, policy = (
        _patrol_prompt_contract(
            owner,
            configured_scope=configured_scope,
            excluded_scope=excluded_scope,
        )
    )
    decisions = await _run_patrol_decisions(
        owner,
        patrol_spaces=patrol_spaces,
        source=source,
        quiet_policy=quiet_policy,
        low_risk_policy=low_risk_policy,
        occurrence_interval_minutes=interval_minutes,
        occurrence_policy=policy,
        build_task_occurrence=build_task_occurrence,
    )
    status, failed_count, matched_count, executed_count, failed_space_ids = (
        _summarize_decisions(decisions)
    )
    if automatic_submit_at is not None:
        if failed_count:
            owner._ai_patrol_retry_space_ids = tuple(
                dict.fromkeys(space_id for space_id in failed_space_ids if space_id)
            )
            owner._ai_patrol_retry_not_before_monotonic = automatic_submit_at + 60.0
        else:
            owner._ai_patrol_retry_space_ids = ()
            owner._ai_patrol_retry_not_before_monotonic = 0.0
    owner._sys_log(
        "WARN" if failed_count else "INFO",
        "[AIPatrol] absolute-state reconciliation completed | "
        f"runs={len(decisions)} failed={failed_count} matched={matched_count} "
        f"executed={executed_count} source={source}",
    )
    return {
        "status": status,
        "source": source,
        "retry_run": automatic_retry_run,
        "run_count": len(decisions),
        "failed_count": failed_count,
        "matched_count": matched_count,
        "executed_count": executed_count,
        "results": decisions,
    }


def _quiet_minutes(value: Any) -> int | None:
    parts = str(value or "").strip().split(":", 1)
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return None
    hour, minute = (int(part) for part in parts)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return hour * 60 + minute


def _automatic_safety_net_submit_time(owner: Any, source: str) -> tuple[bool, float | None]:
    if source != "ha_low_frequency_patrol":
        return True, None
    quiet_start = _quiet_minutes(getattr(owner, "_patrol_quiet_hours_start", ""))
    quiet_end = _quiet_minutes(getattr(owner, "_patrol_quiet_hours_end", ""))
    if quiet_start is not None and quiet_end is not None and quiet_start != quiet_end:
        now = owner._ha_local_now()
        now_minutes = int(now.hour) * 60 + int(now.minute)
        in_quiet_hours = (
            quiet_start <= now_minutes < quiet_end
            if quiet_start < quiet_end
            else now_minutes >= quiet_start or now_minutes < quiet_end
        )
        if in_quiet_hours:
            return False, None
    try:
        interval_minutes = int(getattr(owner, "_patrol_interval_minutes", 15) or 15)
    except (TypeError, ValueError):
        interval_minutes = 15
    interval_seconds = max(5, min(interval_minutes, 1440)) * 60
    automatic_submit_at = time.monotonic()
    try:
        last_submit_at = float(
            getattr(owner, "_patrol_last_automatic_submit_monotonic", 0.0) or 0.0
        )
    except (TypeError, ValueError):
        last_submit_at = 0.0
    if last_submit_at > 0 and automatic_submit_at - last_submit_at < interval_seconds:
        return False, None
    return True, automatic_submit_at


def _attach_safety_net_occurrence(
    owner: Any,
    *,
    source: str,
    payload: dict[str, Any],
    build_task_occurrence: PatrolOccurrenceBuilder,
) -> None:
    if source != "ha_low_frequency_patrol":
        return
    patrol_policy = (
        payload.get("patrol_policy")
        if isinstance(payload.get("patrol_policy"), dict)
        else {}
    )
    try:
        interval_minutes = int(patrol_policy.get("interval_minutes") or 15)
    except (TypeError, ValueError):
        interval_minutes = 15
    payload["task_occurrence"] = build_task_occurrence(
        now=owner._ha_local_now(),
        interval_minutes=max(1, min(interval_minutes, 1440)),
        scope_id="patrol_safety_net",
        policy=dict(patrol_policy),
        job_id="ha_low_frequency_patrol_safety_net",
    )


def _update_safety_net_fingerprint(owner: Any, payload: dict[str, Any]) -> None:
    fingerprint = json.dumps(
        {
            "devices": sorted(
                (payload.get("device_capability_snapshot") or {}).keys()
            ),
            "states": payload.get("states") or {},
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    if fingerprint == owner._last_patrol_snapshot:
        owner._patrol_no_change_count += 1
    else:
        owner._last_patrol_snapshot = fingerprint
        owner._patrol_no_change_count = 0


def _notify_sensorless_confirmation(owner: Any, result: dict[str, Any]) -> None:
    sensorless = (
        result.get("sensorless_confirmations")
        if isinstance(result.get("sensorless_confirmations"), dict)
        else {}
    )
    created = [
        item
        for item in list(sensorless.get("created") or [])
        if isinstance(item, dict)
    ]
    if int(sensorless.get("created_count") or 0) <= 0 or not created:
        return
    confirmation_item = created[0]
    action_rows = [
        item
        for item in list(confirmation_item.get("actions") or [])
        if isinstance(item, dict)
    ]
    entity_names = [
        str(item.get("entity_id") or "").strip()
        for item in action_rows
        if str(item.get("entity_id") or "").strip()
    ]
    space_name = str(confirmation_item.get("space_id") or "该区域").strip() or "该区域"
    target_names = "、".join(entity_names) or "相关设备"
    owner._notify_dedup(
        f"{space_name} 的 {target_names} 可能可以关闭。"
        "请在 SmartAgent AI 决策中确认；未回复不会执行。",
        "SmartAgent 设备关闭确认",
    )


def _safety_net_execution_token(
    result: dict[str, Any],
) -> tuple[int, int, str, list[str]]:
    status = int(result.get("__status") or 0)
    plan = result.get("plan") if isinstance(result.get("plan"), dict) else {}
    safety = plan.get("safety_net") if isinstance(plan.get("safety_net"), dict) else {}
    candidate_count = int(safety.get("candidate_count") or 0) if safety else 0
    gate = (
        result.get("execution_gate")
        if isinstance(result.get("execution_gate"), dict)
        else {}
    )
    blockers = [str(item) for item in list(gate.get("blockers") or []) if str(item)]
    confirmation = (
        result.get("confirmation")
        if isinstance(result.get("confirmation"), dict)
        else {}
    )
    token = str(confirmation.get("token") or "").strip()
    token_issued = confirmation.get("token_issued") is True and bool(token)
    executable_blockers = [
        item for item in blockers if item != "confirmation_token_required"
    ]
    return status, candidate_count, token if token_issued else "", executable_blockers


async def submit_patrol_safety_net_plan(
    owner: Any,
    *,
    source: str = "ha_low_frequency_patrol",
    build_task_occurrence: PatrolOccurrenceBuilder,
) -> dict[str, Any] | None:
    """Submit and, only with a server confirmation token, execute a patrol plan."""

    if not owner._is_enabled():
        return None
    if bool(getattr(owner, "_learning_mode", False)):
        return None
    if not bool(getattr(owner, "_patrol_enabled", False)):
        return None
    addon_client = getattr(owner, "_addon_client", None)
    if addon_client is None:
        return None
    should_submit, automatic_submit_at = _automatic_safety_net_submit_time(
        owner,
        source,
    )
    if not should_submit:
        return None

    payload = owner._build_patrol_safety_net_payload(source=source)
    _attach_safety_net_occurrence(
        owner,
        source=source,
        payload=payload,
        build_task_occurrence=build_task_occurrence,
    )
    _update_safety_net_fingerprint(owner, payload)
    plan_request = {
        "domain": "patrol",
        "action": "trigger",
        "payload": payload,
        "reason": "low frequency vacant lighting safety net",
        "requested_by": "ha_patrol_scheduler",
        "dry_run": True,
    }
    result = await addon_client.post_operations_action_plan(plan_request)
    if not isinstance(result, dict):
        return None
    if automatic_submit_at is not None:
        owner._patrol_last_automatic_submit_monotonic = automatic_submit_at

    _notify_sensorless_confirmation(owner, result)
    status, candidate_count, token, executable_blockers = (
        _safety_net_execution_token(result)
    )
    owner._sys_log(
        "INFO",
        f"[PatrolSafetyNet] plan submitted | status={status} "
        f"candidates={candidate_count} source={source}",
    )
    if candidate_count <= 0 or not token or executable_blockers:
        return result

    execute_request = {
        **plan_request,
        "dry_run": False,
        "confirmation_token": token,
    }
    execution = await addon_client.post_operations_action_execute(execute_request)
    if not isinstance(execution, dict):
        return result
    execution_status = int(execution.get("__status") or 0)
    transaction_id = str(execution.get("transaction_id") or "")
    provider_result = (
        execution.get("result") if isinstance(execution.get("result"), dict) else {}
    )
    executed_count = int(provider_result.get("executed_count") or 0)
    owner._sys_log(
        "INFO",
        "[PatrolSafetyNet] controlled execution | "
        f"status={execution_status} executed={executed_count} "
        f"transaction_id={transaction_id or '-'} source={source}",
    )
    return execution


__all__ = [
    "filter_patrol_reconciliation_actions",
    "run_ai_patrol",
    "submit_patrol_safety_net_plan",
]
