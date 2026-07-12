"""
CircadianEngine — 昼夜节律引擎 (Phase 13.2)。

基于分段线性插值生成全天连续的亮度/色温/过渡时长曲线。
自动读取 HA sun.sun 实体的日出日落时间，适应季节变化。
支持房间修正系数（卧室更暗暖、书房更亮冷等）。

使用方法::

    engine = CircadianEngine(hass, wake_time="07:00", sleep_time="23:00")
    target = engine.get_target("客厅")
    # {"brightness_pct": 72, "color_temp_kelvin": 4200, "transition": 3}
"""
from __future__ import annotations

import logging
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _circadian_timezone(configured_timezone: str):
    normalized_tz = configured_timezone.lower()
    fixed_offset_hours = {
        "asia/shanghai": 8,
        "asia/chongqing": 8,
        "asia/harbin": 8,
        "asia/hong_kong": 8,
        "hongkong": 8,
        "prc": 8,
        "utc": 0,
    }.get(normalized_tz)
    try:
        return ZoneInfo(configured_timezone)
    except ZoneInfoNotFoundError:
        if fixed_offset_hours is not None:
            return timezone(timedelta(hours=fixed_offset_hours), configured_timezone)
        raise

# 房间修正系数：(亮度倍率, 色温偏移K)
_ROOM_MODIFIERS: dict[str, tuple[float, int]] = {
    "卧室": (0.5, -500),
    "主卧": (0.5, -500),
    "次卧": (0.5, -500),
    "bedroom": (0.5, -500),
    "书房": (1.0, 500),
    "学习": (1.0, 500),
    "study": (1.0, 500),
    "办公": (1.0, 300),
    "工作": (0.95, 200),
    "office": (1.0, 300),
    "客厅": (0.9, 0),
    "living": (0.9, 0),
    "茶室": (0.7, -300),
    "茶": (0.7, -300),
    "tea": (0.7, -300),
    "餐厅": (0.8, -200),
    "dining": (0.8, -200),
    "厨房": (1.0, 200),
    "kitchen": (1.0, 200),
    "卫生间": (0.9, 0),
    "浴室": (0.9, 0),
    "bathroom": (0.9, 0),
    "玄关": (0.85, 0),
    "走廊": (0.8, 0),
    "corridor": (0.8, 0),
    "阳台": (0.7, -200),
    "balcony": (0.7, -200),
}


def _parse_time(t: str) -> dt_time:
    """解析 HH:MM 格式时间字符串，非法格式抛出 ValueError。"""
    try:
        parts = str(t).strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return dt_time(h, m)  # dt_time 构造函数自动校验 0<=h<=23, 0<=m<=59
    except (ValueError, IndexError, AttributeError) as exc:
        raise ValueError(f"非法昼夜节律时间格式 '{t}'，应为 HH:MM（如 07:00）") from exc


def _time_to_minutes(t: dt_time) -> float:
    return t.hour * 60 + t.minute


def _lerp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """两点间线性插值。当 x0==x1 时直接返回 y0。"""
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


