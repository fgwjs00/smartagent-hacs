"""
DecisionPipeline — 渐进式解耦：统一决策管道 (Phase 9.6 / P2.3)。

将原先分散在 coordinator.py + listeners.py 中的决策组件统一为独立类：
  FastBrainEngine  + FeatureEncoder  + IntentVerifier → DecisionPipeline

外部（coordinator/listeners）只需要实例化此类并调用 run_fast_path()，
无需关心内部组件的实例化和调用顺序。

渐进式解耦目标：
  Phase 9.6 (当前): FastBrain + FeatureEncoder + IntentVerifier 三合一
  未来: PatrolMixin、FrigateMixin 抽为独立 service
  终极: coordinator 只做"胶水层"，各模块通过事件总线通信
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# 存在/人体/占用类传感器关键词（arrival + departure 缓存共用）
_PRESENCE_SENSOR_KWS: tuple[str, ...] = (
    "motion", "occupancy", "presence", "pir", "person",
    "人体", "存在", "占用", "人感",
)


class DecisionPipeline:
    """
    统一决策管道。

    封装 System 1（极速快脑）+ 意图验证 的完整流水线。
    System 2（慢脑 LLM）仍在 InferenceMixin 中维护，后续版本迁移。

    使用方法（在 coordinator 或 listeners 中）::

        from .decision_pipeline import DecisionPipeline

        pipeline = DecisionPipeline(coordinator)
        result = pipeline.run_fast_path(entity_id, new_state, old_state)
        if result:
            # 直接执行 result["actions"]，跳过慢脑
            ...
    """

    def __init__(self, coordinator):
        """
        Args:
            coordinator: SmartAgentCoordinator 实例（注入而非继承，便于测试）
        """
        self._coord = coordinator

    def _get_presence_snapshot(self) -> dict:
        """优先读取统一 Presence Snapshot；不可用时返回空字典。"""
        coord = self._coord
        getter = getattr(coord, "get_presence_snapshot", None)
        if callable(getter):
            try:
                snap = getter()
                if isinstance(snap, dict):
                    return snap
            except Exception as exc:
                _LOGGER.debug("[DecisionPipeline] get_presence_snapshot 异常，降级: %s", exc)
        return {}

    def _get_device_capability_snapshot(self) -> dict[str, dict]:
        """优先读取统一设备能力快照；不可用时返回空字典。"""
        coord = self._coord
        getter = getattr(coord, "get_device_capability_snapshot", None)
        if callable(getter):
            try:
                snap = getter()
                if isinstance(snap, dict):
                    return snap
            except Exception as exc:
                _LOGGER.debug("[DecisionPipeline] get_device_capability_snapshot 异常，降级: %s", exc)
        return {}

    @staticmethod
    def _is_night_time() -> bool:
        """夜间窗口判定（保守）：22:00-06:00。"""
        h = datetime.now().hour
        return h >= 22 or h < 6

    @staticmethod
    def _room_looks_like_bedroom(room: str) -> bool:
        """基于房间语义做卧室判定。"""
        room_l = str(room or "").lower()
        return any(k in room_l for k in ("卧", "bedroom", "主卧", "次卧", "儿童房", "master", "guest"))

    def _build_sleep_runtime_hints(self, trigger_room: str) -> dict:
        """构建轻量睡眠运行时 hint，不引入新写库热路径。"""
        hints = {
            "sleep_candidate": False,
            "night_reentry": False,
            "sleep_reentry": False,
        }
        if not trigger_room or not self._room_looks_like_bedroom(trigger_room):
            return hints
        if not self._is_night_time():
            return hints

        hints["sleep_candidate"] = True
        coord = self._coord
        last_leave_map = getattr(coord, "_bedroom_last_leave_ts", {}) or {}
        leave_ts = float(last_leave_map.get(trigger_room, 0) or 0)
        if leave_ts > 0 and (time.time() - leave_ts) <= 30 * 60:
            hints["night_reentry"] = True
            hints["sleep_reentry"] = True
        return hints

    @staticmethod
    def _attach_runtime_hints(actions: list[dict], hints: dict) -> list[dict]:
        """将 runtime hint 注入动作，供执行期策略使用。"""
        if not actions:
            return actions
        if not any(hints.values()):
            return actions
        enriched: list[dict] = []
        for a in actions:
            _a = dict(a)
            _rh = dict(_a.get("runtime_hints") or {})
            _rh.update(hints)
            _a["runtime_hints"] = _rh
            enriched.append(_a)
        return enriched

    # ── Step 0: HA AI 场景优先路径 ─────────────────────────────────────────

    def run_ha_scene_path(self, entity_id: str, new_state: str) -> dict | None:
        """
        在 FastBrain 之前执行：检查是否存在与触发事件匹配的已激活 AI 场景。

        若匹配成功，经 IntentVerifier 验证后返回场景调用动作，跳过 FastBrain 和慢脑 LLM。
        触发条件：到达类事件（PIR binary_sensor 变 on / Frigate 人数传感器 > 0）。
        匹配逻辑：AI 场景内 50% 以上设备属于触发房间 + 时段 + 星期匹配 + 置信度 ≥ 70%。

        安全层（与 run_fast_path 对齐）：
          - control_mode=ha 的场景核心设备：若场景中多数设备均为 HA 优先，跳过此场景。
          - IntentVerifier 双阶段验证：确保场景调用不违反区域隔离和用户覆盖保护。
          - 用户覆盖保护：触发房间在保护窗口内，跳过 Scene Path 交由用户手动控制。

        Args:
            entity_id: 触发实体 ID
            new_state: 新状态

        Returns:
            包含 actions/confidence/scene/trigger_room 的字典，或 None（无匹配场景）
        """
        import json as _json
        from datetime import datetime as _dt

        coord = self._coord
        from .const import MODE_SHOWROOM, AI_SCENE_STATUS_ACTIVE, ai_scene_matches_now

        if getattr(coord, "_mode", "") == MODE_SHOWROOM:
            return None
        if getattr(coord, "_learning_mode", False):
            return None

        # 仅响应"到达"类事件
        domain = entity_id.split(".")[0]
        is_arrival = (
            domain == "binary_sensor" and new_state == "on"
        ) or (
            domain == "sensor"
            and "person" in entity_id.lower()
            and new_state not in ("0", "unknown", "unavailable")
        )
        if not is_arrival:
            return None

        # 获取触发房间
        trigger_room = (coord.device_info.get(entity_id) or {}).get("room", "")
        if not trigger_room:
            return None

        # 用户覆盖保护：若触发房间内的任意设备近期有手动操作，跳过 Scene Path 不干预。
        # _user_manual_actions 以 entity_id 为键、{"state":str,"time":float} 为值，
        # 需要通过 device_info 的 room 字段查找属于 trigger_room 的实体。
        import time as _time
        _manual_lock = getattr(coord, "_user_manual_actions_lock", None)
        if _manual_lock is not None:
            with _manual_lock:
                _manual_actions = dict(getattr(coord, "_user_manual_actions", {}))
        else:
            _manual_actions = dict(getattr(coord, "_user_manual_actions", {}))
        _manual_window = getattr(coord, "_USER_MANUAL_WINDOW", 1800)
        _now_ts = _time.time()
        _room_protected = any(
            _now_ts - v.get("time", 0) < _manual_window
            for eid, v in _manual_actions.items()
            if isinstance(v, dict)
            and (coord.device_info.get(eid) or {}).get("room") == trigger_room
        )
        if _room_protected:
            if hasattr(coord, "_sys_log"):
                coord._sys_log(
                    "INFO",
                    f"[Scene Path] {trigger_room} 在用户覆盖保护窗口内，跳过 AI 场景优先路径"
                )
            return None

        now = _dt.now()
        now_hour = now.hour

        ai_scenes = getattr(coord, "_ai_scenes_cache", [])
        for sc in ai_scenes:
            if sc.get("status") != AI_SCENE_STATUS_ACTIVE:
                continue
            # 时段 + 星期匹配（统一使用 ai_scene_matches_now，SQLite %w 格式）
            if not ai_scene_matches_now(sc, now_hour, now.weekday()):
                continue
            # 场景置信度门槛
            sc_conf = sc.get("confidence", 80)
            if sc_conf < 70:
                continue
            # 房间匹配：场景中 ≥50% 设备属于触发房间
            try:
                ents = _json.loads(sc.get("entities_json", "[]"))
            except Exception:
                continue
            if not ents:
                continue
            room_count = sum(
                1 for e in ents
                if (coord.device_info.get(e.get("entity_id", "")) or {}).get("room") == trigger_room
            )
            if room_count == 0 or room_count < len(ents) * 0.5:
                continue

            # control_mode 检查：若场景中 >50% 的触发房间设备均为 HA 优先模式，跳过此场景
            # 场景整体受 HA 管辖，AI 不应主动触发
            room_ents = [
                e for e in ents
                if (coord.device_info.get(e.get("entity_id", "")) or {}).get("room") == trigger_room
            ]
            ha_mode_count = sum(
                1 for e in room_ents
                if (coord.device_info.get(e.get("entity_id", "")) or {}).get("control_mode", "shared") == "ha"
            )
            if room_ents and ha_mode_count / len(room_ents) > 0.5:
                if hasattr(coord, "_sys_log"):
                    coord._sys_log(
                        "INFO",
                        f"[Scene Path] 跳过场景「{sc.get('name', '')}」— 触发房间 {trigger_room} 中"
                        f" {ha_mode_count}/{len(room_ents)} 个设备为 HA 优先模式"
                    )
                continue

            # 确认 HA 场景实体存在
            ha_eid = f"scene.ai_{sc['id']}"
            if coord.hass.states.get(ha_eid) is None:
                continue

            candidate_actions = [{
                "domain": "scene",
                "service": "turn_on",
                "entity_id": ha_eid,
                "params": {},
                "reason": (
                    f"[Scene Path] {trigger_room}检测到人员，"
                    f"优先调用已激活 AI 场景「{sc.get('name', '')}」"
                ),
                "delay_seconds": 0,
            }]

            # IntentVerifier 双阶段验证（与 run_fast_path 对齐，保证 fail-closed 安全性）
            try:
                from .intent_verifier import IntentVerifier
                _occ_map = {}
                if hasattr(coord, "_get_room_occupancy_map"):
                    _occ_map = coord._get_room_occupancy_map()
                _presence_snapshot = self._get_presence_snapshot()
                _cap_snapshot = self._get_device_capability_snapshot()
                verifier = IntentVerifier(
                    coord.hass, coord.device_info, _occ_map,
                    sys_log_func=getattr(coord, "_sys_log", None),
                    suppress_check_func=getattr(coord, "_should_suppress_action", None),
                )
                verifier._presence_snapshot = _presence_snapshot
                verifier._device_capability_snapshot = _cap_snapshot
                verifier._locked_people_rules = (
                    coord._build_locked_people_rules()
                    if hasattr(coord, "_build_locked_people_rules")
                    else []
                )
                verifier._room_topology = getattr(coord, "_room_topology_cache", {}) or {}
                clean_actions, rejected = verifier.verify(candidate_actions, trigger_room=trigger_room)
                if rejected and hasattr(coord, "_sys_log"):
                    coord._sys_log(
                        "INFO",
                        f"[Scene Path] 场景「{sc.get('name', '')}」被 IntentVerifier 拒绝: "
                        + ", ".join(a.get("reject_reason", "") for a in rejected)
                    )
                if not clean_actions:
                    continue
            except Exception as exc:
                # fail-closed：验证异常时跳过此场景，不执行未验证动作
                _LOGGER.error("[Scene Path] IntentVerifier 异常，fail-closed 跳过场景: %s", exc)
                if hasattr(coord, "_sys_log"):
                    coord._sys_log("ERROR", f"[Scene Path] IntentVerifier 验证异常，跳过场景: {exc}")
                continue

            if hasattr(coord, "_sys_log"):
                coord._sys_log(
                    "INFO",
                    f"[Scene Path] {trigger_room} 检测到人员 → 优先调用 AI 场景"
                    f"「{sc.get('name', ha_eid)}」({ha_eid}，置信度 {sc_conf}%，已通过 IntentVerifier)"
                )
            return {
                "scene": sc.get("name", "AI场景"),
                "confidence": sc_conf,
                "actions": clean_actions,
                "trigger_room": trigger_room,
            }
        return None

    # ── Phase 1: DecisionCache — LLM 历史决策快速复用 ─────────────────────────

    def _try_decision_cache(self, entity_id: str, new_state: str) -> dict | None:
        """Phase 1: 尝试从 DecisionCache 中复用 LLM 历史决策。

        缓存命中流程：
          1. 判断是否为 arrival 类型触发（存在传感器变为 on）
          2. 确定触发房间、当前时段、星期
          3. 调用 `_lookup_decision_cache` 查询缓存
          4. 命中后经 IntentVerifier 验证再返回，确保安全防护完整

        Args:
            entity_id: 触发实体 ID
            new_state: 新状态

        Returns:
            包含 actions/confidence/scene/trigger_room 的字典，或 None（未命中/不适用）
        """
        from datetime import datetime as _dt
        coord = self._coord

        # 仅对"到达"类触发走缓存（binary_sensor 变为 on，且是存在/人体/占用类传感器）
        if new_state != "on":
            return None
        domain = entity_id.split(".")[0]
        if domain != "binary_sensor":
            return None
        eid_lower = entity_id.lower()
        if not any(kw in eid_lower for kw in _PRESENCE_SENSOR_KWS):
            return None

        # 获取触发房间
        trigger_room = (coord.device_info.get(entity_id) or {}).get("room", "")
        if not trigger_room and hasattr(coord, "_get_entity_area"):
            trigger_room = coord._get_entity_area(entity_id)
        if not trigger_room:
            return None

        # 查询缓存
        _lookup = getattr(coord, "_lookup_decision_cache", None)
        if _lookup is None:
            return None

        _now = _dt.now()
        # 5B-3: _lookup_decision_cache 返回 dict{actions, confidence, scene, intent, scene_candidate}
        cached_result = _lookup(
            trigger_room,
            _now.hour,
            _now.weekday(),
            "arrival",
        )
        if not cached_result:
            return None
        cached_actions = cached_result["actions"] if isinstance(cached_result, dict) else cached_result
        _cached_intent = cached_result.get("intent", "") if isinstance(cached_result, dict) else ""
        _cached_sc = cached_result.get("scene_candidate", "") if isinstance(cached_result, dict) else ""

        # 命中后仍走 IntentVerifier，确保修正抑制/区域隔离等安全检查生效
        try:
            from .intent_verifier import IntentVerifier
            needs_occ_check = any(
                a.get("service") == "turn_off" and a.get("domain") == "light"
                for a in cached_actions
            )
            _occ_map = {}
            if needs_occ_check and hasattr(coord, "_get_room_occupancy_map"):
                _occ_map = coord._get_room_occupancy_map()

            verifier = IntentVerifier(
                coord.hass, coord.device_info, _occ_map,
                sys_log_func=getattr(coord, "_sys_log", None),
                suppress_check_func=getattr(coord, "_should_suppress_action", None),
            )
            verifier._presence_snapshot = self._get_presence_snapshot()
            verifier._device_capability_snapshot = self._get_device_capability_snapshot()
            verifier._room_topology = getattr(coord, "_room_topology_cache", {}) or {}
            clean_actions, rejected = verifier.verify(cached_actions, trigger_room=trigger_room)
        except Exception as exc:
            _LOGGER.warning("[DecisionCache] IntentVerifier 异常，放弃缓存命中: %s", exc)
            return None

        if not clean_actions:
            if hasattr(coord, "_sys_log"):
                coord._sys_log(
                    "INFO",
                    f"[DecisionCache] 缓存命中但全部动作被验证拒绝（{len(rejected)} 个），交由慢脑",
                )
            return None

        if hasattr(coord, "_sys_log"):
            coord._sys_log(
                "INFO",
                f"[DecisionCache] ✅ 缓存命中: room={trigger_room} "
                f"h={_now.hour} wd={_now.weekday()} intent={_cached_intent} "
                f"→ {len(clean_actions)} 个动作（跳过 FastBrain 和 LLM）",
            )
        return {
            "scene": "DecisionCache",
            "confidence": 88,
            "actions": clean_actions,
            "trigger_room": trigger_room,
            "intent": _cached_intent,
            "scene_candidate": _cached_sc,
        }

    # ── Departure DecisionCache（Phase 1+）──────────────────────────────────

    def _try_departure_cache(self, entity_id: str, new_state: str) -> dict | None:
        """Phase 1+: 尝试从 DecisionCache 复用 LLM 历史离开决策（departure 场景）。

        缓存命中流程：
          1. 确认为存在传感器变为 off（离开类事件）
          2. 验证房间内所有存在传感器均已离线（非单传感器抖动）
          3. 确认房间内有设备处于开启状态（有东西可关，避免无效命中）
          4. 用户最近手动操作保护：30 分钟内手动操作过该房间的设备，不干预
          5. 查询 departure 类型缓存并经 IntentVerifier 验证后返回

        安全设计：
          - 多传感器保护：房间任意一个存在传感器仍为 on → 不触发（可能仍有人）
          - 用户覆盖保护：_USER_MANUAL_WINDOW 内有手动操作 → 不触发
          - 缓存仅写入经 IntentVerifier 验证的决策（由 inference.py 写回端保证）
          - 命中后仍经 IntentVerifier 二次验证，确保修正抑制等安全层不被绕过

        Args:
            entity_id: 触发实体 ID（存在传感器）
            new_state: 新状态（应为 "off"）

        Returns:
            包含 actions/confidence/scene/trigger_room 的字典，或 None（未命中/不适用）
        """
        import time as _time
        from datetime import datetime as _dt

        # 仅响应 binary_sensor 存在类传感器变为 off
        if new_state != "off":
            return None
        if entity_id.split(".")[0] != "binary_sensor":
            return None
        if not any(kw in entity_id.lower() for kw in _PRESENCE_SENSOR_KWS):
            return None

        coord = self._coord

        # 获取触发房间
        trigger_room = (coord.device_info.get(entity_id) or {}).get("room", "")
        if not trigger_room:
            return None

        # 安全检查 1：房间内所有存在传感器均已变为 off（防止单传感器抖动误触发）
        _room_presence = [
            e for e, info in coord.device_info.items()
            if info.get("room") == trigger_room
            and e.startswith("binary_sensor.")
            and any(kw in e.lower() for kw in _PRESENCE_SENSOR_KWS)
        ]
        for _ps in _room_presence:
            if _ps == entity_id:
                continue  # 当前触发传感器（已是 off）
            _ps_st = coord.hass.states.get(_ps)
            if _ps_st and _ps_st.state == "on":
                return None  # 房间内还有传感器显示有人，不触发离开缓存

        # 安全检查 2：房间内至少有一盏灯或开关处于开启状态（有操作价值）
        # M1修复(v4.10.5): 使用中间变量避免双次 states.get() 调用
        _has_on_devices = False
        for _e, _einfo in coord.device_info.items():
            if _einfo.get("room") != trigger_room:
                continue
            if _e.split(".")[0] not in ("light", "switch"):
                continue
            _est = coord.hass.states.get(_e)
            if _est and _est.state == "on":
                _has_on_devices = True
                break
        if not _has_on_devices:
            return None  # 房间已全关，无需执行

        # 安全检查 3：用户最近手动操作保护
        _manual_actions = getattr(coord, "_user_manual_actions", {})
        _manual_window = getattr(coord, "_USER_MANUAL_WINDOW", 1800)
        _now_ts = _time.time()
        _room_protected = any(
            _now_ts - v.get("time", 0) < _manual_window
            for eid_key, v in _manual_actions.items()
            if (coord.device_info.get(eid_key) or {}).get("room") == trigger_room
        )
        if _room_protected:
            return None  # 用户最近手动操作过该房间设备，让慢脑重新推理

        # 查询缓存
        _lookup = getattr(coord, "_lookup_decision_cache", None)
        if _lookup is None:
            return None

        _now = _dt.now()
        # 5B-3: _lookup_decision_cache 返回 dict
        _dep_cached = _lookup(trigger_room, _now.hour, _now.weekday(), "departure")
        if not _dep_cached:
            return None
        cached_actions = _dep_cached["actions"] if isinstance(_dep_cached, dict) else _dep_cached
        _dep_intent = _dep_cached.get("intent", "") if isinstance(_dep_cached, dict) else ""

        # 命中后仍走 IntentVerifier，确保修正抑制/区域隔离等安全检查生效
        try:
            from .intent_verifier import IntentVerifier
            needs_occ_check = any(
                a.get("service") == "turn_off" for a in cached_actions
            )
            _occ_map = {}
            if needs_occ_check and hasattr(coord, "_get_room_occupancy_map"):
                _occ_map = coord._get_room_occupancy_map()

            verifier = IntentVerifier(
                coord.hass, coord.device_info, _occ_map,
                sys_log_func=getattr(coord, "_sys_log", None),
                suppress_check_func=getattr(coord, "_should_suppress_action", None),
            )
            verifier._presence_snapshot = self._get_presence_snapshot()
            verifier._device_capability_snapshot = self._get_device_capability_snapshot()
            verifier._room_topology = getattr(coord, "_room_topology_cache", {}) or {}
            clean_actions, rejected = verifier.verify(cached_actions, trigger_room=trigger_room)
        except Exception as exc:
            _LOGGER.warning("[DepartureCache] IntentVerifier 异常，放弃缓存命中: %s", exc)
            return None

        if not clean_actions:
            if hasattr(coord, "_sys_log"):
                coord._sys_log(
                    "INFO",
                    f"[DepartureCache] 缓存命中但全部动作被验证拒绝（{len(rejected)} 个），交由慢脑",
                )
            return None

        # 离开确认延迟：返回 defer_seconds=30，由 listeners.py 做延迟重验证
        # 防止用户短暂离开（去倒水/上厕所）后灯被立即关掉
        _defer_sec = getattr(coord, "_DEPARTURE_CONFIRM_DELAY", 30)
        if hasattr(coord, "_sys_log"):
            coord._sys_log(
                "INFO",
                f"[DepartureCache] ⏳ 离开缓存命中（延迟 {_defer_sec}s 后执行）: "
                f"room={trigger_room} h={_now.hour} wd={_now.weekday()} "
                f"→ {len(clean_actions)} 个动作",
            )
        return {
            "scene": "DepartureCache",
            "confidence": 88,
            "actions": clean_actions,
            "trigger_room": trigger_room,
            "intent": _dep_intent,
            "defer_seconds": _defer_sec,  # listeners.py 延迟执行 + 重验证
        }

    # ── 快脑路径（System 1）──────────────────────────────────────────────────

    def run_fast_path(
        self,
        entity_id: str,
        new_state: str,
        old_state: str = "",
    ) -> dict | None:
        """
        执行 System 1（极速快脑）完整流水线。

        流程：
          0.   展厅模式：走展厅占用反射弧（PIR ON → 立即开灯，跳过 LLM）
          0.5. Phase 1 DecisionCache：arrival 类触发优先查历史 LLM 决策缓存
          1.   FastBrainEngine.decide() - arrival_baseline / 习惯命中；无可靠数据则返回 None
          2.   IntentVerifier.verify()  - 双阶段意图验证（过滤不合规动作）

        Args:
            entity_id: 触发实体 ID
            new_state: 新状态
            old_state: 旧状态（可选）

        Returns:
            包含 actions/confidence/scene 的字典，或 None（交由 System 2 处理）
        """
        coord = self._coord
        from .const import MODE_SHOWROOM, ZONE_ROLE_WORK

        # 展厅模式：走专属占用反射弧（PIR ON 立即开灯，不走通用 FastBrain 和 LLM）
        # 工作区（ZONE_ROLE_WORK）例外：完全不走反射弧，交由 LLM 按家庭模式处理
        # 其他展厅事件（离开、时段切换等）反射弧返回 None 后仍走 LLM
        if getattr(coord, "_mode", "") == MODE_SHOWROOM:
            _trigger_room = (coord.device_info.get(entity_id) or {}).get("room", "")
            _zone_role = coord.get_zone_role(_trigger_room) if hasattr(coord, "get_zone_role") else ""
            if _zone_role == ZONE_ROLE_WORK:
                # 工作区：跳过反射弧，进入家庭模式的常规决策路径
                pass
            else:
                return self._showroom_occupancy_reflex(entity_id, new_state)
        if getattr(coord, "_learning_mode", False):
            return None

        # ── Step 0.5: Phase 1 DecisionCache — 优先复用 LLM 历史决策 ────────
        # arrival 类触发（存在传感器 on）→ 查 arrival 缓存
        # departure 类触发（存在传感器 off）→ 查 departure 缓存（Phase 1+，v4.10.4）
        # 缓存命中时仍经过 IntentVerifier 验证，保持安全防护完整。
        _cache_result = self._try_decision_cache(entity_id, new_state)
        if _cache_result is not None:
            return _cache_result

        # Phase 1+: Departure DecisionCache（仅对存在传感器 off 有效）
        _depart_result = self._try_departure_cache(entity_id, new_state)
        if _depart_result is not None:
            return _depart_result

        # ── Step 1: FastBrain 决策 ────────────────────────────────────────
        try:
            from .fast_brain import FastBrainEngine
            _patterns = getattr(coord, "_behavior_patterns_cache", [])
            fb = FastBrainEngine(
                coord.hass, coord.device_info,
                behavior_patterns=_patterns,
                sys_log_func=getattr(coord, "_sys_log", None),
                get_baseline_func=getattr(coord, "_get_baseline", None),
                get_arrival_baseline_func=getattr(coord, "_get_arrival_baseline_for_room", None),
            )
            fb._presence_snapshot = self._get_presence_snapshot()
            fb._device_capability_snapshot = self._get_device_capability_snapshot()
            fb._room_topology_cache = getattr(coord, "_room_topology_cache", {}) or {}
            # Phase 13: 注入昼夜节律引擎
            fb._circadian_engine = getattr(coord, "_circadian_engine", None)
            # 5A-1: 注入场景路由所需的场景缓存
            fb._ai_scenes_cache = getattr(coord, "_ai_scenes_cache", [])
            fb._ha_scenes_cache = getattr(coord, "_ha_scenes", [])
            fb_result = fb.decide(entity_id, new_state, old_state)
        except Exception as exc:
            _LOGGER.warning("[DecisionPipeline] FastBrain 异常: %s", exc)
            if hasattr(coord, "_sys_log"):
                coord._sys_log("ERROR", f"[DecisionPipeline] FastBrain 决策异常: {exc}")
            fb_result = None

        if not fb_result:
            return None

        # ── Step 2: IntentVerifier 双阶段验证 ─────────────────────────────
        actions = fb_result.get("actions", [])
        if not actions:
            return None

        trigger_room = (coord.device_info.get(entity_id) or {}).get("room", "")
        if not trigger_room and hasattr(coord, "_get_entity_area"):
            trigger_room = coord._get_entity_area(entity_id)

        try:
            from .intent_verifier import IntentVerifier
            # 懒加载 occ_map：仅当存在关灯动作时才计算（避免每次触发 O(N) 传感器扫描）
            # FastBrain 主要执行 turn_on，关灯动作极少出现，绝大多数事件可跳过此调用
            needs_occ_check = any(
                a.get("service") == "turn_off" and a.get("domain") == "light"
                for a in actions
            )
            _occ_map = {}
            if needs_occ_check and hasattr(coord, "_get_room_occupancy_map"):
                _occ_map = coord._get_room_occupancy_map()
            
            verifier = IntentVerifier(
                coord.hass, coord.device_info, _occ_map,
                sys_log_func=getattr(coord, "_sys_log", None),
                suppress_check_func=getattr(coord, "_should_suppress_action", None),
            )
            verifier._presence_snapshot = self._get_presence_snapshot()
            verifier._device_capability_snapshot = self._get_device_capability_snapshot()
            verifier._room_topology = getattr(coord, "_room_topology_cache", {}) or {}
            clean_actions, rejected = verifier.verify(actions, trigger_room=trigger_room)
            sleep_hints = self._build_sleep_runtime_hints(trigger_room)
            clean_actions = self._attach_runtime_hints(clean_actions, sleep_hints)
            if rejected and hasattr(coord, "_sys_log"):
                _rej_detail = ", ".join(
                    "{eid}({reason})".format(
                        eid=a.get("entity_id", "?"),
                        reason=a.get("reject_reason", ""),
                    )
                    for a in rejected
                )
                coord._sys_log(
                    "INFO",
                    f"[意图验证] 拒绝 {len(rejected)} 个不合规动作: [{_rej_detail}]",
                )
        except Exception as exc:
            # fail-closed 原则：验证器自身异常时，拒绝所有动作而不是放行。
            # 放行未经验证的动作会绕过所有安全防护，风险远高于误拒绝。
            _LOGGER.error("[DecisionPipeline] IntentVerifier 异常，已 fail-closed 拒绝全部动作: %s", exc)
            if hasattr(coord, "_sys_log"):
                coord._sys_log("ERROR", f"[DecisionPipeline] IntentVerifier 验证异常（fail-closed，已拒绝全部 {len(actions)} 个动作）: {exc}")
            clean_actions = []
            rejected = [dict(a, reject_reason=f"验证器异常: {exc}") for a in actions]

        if not clean_actions:
            _msg = f"[DecisionPipeline] 快脑动作全部被验证拒绝（{len(rejected)} 个），交由慢脑处理"
            _LOGGER.info(_msg)
            if hasattr(coord, "_sys_log"):
                coord._sys_log("INFO", _msg)
            return None

        # 返回过滤后的结果
        return {
            "scene": fb_result.get("scene", "FastBrain"),
            "confidence": fb_result.get("confidence", 85),
            "actions": clean_actions,
            "trigger_room": trigger_room,
        }

    # ── 展厅占用反射弧（System 0）────────────────────────────────────────────

    # 反射弧专用保护窗口（秒）：仅对"关灯"类手动操作生效，远短于 LLM 路径的 30 分钟
    _REFLEX_MANUAL_WINDOW = 300  # 5 分钟

    def _showroom_occupancy_reflex(self, entity_id: str, new_state: str) -> dict | None:
        """
        占用反射弧：存在传感器 ON → 基线驱动选灯 → 立即开启，完全跳过 LLM。

        v4.8.68 架构改进：
          - **基线驱动选灯**：不再全部开灯，而是查询 device_baseline 的 on_ratio，
            仅开启使用率 >= 50% 的「常用灯」。无基线数据的新设备默认开启。
          - **豁免修正抑制**：反射弧是确定性快路径（有人→开灯），其准确性由基线筛选保证，
            不受 LLM 路径的修正抑制约束（修正抑制仅对 LLM 慢脑决策生效）。
          - **保护窗口精细化**：从 30 分钟无差别保护改为 5 分钟 + 仅关灯方向触发。

        安全层：
          - 反射冷却：同传感器 30s 内不重复触发
          - 用户覆盖保护：5 分钟内同房间有「关灯」手动操作时跳过
          - IntentVerifier 纯安全验证（不含修正抑制）
        """
        import time as _time
        from datetime import datetime as _dt

        coord = self._coord

        if entity_id.split(".")[0] != "binary_sensor" or new_state != "on":
            return None

        _PRESENCE_KW = getattr(coord, "_PRESENCE_KW", (
            "occupancy", "presence", "motion", "人体", "存在", "有人", "移动",
        ))
        check_str = (coord.device_info.get(entity_id, {}).get("name", "") + entity_id).lower()
        if not any(kw in check_str for kw in _PRESENCE_KW):
            return None

        trigger_room = (coord.device_info.get(entity_id) or {}).get("room", "")
        if not trigger_room:
            return None

        _now_ts = _time.time()

        # 反射冷却：30s 内同传感器不重复触发
        _REFLEX_COOLDOWN = 30
        if not isinstance(getattr(coord, "_showroom_reflex_last", None), dict):
            coord._showroom_reflex_last = {}
        if _now_ts - coord._showroom_reflex_last.get(entity_id, 0) < _REFLEX_COOLDOWN:
            if hasattr(coord, "_sys_log"):
                coord._sys_log("INFO", f"[展厅反射] {entity_id} 反射冷却中，跳过")
            return None

        # ── 用户覆盖保护（精细化：5 分钟 + 仅关灯方向）────────────────────
        _OFF_STATES = getattr(coord, "_OFF_STATES", ("off", "0", "closed"))
        _manual_actions = getattr(coord, "_user_manual_actions", {})
        _room_protected = any(
            _now_ts - v.get("time", 0) < self._REFLEX_MANUAL_WINDOW
            for eid, v in _manual_actions.items()
            if isinstance(v, dict)
            and (coord.device_info.get(eid) or {}).get("room") == trigger_room
            and v.get("state") in _OFF_STATES  # 仅关灯操作触发保护
        )
        if _room_protected:
            if hasattr(coord, "_sys_log"):
                coord._sys_log(
                    "INFO",
                    f"[展厅反射] {trigger_room} 5分钟内有关灯操作，尊重用户意图，跳过"
                )
            return None

        # ── 基线驱动选灯：优先 arrival_baseline，回退 device_baseline ────────
        _REFLEX_ON_RATIO_THRESHOLD = 0.5
        _hour_now = _dt.now().hour

        # 1. 尝试 arrival_baseline（语义：进门时该开哪些灯）
        baseline_map: dict[str, float] = {}
        _get_arrival_bl = getattr(coord, "_get_arrival_baseline_for_room", None)
        if _get_arrival_bl:
            try:
                arrival_rows = _get_arrival_bl(
                    trigger_room, hour_bucket=_hour_now, min_samples=3
                )
                if arrival_rows:
                    baseline_map = {r["entity_id"]: r["turn_on_ratio"] for r in arrival_rows}
            except Exception:
                pass

        # 2. 若 arrival_baseline 无数据，回退到 device_baseline
        _baseline_source = "arrival_baseline"
        if not baseline_map:
            _baseline_source = "device_baseline"
            _get_baseline = getattr(coord, "_get_baseline_for_room", None)
            if _get_baseline:
                try:
                    baselines = _get_baseline(trigger_room, min_samples=3)
                    baseline_map = {r["entity_id"]: r["on_ratio"] for r in baselines}
                except Exception:
                    pass

        if not baseline_map:
            if hasattr(coord, "_sys_log"):
                coord._sys_log(
                    "INFO",
                    f"[展厅反射] {trigger_room} 无可用 arrival/device baseline，"
                    "跳过反射弧，移交慢路径，不做全房间开灯兜底",
                )
            return None

        room_lights_off = []
        skipped_by_baseline = []
        missing_baseline = []
        all_room_lights_off = []  # 未经基线筛选的全量关灯列表，仅用于诊断
        for eid, info in coord.device_info.items():
            if not eid.startswith("light."):
                continue
            if info.get("room") != trigger_room:
                continue
            st = coord.hass.states.get(eid)
            if st is None or st.state != "off":
                continue
            all_room_lights_off.append(eid)
            ratio = baseline_map.get(eid)
            if ratio is None:
                missing_baseline.append(eid)
                continue
            if ratio is not None and ratio < _REFLEX_ON_RATIO_THRESHOLD:
                skipped_by_baseline.append(eid)
                continue
            room_lights_off.append(eid)

        if (skipped_by_baseline or missing_baseline) and hasattr(coord, "_sys_log"):
            names = [
                (coord.device_info.get(e) or {}).get("name", e) for e in skipped_by_baseline
            ]
            unknown_names = [
                (coord.device_info.get(e) or {}).get("name", e) for e in missing_baseline
            ]
            coord._sys_log(
                "INFO",
                f"[展厅反射] {trigger_room} 基线筛选({_baseline_source})跳过 "
                f"{len(skipped_by_baseline)} 盏低使用率灯"
                + (": " + ", ".join(names) if names else "")
                + (
                    f"；{len(missing_baseline)} 盏灯缺少基线，按未知设备跳过: "
                    + ", ".join(unknown_names)
                    if unknown_names
                    else ""
                ),
            )

        # ── 用户锁定规则：人数条件性设备过滤 ────────────────────────────────
        # 解析形如"大于N人才能开XXX"的锁定规则，Frigate person_count 不满足时
        # 将对应设备从本次开灯列表中排除，保持 LLM 路径与反射弧一致的行为。
        try:
            _person_count = 0
            try:
                _person_count = int((coord._get_room_person_counts() or {}).get(trigger_room, 0) or 0)
            except Exception:
                _person_count = 0

            _parsed_rules = coord._build_locked_people_rules()
            _rule_blocked: set[str] = set()
            for _le in room_lights_off:
                _blocked, _rule_text = coord._is_light_blocked_by_people_rule(
                    entity_id=_le,
                    room=trigger_room,
                    person_count=_person_count,
                    parsed_rules=_parsed_rules,
                )
                if _blocked:
                    _rule_blocked.add(_le)

            if _rule_blocked:
                _blocked_names = [
                    (coord.device_info.get(e) or {}).get("name", e) for e in _rule_blocked
                ]
                coord._sys_log(
                    "INFO",
                    f"[展厅反射] {trigger_room} 人数={_person_count}人，"
                    f"未达用户规则阈值，过滤 {len(_rule_blocked)} 盏条件性设备: "
                    + ", ".join(_blocked_names),
                )
                room_lights_off = [e for e in room_lights_off if e not in _rule_blocked]
        except Exception as _rule_exc:
            _LOGGER.warning("[展厅反射] 用户规则人数检查异常（忽略，继续开灯）: %s", _rule_exc)
        # ── 用户规则人数过滤 END ──────────────────────────────────────────────

        if not room_lights_off:
            if hasattr(coord, "_sys_log"):
                if all_room_lights_off and (skipped_by_baseline or missing_baseline):
                    coord._sys_log(
                        "INFO",
                        f"[展厅反射] {trigger_room} 基线过滤后无可开灯，跳过反射弧，不做关键词选灯兜底",
                    )
                else:
                    coord._sys_log("INFO", f"[展厅反射] {trigger_room} 无需开灯（灯已全亮）")
            return None

        # Phase 13: 优先使用昼夜节律引擎获取亮度/色温/过渡时长（必须 enabled=True）
        hour = _dt.now().hour
        _circadian = getattr(coord, "_circadian_engine", None)
        if _circadian is not None and _circadian.enabled:
            try:
                _ct = _circadian.get_target(trigger_room)
                brightness = _ct["brightness_pct"]
                color_temp = _ct["color_temp_kelvin"]
                transition = _ct["transition"]
            except Exception:
                brightness = coord._get_time_brightness(hour) if hasattr(coord, "_get_time_brightness") else 80
                color_temp = None
                transition = 2
        else:
            brightness = (
                coord._get_time_brightness(hour)
                if hasattr(coord, "_get_time_brightness")
                else 80
            )
            color_temp = None
            transition = 2

        now_min = hour * 60 + _dt.now().minute
        is_biz = (
            getattr(coord, "showroom_biz_start_min", 9 * 60) <= now_min
            < getattr(coord, "showroom_biz_end_min", 21 * 60)
        )
        if is_biz:
            brightness = max(brightness, 80)

        actions = []
        for eid in room_lights_off:
            _params = {"brightness_pct": brightness, "transition": transition}
            if color_temp is not None:
                _a_ct = color_temp
                _state = coord.hass.states.get(eid)
                if _state and _state.attributes:
                    _min_ct = _state.attributes.get("min_color_temp_kelvin")
                    _max_ct = _state.attributes.get("max_color_temp_kelvin")
                    if _min_ct is not None and _max_ct is not None:
                        _a_ct = max(_min_ct, min(_max_ct, _a_ct))
                _params["color_temp_kelvin"] = _a_ct
            actions.append({
                "domain": "light",
                "service": "turn_on",
                "entity_id": eid,
                "params": _params,
                "reason": (
                    f"[展厅反射] {trigger_room}检测到人员，开灯至 {brightness}%"
                    + (f" / {color_temp}K" if color_temp else "")
                    + f" / {transition}s渐变"
                ),
                "delay_seconds": 0,
            })

        # ── IntentVerifier 纯安全验证（豁免修正抑制）──────────────────────
        try:
            from .intent_verifier import IntentVerifier
            verifier = IntentVerifier(
                coord.hass, coord.device_info, {},
                sys_log_func=getattr(coord, "_sys_log", None),
                suppress_check_func=None,  # 反射弧豁免修正抑制，准确性由基线筛选保证
            )
            clean_actions, rejected = verifier.verify(actions, trigger_room=trigger_room)
            if rejected and hasattr(coord, "_sys_log"):
                coord._sys_log(
                    "INFO",
                    f"[展厅反射] {len(rejected)} 个动作被安全验证拒绝: "
                    + ", ".join(a.get("entity_id", "") for a in rejected),
                )
            if not clean_actions:
                return None
        except Exception as exc:
            _LOGGER.error("[展厅反射] IntentVerifier 异常，fail-closed: %s", exc)
            if hasattr(coord, "_sys_log"):
                coord._sys_log("ERROR", f"[展厅反射] 验证异常，已拒绝全部动作: {exc}")
            return None

        coord._showroom_reflex_last[entity_id] = _now_ts

        # 记录本房间最近反射弧开灯时间，供 listeners.py 对 Frigate 摄像头传感器
        # 的离开确认延迟动态调整（5分钟内再次无人 → 延长至 180s，减少开关闪烁）
        if not isinstance(getattr(coord, "_reflex_room_open_time", None), dict):
            coord._reflex_room_open_time = {}
        coord._reflex_room_open_time[trigger_room] = _now_ts

        if hasattr(coord, "_sys_log"):
            coord._sys_log(
                "INFO",
                f"[展厅反射] {trigger_room}检测到人员 → 基线选灯开启 {len(clean_actions)} 盏"
                f"（亮度 {brightness}%，跳过 {len(skipped_by_baseline)} 盏低使用率灯）",
            )

        return {
            "scene": f"展厅反射·{trigger_room}有人开灯",
            "confidence": 95,
            "actions": clean_actions,
            "trigger_room": trigger_room,
        }

    # ── 管道状态报告 ─────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """
        返回当前管道的组件状态（用于调试和监控面板）。
        """
        coord = self._coord
        return {
            "mode": getattr(coord, "_mode", "unknown"),
            "learning_mode": getattr(coord, "_learning_mode", False),
            "behavior_patterns_count": len(getattr(coord, "_behavior_patterns_cache", [])),
            "device_count": len(getattr(coord, "device_info", {})),
            "fast_brain": "enabled",
            "intent_verifier": "enabled",
        }
