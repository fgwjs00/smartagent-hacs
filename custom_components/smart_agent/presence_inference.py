"""
PresenceInference — 虚拟在场推断引擎 (Phase 10.0)。

解决无传感器家庭的"占用状态"判断问题。

设计目标：
  即便家里没有任何人体传感器，系统也能通过融合多维度间接信号，
  为每个房间推断出概率化的占用置信度，供安全守卫、意图验证等模块使用。

三层信号融合架构：
  Layer 1 (硬件直觉层): mmWave / PIR / Frigate → confidence = 1.0
  Layer 2 (软件推断层): device_tracker / person / 设备操作痕迹 / 门窗状态 → 0.3~0.7
  Layer 3 (行为推理层): 时间模式 / 设备使用关联 / 历史习惯 → 0.1~0.4

输出格式：
  {
    "客厅": RoomPresence(confidence=0.85, level="high", has_hw_sensor=False, ...),
    "卧室": RoomPresence(confidence=0.35, level="low", ...),
  }

置信度分级与决策策略：
  ≥ 0.8  → "high"    等同硬件有人：开灯保护生效、关灯拦截
  0.5~0.8 → "medium"  可能有人：允许安全可逆操作，高危操作需确认
  0.2~0.5 → "low"     不确定：仅允许安全可逆操作，不主动关空调/热水器
  < 0.2  → "empty"   大概率无人：允许节能策略

注意：当房间有硬件传感器时，始终以硬件传感器结果为最终判断（confidence=1.0）。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_LOGGER = logging.getLogger(__name__)

# 置信度分级阈值
CONFIDENCE_HIGH = 0.8    # ≥ 0.8 → 等同有人
CONFIDENCE_MEDIUM = 0.5  # ≥ 0.5 → 可能有人
CONFIDENCE_LOW = 0.2     # ≥ 0.2 → 不确定

# 设备操作痕迹有效期（秒）：若 N 秒内用户手动操作过该房间设备，视为有人信号
DEVICE_TRACE_WINDOW_SEC = 15 * 60   # 15 分钟

# person/device_tracker 实体状态中表示"在家"的值
HOME_STATES = frozenset(("home", "Home", "HOME"))

# 媒体播放器"活跃"状态
MEDIA_ACTIVE_STATES = frozenset(("playing", "paused"))

# 只有人工交互可以作为在场证据，AI/自动化动作必须过滤，避免自强化。
HUMAN_DEVICE_TRACE_SOURCES = frozenset(("user", "manual", "physical", "dashboard", "voice"))


@dataclass
class RoomPresence:
    """单个房间的在场推断结果。"""

    room: str
    """房间名称"""

    confidence: float = 0.0
    """综合占用置信度 0.0~1.0"""

    level: str = "unknown"
    """置信度等级: high / medium / low / empty / unknown"""

    has_hw_sensor: bool = False
    """该房间是否有硬件在场传感器（mmWave/PIR/Frigate）"""

    signals: list[tuple[str, str, float]] = field(default_factory=list)
    """贡献信号列表: [(entity_id_or_tag, description, weight), ...]"""

    sensor_state: str | None = None
    """硬件传感器状态（on/off/unknown），仅 has_hw_sensor=True 时有意义"""

    def to_occ_map_entry(self) -> list[tuple[str, str]]:
        """
        兼容旧版 occ_map 格式，返回 [(entity_id, state)] 结构。
        供 protection / intent_verifier 直接消费，无需改动消费方。
        """
        if self.has_hw_sensor and self.sensor_state is not None:
            return [("hw_sensor", self.sensor_state)]
        # 软推断结果：根据置信度合成虚拟传感器状态
        if self.level in ("high", "medium"):
            return [("inferred_presence", "on")]
        if self.level == "low":
            # 不确定时返回 unknown 触发消费方的"放行"逻辑
            return [("inferred_presence", "unknown")]
        if self.level == "empty":
            return [("inferred_presence", "off")]
        # unknown 级别：没有任何信号
        return []

    def to_presence_snapshot(self) -> dict[str, Any]:
        """将房间推断结果转换为统一 Presence Snapshot 结构。"""
        if self.has_hw_sensor and self.sensor_state is not None:
            state = self.sensor_state if self.sensor_state in ("on", "off") else "unknown"
        elif self.level in ("high", "medium"):
            state = "on"
        elif self.level == "empty":
            state = "off"
        else:
            state = "unknown"

        reasons = [f"room={self.room}", f"level={self.level}"]
        reasons.extend([f"{eid}:{desc}" for eid, desc, _w in self.signals[:8]])

        enter_qualified = state == "on"
        leave_qualified = state == "off" and not (self.has_hw_sensor and self.sensor_state == "unknown")

        blocked_actions: list[str] = []
        if state == "unknown":
            blocked_actions.append("turn_off")
        if self.level == "low":
            blocked_actions.append("high_risk_off")

        return {
            "state": state,
            "confidence": round(max(0.0, min(self.confidence, 1.0)), 3),
            "reasons": reasons,
            "enter_qualified": enter_qualified,
            "leave_qualified": leave_qualified,
            "localized_spaces": [self.room] if self.room else [],
            "blocked_actions": blocked_actions,
        }


class PresenceInference:
    """
    虚拟在场推断引擎。

    使用方法（在 coordinator / protection 中）::

        pi = PresenceInference(hass, device_info)
        pi.update_device_trace(entity_id, "on", source="user")  # 每次用户操作时调用
        room_map = pi.infer_all_rooms()                         # 获取所有房间推断结果
        presence = pi.infer_room("客厅")                        # 获取单个房间结果
    """

    def __init__(self, hass, device_info: dict):
        self.hass = hass
        self.device_info = device_info
        # 设备操作痕迹缓存: {entity_id: {"time": ts, "state": s, "source": src}}
        self._device_traces: dict[str, dict] = {}

    # ── 外部接口 ────────────────────────────────────────────────────────────────

    def update_device_trace(self, entity_id: str, state: str, source: str = "user") -> None:
        """
        记录用户手动操作的设备痕迹（该房间"刚有人"的间接证明）。
        应在 listeners 检测到用户操作时调用。
        """
        self._device_traces[entity_id] = {
            "time": time.time(),
            "state": state,
            "source": source,
        }

    def _is_human_device_trace(self, trace: dict[str, Any]) -> bool:
        source = str(trace.get("source") or "user").strip().lower()
        return source in HUMAN_DEVICE_TRACE_SOURCES

    def get_recent_device_trace_evidence(self) -> list[dict[str, Any]]:
        """Export recent human device interactions as raw presence evidence.

        The add-on PresenceEngine remains the semantic owner. HA only forwards
        interaction traces that can guard a leave/turn-off decision.
        """
        now = time.time()
        evidence: list[dict[str, Any]] = []
        for entity_id, trace in self._device_traces.items():
            if not isinstance(trace, dict) or not self._is_human_device_trace(trace):
                continue
            try:
                trace_ts = float(trace.get("time") or 0)
            except (TypeError, ValueError):
                continue
            if trace_ts <= 0 or now - trace_ts > DEVICE_TRACE_WINDOW_SEC:
                continue

            info = self.device_info.get(entity_id, {}) if isinstance(self.device_info, dict) else {}
            if not isinstance(info, dict):
                info = {}
            space_id = str(
                info.get("space_id")
                or info.get("room")
                or info.get("area")
                or info.get("control_space_id")
                or ""
            ).strip()
            if not space_id:
                continue

            trace_age = max(0, int(now - trace_ts))
            evidence.append(
                {
                    "id": f"{entity_id}:presence_interaction",
                    "entity_id": entity_id,
                    "source": entity_id,
                    "source_type": "manual_action",
                    "action": "presence_interaction",
                    "state": "on",
                    "space_id": space_id,
                    "target_space_ids": [space_id],
                    "coverage_space_ids": [space_id],
                    "confidence": 0.6,
                    "use_for": ["turn_off", "guard"],
                    "observed_at": datetime.fromtimestamp(trace_ts, timezone.utc).isoformat(),
                    "attributes": {
                        "interaction_source": str(trace.get("source") or "user").strip().lower(),
                        "trace_age_sec": trace_age,
                    },
                }
            )
        return evidence

    def infer_all_rooms(self) -> dict[str, RoomPresence]:
        """
        对所有已知房间执行在场推断。

        Returns:
            {room_name: RoomPresence, ...}
        """
        rooms: set[str] = set()
        for info in self.device_info.values():
            r = info.get("room", "").strip()
            if r:
                rooms.add(r)

        result: dict[str, RoomPresence] = {}
        for room in rooms:
            result[room] = self.infer_room(room)
        return result

    def infer_presence_snapshots(self) -> dict[str, dict[str, Any]]:
        """返回所有房间统一 Presence Snapshot 结构。"""
        all_rooms = self.infer_all_rooms()
        return {room: presence.to_presence_snapshot() for room, presence in all_rooms.items()}

    def infer_room_presence_snapshot(self, room: str) -> dict[str, Any]:
        """返回单个房间统一 Presence Snapshot 结构。"""
        return self.infer_room(room).to_presence_snapshot()

    def infer_room(self, room: str) -> RoomPresence:
        """
        对指定房间执行在场推断。

        推断顺序（短路原则）：
          1. Layer 1 硬件传感器（有则直接返回，最高权威）
          2. Layer 2 + Layer 3 软推断，融合多信号计算置信度
        """
        presence = RoomPresence(room=room)
        signals: list[tuple[str, str, float]] = []

        # ── Layer 1: 硬件传感器（mmWave / PIR / Frigate occupancy）──────────────
        hw_result = self._check_hw_sensors(room)
        if hw_result is not None:
            entity_id, state = hw_result
            presence.has_hw_sensor = True
            presence.sensor_state = state
            if state == "on":
                presence.confidence = 1.0
                presence.level = "high"
            elif state == "off":
                presence.confidence = 0.0
                presence.level = "empty"
            else:  # unknown / unavailable
                presence.confidence = 0.3
                presence.level = "low"
            presence.signals = [(entity_id, f"硬件传感器={state}", 1.0)]
            return presence

        # ── Layer 2 + 3: 无硬件传感器，软信号融合 ──────────────────────────────
        confidence = 0.0

        # Signal A: person / device_tracker（家里有人 → 加成；全员外出 → 负信号）
        # 注：Signal A 可返回负值，必须无条件累加；仅无数据时（sigs 为空）跳过
        home_conf, home_sigs = self._check_home_presence()
        if home_sigs:
            confidence += home_conf
            signals.extend(home_sigs)

        # Signal B: 媒体播放器活跃 (电视/音箱播放 → 该房间有人，恒正)
        media_conf, media_sigs = self._check_media_activity(room)
        if media_conf > 0:
            confidence += media_conf
            signals.extend(media_sigs)

        # Signal C: 设备操作痕迹 (用户刚手动操作过该房间设备，恒正)
        trace_conf, trace_sigs = self._check_device_traces(room)
        if trace_conf > 0:
            confidence += trace_conf
            signals.extend(trace_sigs)

        # Signal D: 门窗/门锁状态 (门刚被打开 → 可能有人进出，恒正)
        door_conf, door_sigs = self._check_door_state(room)
        if door_conf > 0:
            confidence += door_conf
            signals.extend(door_sigs)

        # Signal E: 时间+行为模式推理（可返回负值如"工作日日间无人"）
        time_conf, time_sigs = self._check_time_pattern(room)
        if time_sigs:   # 有规则命中就累加，无论正负
            confidence += time_conf
            signals.extend(time_sigs)

        # 置信度限定在 [0, 1]：负信号可抵消正信号，但最终不小于 0
        confidence = max(0.0, min(confidence, 1.0))

        presence.confidence = round(confidence, 3)
        presence.signals = signals

        if confidence >= CONFIDENCE_HIGH:
            presence.level = "high"
        elif confidence >= CONFIDENCE_MEDIUM:
            presence.level = "medium"
        elif confidence >= CONFIDENCE_LOW:
            presence.level = "low"
        elif confidence > 0 or signals:
            presence.level = "empty"
        else:
            presence.level = "unknown"

        return presence

    def to_occ_map(self) -> dict[str, list[tuple[str, str]]]:
        """
        将所有房间推断结果转换为旧版 occ_map 格式，供现有代码直接使用。

        返回格式: {room_name: [(entity_id, state), ...]}
        """
        all_rooms = self.infer_all_rooms()
        result: dict[str, list[tuple[str, str]]] = {}
        for room, presence in all_rooms.items():
            entry = presence.to_occ_map_entry()
            if entry:
                result[room] = entry
        return result

    # ── Layer 1: 硬件传感器 ────────────────────────────────────────────────────

    _PRESENCE_KW = (
        "presence", "occupancy", "motion", "人体", "存在", "人员",
        "mmwave", "pir", "radar", "radar_occupancy", "ld2402",
    )

    def _check_hw_sensors(self, room: str) -> tuple[str, str] | None:
        """
        查找该房间的硬件在场传感器，返回 (entity_id, state) 或 None。

        优先 binary_sensor（mmWave/PIR）, 次选 sensor.xxx_person_count（Frigate）。
        存在多个传感器时，任意一个为 on 即视为有人。

        PIR 传感器优化：
          - on -> 返回 'on' (高置信度)
          - off -> 若类型标记为 'pir'，返回 'unknown' (低置信度/不确定)，
                   不触发关灯拦截，交给 PresenceInference 软推断。
        """
        on_sensor: str | None = None
        off_sensors: list[str] = []
        unknown_sensors: list[str] = []
        pir_off_sensors: list[str] = []

        for eid, info in self.device_info.items():
            r = info.get("room", "").strip()
            if not r and hasattr(self, "_get_entity_area"):
                r = self._get_entity_area(eid)
            if r != room:
                continue

            eid_lower = eid.lower()
            name_lower = info.get("name", "").lower()
            s_type = info.get("sensor_type", "")

            if eid.startswith("binary_sensor."):
                if not any(kw in eid_lower or kw in name_lower for kw in self._PRESENCE_KW):
                    continue
                state = self.hass.states.get(eid)
                cur = state.state if state else "unknown"
                
                if cur == "on":
                    on_sensor = eid
                elif cur == "off":
                    if s_type == "pir":
                        pir_off_sensors.append(eid)
                    else:
                        off_sensors.append(eid)
                else:
                    unknown_sensors.append(eid)

            elif eid.startswith("sensor."):
                if not any(kw in eid_lower for kw in ("person_count", "people_count")):
                    continue
                state = self.hass.states.get(eid)
                if not state:
                    unknown_sensors.append(eid)
                    continue
                try:
                    count = int(float(state.state))
                    if count > 0:
                        on_sensor = eid
                    else:
                        # Frigate 通常被视为 mmwave 级别（持续存在）
                        off_sensors.append(eid)
                except (ValueError, TypeError):
                    unknown_sensors.append(eid)

        if on_sensor:
            return (on_sensor, "on")
        
        # 若有 mmWave 传感器明确报告 off，则返回 off
        if off_sensors:
            return (off_sensors[0], "off")
            
        # 若只有 PIR 传感器报告 off，返回 unknown (不确定状态)
        if pir_off_sensors:
            return (pir_off_sensors[0], "unknown")
            
        if unknown_sensors:
            return (unknown_sensors[0], "unknown")
            
        return None  # 该房间无硬件传感器

    # ── Layer 2: 软件推断 ──────────────────────────────────────────────────────

    def _check_home_presence(self) -> tuple[float, list]:
        """
        Signal A: person / device_tracker 实体状态。
        返回 (confidence_contribution, signals)。

        逻辑：
        - 有任意成员在家 (home) → 为所有房间添加基础占用可能 (+0.25)
        - 无人在家 (全部 not_home) → 强烈信号表示无人 → 置信度贡献为负（由调用方决策）
        """
        home_count = 0
        away_count = 0
        sigs = []

        for eid, info in self.device_info.items():
            if not (eid.startswith("person.") or eid.startswith("device_tracker.")):
                continue
            state = self.hass.states.get(eid)
            if not state or state.state in ("unavailable", "unknown"):
                continue
            name = info.get("name", eid)
            if state.state in HOME_STATES:
                home_count += 1
                sigs.append((eid, f"{name} 在家", 0.25))
            else:
                away_count += 1
                sigs.append((eid, f"{name} 外出", -0.1))

        if not sigs:
            return 0.0, []

        # 全部成员外出 → 强负信号，但调用方会 min(confidence, 1.0)，负值不会叠加错误
        if away_count > 0 and home_count == 0:
            # 全员外出 → 强负信号；调用方（infer_room）累加后会 max(0, sum) 兜底
            total = 0.4 * away_count   # 正数，外面取负后传出
            return -total, sigs

        total = min(0.35, 0.25 * home_count)  # 最多贡献 0.35
        return total, sigs

    def _check_media_activity(self, room: str) -> tuple[float, list]:
        """
        Signal B: 媒体播放器活跃状态（电视/音箱正在播放）。
        媒体播放 → 该房间几乎肯定有人 (+0.55)。
        """
        for eid, info in self.device_info.items():
            if not eid.startswith("media_player."):
                continue
            r = info.get("room", "").strip()
            if not r and hasattr(self, "_get_entity_area"):
                r = self._get_entity_area(eid)
            if r != room:
                continue
            state = self.hass.states.get(eid)
            if not state:
                continue
            if state.state in MEDIA_ACTIVE_STATES:
                trace = self._device_traces.get(eid)
                if isinstance(trace, dict) and not self._is_human_device_trace(trace):
                    continue
                name = info.get("name", eid)
                return 0.55, [(eid, f"{name} 正在播放", 0.55)]
        return 0.0, []

    def _check_device_traces(self, room: str) -> tuple[float, list]:
        """
        Signal C: 用户近期手动操作该房间设备的痕迹（间接在场证明）。

        计分：
        - 5 分钟内操作 → +0.60
        - 5~15 分钟内操作 → +0.30
        """
        now = time.time()
        best_conf = 0.0
        best_sig = None

        for eid, trace in self._device_traces.items():
            if not isinstance(trace, dict) or not self._is_human_device_trace(trace):
                continue
            info = self.device_info.get(eid, {})
            r = info.get("room", "").strip()
            if not r:
                continue
            if r != room:
                continue
            elapsed = now - trace.get("time", 0)
            if elapsed > DEVICE_TRACE_WINDOW_SEC:
                continue
            if elapsed <= 300:  # 5 分钟内
                conf = 0.60
            else:
                conf = 0.30

            if conf > best_conf:
                best_conf = conf
                name = info.get("name", eid)
                mins = int(elapsed / 60)
                best_sig = (eid, f"{name} {mins}分钟前被手动操作", conf)

        if best_sig:
            return best_conf, [best_sig]
        return 0.0, []

    def _check_door_state(self, room: str) -> tuple[float, list]:
        """
        Signal D: 门窗/门锁状态。
        - 门窗 on（打开）→ 可能有人在附近 (+0.15)
        - 门锁解锁 → 可能有人刚进门 (+0.20)
        """
        for eid, info in self.device_info.items():
            r = info.get("room", "").strip()
            if not r:
                continue
            if r != room:
                continue
            eid_lower = eid.lower()
            name_lower = info.get("name", "").lower()
            state = self.hass.states.get(eid)
            if not state:
                continue

            # 门窗传感器
            if eid.startswith("binary_sensor.") and any(
                kw in eid_lower or kw in name_lower
                for kw in ("door", "window", "门", "窗")
            ):
                if state.state == "on":
                    name = info.get("name", eid)
                    return 0.15, [(eid, f"{name} 开启中", 0.15)]

            # 门锁
            if eid.startswith("lock."):
                if state.state == "unlocked":
                    name = info.get("name", eid)
                    return 0.20, [(eid, f"{name} 已解锁", 0.20)]

        return 0.0, []

    # ── Layer 3: 时间/行为模式推理 ────────────────────────────────────────────

    def _check_time_pattern(self, room: str) -> tuple[float, list]:
        """
        Signal E: 基于时间段与房间名称的行为模式推理。

        使用通用规则（后续可被 ML 行为模式取代）：
        - 卧室：深夜/清晨（22:00-8:00）概率较高
        - 卫生间/厨房：早晨/傍晚（7-9, 17-20）概率较高
        - 客厅：傍晚/晚间（18-23）概率较高
        """
        now = datetime.now()
        h = now.hour
        is_weekend = now.weekday() >= 5
        room_lower = room.lower()

        # 判断是工作日白天 (8-18) — 大概率无人在家
        if not is_weekend and 9 <= h < 18:
            return -0.15, [("time_pattern", f"工作日日间({h}:00)，大概率无人在家", -0.15)]

        # 卧室规则
        if any(kw in room_lower for kw in ("卧", "bedroom", "主卧", "次卧", "儿童房")):
            if 22 <= h or h < 7:
                return 0.35, [("time_pattern", f"深夜/清晨({h}:00)，卧室大概率有人休息", 0.35)]
            if is_weekend and 7 <= h < 10:
                return 0.25, [("time_pattern", f"周末早晨({h}:00)，卧室可能有人", 0.25)]

        # 客厅/起居室规则
        if any(kw in room_lower for kw in ("客厅", "living", "起居", "会客")):
            if 18 <= h < 23:
                return 0.25, [("time_pattern", f"晚间({h}:00)，客厅可能有人活动", 0.25)]
            if is_weekend and 9 <= h < 22:
                return 0.20, [("time_pattern", f"周末白天({h}:00)，客厅可能有人", 0.20)]

        # 厨房/餐厅规则
        if any(kw in room_lower for kw in ("厨", "餐", "kitchen", "dining")):
            if h in (7, 8, 12, 17, 18, 19):
                return 0.30, [("time_pattern", f"用餐/备餐时段({h}:00)，厨房/餐厅可能有人", 0.30)]

        return 0.0, []