class CircadianEngine:
    """昼夜节律引擎：全天连续亮度/色温/过渡时长曲线。"""

    # 色温硬限制
    CT_MIN = 2000
    CT_MAX = 6500

    def __init__(
        self,
        hass: HomeAssistant,
        wake_time: str = "07:00",
        sleep_time: str = "23:00",
        max_brightness: int = 100,
        enabled: bool = True,
    ):
        self.hass = hass
        self._wake = _parse_time(wake_time)
        self._sleep = _parse_time(sleep_time)
        self._max_bri = max(20, min(100, max_brightness))
        self.enabled = enabled

    def update_config(
        self,
        wake_time: str | None = None,
        sleep_time: str | None = None,
        max_brightness: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        """热更新配置（无需重建实例）。非法时间字符串记录警告并保持原值。"""
        import logging as _logging
        _log = _logging.getLogger(__name__)
        if wake_time is not None:
            try:
                self._wake = _parse_time(wake_time)
            except ValueError as exc:
                _log.warning("[CircadianEngine] 起床时间无效，保持原值: %s", exc)
        if sleep_time is not None:
            try:
                self._sleep = _parse_time(sleep_time)
            except ValueError as exc:
                _log.warning("[CircadianEngine] 睡觉时间无效，保持原值: %s", exc)
        if max_brightness is not None:
            self._max_bri = max(20, min(100, max_brightness))
        if enabled is not None:
            self.enabled = enabled

    def _get_sun_times(self) -> tuple[float, float]:
        """从 HA sun.sun 获取今日日出/日落时间（分钟），回退到默认值。"""
        default_rise = 6 * 60 + 30   # 06:30
        default_set = 18 * 60 + 30   # 18:30
        try:
            sun = self.hass.states.get("sun.sun")
            if sun is None:
                return default_rise, default_set
            attrs = sun.attributes or {}
            nr = attrs.get("next_rising")
            ns = attrs.get("next_setting")
            rise_min = default_rise
            set_min = default_set
            if nr:
                if isinstance(nr, str):
                    nr_dt = datetime.fromisoformat(nr.replace("Z", "+00:00"))
                else:
                    nr_dt = nr
                nr_local = nr_dt.astimezone()
                rise_min = nr_local.hour * 60 + nr_local.minute
            if ns:
                if isinstance(ns, str):
                    ns_dt = datetime.fromisoformat(ns.replace("Z", "+00:00"))
                else:
                    ns_dt = ns
                ns_local = ns_dt.astimezone()
                set_min = ns_local.hour * 60 + ns_local.minute
            if set_min <= rise_min:
                set_min = default_set
            return rise_min, set_min
        except Exception:
            return default_rise, default_set

    def _build_anchors(self) -> list[tuple[float, float, float, float]]:
        """构建锚点序列: [(minute, brightness%, color_temp_K, transition_s), ...]。

        锚点基于起床/睡觉时间 + 日出/日落动态计算。
        """
        wake_min = _time_to_minutes(self._wake)
        sleep_min = _time_to_minutes(self._sleep)
        rise_min, set_min = self._get_sun_times()

        M = self._max_bri

        anchors = [
            # 深夜最低点
            (2 * 60,                    max(5, M * 0.05),    2200,  10),
            # 起床时刻
            (wake_min,                  max(10, M * 0.30),   2700,  8),
            # 日出后1小时
            (rise_min + 60,             max(30, M * 0.70),   4000,  5),
            # 正午
            (12 * 60,                   M,                   5500,  2),
            # 日落前1小时
            (set_min - 60,              max(30, M * 0.80),   4500,  3),
            # 日落
            (set_min,                   max(20, M * 0.60),   3500,  5),
            # 睡前1小时
            (sleep_min - 60,            max(15, M * 0.40),   3000,  8),
            # 睡觉时刻
            (sleep_min,                 max(10, M * 0.15),   2700,  10),
            # 次日深夜（wrap）
            (24 * 60 + 2 * 60,          max(5, M * 0.05),    2200,  10),
        ]
        anchors.sort(key=lambda a: a[0])
        return anchors

    def _interpolate(self, now_min: float) -> tuple[float, float, float]:
        """在锚点间线性插值，返回 (brightness%, color_temp_K, transition_s)。"""
        anchors = self._build_anchors()

        search_min = now_min
        if now_min < anchors[0][0]:
            search_min = now_min + 24 * 60

        prev = anchors[0]
        for anchor in anchors:
            if anchor[0] >= search_min:
                bri = _lerp(search_min, prev[0], anchor[0], prev[1], anchor[1])
                ct  = _lerp(search_min, prev[0], anchor[0], prev[2], anchor[2])
                tr  = _lerp(search_min, prev[0], anchor[0], prev[3], anchor[3])
                return bri, ct, tr
            prev = anchor

        return prev[1], prev[2], prev[3]

    def _apply_room_modifier(
        self, room: str, bri: float, ct: float
    ) -> tuple[float, float]:
        """根据房间类型微调亮度和色温。"""
        room_lower = room.lower()
        for kw, (bri_mult, ct_offset) in _ROOM_MODIFIERS.items():
            if kw in room_lower:
                bri = bri * bri_mult
                ct = ct + ct_offset
                break
        bri = max(1, min(100, bri))
        ct = max(self.CT_MIN, min(self.CT_MAX, ct))
        return bri, ct

    def _ha_local_now(self) -> datetime:
        config = getattr(getattr(self, "hass", None), "config", None)
        configured_timezone = str(getattr(config, "time_zone", "") or "").strip()
        if configured_timezone:
            try:
                return datetime.now(_circadian_timezone(configured_timezone))
            except ZoneInfoNotFoundError:
                _LOGGER.debug("[CircadianEngine] invalid HA timezone for local clock: %s", configured_timezone)
            except Exception as exc:
                _LOGGER.debug("[CircadianEngine] HA timezone read failed for local clock: %s", exc)
        from homeassistant.util import dt as dt_util

        return dt_util.now()

    def get_target(
        self, room: str = "", now: datetime | None = None
    ) -> dict:
        """返回当前时刻该房间的推荐灯光参数。

        :param room: 房间名称（中文或英文）
        :param now: 当前时间，None 则使用系统时间
        :return: {"brightness_pct": int, "color_temp_kelvin": int, "transition": int}
        """
        if not self.enabled:
            return {"brightness_pct": 80, "color_temp_kelvin": 4000, "transition": 2}

        if now is None:
            now = self._ha_local_now()
        now_min = now.hour * 60 + now.minute + now.second / 60

        bri, ct, tr = self._interpolate(now_min)

        if room:
            bri, ct = self._apply_room_modifier(room, bri, ct)

        return {
            "brightness_pct": round(bri),
            "color_temp_kelvin": round(ct),
            "transition": max(1, round(tr)),
        }

    def should_adjust(
        self,
        entity_id: str,
        current_brightness: int | None,
        current_ct: int | None,
        room: str = "",
    ) -> dict | None:
        """对比当前灯光状态与节律目标，若偏差超阈值则返回调整动作。

        用于巡检精调。偏差阈值：亮度 >15%，色温 >500K。
        返回 None 表示无需调整。
        """
        if not self.enabled:
            return None

        target = self.get_target(room)
        t_bri = target["brightness_pct"]
        t_ct = target["color_temp_kelvin"]

        bri_diff = abs((current_brightness or 0) - t_bri)
        # current_ct=None 表示该灯不支持色温，跳过色温偏差判断
        supports_ct = current_ct is not None
        ct_diff = abs(current_ct - t_ct) if supports_ct else 0

        if bri_diff <= 15 and ct_diff <= 500:
            return None

        _params: dict = {"brightness_pct": t_bri, "transition": 30}
        reason_parts = [f"亮度差{bri_diff}%"]
        if supports_ct:
            _params["color_temp_kelvin"] = t_ct
            reason_parts.append(f"色温差{ct_diff}K")

        return {
            "domain": "light",
            "service": "turn_on",
            "entity_id": entity_id,
            "params": _params,
            "reason": (
                f"[昼夜节律] 灯光偏离节律曲线（{'，'.join(reason_parts)}），"
                f"渐变调整至 {t_bri}%"
                + (f"/{t_ct}K" if supports_ct else "")
            ),
            "delay_seconds": 0,
        }
