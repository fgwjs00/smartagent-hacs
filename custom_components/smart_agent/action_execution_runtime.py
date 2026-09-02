"""Action-batch orchestration extracted from the Home Assistant action facade.

The mixin owns normalization, guard convergence, transaction accounting and
decision-linked batch receipt handling. Concrete service invocation remains
on ActionsMixin so this module cannot become a second HA execution sink.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from .admin_actor import AuthenticatedOwnerSession
from .action_normalization import action_domain, action_entity_id
from .action_receipts import ActionResultCollector
from .const import ACTION_PARAM_KEYS_LIGHT_SCENE, MODE_SHOWROOM
from .execution_gate import (
    evaluate_self_trigger_protection,
    evaluate_thin_execution_gate,
)
from .service_contracts import (
    EXECUTION_DOMAINS as THIN_GATE_EXECUTION_DOMAINS,
    STATELESS_DOMAINS as THIN_GATE_STATELESS_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


class ActionExecutionRuntimeMixin:
    """Orchestrate one guarded action batch without owning the HA transport."""

    async def _execute_actions(
        self,
        actions: list,
        trigger_summary: str = "",
        scene_desc: str = "",
        confidence: int = 0,
        trigger_room: str = "",
        is_global_cmd: bool = False,
        cmd_source: str = "",
        parent_transaction_id: str = "",
        world_snapshot_id: str = "",
        correlation_id: str = "",
        active_space_id: str = "",
        decision_time: str = "",
        require_world_snapshot_guard: bool = False,
        direct_entity_only: bool = False,
        decision_contract_lineage: dict[str, Any] | None = None,
        user_intent_authority: Any | None = None,
    ) -> int:
        """Execute a list of AI actions with transaction tracking."""
        import json as _json

        correlation_id = str(correlation_id or "").strip()

        if not actions:
            return self._action_execution_result(0, correlation_id=correlation_id)

        original_actions = list(actions)
        result_collector = ActionResultCollector(original_actions, correlation_id=correlation_id)
        _claim_action_position = result_collector.claim_position
        _remember_result = result_collector.remember
        _ordered_results = result_collector.ordered_results
        guard_pre_states: dict[str, str] = {}

        _USER_EXPLICIT = "USER_EXPLICIT"
        _is_user_explicit = (cmd_source == _USER_EXPLICIT)
        _has_authenticated_user_intent = bool(
            _is_user_explicit
            and type(user_intent_authority) is AuthenticatedOwnerSession
        )
        _decision_lineage = (
            decision_contract_lineage
            if isinstance(decision_contract_lineage, dict)
            else {}
        )
        _decision_transaction_id = str(
            _decision_lineage.get("decision_transaction_id") or ""
        ).strip()
        _decision_linked_batch = bool(
            require_world_snapshot_guard
            and not _is_user_explicit
            and _decision_transaction_id
            and len(original_actions) > 1
        )

        def _remember_guard_pre_state(action: dict[str, Any]) -> None:
            entity_id = action_entity_id(action)
            if not isinstance(entity_id, str) or "." not in entity_id:
                return
            state = self.hass.states.get(entity_id)
            if state:
                guard_pre_states[entity_id] = state.state

        # ── 区域隔离守卫校验 (AI-03) ──
        # 若有明确触发区域且非全局指令，过滤掉不属于该区域且非全局属性的动作
        # 允许的例外：巡检、位置变化、Frigate视觉触发（通常涉及多区域）
        # USER_EXPLICIT（用户主动指令/一次性场景/语音）豁免区域隔离，与 IntentVerifier 保持一致
        _SKIP_ISOLATION = ("巡检", "位置变化", "视觉检测")
        should_isolate = bool(
            trigger_room
            and not is_global_cmd
            and not _is_user_explicit
            and not any(k in trigger_summary for k in _SKIP_ISOLATION)
        )

        if should_isolate:
            filtered_actions = []
            for a in actions:
                eid = action_entity_id(a)
                if not eid: continue
                cap = self._get_action_device_capability(eid)
                dev_room = (cap.get("room") or "").strip()
                if not dev_room and hasattr(self, "_get_entity_area"):
                    dev_room = (self._get_entity_area(eid) or "").strip()
                cap = {**cap, "room": dev_room}

                # 隔离规则（与 IntentVerifier._stage1_semantic_check 保持完全一致）：
                # 1. 设备所在房间匹配触发房间 -> 放行
                # 2. 豁免域 (climate/cover/scene/script/vacuum) -> 放行
                # 3. action 本身标记了 is_global (LLM 合法跨区指令) -> 放行
                # 4. 房间信息经 device_info + Registry 双重查找后仍为空 -> 放行（全局设备）
                #    注意：仅靠 device_info 为空就豁免是不安全的，已在 _get_entity_area 回退后才豁免
                _domain = action_domain(a)
                is_cross_zone = self._is_cross_zone_action(trigger_room, cap)
                control_spaces = self._resolve_action_control_spaces(cap)
                has_adjacent_space = any(
                    hasattr(self, "_is_adjacent_room") and self._is_adjacent_room(trigger_room, space)
                    for space in control_spaces
                    if space
                )
                is_exempt = (
                    (not dev_room and not cap.get("control_zone"))
                    or not is_cross_zone
                    or _domain in ("climate", "cover", "scene", "script", "vacuum")
                    or a.get("is_global", False)
                    or has_adjacent_space
                )

                if is_exempt:
                    filtered_actions.append(a)
                else:
                    self._sys_log("WARN", f"[区域隔离] 拦截跨区域操作: {eid}(属于{dev_room})，本次触发于「{trigger_room}」")
                    _msg = f"cross_zone_isolation: {eid} belongs to {dev_room or 'unknown'}; trigger_room={trigger_room}"
                    _result = {
                        "domain": str(_domain or ""),
                        "service": str(
                            a.get("service")
                            or a.get("action")
                            or a.get("command")
                            or ""
                        ).split(".", 1)[-1],
                        "entity_id": str(eid or ""),
                        "status": "blocked_cross_zone_isolation",
                        "msg": _msg,
                        "error": _msg,
                        "error_type": "cross_zone_isolation",
                    }
                    if scene_desc:
                        _result["scene_desc"] = scene_desc
                    if trigger_summary:
                        _result["trigger_summary"] = trigger_summary
                    _remember_result(_claim_action_position(a), _result)
                    _remember_guard_pre_state(a)

            if len(filtered_actions) < len(actions):
                self._sys_log("INFO", f"[区域隔离] 动作集已精简: {len(actions)} -> {len(filtered_actions)} (拦截了 {len(actions)-len(filtered_actions)} 个跨区域动作)")
                actions = filtered_actions
                if not actions:
                    ordered_guard_results = _ordered_results()
                    txn_id: int = await self.hass.async_add_executor_job(
                        self._begin_transaction_db,
                        trigger_summary,
                        scene_desc,
                        confidence,
                        len(original_actions),
                        _json.dumps(guard_pre_states, ensure_ascii=False),
                        _json.dumps(original_actions, ensure_ascii=False, default=str),
                    )
                    if not txn_id:
                        return self._action_execution_result(
                            0,
                            results=ordered_guard_results,
                            pre_states=guard_pre_states,
                            correlation_id=correlation_id,
                        )
                    await self.hass.async_add_executor_job(
                        self._complete_transaction_db,
                        txn_id,
                        0,
                        len(ordered_guard_results),
                        0,
                        _json.dumps(ordered_guard_results, ensure_ascii=False),
                    )
                    return self._action_execution_result(
                        0,
                        transaction_id=txn_id,
                        results=ordered_guard_results,
                        pre_states=guard_pre_states,
                        correlation_id=correlation_id,
                    )

        if not actions:
            return self._action_execution_result(0, correlation_id=correlation_id)

        # ── 自触发保护快速预过滤 ────────────────────────────────────────────────
        # 在动作执行前提前过滤掉触发了本次推理的可控设备，避免浪费完整 LLM 推理后才在
        # _do_call_service 逐设备拦截（该拦截仍保留作最后一道防线）。
        # 注意：仅过滤 turn_on（防止触发灯被 AI 原地开回）；turn_off 通常是合理的关灯指令。
        if self._batch_trigger_controllable:
            _pre_filtered = []
            _pre_blocked = []
            for _a in actions:
                _eid = action_entity_id(_a)
                _svc = str(
                    _a.get("service")
                    or _a.get("action")
                    or _a.get("command")
                    or ""
                ).split(".", 1)[-1]
                if _eid and _svc == "turn_on" and _eid in self._batch_trigger_controllable:
                    _pre_blocked.append(_eid)
                    _domain = action_domain(_a)
                    _guard = evaluate_self_trigger_protection(
                        entity_id=_eid,
                        service=_svc,
                        trigger_entities=self._batch_trigger_controllable,
                    )
                    _msg = _guard.msg or f"self_trigger_protection: {_eid} triggered current inference; rejected {_svc}"
                    _result = {
                        "domain": _domain,
                        "service": str(_svc or ""),
                        "entity_id": str(_eid or ""),
                        "status": _guard.status or "blocked_self_trigger",
                        "msg": _msg,
                        "error": _msg,
                        "error_type": _guard.error_type or "self_trigger_protection",
                    }
                    if scene_desc:
                        _result["scene_desc"] = scene_desc
                    if trigger_summary:
                        _result["trigger_summary"] = trigger_summary
                    _remember_result(_claim_action_position(_a), _result)
                    _remember_guard_pre_state(_a)
                else:
                    _pre_filtered.append(_a)
            if _pre_blocked:
                self._sys_log("INFO",
                    f"[自触发预过滤] 移除 {len(_pre_blocked)} 个自触发设备的 turn_on 动作: "
                    f"{', '.join(_pre_blocked)}"
                )
                actions = _pre_filtered
            if not actions:
                self._sys_log("INFO", "[自触发预过滤] 所有动作均为自触发设备，跳过执行")
                ordered_guard_results = _ordered_results()
                _txn_id: int = await self.hass.async_add_executor_job(
                    self._begin_transaction_db,
                    trigger_summary,
                    scene_desc,
                    confidence,
                    len(original_actions),
                    _json.dumps(guard_pre_states, ensure_ascii=False),
                    _json.dumps(original_actions, ensure_ascii=False, default=str),
                )
                if not _txn_id:
                    return self._action_execution_result(
                        0,
                        results=ordered_guard_results,
                        pre_states=guard_pre_states,
                        correlation_id=correlation_id,
                    )
                await self.hass.async_add_executor_job(
                    self._complete_transaction_db,
                    _txn_id,
                    0,
                    len(ordered_guard_results),
                    0,
                    _json.dumps(ordered_guard_results, ensure_ascii=False),
                )
                return self._action_execution_result(
                    0,
                    transaction_id=_txn_id,
                    results=ordered_guard_results,
                    pre_states=guard_pre_states,
                    correlation_id=correlation_id,
                )

        # ── 1. 执行前：快照目标设备当前状态 ─────────────────────────────────
        pre_states: dict[str, str] = dict(guard_pre_states)
        normalized_actions: list[tuple[int, dict, dict]] = []
        for raw in actions:
            action = self._normalize_action(
                raw,
                allow_fuzzy_entity_match=not require_world_snapshot_guard,
            )
            normalized_actions.append((_claim_action_position(raw), raw, action))
            eid = action.get("entity_id", "")
            if eid and isinstance(eid, str) and "." in eid:
                st = self.hass.states.get(eid)
                if st:
                    pre_states[eid] = st.state

        # ── 2. 写入事务记录（pending）────────────────────────────────────────
        if _decision_linked_batch:
            has_delayed_node = False
            for _position, _raw_action, normalized_action in normalized_actions:
                try:
                    has_delayed_node = int(normalized_action.get("delay_seconds", 0)) > 0
                except (TypeError, ValueError):
                    has_delayed_node = False
                if has_delayed_node:
                    break
            if has_delayed_node:
                reason = "decision_linked_batch_delayed_node_not_authorized"
                for position, _raw_action, normalized_action in normalized_actions:
                    params = normalized_action.get("params")
                    result = {
                        "domain": str(normalized_action.get("domain") or ""),
                        "service": str(normalized_action.get("service") or ""),
                        "entity_id": str(normalized_action.get("entity_id") or ""),
                        "status": "blocked_decision_linked_batch_delayed_node",
                        "msg": reason,
                        "error": reason,
                        "error_type": reason,
                        "ha_command_status": "not_dispatched",
                        "decision_trace": {
                            "decision_transaction_id": _decision_transaction_id,
                        },
                    }
                    if isinstance(params, dict) and params:
                        result["params"] = dict(params)
                    _remember_result(position, result)
                return self._action_execution_result(
                    0,
                    results=_ordered_results(),
                    pre_states=pre_states,
                    correlation_id=correlation_id,
                )

        txn_id: int = await self.hass.async_add_executor_job(
            self._begin_transaction_db,
            trigger_summary,
            scene_desc,
            confidence,
            len(original_actions),
            _json.dumps(pre_states, ensure_ascii=False),
            _json.dumps(original_actions, ensure_ascii=False, default=str),
        )
        if not txn_id:
            self._sys_log("WARN", "[事务] 事务记录写入失败（DB锁/磁盘等），已中止动作执行以保持审计一致性")
            for _position, _raw_action, _action in normalized_actions:
                _entity_id = str(_action.get("entity_id") or "")
                _params = _action.get("params")
                _result = {
                    "domain": str(_action.get("domain") or ""),
                    "service": str(_action.get("service") or ""),
                    "entity_id": _entity_id,
                    "status": "blocked_or_error",
                    "msg": "transaction_start_failed",
                    "error": "transaction_start_failed",
                    "error_type": "transaction_start_failed",
                    "ha_command_status": "not_dispatched",
                }
                if isinstance(_params, dict) and _params:
                    _result["params"] = dict(_params)
                _reason = str(_action.get("reason") or "").strip()
                if _reason:
                    _result["reason"] = _reason
                if scene_desc:
                    _result["scene_desc"] = scene_desc
                if trigger_summary:
                    _result["trigger_summary"] = trigger_summary
                _remember_result(_position, _result)
            ordered_failure_results = _ordered_results()
            return self._action_execution_result(
                0,
                results=ordered_failure_results,
                pre_states=pre_states,
                correlation_id=correlation_id,
            )

        # ── 3. 执行所有动作，收集结果 ────────────────────────────────────────
        executed = 0
        blocked_count = len(_ordered_results())
        failed_count = 0
        guard_result_count = len(_ordered_results())
        results: list[dict] = _ordered_results()
        prepared_batch_calls: list[dict[str, Any]] = []
        parent_transaction_id = str(parent_transaction_id or "").strip()
        parent_decision_trace: dict[str, Any] = {}
        if parent_transaction_id:
            parent_decision_trace = {
                "available": True,
                "transaction_id": parent_transaction_id,
                "url": f"/decision-trace/{parent_transaction_id}",
            }

        # Product Rule P1 优化：提前获取展厅兼容在场证据、灯光层级与人数锁定规则，避免循环内重复调用
        # Contract: legacy_presence_evidence_only; canonical presence guards use _room_occupancy_entries().
        legacy_occ_map = self._get_room_occupancy_map()
        people_counts_by_room = self._get_room_person_counts() if hasattr(self, "_get_room_person_counts") else {}
        parsed_people_rules = self._build_locked_people_rules() if hasattr(self, "_build_locked_people_rules") else []

        _now_min = self._ha_local_minute_of_day()
        is_working_hour = (
            _now_min is not None
            and self.showroom_biz_start_min <= _now_min < self.showroom_biz_end_min
        )

        # 预取展厅有人状态
        is_showroom_occupied = False
        showroom_light_tiers = {}
        if self._mode == MODE_SHOWROOM:
            _showroom_area = self.showroom_area_name
            showroom_sensors = legacy_occ_map.get(_showroom_area, []) if _showroom_area else []
            if not showroom_sensors:
                is_showroom_occupied = True
            else:
                is_showroom_occupied = any(s == "on" for _, s in showroom_sensors)
                if not is_showroom_occupied and all(s in ("unknown", "unavailable") for _, s in showroom_sensors):
                    is_showroom_occupied = True

            # 预取所有展厅灯的层级信息（v2：优先使用基线分数）
            for eid, info in self.device_info.items():
                if not eid.startswith("light."):
                    continue
                _room = info.get("room", "")
                if _showroom_area and _room == _showroom_area and _room not in self.showroom_excluded_subareas:
                    showroom_light_tiers[eid] = await self.hass.async_add_executor_job(self._get_showroom_light_tier_v2, eid)

        # ── Product Rule P2: 动作节拍控制 (Action Pacing) ──
        # 若动作数较多，每个动作之间加入微小延迟，缓解 Zigbee 拥塞
        _is_bulk = len(actions) > 5
        _pacing_delay = 0.2 if _is_bulk else 0.0

        def _result_counts_from_current_results() -> tuple[int, int, int]:
            dispatched_now = sum(1 for item in results if item.get("status") == "ok")
            blocked_now = sum(
                1
                for item in results
                if str(item.get("status") or "").startswith("blocked")
                and item.get("status") != "blocked_or_error"
            )
            failed_now = sum(1 for item in results if item.get("status") == "blocked_or_error")
            return dispatched_now, blocked_now, failed_now

        async def _refresh_transaction_from_results() -> None:
            dispatched_now, blocked_now, failed_now = _result_counts_from_current_results()
            await self.hass.async_add_executor_job(
                self._complete_transaction_db,
                txn_id,
                dispatched_now,
                blocked_now,
                failed_now,
                _json.dumps(results, ensure_ascii=False),
            )

        def _refresh_transaction_from_results_sync() -> None:
            dispatched_now, blocked_now, failed_now = _result_counts_from_current_results()
            self._complete_transaction_db(
                txn_id,
                dispatched_now,
                blocked_now,
                failed_now,
                _json.dumps(results, ensure_ascii=False),
            )

        def _pop_service_call_error_or_unknown(txid: int, aseq: int, eid: str) -> dict[str, Any]:
            detail = self._pop_service_call_error(txid, aseq, eid)
            if detail:
                return detail
            return {
                "msg": "ha_service_returned_false",
                "error": "ha_service_returned_false",
                "error_type": "ha_service_unknown_failure",
                "ha_command_status": "failed",
            }

        for idx, (original_position, raw_action, action) in enumerate(normalized_actions):
            action_seq = original_position + 1
            if idx > 0 and _pacing_delay > 0:
                await asyncio.sleep(_pacing_delay)

            domain = action.get("domain")
            service = action.get("service")
            entity_id = action.get("entity_id")
            params = action.get("params", {})
            reason = action.get("reason", "")
            priority_override_claim = action.get("priority_override_claim")
            target_info = self.device_info.get(entity_id, {}) if isinstance(self.device_info, dict) else {}
            if not isinstance(target_info, dict):
                target_info = {}
            authoritative_target_space_id = str(
                target_info.get("space_id")
                or target_info.get("room_id")
                or target_info.get("area_id")
                or ""
            ).strip()
            target_space_id = str(
                authoritative_target_space_id
                or action.get("target_space_id")
                or action.get("space_id")
                or (
                    priority_override_claim.get("space_id")
                    if isinstance(priority_override_claim, dict)
                    else ""
                )
                or target_info.get("space_id")
                or target_info.get("room_id")
                or target_info.get("area_id")
                or target_info.get("room")
                or target_info.get("area")
                or ""
            ).strip()
            action_result_context = {
                "domain": domain,
                "service": service,
                "entity_id": entity_id,
            }
            daylight_guard_evaluation: dict[str, Any] | None = None
            if correlation_id:
                action_result_context["correlation_id"] = correlation_id
            if parent_transaction_id:
                action_result_context["execution_transaction_id"] = txn_id
                action_result_context["parent_transaction_id"] = parent_transaction_id
                action_result_context["decision_trace"] = dict(parent_decision_trace)
            if isinstance(params, dict) and params:
                action_result_context["params"] = dict(params)
            if scene_desc:
                action_result_context["scene_desc"] = scene_desc
            if trigger_summary:
                action_result_context["trigger_summary"] = trigger_summary
            if reason:
                action_result_context["reason"] = reason
            raw_target = raw_action.get("target") if isinstance(raw_action, dict) else None
            raw_entity_id = (
                raw_action.get("entity_id")
                or raw_action.get("entity")
                or (raw_target.get("entity_id") if isinstance(raw_target, dict) else None)
            )
            try:
                delay = max(0, int(action.get("delay_seconds", 0)))
            except (ValueError, TypeError):
                delay = 0
            raw_entity_exists = True
            if (
                isinstance(raw_entity_id, str)
                and "." in raw_entity_id
                and domain not in THIN_GATE_STATELESS_DOMAINS
            ):
                raw_entity_exists = self.hass.states.get(raw_entity_id) is not None
            entity_exists = True
            if isinstance(entity_id, str) and domain not in THIN_GATE_STATELESS_DOMAINS:
                entity_exists = self.hass.states.get(entity_id) is not None
            thin_gate = evaluate_thin_execution_gate(
                domain=domain,
                service=service,
                entity_id=entity_id,
                raw_entity_id=raw_entity_id,
                entity_exists=entity_exists,
                raw_entity_exists=raw_entity_exists,
                allowed_domains=THIN_GATE_EXECUTION_DOMAINS,
                stateless_domains=THIN_GATE_STATELESS_DOMAINS,
            )
            if not thin_gate.allowed:
                blocked_count += 1
                results.append(thin_gate.to_action_result())
                if thin_gate.log_code == "missing_required_action_fields":
                    self._sys_log("WARN", f"[动作] 字段缺失，跳过: {raw_action} → 标准化后: {action}")
                elif thin_gate.log_code == "domain_not_allowed":
                    self._sys_log("WARN", f"[安全] 拒绝 AI 操作不在白名单中的域: {domain}.{service}({entity_id})")
                elif thin_gate.log_code == "service_blocked":
                    self._sys_log("WARN", f"[安全] 拒绝 AI 执行危险服务: {domain}.{service}({entity_id})")
                elif thin_gate.log_code == "raw_entity_not_found":
                    self._sys_log("WARN", f"[安全] 拒绝原始动作中不存在的实体（防幻觉）: {domain}.{service}({raw_entity_id})")
                elif thin_gate.log_code == "entity_not_found":
                    self._sys_log("WARN", f"[安全] 拒绝操作不存在的实体（防幻觉）: {domain}.{service}({entity_id})")
                continue
            # ─── 设备管辖域 (Action Router) ───────────────────────────────────
            # Run daylight guard before Action Router can rewrite a simple
            # light.turn_on into scene.turn_on/script.turn_on. The guard must
            # evaluate the original light entity and its room context.
            pre_router_auto_presence_lighting = (
                service == "turn_on"
                and self._entity_looks_like_lighting(
                    entity_id,
                    domain,
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                )
                and self._looks_like_automatic_presence_lighting(
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                    cmd_source=str(cmd_source or ""),
                )
            )
            if pre_router_auto_presence_lighting:
                daylight_guard_evaluation = (
                    self._daylight_auto_lighting_execution_evaluation(
                        entity_id,
                        domain,
                        service,
                        actions=original_actions,
                        require_world_snapshot_guard=require_world_snapshot_guard,
                        decision_contract_lineage=decision_contract_lineage,
                        world_snapshot_id=world_snapshot_id,
                        active_space_id=active_space_id,
                        decision_time=decision_time,
                    )
                )
                action_result_context["daylight_guard_evaluation"] = dict(
                    daylight_guard_evaluation
                )
                daylight_reason = str(
                    daylight_guard_evaluation.get("reason_code") or ""
                ).strip()
                if daylight_guard_evaluation.get("allowed") is not True:
                    self._sys_log(
                        "WARN",
                        f"[DaylightGuard] blocked daytime automatic presence lighting {domain}.turn_on({entity_id}): {daylight_reason}",
                    )
                    blocked_count += 1
                    results.append({
                        **action_result_context,
                        "status": "blocked_daylight_auto_lighting",
                        "msg": daylight_reason,
                        "ha_command_status": "not_dispatched",
                    })
                    continue
            if domain not in ("script", "scene"):
                ctrl_mode = self.device_info.get(entity_id, {}).get("control_mode", "shared")
                if ctrl_mode == "ha":
                    results.append({
                        "entity_id": entity_id,
                        "service": service,
                        "status": "skip",
                        "msg": "ha_control_mode",
                    })
                    # HA 优先模式：AI 不直接操作，仅记录建议
                    self._sys_log("INFO", f"[管辖域] {entity_id} 为 HA优先模式，AI 跳过直接操作（建议: {service}）")
                    continue
                elif ctrl_mode in ("ai", "shared"):
                    # AI全权 或 共享模式：shared 时尝试关联脚本/场景。
                    # 若是灯光精细参数（亮度/色温/颜色），优先直控设备，避免语义被场景路由吞掉。
                    _is_simple_off_with_params = (
                        service in ("turn_off", "close") and params
                    )
                    _has_precise_light_params = (
                        domain == "light" and service == "turn_on" and any(
                            k in params
                            for k in (
                                "brightness_pct", "brightness", "color_temp", "color_temp_kelvin",
                                "rgb_color", "hs_color", "xy_color", "effect",
                            )
                        )
                    )
                    if (
                        not direct_entity_only
                        and ctrl_mode == "shared"
                        and domain in ("light", "switch", "cover", "fan", "climate")
                        and service in ("turn_on", "turn_off", "open", "close", "toggle")
                        and not _is_simple_off_with_params
                        and not _has_precise_light_params
                        and not (
                            domain in ("light", "switch") and service == "turn_off"
                        )
                    ):
                        assoc_script = self._find_associated_script(entity_id, service)
                        if assoc_script:
                            # 安全检查：若 AI 意图是 turn_off 且关联脚本名称含"关"/"turn_off"/"guan"，
                            # 该类脚本通常会关闭一批设备（全关脚本）；
                            # 仅当当前设备与脚本高度对应时才路由，否则跳过 Action Router 直接控制设备，
                            # 避免"降低亮度"等精细操作被全关脚本覆盖。
                            _script_local = assoc_script.split(".", 1)[-1].lower()
                            _IS_TURNOFF_SCRIPT = any(kw in _script_local for kw in
                                                     ("turn_off", "guan_deng", "guan_bi", "all_off", "quan_guan"))
                            if service == "turn_off" and _IS_TURNOFF_SCRIPT:
                                # 只路由当前设备唯一对应该脚本时才放行（脚本名称本地部分包含 entity_id 本地部分）
                                _eid_local = entity_id.split(".", 1)[-1].lower()
                                _script_parts = set(_script_local.replace("turn_off_", "").replace("_lights", "").split("_"))
                                _eid_parts = set(_eid_local.split("_"))
                                _overlap_ratio = len(_script_parts & _eid_parts) / max(len(_eid_parts), 1)
                                if _overlap_ratio < 0.8:
                                    self._sys_log("INFO",
                                        f"[Action Router] 跳过路由 {entity_id} → {assoc_script}"
                                        f"（turn_off 全关脚本保护，重叠率={_overlap_ratio:.0%} < 80%，直接控制单个设备）")
                                    assoc_script = None

                            if assoc_script:
                                assoc_domain = assoc_script.split(".")[0]
                                _had_params = bool(params)
                                _keep_precise = (assoc_domain == "scene" and domain == "light" and service == "turn_on")
                                self._sys_log("INFO",
                                    f"[Action Router] {entity_id} → 路由至 {assoc_domain}: {assoc_script}"
                                    f"（优先使用脚本/场景"
                                    f"{', 保留灯光精细参数' if (_had_params and _keep_precise) else (', 丢弃 AI params' if _had_params else '')}）")
                                orig_domain = domain
                                orig_service = service
                                domain = assoc_domain
                                entity_id = assoc_script
                                service = "turn_on"
                                params = {
                                    k: v
                                    for k, v in params.items()
                                    if k in ACTION_PARAM_KEYS_LIGHT_SCENE
                                } if (assoc_domain == "scene" and orig_domain == "light" and orig_service == "turn_on") else {}
            # ─────────────────────────────────────────────────────────────────

            runtime_hints = action.get("runtime_hints") or {}
            service, params = self._apply_sleep_reentry_low_disturbance(
                entity_id, domain, service, params, runtime_hints
            )

            # script / scene pass the pre-guards here, then continue through
            # _do_call_service so service errors and action trace stay unified.
            if domain in ("script", "scene"):
                # 拦截全局场景：entity_id 的本地部分（domain 后）以全局关键词开头才拦截
                # 例如 scene.quan_bu_off / scene.all_off → 拦截
                # 例如 scene.yi_lou_zhan_ting_suo_you_deng_guang_0_scene_0 → 放行（含房间前缀）
                _eid_local = entity_id.split(".", 1)[-1].lower()
                _GLOBAL_KW = ("turn_all", "all_on", "all_off", "quan_bu", "suo_you", "全部", "所有")
                if any(_eid_local == kw or _eid_local.startswith(kw + "_") for kw in _GLOBAL_KW):
                    blocked_count += 1
                    results.append({
                        "entity_id": entity_id,
                        "service": service,
                        "status": "blocked_global_scene",
                        "msg": "global_scene_blocked",
                    })
                    self._sys_log("WARN", f"[全局场景拦截] 拒绝执行 {entity_id}（以全局关键词开头），请使用区域场景替代")
                    continue
                # 场景/脚本人员在场守卫（家庭模式）
                if self._mode != MODE_SHOWROOM:
                    scene_room = self._guess_scene_room(entity_id)
                    if scene_room:
                        sensors = self._room_occupancy_entries(scene_room)
                        if sensors:
                            occupied = any(s == "on" for _, s in sensors)
                            uncertain = any(s in ("unknown", "unavailable") for _, s in sensors)
                            if not occupied and not uncertain:
                                blocked_count += 1
                                results.append({
                                    "entity_id": entity_id,
                                    "service": service,
                                    "status": "blocked_scene_vacant",
                                    "msg": f"scene_room_vacant:{scene_room}",
                                })
                                sensor_str = ", ".join(f"{eid}={s}" for eid, s in sensors[:2])
                                self._sys_log("WARN", f"[场景守卫] 拒绝 {domain}.turn_on({entity_id})：区域「{scene_room}」无人（{sensor_str}）")
                                continue
                # 场景/脚本重复执行冷却
                now_ts = time.time()
                last_exec = self._scene_last_exec.get(entity_id, 0)
                if now_ts - last_exec < self._SCENE_COOLDOWN:
                    results.append({
                        "entity_id": entity_id,
                        "service": service,
                        "status": "skip",
                        "msg": "scene_cooldown",
                    })
                    remain = int(self._SCENE_COOLDOWN - (now_ts - last_exec))
                    self._sys_log("INFO", f"[场景冷却] {entity_id} 距上次执行 {int(now_ts - last_exec)}s < {self._SCENE_COOLDOWN}s，跳过（{remain}s 后可再执行）")
                    continue
                self._sys_log("INFO", f"[动作] 场景/脚本通过前置守卫，转交统一保护链: {domain}.{service}({entity_id})")

            self._sys_log("INFO", f"[动作] 准备执行: {domain}.{service}({entity_id}) params={params} reason={reason}")
            is_automatic_presence_lighting = (
                service == "turn_on"
                and self._entity_looks_like_lighting(
                    entity_id,
                    domain,
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                )
                and self._looks_like_automatic_presence_lighting(
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                    cmd_source=str(cmd_source or ""),
                )
            )
            is_presence_departure_turnoff = (
                service == "turn_off"
                and self._looks_like_presence_departure_turnoff(
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                    cmd_source=str(cmd_source or ""),
                )
            )
            state = self.hass.states.get(entity_id)
            if state:
                if service == "turn_off" and state.state == "off" and not is_presence_departure_turnoff:
                    self._sys_log("INFO", f"[动作] 跳过(已是off): {entity_id}")
                    results.append({
                        **action_result_context,
                        "status": "skip",
                        "msg": "already off",
                        "ha_command_status": "not_dispatched",
                    })
                    continue
                if service == "turn_on" and state.state == "on" and (not params or is_automatic_presence_lighting):
                    self._sys_log("INFO", f"[动作] 跳过(已是on): {entity_id}")
                    results.append({**action_result_context, "status": "skip", "msg": "already on"})
                    continue
            _authenticated_user_explicit_turn_on = bool(
                _has_authenticated_user_intent and service == "turn_on"
            )

            # 人员在场守卫：light/switch turn_on 前确认区域有人（仅家庭模式）
            if (
                domain in ("light", "switch")
                and self._mode != MODE_SHOWROOM
                and not _authenticated_user_explicit_turn_on
            ):
                if service == "turn_on":
                    refresh_presence = getattr(
                        self,
                        "_async_refresh_presence_snapshot_cache",
                        None,
                    )
                    if callable(refresh_presence):
                        try:
                            presence_refreshed = bool(await refresh_presence())
                        except Exception:
                            presence_refreshed = False
                        if not presence_refreshed:
                            blocked_count += 1
                            results.append(
                                {
                                    **action_result_context,
                                    "status": "blocked_person",
                                    "msg": "presence_refresh_failed",
                                    "ha_command_status": "not_dispatched",
                                    "presence_source": "addon_presence_engine",
                                    "presence_reason": "presence_refresh_failed",
                                    "presence_evidence_ids": [],
                                    "presence_states": [],
                                }
                            )
                            continue
                guard_blocked, guard_reason = self._occupancy_guard_check(entity_id, service)
                if guard_blocked:
                    self._sys_log("WARN", f"[人员守卫] 拒绝 {domain}.turn_on({entity_id})：{guard_reason}（无人区域禁止开灯）")
                    blocked_count += 1
                    results.append({"entity_id": entity_id, "service": service, "status": "blocked", "msg": guard_reason})
                    continue

            if (
                service == "turn_on"
                and is_automatic_presence_lighting
            ):
                if daylight_guard_evaluation is None:
                    daylight_guard_evaluation = (
                        self._daylight_auto_lighting_execution_evaluation(
                            entity_id,
                            domain,
                            service,
                            actions=original_actions,
                            require_world_snapshot_guard=require_world_snapshot_guard,
                            decision_contract_lineage=decision_contract_lineage,
                            world_snapshot_id=world_snapshot_id,
                            active_space_id=active_space_id,
                            decision_time=decision_time,
                        )
                    )
                    action_result_context["daylight_guard_evaluation"] = dict(
                        daylight_guard_evaluation
                    )
                daylight_reason = str(
                    daylight_guard_evaluation.get("reason_code") or ""
                ).strip()
                if daylight_guard_evaluation.get("allowed") is not True:
                    self._sys_log(
                        "WARN",
                        f"[日照守卫] 拒绝白天自动开灯 {domain}.turn_on({entity_id})：{daylight_reason}",
                    )
                    blocked_count += 1
                    results.append({
                        **action_result_context,
                        "status": "blocked_daylight_auto_lighting",
                        "msg": daylight_reason,
                        "ha_command_status": "not_dispatched",
                    })
                    continue

            # 展厅模式人数阈值锁定规则（统一执行层）：
            # 无论动作来自反射弧/快脑/慢脑，只要命中“>N人才能开X”锁定规则，
            # 且当前人数不满足阈值，就阻止自动 turn_on。
            if (
                domain == "light"
                and service == "turn_on"
                and not _is_user_explicit
            ):
                _room = ((self.device_info.get(entity_id) or {}).get("room") or "").strip()
                if not _room and hasattr(self, "_get_entity_area"):
                    _room = (self._get_entity_area(entity_id) or "").strip()
                if _room:
                    _person_count = int((people_counts_by_room or {}).get(_room, 0) or 0)
                    _blocked_by_rule, _rule_text = self._is_light_blocked_by_people_rule(
                        entity_id=entity_id,
                        room=_room,
                        person_count=_person_count,
                        parsed_rules=parsed_people_rules,
                    )
                    if _blocked_by_rule:
                        self._sys_log(
                            "WARN",
                            f"[P1人数阈值] 阻止 turn_on({entity_id})：{_room} 当前人数={_person_count}，未满足锁定规则({_rule_text}人)",
                        )
                        blocked_count += 1
                        results.append({
                            "entity_id": entity_id,
                            "service": service,
                            "status": "blocked_p1_people",
                            "msg": f"{_room}人数{_person_count}未满足锁定阈值",
                        })
                        continue
            # 展厅代码层硬保护：展厅模式下上班时间实施分层保护。
            # 这是确定性执行守卫，不是交给 LLM 遵守的 Product Rule P1 运行时规则。
            # 有人时全保，无人时按学习到的层级（Core/Display/Auxiliary）进行差异化保护。
            if self._mode == MODE_SHOWROOM and domain == "light":
                _info = self.device_info.get(entity_id, {})
                _room = (_info.get("room") or "").strip()
                _showroom_area = self.showroom_area_name
                # 完全基于 HA Area Registry 中的 room 字段判断，不依赖实体 ID 拼音
                _is_showroom_light = (
                    bool(_showroom_area)
                    and _room == _showroom_area
                    and _room not in self.showroom_excluded_subareas
                )

                if _is_showroom_light and not _authenticated_user_explicit_turn_on:
                    # B. 获取设备层级（优先从基线分数，兜底旧 tier 表）
                    tier = showroom_light_tiers.get(entity_id) or await self.hass.async_add_executor_job(self._get_showroom_light_tier_v2, entity_id)

                    # C. 分层保护逻辑
                    from .const import (
                        SHOWROOM_DISPLAY_DIM_PCT, SHOWROOM_OCCUPIED_PCT, SHOWROOM_CORE_MIN_PCT,
                    )
                    if is_showroom_occupied:
                        # 【有人状态】Core/Display 层：禁止关闭；AI turn_off → 转换为有人亮度
                        if service == "turn_off":
                            if tier in ("core", "display"):
                                self._sys_log("INFO",
                                    f"[展厅P1] {entity_id}({tier}) 展厅有人，turn_off 转为 turn_on {SHOWROOM_OCCUPIED_PCT}%")
                                service = "turn_on"
                                params = {"brightness_pct": SHOWROOM_OCCUPIED_PCT}
                            # Auxiliary 层有人时也不应随意关灯，但允许 AI 决定
                        elif service == "turn_on":
                            bri = params.get("brightness_pct")
                            if tier == "core" and bri is not None and bri < SHOWROOM_CORE_MIN_PCT:
                                # Core 层：有人时不得低于最低亮度
                                self._sys_log("INFO",
                                    f"[展厅P1] {entity_id}(core) 亮度下限保护：{bri}% → {SHOWROOM_CORE_MIN_PCT}%")
                                params["brightness_pct"] = SHOWROOM_CORE_MIN_PCT
                            elif bri is None:
                                # 无亮度参数时注入有人默认亮度
                                params["brightness_pct"] = SHOWROOM_OCCUPIED_PCT
                    elif is_working_hour:
                        # 【营业时间 + 无人状态】根据层级差异化节能
                        if tier == "core":
                            # 🟢 Core（常用灯）：即便无人也不关闭，维持最低展示亮度
                            if service == "turn_off":
                                self._sys_log("WARN",
                                    f"[展厅P1] 阻止 turn_off({entity_id})：Core 层在营业时间内禁止关闭")
                                blocked_count += 1
                                results.append({"entity_id": entity_id, "service": service, "status": "blocked_p1", "msg": "P1 core"})
                                continue
                            if service == "turn_on" and params.get("brightness_pct") is not None and params["brightness_pct"] < SHOWROOM_CORE_MIN_PCT:
                                self._sys_log("INFO",
                                    f"[展厅P1] {entity_id}(core) 无人亮度下限：{params['brightness_pct']}% → {SHOWROOM_CORE_MIN_PCT}%")
                                params["brightness_pct"] = SHOWROOM_CORE_MIN_PCT

                        elif tier == "display":
                            # 🟡 Display（展示灯）：无人时调暗至 DIM_PCT，不允许彻底关闭
                            if service == "turn_off":
                                self._sys_log("INFO",
                                    f"[展厅分层] {entity_id}(display) 无人节能：turn_off → turn_on {SHOWROOM_DISPLAY_DIM_PCT}%")
                                service = "turn_on"
                                params = {"brightness_pct": SHOWROOM_DISPLAY_DIM_PCT}
                            elif service == "turn_on" and params.get("brightness_pct") is not None and params["brightness_pct"] < SHOWROOM_DISPLAY_DIM_PCT:
                                self._sys_log("INFO",
                                    f"[展厅分层] {entity_id}(display) 无人节能：亮度限制至 {SHOWROOM_DISPLAY_DIM_PCT}%")
                                params["brightness_pct"] = SHOWROOM_DISPLAY_DIM_PCT

                        # 🔴 Auxiliary（辅助灯）：无人时允许 AI 自由执行 turn_off，不予拦截
                    else:
                        # 【非营业时间 + 无人状态】完全释放 Product Rule P1 保护，允许 AI 关闭所有灯光
                        self._sys_log("INFO", f"[展厅下班] 非营业时间且无人，放行对 {entity_id} 的操作")

            # 关灯安全守卫：light/switch turn_off 前双重确认区域无人
            # 因 Frigate 存在漏检，优先以物理人体传感器为准；任意一路检测到有人则阻止关灯
            if (
                domain in ("light", "switch")
                and self._mode != MODE_SHOWROOM
                and not _is_user_explicit
            ):
                if service == "turn_off":
                    refresh_presence = getattr(
                        self,
                        "_async_refresh_presence_snapshot_cache",
                        None,
                    )
                    if callable(refresh_presence):
                        try:
                            presence_refreshed = bool(await refresh_presence())
                        except Exception:
                            presence_refreshed = False
                        if not presence_refreshed:
                            blocked_count += 1
                            results.append(
                                {
                                    **action_result_context,
                                    "status": "blocked_person",
                                    "msg": "presence_refresh_failed",
                                    "ha_command_status": "not_dispatched",
                                    "presence_source": "addon_presence_engine",
                                    "presence_reason": "presence_refresh_failed",
                                    "presence_evidence_ids": [],
                                    "presence_states": [],
                                }
                            )
                            continue
                off_blocked, off_reason = self._turnoff_presence_guard(entity_id, service)
                presence_detail = getattr(self, "_last_turnoff_presence_guard_detail", {})
                if not isinstance(presence_detail, dict):
                    presence_detail = {}
                if off_blocked:
                    self._sys_log("WARN",
                        f"[关灯守卫] 阻止 {domain}.turn_off({entity_id})：{off_reason}")
                    blocked_count += 1
                    results.append({"entity_id": entity_id, "service": service,
                                    "status": "blocked_person", "msg": off_reason,
                                    **presence_detail})
                    continue
                if presence_detail:
                    action_result_context.update(presence_detail)
            if entity_id in self._active_timers:
                try:
                    self._active_timers[entity_id]()
                except Exception as exc:
                    _LOGGER.debug("[Actions] 取消定时任务失败 %s: %s", entity_id, exc)
                del self._active_timers[entity_id]
            if delay > 0:
                # 在闭包中捕获 scene_desc/trigger_summary，保证延迟执行时仍用正确的上下文
                # 避免并发推理时 self._current_scene_desc 被其他房间的推理覆盖
                result_entry = {
                    "entity_id": entity_id,
                    "service": service,
                    "status": "scheduled",
                    "delay": delay,
                }
                result_entry.update(action_result_context)
                results.append(result_entry)

                async def _run_delayed(
                    d: str, s: str, eid: str, p: dict, r: str,
                    sc: str, trig: str, txid: int, aseq: int, parent_txid: str,
                    corr_id: str, target_sid: str, override_claim: dict, result: dict,
                ) -> None:
                    try:
                        state = self.hass.states.get(eid)
                        if (
                            state
                            and s == "turn_off"
                            and getattr(state, "state", None) == "off"
                            and not self._looks_like_presence_departure_turnoff(
                                reason=str(r or ""),
                                scene_desc=str(sc or ""),
                                trigger_summary=str(trig or ""),
                            )
                        ):
                            result.update({
                                "status": "skip",
                                "msg": "already off",
                                "ha_command_status": "not_dispatched",
                            })
                            await _refresh_transaction_from_results()
                            return
                        if (
                            d in ("light", "switch")
                            and s == "turn_off"
                            and self._mode != MODE_SHOWROOM
                        ):
                            refresh_presence = getattr(
                                self,
                                "_async_refresh_presence_snapshot_cache",
                                None,
                            )
                            if callable(refresh_presence):
                                try:
                                    presence_refreshed = bool(
                                        await refresh_presence()
                                    )
                                except Exception:
                                    presence_refreshed = False
                                if not presence_refreshed:
                                    result.update(
                                        {
                                            "status": "blocked_person",
                                            "msg": "presence_refresh_failed",
                                            "ha_command_status": "not_dispatched",
                                            "presence_source": "addon_presence_engine",
                                            "presence_reason": "presence_refresh_failed",
                                            "presence_evidence_ids": [],
                                            "presence_states": [],
                                        }
                                    )
                                    await _refresh_transaction_from_results()
                                    return
                            off_blocked, off_reason = self._turnoff_presence_guard(
                                eid,
                                s,
                            )
                            presence_detail = getattr(
                                self,
                                "_last_turnoff_presence_guard_detail",
                                {},
                            )
                            if isinstance(presence_detail, dict):
                                result.update(presence_detail)
                            if off_blocked:
                                result.update(
                                    {
                                        "status": "blocked_person",
                                        "msg": off_reason,
                                        "ha_command_status": "not_dispatched",
                                    }
                                )
                                await _refresh_transaction_from_results()
                                return
                        ok = await self._do_call_service(
                            d,
                            s,
                            eid,
                            p,
                            r,
                            sc,
                            trig,
                            txid,
                            aseq,
                            parent_txid,
                            world_snapshot_id,
                            corr_id,
                            active_space_id=active_space_id,
                            decision_time=decision_time,
                            target_space_id=target_sid,
                            cmd_source=cmd_source,
                            require_world_snapshot_guard=require_world_snapshot_guard,
                            priority_override_claim=override_claim,
                            decision_contract_lineage=decision_contract_lineage,
                            user_intent_authority=user_intent_authority,
                        )
                    except Exception as exc:
                        _LOGGER.debug("[Actions] 延迟动作执行失败 %s.%s(%s): %s", d, s, eid, exc)
                        ok = False
                    if ok:
                        result["status"] = "ok"
                    else:
                        service_error = _pop_service_call_error_or_unknown(txid, aseq, eid)
                        result.update(service_error)
                        result["status"] = (
                            "skip"
                            if service_error.get("ha_command_status") == "skipped"
                            else "blocked_or_error"
                        )
                    try:
                        await _refresh_transaction_from_results()
                    except Exception as exc:
                        _LOGGER.warning(
                            "[Actions] delayed action transaction refresh failed %s.%s(%s): %s",
                            d,
                            s,
                            eid,
                            exc,
                            exc_info=True,
                        )

                @callback
                def _delayed(
                    _: datetime,
                    d: str = domain,
                    s: str = service,
                    eid: str = entity_id,
                    p: dict = params,
                    r: str = reason,
                    sc: str = scene_desc,
                    trig: str = trigger_summary,
                    txid: int = txn_id,
                    aseq: int = action_seq,
                    parent_txid: str = parent_transaction_id,
                    corr_id: str = correlation_id,
                    target_sid: str = target_space_id,
                    override_claim: dict = priority_override_claim,
                    result: dict = result_entry,
                ) -> None:
                    coro = _run_delayed(
                        d, s, eid, p, r, sc, trig, txid, aseq, parent_txid,
                        corr_id, target_sid, override_claim, result,
                    )
                    try:
                        self.hass.async_create_task(coro)
                    except Exception as exc:
                        close = getattr(coro, "close", None)
                        if callable(close):
                            close()
                        _LOGGER.warning(
                            "[Actions] delayed action task create failed %s.%s(%s): %s",
                            d,
                            s,
                            eid,
                            exc,
                            exc_info=True,
                        )
                        result.update(
                            {
                                "status": "blocked_or_error",
                                "msg": f"task_create_failed: {exc}",
                                "error": "task_create_failed",
                                "error_type": "task_create_failed",
                                "ha_command_status": "not_dispatched",
                                "exception_type": type(exc).__name__,
                            }
                        )
                        try:
                            _refresh_transaction_from_results_sync()
                        except Exception as refresh_exc:
                            _LOGGER.warning(
                                "[Actions] delayed action task create failure transaction refresh failed %s.%s(%s): %s",
                                d,
                                s,
                                eid,
                                refresh_exc,
                                exc_info=True,
                            )

                handle = async_call_later(
                    self.hass,
                    delay,
                    _delayed,
                )
                self._active_timers[entity_id] = handle
            else:
                prepared_or_executed = await self._do_call_service(
                    domain, service, entity_id, params, reason, scene_desc, trigger_summary, txn_id, action_seq,
                    parent_transaction_id, world_snapshot_id, correlation_id,
                    active_space_id=active_space_id,
                    decision_time=decision_time,
                    target_space_id=target_space_id,
                    cmd_source=cmd_source,
                    require_world_snapshot_guard=require_world_snapshot_guard,
                    priority_override_claim=priority_override_claim,
                    decision_contract_lineage=decision_contract_lineage,
                    user_intent_authority=user_intent_authority,
                    prepare_only=_decision_linked_batch,
                )
                if _decision_linked_batch and isinstance(prepared_or_executed, dict):
                    prepared_batch_calls.append({
                        **prepared_or_executed,
                        "original_position": original_position,
                        "action_seq": action_seq,
                        "reason": str(reason or ""),
                        "target_space_id": str(target_space_id or "").strip(),
                        "result_context": dict(action_result_context),
                    })
                elif prepared_or_executed:
                    executed += 1
                    results.append({**action_result_context, "status": "ok"})
                else:
                    service_error = _pop_service_call_error_or_unknown(txn_id, action_seq, entity_id)
                    if service_error.get("ha_command_status") == "skipped":
                        results.append({**action_result_context, **service_error, "status": "skip"})
                    else:
                        failed_count += 1
                        results.append({**action_result_context, **service_error, "status": "blocked_or_error"})

        if _decision_linked_batch:
            batch_preparation_complete = (
                len(prepared_batch_calls) == len(original_actions)
                and len(normalized_actions) == len(original_actions)
                and all(
                    str(item.get("target_space_id") or "").strip()
                    for item in prepared_batch_calls
                )
            )
            if not batch_preparation_complete:
                batch_reason = "decision_linked_batch_preparation_incomplete"
                batch_results: list[dict[str, Any]] = []
                for raw_action in original_actions:
                    service_raw = (
                        str(
                            raw_action.get("service")
                            or raw_action.get("action")
                            or raw_action.get("command")
                            or ""
                        ).strip()
                        if isinstance(raw_action, dict)
                        else ""
                    )
                    batch_results.append({
                        "domain": str(action_domain(raw_action) or ""),
                        "service": service_raw.split(".", 1)[-1],
                        "entity_id": str(action_entity_id(raw_action) or ""),
                        "status": "blocked_decision_linked_batch_preparation_incomplete",
                        "msg": batch_reason,
                        "error": batch_reason,
                        "error_type": batch_reason,
                        "ha_command_status": "not_dispatched",
                        "decision_trace": {
                            "decision_transaction_id": _decision_transaction_id,
                        },
                        **({"correlation_id": correlation_id} if correlation_id else {}),
                    })
                await self.hass.async_add_executor_job(
                    self._complete_transaction_db,
                    txn_id,
                    0,
                    len(batch_results),
                    0,
                    _json.dumps(batch_results, ensure_ascii=False),
                )
                return self._action_execution_result(
                    0,
                    transaction_id=txn_id,
                    results=batch_results,
                    pre_states=pre_states,
                    correlation_id=correlation_id,
                )

            prepared_batch_calls.sort(key=lambda item: int(item["original_position"]))
            batch_commands = [
                {
                    "entity_id": item["entity_id"],
                    "domain": item["domain"],
                    "service": item["service"],
                    "data": dict(item["data"]),
                }
                for item in prepared_batch_calls
            ]
            batch_target_spaces = [
                str(item["target_space_id"]).strip()
                for item in prepared_batch_calls
            ]
            primary = prepared_batch_calls[0]
            try:
                batch_response = await self._execute_enveloped_service(
                    primary["domain"],
                    primary["service"],
                    primary["entity_id"],
                    primary["data"],
                    scene_desc or "decision_linked_batch",
                    txn_id,
                    int(primary["action_seq"]),
                    world_snapshot_id=world_snapshot_id,
                    active_space_id=active_space_id,
                    decision_time=decision_time,
                    target_space_id=primary["target_space_id"],
                    cmd_source=cmd_source,
                    require_world_snapshot_guard=True,
                    decision_contract_lineage=decision_contract_lineage,
                    commands_override=batch_commands,
                    target_space_ids_override=batch_target_spaces,
                    return_failed_result=True,
                    correlation_id_override=correlation_id,
                    user_intent_authority=user_intent_authority,
                )
            except Exception as exc:
                batch_response = {
                    "ok": False,
                    "error": str(exc) or "decision_linked_batch_dispatch_failed",
                    "error_type": "decision_linked_batch_dispatch_failed",
                    "status": "failed",
                }

            response_rows = batch_response.get("results")
            receipt_dispositions = batch_response.get(
                "_smartagent_receipt_dispositions"
            )
            response_shape_valid = (
                isinstance(response_rows, list)
                and len(response_rows) == len(prepared_batch_calls)
                and all(isinstance(row, dict) for row in response_rows)
                and isinstance(receipt_dispositions, list)
                and len(receipt_dispositions) == len(prepared_batch_calls)
            )
            if not response_shape_valid:
                response_rows = [None] * len(prepared_batch_calls)

            results = []
            executed = 0
            failed_count = 0
            blocked_count = 0
            for index, (prepared, receipt) in enumerate(
                zip(prepared_batch_calls, response_rows)
            ):
                receipt_disposition = (
                    receipt_dispositions[index]
                    if isinstance(receipt_dispositions, list)
                    and index < len(receipt_dispositions)
                    else ""
                )
                result_context = dict(prepared["result_context"])
                result_context.update({
                    "domain": prepared["domain"],
                    "service": prepared["service"],
                    "entity_id": prepared["entity_id"],
                })
                if prepared["data"]:
                    result_context["params"] = dict(prepared["data"])
                if (
                    isinstance(receipt, dict)
                    and receipt.get("ok") is True
                    and receipt.get("executed") is True
                    and receipt_disposition == "verified_success"
                ):
                    await self._record_prepared_service_success(
                        domain=prepared["domain"],
                        service=prepared["service"],
                        entity_id=prepared["entity_id"],
                        params=dict(prepared["data"]),
                        reason=prepared["reason"],
                        scene_desc=scene_desc,
                        trigger_text=trigger_summary,
                        transaction_id=txn_id,
                        action_seq=int(prepared["action_seq"]),
                        parent_transaction_id=parent_transaction_id,
                        world_snapshot_id=world_snapshot_id,
                        correlation_id=correlation_id,
                        now_ts=float(prepared["now_ts"]),
                        ai_source=prepared["ai_source"],
                        ai_new_state=prepared["ai_new_state"],
                        occupancy_cycle_id=str(
                            _decision_lineage.get("occupancy_cycle_id") or ""
                        ).strip(),
                    )
                    self._clear_service_call_error(
                        txn_id,
                        int(prepared["action_seq"]),
                        prepared["entity_id"],
                    )
                    executed += 1
                    results.append({**result_context, "status": "ok"})
                    continue

                if isinstance(receipt, dict):
                    receipt_status = str(receipt.get("status") or "").strip()
                    receipt_error = str(
                        receipt.get("error")
                        or receipt.get("reason")
                        or receipt_status
                        or "ha_execution_receipt_unverified"
                    ).strip()
                    receipt_error_type = str(
                        receipt.get("error_type")
                        or "ha_service_unverified_success"
                    ).strip()
                    if receipt_disposition == "noop" and receipt.get("ok") is True and (
                        receipt.get("executed") is False
                        or receipt_status.lower() == "skipped"
                    ):
                        blocked_count += 1
                        results.append({
                            **result_context,
                            "status": "skip",
                            "msg": receipt_error,
                            "ha_command_status": "skipped",
                        })
                        continue
                    command_status = str(
                        receipt.get("effect_status")
                        or receipt.get("ha_command_status")
                        or receipt_status
                        or "effect_unknown"
                    ).strip()
                else:
                    receipt_error = str(
                        batch_response.get("error")
                        or batch_response.get("error_type")
                        or "decision_linked_batch_receipt_shape_invalid"
                    ).strip()
                    receipt_error_type = str(
                        batch_response.get("error_type")
                        or "decision_linked_batch_receipt_shape_invalid"
                    ).strip()
                    response_status = str(batch_response.get("status") or "").strip().lower()
                    command_status = (
                        "not_dispatched"
                        if response_status in {"blocked", "rejected"}
                        or receipt_error_type in {"policy_rejected", "preflight_rejected"}
                        else "effect_unknown"
                    )
                self._remember_service_call_error(
                    txn_id,
                    int(prepared["action_seq"]),
                    prepared["entity_id"],
                    msg=receipt_error,
                    error=receipt_error,
                    error_type=receipt_error_type,
                    status=command_status,
                )
                failed_count += 1
                results.append({
                    **result_context,
                    "status": "blocked_or_error",
                    "msg": receipt_error,
                    "error": receipt_error,
                    "error_type": receipt_error_type,
                    "ha_command_status": command_status,
                })

        for (original_position, _raw_action, _action), result in zip(
            normalized_actions,
            results[guard_result_count:],
        ):
            _remember_result(original_position, result)
        results[:] = _ordered_results()
        if correlation_id:
            for item in results:
                item["correlation_id"] = correlation_id

        # ── 4. 提交事务结果 ────────────────────────────────────────────────────
        if txn_id:
            await self.hass.async_add_executor_job(
                self._complete_transaction_db,
                txn_id,
                executed,
                blocked_count,
                failed_count,
                _json.dumps(results, ensure_ascii=False),
            )
        return self._action_execution_result(
            executed,
            transaction_id=txn_id,
            results=results,
            pre_states=pre_states,
            correlation_id=correlation_id,
        )

    # ── 服务调用 + 保护机制 ───────────────────────────────────────────────────



__all__ = ["ActionExecutionRuntimeMixin"]
