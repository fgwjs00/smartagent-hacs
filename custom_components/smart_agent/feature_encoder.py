from __future__ import annotations
import time
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)

class FeatureEncoder:
    """
    Phase 8A: 多模态特征编码器。
    负责将 HA 的状态（时间、触发器、设备状态等）提取并格式化为字典特征。
    在未来，该字典可直接转换为 numpy 数组输入给本地极速小模型。
    """
    def __init__(self, hass, device_info, db_query_func=None, room_topology=None,
                 capability_getter=None, device_capability_snapshot=None):
        self.hass = hass
        self.device_info = device_info
        self._db_query = db_query_func          # 可选，用于 recent_activity_level
        self._room_topology = room_topology or {}  # 可选，用于 adjacent_occupied_count
        self._capability_getter = capability_getter
        self._device_capability_snapshot = device_capability_snapshot or {}

    def _get_device_capability(self, entity_id: str) -> dict:
        """统一读取设备能力，优先复用 coordinator/devices 的快照接口。"""
        if hasattr(self, "_device_capability_snapshot") and isinstance(self._device_capability_snapshot, dict):
            snap = self._device_capability_snapshot.get(entity_id)
            if isinstance(snap, dict):
                return snap
        getter = getattr(self, "_capability_getter", None)
        if callable(getter):
            try:
                cap = getter(entity_id)
                if isinstance(cap, dict):
                    return cap
            except Exception:
                pass
        raw = self.device_info.get(entity_id, {}) or {}
        room = raw.get("room", "")
        return {
            "room": room,
            "control_mode": raw.get("control_mode", "shared"),
            "sensor_type": raw.get("sensor_type", ""),
            "role": raw.get("role", ""),
            "control_zone": raw.get("control_zone", room),
            "disturbance_level": raw.get("disturbance_level", ""),
            "coverage_spaces": raw.get("coverage_spaces", [room] if room else []),
            "shared_fixture": raw.get("shared_fixture", False),
            "sleep_safe": raw.get("sleep_safe", False),
            "risk_level": raw.get("risk_level", "medium"),
            "energy_level": raw.get("energy_level", "medium"),
            "can_trigger_enter": raw.get("can_trigger_enter", False),
            "can_confirm_leave": raw.get("can_confirm_leave", False),
            "can_block_turn_off": raw.get("can_block_turn_off", False),
            "can_localize_zone": raw.get("can_localize_zone", False),
        }

    def encode(self, entity_id: str, new_state: str, old_state: str = "") -> dict:
        """
        将当前环境状态编码为特征字典。

        Args:
            entity_id: 触发实体 ID
            new_state: 新状态字符串
            old_state: 旧状态字符串（可选）。用于判断状态转换方向，
                       例如区分"刚进入有人"（off→on）与"持续有人"（on→on）。
        """
        now = datetime.now()
        features = {
            "trigger_entity": entity_id,
            "trigger_state": new_state,
            "trigger_old_state": old_state,
            # 状态从 off 变 on 表示刚刚进入，比持续有人更需要立即响应
            "trigger_state_changed": old_state != new_state and bool(old_state),
            "trigger_domain": entity_id.split(".")[0] if entity_id else "",
            "time_hour": now.hour,
            "time_minute": now.minute,
            "is_weekend": now.weekday() >= 5,
        }
        
        # 提取触发实体的房间信息
        trigger_cap = self._get_device_capability(entity_id)
        room = trigger_cap.get("room", "")
        features["trigger_room"] = room
        
        # 获取同房间内设备状态 (构建局部感知上下文)
        # room_lights: 仅灯光，供现有快脑启发式路径使用。
        # room_devices: 通用可控设备集合，供本地 ML 预测校验使用。
        # 排除 control_mode=ha 的设备：这些设备由 HA 自动化管控，FastBrain 不应干预。
        room_lights = {}
        room_devices = {}
        ctrl_domains = {"light", "switch", "climate", "fan", "cover", "media_player"}
        if room:
            for eid in self.device_info.keys():
                info = self._get_device_capability(eid)
                if info.get("room") != room:
                    continue
                if info.get("control_mode", "shared") == "ha":
                    continue  # HA 优先模式：FastBrain 不选此设备
                domain = eid.split(".")[0] if "." in eid else ""
                if domain not in ctrl_domains:
                    continue
                st = self.hass.states.get(eid)
                # 显式处理 unavailable 和 unknown
                if not st or st.state in ("unavailable", "unknown"):
                    state = "unknown"
                else:
                    state = st.state
                room_devices[eid] = state
                if domain == "light":
                    room_lights[eid] = state

        features["room_lights"] = room_lights
        features["room_devices"] = room_devices
        
        # P2 主动智能宏观感知: 季节与室外气温
        features["season_encoding"] = self._get_season_encoding(now.month)
        
        outdoor_temp = self._get_outdoor_temp()
        features["outdoor_temp"] = outdoor_temp
        
        # 简化版的气温趋势标签，帮助 FastBrain 判断是"夏天该制冷"还是"冬天该制热"
        features["outdoor_temp_trend"] = "unknown"
        if outdoor_temp is not None:
            if outdoor_temp < 15:
                features["outdoor_temp_trend"] = "cold"
            elif outdoor_temp > 26:
                features["outdoor_temp_trend"] = "hot"
            else:
                features["outdoor_temp_trend"] = "moderate"

        # P3 主动智能多模态感知: Frigate 视觉人数融合
        features["room_person_count"] = self._get_room_person_count(room)

        # ── P0-2 扩展特征（14维→20维）────────────────────────────────────────
        features["occupancy_duration_min"] = self._get_occupancy_duration(room)
        features["ambient_lux"] = self._get_ambient_lux(room)
        features["is_holiday"] = self._is_chinese_holiday(now)
        features["weather_condition"] = self._get_weather_condition()
        features["recent_activity_level"] = self._get_recent_activity_level(room)
        features["adjacent_occupied_count"] = self._get_adjacent_occupied_count(room)

        return features

    def _get_room_person_count(self, room: str) -> int:
        """从对应房间的 Frigate person_count 传感器获取人数。"""
        if not room:
            return 0
        room_lower = room.lower()
        kw_list = ("person_count", "people_count", "person_detected", "人数")
        
        max_count = 0
        for state in self.hass.states.async_all("sensor"):
            eid = state.entity_id.lower()
            name = state.attributes.get("friendly_name", eid).lower()
            if any(kw in eid or kw in name for kw in kw_list):
                cap = self._get_device_capability(state.entity_id)
                dev_room = cap.get("room", "").lower()

                if dev_room == room_lower or room_lower in eid or room_lower in name:
                    try:
                        count = int(float(state.state))
                        if count > max_count:
                            max_count = count
                    except (ValueError, TypeError) as exc:
                        _LOGGER.debug("[FeatureEncoder] 解析人数传感器 %s 状态失败: %s", state.entity_id, exc)
        return max_count

    def _get_season_encoding(self, month: int) -> str:
        """根据月份返回简单的季节特征，防止机器遗忘症（夏天学的经验在冬天用错）"""
        if month in (3, 4, 5): return "spring"
        if month in (6, 7, 8): return "summer"
        if month in (9, 10, 11): return "autumn"
        return "winter"

    def _get_outdoor_temp(self) -> float | None:
        """尝试从 HA 获取室外气温。优先天气组件，其次室外温度传感器。"""
        # 天气组件通常包含 attributes: temperature
        for state in self.hass.states.async_all("weather"):
            if state.attributes and "temperature" in state.attributes:
                try:
                    return float(state.attributes["temperature"])
                except (ValueError, TypeError) as exc:
                    _LOGGER.debug("[FeatureEncoder] 解析天气组件 %s 温度失败: %s", state.entity_id, exc)
                    
        # 兜底：搜索可能包含 outdoor temperature 的传感器
        for state in self.hass.states.async_all("sensor"):
            eid = state.entity_id.lower()
            if "temperature" in eid and ("outdoor" in eid or "outside" in eid or "out" in eid):
                try:
                    return float(state.state)
                except (ValueError, TypeError) as exc:
                    _LOGGER.debug("[FeatureEncoder] 解析温度传感器 %s 状态失败: %s", state.entity_id, exc)
        return None

    # ── P0-2 扩展特征方法 ────────────────────────────────────────────────────

    _PRESENCE_KW = (
        "occupancy", "presence", "motion", "人体", "存在", "有人",
        "移动", "ren_ti", "cun_zai", "radar", "mmwave", "雷达",
    )

    def _get_occupancy_duration(self, room: str) -> int:
        """当前房间存在传感器持续 on 的时长（分钟）。无传感器或无人返回 0。"""
        if not room:
            return 0
        room_lower = room.lower()
        now = datetime.now()
        max_minutes = 0
        for state in self.hass.states.async_all("binary_sensor"):
            eid = state.entity_id.lower()
            name = (state.attributes.get("friendly_name") or eid).lower()
            if not any(kw in eid or kw in name for kw in self._PRESENCE_KW):
                continue
            cap = self._get_device_capability(state.entity_id)
            dev_room = cap.get("room", "").lower()
            if dev_room != room_lower and room_lower not in eid:
                continue
            if state.state != "on":
                continue
            last_changed = state.last_changed
            if last_changed is None:
                continue
            try:
                from homeassistant.util.dt import utcnow
                now_utc = utcnow()
                if last_changed.tzinfo is None:
                    delta = (datetime.now() - last_changed).total_seconds()
                else:
                    delta = (now_utc - last_changed).total_seconds()
                minutes = int(max(0, delta) / 60)
                if minutes > max_minutes:
                    max_minutes = minutes
            except Exception:
                pass
        return max_minutes

    def _get_ambient_lux(self, room: str) -> float | None:
        """获取房间照度传感器的当前值（lux）。"""
        if not room:
            return None
        room_lower = room.lower()
        lux_kw = ("illuminance", "lux", "照度", "光照", "brightness_lux")
        for state in self.hass.states.async_all("sensor"):
            eid = state.entity_id.lower()
            name = (state.attributes.get("friendly_name") or eid).lower()
            if not any(kw in eid or kw in name for kw in lux_kw):
                continue
            dev_info = self.device_info.get(state.entity_id, {})
            dev_room = dev_info.get("room", "").lower()
            if dev_room == room_lower or room_lower in eid or room_lower in name:
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        return None

    def _is_chinese_holiday(self, now: datetime) -> bool:
        """判断当前日期是否为中国法定节假日。"""
        from .const import CHINESE_HOLIDAYS_2026

        if now.year != 2026:
            _LOGGER.warning("[FeatureEncoder] CHINESE_HOLIDAYS_2026 仅覆盖 2026 年，当前年份=%s", now.year)
            return False

        return now.strftime("%Y-%m-%d") in CHINESE_HOLIDAYS_2026

    def _get_weather_condition(self) -> str:
        """从 HA weather 组件获取天气状况字符串（如 sunny/cloudy/rainy）。"""
        for state in self.hass.states.async_all("weather"):
            if state.state and state.state not in ("unavailable", "unknown"):
                return state.state
        return "unknown"

    def _get_recent_activity_level(self, room: str) -> str:
        """近 30 分钟该房间的事件频率：high(≥10)/medium(3-9)/low(<3)。"""
        if not room or not self._db_query:
            return "unknown"
        try:
            rows = self._db_query(
                "SELECT COUNT(*) as cnt FROM events "
                "WHERE area = ? AND time >= datetime('now', '-30 minutes')",
                (room,),
            )
            cnt = rows[0]["cnt"] if rows else 0
            if cnt >= 10:
                return "high"
            if cnt >= 3:
                return "medium"
            return "low"
        except Exception:
            return "unknown"

    def _get_adjacent_occupied_count(self, room: str) -> int:
        """相邻房间中有人的房间数量。"""
        if not room or not self._room_topology:
            return 0
        adjacent_rooms = self._room_topology.get(room, set())
        if not adjacent_rooms:
            return 0
        count = 0
        for adj_room in adjacent_rooms:
            adj_lower = adj_room.lower()
            for state in self.hass.states.async_all("binary_sensor"):
                eid = state.entity_id.lower()
                name = (state.attributes.get("friendly_name") or eid).lower()
                if not any(kw in eid or kw in name for kw in self._PRESENCE_KW):
                    continue
                cap = self._get_device_capability(state.entity_id)
                dev_room = cap.get("room", "").lower()
                if dev_room == adj_lower and state.state == "on":
                    count += 1
                    break  # 该相邻房间已确认有人，跳到下一个
        return count
