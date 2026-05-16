"""
ListenersMixin — 事件监听层。
负责：HA 状态变化监听、存在传感器去抖、触发合并、冷却管理、快速通道。
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .ha_adapter import async_call_service
from .const import (
    FRIGATE_PERSON_COUNT_KW as _FRIGATE_PERSON_COUNT_KW,
    AI_ACTION_SKIP_WINDOW, URGENT_MERGE_WINDOW, NORMAL_MERGE_WINDOW,
    GLITCH_THRESHOLD, GLITCH_WINDOW, GLITCH_SUPPRESS_SECS,
    PRESENCE_OFF_DELAY, PRESENCE_ON_COOLDOWN, PRESENCE_ON_MIN_HOLD,
    PRESENCE_FLAP_WINDOW, PRESENCE_FLAP_THRESHOLD, PRESENCE_FLAP_SUPPRESS_SECS,
    FRIGATE_COUNT_ON_HOLD, FRIGATE_COUNT_CHANGE_HOLD,
    FRIGATE_COUNT_OFF_HOLD, FRIGATE_COUNT_COOLDOWN,
    SENSOR_DEADBAND_PCT,
)

_LOGGER = logging.getLogger(__name__)


class ListenersMixin:
    """Mixin: 事件监听 — 状态变化 / 去抖 / 触发调度 / 快速通道。"""

    # AI 操作后 N 秒内的同向状态变化视为 AI 自身引起，不再触发
    _AI_ACTION_SKIP_WINDOW = AI_ACTION_SKIP_WINDOW

    # 触发合并窗口
    _URGENT_MERGE_WINDOW = URGENT_MERGE_WINDOW    # binary_sensor 类触发：1 秒
    _NORMAL_MERGE_WINDOW = NORMAL_MERGE_WINDOW    # 其他：3 秒

    # 通信闪断累计抑制参数
    _GLITCH_THRESHOLD = GLITCH_THRESHOLD
    _GLITCH_WINDOW = GLITCH_WINDOW
    _GLITCH_SUPPRESS_SECS = GLITCH_SUPPRESS_SECS

    # 存在传感器去抖参数（binary_sensor.*）
    _PRESENCE_KW = ("occupancy", "presence", "motion", "人体", "存在", "有人", "移动",
                    "ren_ti", "cun_zai", "radar", "mmwave", "雷达",
                    "person_occupancy", "object_count")  # Frigate 生成的占用实体
    _PRESENCE_OFF_DELAY = PRESENCE_OFF_DELAY
    _PRESENCE_ON_COOLDOWN = PRESENCE_ON_COOLDOWN
    _PRESENCE_ON_MIN_HOLD = PRESENCE_ON_MIN_HOLD
    _PRESENCE_FLAP_WINDOW = PRESENCE_FLAP_WINDOW
    _PRESENCE_FLAP_THRESHOLD = PRESENCE_FLAP_THRESHOLD
    _PRESENCE_FLAP_SUPPRESS_SECS = PRESENCE_FLAP_SUPPRESS_SECS

    # Frigate person_count sensor 触发阈值
    _PERSON_COUNT_KW = _FRIGATE_PERSON_COUNT_KW

    # Frigate 人数传感器防抖参数
    _FRIGATE_COUNT_ON_HOLD = FRIGATE_COUNT_ON_HOLD
    _FRIGATE_COUNT_CHANGE_HOLD = FRIGATE_COUNT_CHANGE_HOLD
    _FRIGATE_COUNT_OFF_HOLD = FRIGATE_COUNT_OFF_HOLD
    _FRIGATE_COUNT_COOLDOWN = FRIGATE_COUNT_COOLDOWN

    # 数值型传感器触发死区
    _SENSOR_DEADBAND_PCT: float = SENSOR_DEADBAND_PCT

    # 按时段调整开灯亮度的参考表
    _BRIGHTNESS_TABLE = (
        (6, 8, 70),
        (8, 18, 100),
        (18, 21, 80),
        (21, 23, 60),
        (23, 24, 20),
        (0, 6, 20),
    )

    # ── 触发校验 ──────────────────────────────────────────────────────────────

    def _should_trigger(self, entity_id: str, old: str, new: str) -> bool:
        if not self._is_enabled():
            self._sys_log("WARN", f"触发被拒: AI 已暂停 | {entity_id}")
            return False
        elapsed = time.time() - self._startup_time
        if elapsed < self._startup_grace:
            remaining = int(self._startup_grace - elapsed)
            self._sys_log("INFO", f"启动冷却中({remaining}s 后就绪)，忽略触发: {entity_id} {old}→{new}")
            if remaining <= 3 and not getattr(self, "_startup_ready_notified", False):
                self._startup_ready_notified = True
                self._sys_log("INFO", "✅ 系统即将就绪，下次触发将开始 AI 推理")
            return False
        if not getattr(self, "_startup_ready_notified", False):
            self._startup_ready_notified = True
            self._sys_log("INFO", f"✅ 启动冷却已结束（{int(elapsed)}s），AI 推理已就绪")
        if new in ("unavailable", "unknown"):
            self._sys_log("INFO", f"[过滤] 设备状态变为 {new}，跳过: {entity_id}")
            return False
        if old in ("unavailable", "unknown") and new not in ("on", "open", "home", "playing"):
            self._sys_log("INFO", f"[过滤] 设备从 {old} 恢复为 {new}（非激活状态），跳过: {entity_id}")
            return False
        if entity_id not in self.device_info:
            self._sys_log("WARN", f"触发被拒: {entity_id} 不在已配置设备列表中（请在设备页面添加）")
            return False

        # 数值型传感器死区过滤（SYS-02）：
        # 仅针对 sensor.* 且 old/new 均可解析为浮点数的情况做变化量检查。
        # 非数值传感器（motion: on/off / door: open/closed）直接放行。
        if entity_id.split(".")[0] == "sensor":
            try:
                _old_v = float(old)
                _new_v = float(new)
                _base = max(abs(_old_v), abs(_new_v), 1.0)
                _change_pct = abs(_new_v - _old_v) / _base * 100
                if _change_pct < self._SENSOR_DEADBAND_PCT:
                    self._sys_log(
                        "INFO",
                        f"[死区过滤] {entity_id} {old}→{new} 变化 {_change_pct:.1f}% "
                        f"< 阈值 {self._SENSOR_DEADBAND_PCT}%，跳过推理",
                    )
                    return False
            except (ValueError, TypeError):
                pass  # 非数值型状态（on/off 等），直接放行

        last_ai = self._last_ai_actions.get(entity_id)
        if last_ai:
            age = time.time() - last_ai["time"]
            if age < self._AI_ACTION_SKIP_WINDOW and last_ai["state"] == new:
                self._sys_log("INFO", f"[过滤] AI 操作后 {int(age)}s 内同向变化，跳过: {entity_id} → {new}")
                return False
        return True

    def _effective_cooldown(self) -> int:
        """展厅模式使用更短冷却以便快速响应演示。"""
        return self._SHOWROOM_COOLDOWN if self._mode == "showroom" else self.cooldown

    def _is_presence_flap_suppressed(self, entity_id: str) -> tuple[bool, int]:
        """检查存在传感器是否处于抖动风暴抑制期。"""
        now_ts = time.time()
        suppress_until = self._presence_flap_suppressed.get(entity_id, 0)
        if now_ts < suppress_until:
            return True, int(suppress_until - now_ts)
        if suppress_until:
            self._presence_flap_suppressed.pop(entity_id, None)
        return False, 0

    def _record_presence_flap(self, entity_id: str) -> None:
        """记录 on/off 反转并在高频抖动时进入抑制期。"""
        now_ts = time.time()
        history = self._presence_flap_history.setdefault(entity_id, [])
        history.append(now_ts)
        self._presence_flap_history[entity_id] = [
            t for t in history if now_ts - t <= self._PRESENCE_FLAP_WINDOW
        ]
        flap_count = len(self._presence_flap_history[entity_id])
        if flap_count < self._PRESENCE_FLAP_THRESHOLD:
            return

        suppress_until = now_ts + self._PRESENCE_FLAP_SUPPRESS_SECS
        self._presence_flap_suppressed[entity_id] = suppress_until
        self._presence_flap_history[entity_id] = []
        self._presence_on_start.pop(entity_id, None)
        old_off = self._presence_off_timers.pop(entity_id, None)
        if old_off:
            try:
                old_off()
            except Exception as exc:
                _LOGGER.debug("[Listeners] 取消离开确认计时器失败 (flap): %s", exc)

        self._sys_log(
            "WARN",
            f"[存在去抖] {entity_id} 在 {self._PRESENCE_FLAP_WINDOW}s 内状态反转 {flap_count} 次，"
            f"判定抖动风暴，抑制 {self._PRESENCE_FLAP_SUPPRESS_SECS}s",
        )

    def _build_presence_snapshot_for_entity(
        self,
        entity_id: str,
        *,
        blocked_actions: list[str] | None = None,
        reasons: list[str] | None = None,
    ) -> dict[str, Any]:
        """统一构建 Presence Snapshot（优先融合域，其次 PresenceInference）。"""
        room = (self.device_info.get(entity_id, {}) or {}).get("room", "").strip()
        snapshot_fn = getattr(self, "get_presence_snapshot", None)
        if callable(snapshot_fn) and room:
            try:
                root_snapshot = snapshot_fn()
            except Exception as exc:
                _LOGGER.debug("[Listeners] get_presence_snapshot failed: %s", exc)
                root_snapshot = None
            rooms = root_snapshot.get("rooms") if isinstance(root_snapshot, dict) else None
            room_snapshot = rooms.get(room) if isinstance(rooms, dict) else None
            if isinstance(room_snapshot, dict):
                snap = dict(room_snapshot)
                if reasons:
                    snap["reasons"] = list(snap.get("reasons", [])) + list(reasons)
                if blocked_actions:
                    snap["blocked_actions"] = list(snap.get("blocked_actions", [])) + list(blocked_actions)
                localized_spaces = list(snap.get("localized_spaces") or [])
                if room not in localized_spaces:
                    localized_spaces.insert(0, room)
                snap["localized_spaces"] = localized_spaces
                return snap

        _fusion = getattr(self, "_fusion_registry", None)
        if _fusion is not None:
            snap = _fusion.build_presence_snapshot_for_entity(
                entity_id,
                blocked_actions=blocked_actions,
                reasons=reasons,
            )
            if snap is not None:
                return snap

        room = (self.device_info.get(entity_id, {}) or {}).get("room", "").strip()
        if room and hasattr(self, "_presence_inference") and self._presence_inference is not None:
            snap = self._presence_inference.infer_room_presence_snapshot(room)
            if reasons:
                snap["reasons"] = list(snap.get("reasons", [])) + list(reasons)
            if blocked_actions:
                snap["blocked_actions"] = list(snap.get("blocked_actions", [])) + list(blocked_actions)
            return snap

        fallback_reasons = list(reasons or [])
        fallback_reasons.append("no_room_or_inference")
        return {
            "state": "unknown",
            "confidence": 0.0,
            "reasons": fallback_reasons,
            "enter_qualified": False,
            "leave_qualified": False,
            "localized_spaces": [room] if room else [],
            "blocked_actions": list(blocked_actions or []),
        }

    # ── 触发调度与合并 ────────────────────────────────────────────────────────

    @callback
    def _schedule_inference(self, entity_id: str, trigger: str, new_state: str = "", one_off_prompt: str = "") -> None:

        # ── 门控检查（所有路径统一入口，包括 Frigate MQTT / 巡检 / HA 状态变化）──────
        # 1. AI 是否已暂停
        if not self._is_enabled():
            self._sys_log("WARN", f"触发被拒: AI 已暂停 | {entity_id}")
            return
        # 2. 启动冷却（HA 重启后等待设备状态稳定）
        _startup_elapsed = time.time() - self._startup_time
        if _startup_elapsed < self._startup_grace:
            _remaining = int(self._startup_grace - _startup_elapsed)
            self._sys_log("INFO", f"启动冷却中({_remaining}s 后就绪)，忽略触发: {entity_id}")
            return
        # 3. 静默学习模式（只记录不推理）
        if self._learning_mode:
            # 仅记录真实 HA 实体（entity_id 必须含"."，排除"展厅系统"等虚拟调度实体）
            _is_real_entity = "." in entity_id and not entity_id.startswith(".")
            if _is_real_entity:
                self._sys_log("INFO", f"[静默学习] {entity_id} {new_state}，仅记录")
                self.hass.async_add_executor_job(
                    self._record_event, "Learning", trigger, entity_id, new_state
                )
            else:
                self._sys_log("INFO", f"[静默学习] {entity_id} {new_state}，仅记录（不推理）")
            return
        # ──────────────────────────────────────────────────────────────────────────

        now = time.time()
        cooldown = self._effective_cooldown()
        elapsed = now - self._last_inference.get(entity_id, 0)
        if elapsed < cooldown:
            self._sys_log("INFO", f"[冷却] {entity_id} 冷却中({int(cooldown - elapsed)}s 后可再触发)")
            return
        self._last_inference[entity_id] = now
        with self._pending_triggers_lock:
            if len(self._pending_triggers) >= 50:
                _dropped = [t.get("entity_id", "?") for t in self._pending_triggers[:25]]
                self._sys_log("WARN", f"[事件溢出] 触发队列满，丢弃 25 个事件: {_dropped}")
                self._pending_triggers = self._pending_triggers[-25:]
            self._pending_triggers.append({"text": trigger, "entity_id": entity_id, "one_off": one_off_prompt})

        domain = entity_id.split(".")[0]
        if domain in ("light", "switch", "fan", "cover", "climate", "media_player"):
            with self._pending_triggers_lock:
                self._pending_trigger_controllable[entity_id] = new_state
        is_urgent = domain in ("binary_sensor", "device_tracker", "person")
        window = self._URGENT_MERGE_WINDOW if is_urgent else self._NORMAL_MERGE_WINDOW

        if self._merge_timer_unsub is not None and is_urgent:
            try:
                self._merge_timer_unsub()
            except Exception as _e:
                _LOGGER.debug("[调度] 取消合并定时器异常（忽略）: %s", _e)
            self._merge_timer_unsub = None

        self._sys_log("INFO", f"[调度] 推理已加入队列，{window}s 后执行{'（紧急）' if is_urgent else ''}")
        if self._merge_timer_unsub is None:
            self._merge_timer_unsub = async_call_later(self.hass, window, self._flush_triggers)

    @callback
    def _flush_triggers(self, _: datetime) -> None:
        self._merge_timer_unsub = None
        with self._pending_triggers_lock:
            if not self._pending_triggers:
                return

        # 每次 flush 时顺手清理 _user_manual_actions 过期键（超过 _USER_MANUAL_WINDOW）
        # 防止字典无限增长（随历史手动操作实体数线性增大）
        with self._user_manual_actions_lock:
            if self._user_manual_actions:
                _now_ts = time.time()
                _expired = [
                    eid for eid, v in self._user_manual_actions.items()
                    if (_now_ts - v.get("time", 0)) > self._USER_MANUAL_WINDOW
                ]
                for eid in _expired:
                    del self._user_manual_actions[eid]

        with self._pending_triggers_lock:
            triggers = self._pending_triggers.copy()
            self._pending_triggers.clear()
            controllable_snapshot = self._pending_trigger_controllable.copy()
            self._pending_trigger_controllable.clear()

        # 状态校验：合并窗口内检查可控设备当前状态是否与上报一致
        # 同时维护闪断累计计数，频繁闪断的设备进入抑制期，暂停触发推理
        # （_glitch_history / _glitch_suppressed 已在 coordinator.__init__ 中初始化）

        _now_glitch = time.time()
        glitched: list[str] = []
        for eid, reported in controllable_snapshot.items():
            if not reported:
                continue
            # 检查该设备是否处于闪断抑制期，若是则直接视为闪断跳过
            suppress_until = self._glitch_suppressed.get(eid, 0)
            if _now_glitch < suppress_until:
                glitched.append(eid)
                remain = int(suppress_until - _now_glitch)
                self._sys_log("INFO", f"[状态校验] {eid} 处于闪断抑制期，跳过触发（剩余{remain}s）")
                continue
            current = self.hass.states.get(eid)
            if current and current.state != reported:
                glitched.append(eid)
                name = self.get_device_name(eid)
                self._sys_log("WARN", f"[状态校验] {name}({eid}) 上报 {reported} 但刷新后为 {current.state}，判定为通信闪断，移除该触发")
                with self._user_overrides_lock:
                    self._user_overrides.pop(eid, None)
                # 累计闪断记录，清理超出时间窗口的旧记录
                history = self._glitch_history.setdefault(eid, [])
                history.append(_now_glitch)
                self._glitch_history[eid] = [t for t in history if _now_glitch - t < self._GLITCH_WINDOW]
                # 若在时间窗口内闪断次数达到阈值，进入抑制期
                if len(self._glitch_history[eid]) >= self._GLITCH_THRESHOLD:
                    self._glitch_suppressed[eid] = _now_glitch + self._GLITCH_SUPPRESS_SECS
                    self._sys_log("WARN",
                        f"[状态校验] {name}({eid}) {self._GLITCH_WINDOW}s内闪断{len(self._glitch_history[eid])}次，"
                        f"进入{self._GLITCH_SUPPRESS_SECS}s抑制期，暂停触发推理"
                    )
                    self._glitch_history[eid] = []  # 重置计数，等待抑制期结束

        if glitched:
            triggers = [t for t in triggers if t["entity_id"] not in glitched]
            for eid in glitched:
                controllable_snapshot.pop(eid, None)

        if not triggers:
            self._sys_log("INFO", "[状态校验] 所有触发均为通信闪断，取消本次推理")
            return

        self._batch_trigger_controllable = controllable_snapshot
        if self._batch_trigger_controllable:
            self._sys_log("INFO", f"[自触发保护] 本批次含可控设备触发: {', '.join(self._batch_trigger_controllable)}，AI 不可反向操作这些设备")
        
        # 提取一客制化 Prompt（主要用于展示模式的一次性指令）
        one_off_prompts = [t.get("one_off") for t in triggers if t.get("one_off")]
        final_one_off = one_off_prompts[0] if one_off_prompts else ""
        
        texts = [t["text"] for t in triggers]
        if len(texts) == 1:
            merged = texts[0]
        else:
            merged = self._compact_merged_trigger(texts)
        self._sys_log("INFO", f"[合并] 合并 {len(triggers)} 个触发，启动推理: {merged[:80]}")
        try:
            self.hass.async_create_task(self._run_inference(merged, one_off_prompt=final_one_off))
        except Exception as exc:
            self._sys_log("ERROR", f"[合并] 创建推理任务失败: {exc}")

    # ── 触发文本格式化 ────────────────────────────────────────────────────────

    _DOMAIN_ZH_MAP = {
        "light": "灯光", "switch": "开关", "climate": "空调",
        "cover": "窗帘", "fan": "风扇", "sensor": "数值传感器",
        "binary_sensor": "传感器", "media_player": "播放器",
        "device_tracker": "位置", "person": "人员",
    }

    # 仅存在感/二进制传感器使用"有人/无人"语义翻译
    _PRESENCE_STATE_ZH = {"on": "有人", "off": "无人"}
    # 可控设备（灯/开关/窗帘等）使用"开/关"
    _CTRL_STATE_ZH = {
        "on": "开", "off": "关",
        "open": "已开", "closed": "已关",
        "heat": "制热", "cool": "制冷", "dry": "除湿",
        "fan_only": "送风", "auto": "自动",
        "home": "回家", "not_home": "离家",
        "unavailable": "离线", "unknown": "未知",
    }
    # 存在感传感器关键词（与 _PRESENCE_KW 保持一致）
    _PRESENCE_DOMAINS = frozenset({"binary_sensor"})

    def _fmt_state(self, domain: str, entity_id: str, state: str) -> str:
        """根据设备类型返回语义准确的状态文字。"""
        if domain in self._PRESENCE_DOMAINS:
            eid_lower = entity_id.lower()
            is_presence = any(kw in eid_lower or kw in (
                self.device_info.get(entity_id, {}).get("name", "").lower()
            ) for kw in self._PRESENCE_KW)
            if is_presence:
                return self._PRESENCE_STATE_ZH.get(state, state)
        return self._CTRL_STATE_ZH.get(state, state)

    def _fmt_trigger(self, source: str, domain: str, name: str,
                     entity_id: str, old_s: str, new_s: str) -> str:
        """生成简洁的触发文本，供 AI Prompt 和日志使用。
        
        保留 entity_id 让 AI 可精确识别设备，状态按设备类型语义化翻译。
        """
        dz = self._DOMAIN_ZH_MAP.get(domain, domain)
        oz = self._fmt_state(domain, entity_id, old_s)
        nz = self._fmt_state(domain, entity_id, new_s)
        src_short = {"物理/自动": "物理", "自动化/脚本": "脚本", "用户界面": "用户"}.get(source, source)
        return f"[{src_short}] {dz}「{name}」{oz}→{nz}（{entity_id}）"

    # ── 触发合并压缩 ──────────────────────────────────────────────────────────

    def _compact_merged_trigger(self, texts: list[str]) -> str:
        """将多条触发消息压缩为简洁的合并描述，节省字符，同时保留 AI 决策所需信息。

        优化策略：
        1. 相同变化方向（off→on / on→off）且同域的设备归为一组，仅列设备名
        2. 不同类型/方向的设备各自独立一行
        3. 整体长度控制在 200 字以内
        """
        import re as _re
        # 兼容新格式: [来源] 域「名称」旧→新（entity_id）
        # 兼容旧格式: [来源] domain [名称(entity_id)] changed: old -> new
        _pat_new = _re.compile(r"\[(.+?)\]\s+\S+「(.+?)」(\S+)→(\S+)（(\S+?)）")
        _pat_old = _re.compile(r"\[(.+?)\]\s+\S+\s+\[(.+?)\((.+?)\)\]\s+changed:\s+(\S+)\s+->\s+(\S+)")
        parsed = []
        unparsed = []
        for t in texts:
            m = _pat_new.search(t)
            if m:
                src, name, old_s, new_s, eid = m.groups()
                domain = eid.split(".")[0]
                parsed.append({"src": src, "name": name, "eid": eid,
                                "domain": domain, "old": old_s, "new": new_s})
                continue
            m = _pat_old.search(t)
            if m:
                src, name, eid, old_s, new_s = m.groups()
                domain = eid.split(".")[0]
                parsed.append({"src": src, "name": name, "eid": eid,
                                "domain": domain, "old": old_s, "new": new_s})
            else:
                unparsed.append(t)

        # 按 (src, domain, old→new) 分组，值存 (name, eid) 以便状态翻译时参考 eid
        from collections import defaultdict
        groups: dict = defaultdict(list)
        for p in parsed:
            key = (p["src"], p["domain"], p["old"], p["new"])
            groups[key].append((p["name"], p["eid"]))

        lines = []
        for (src, domain, old_s, new_s), items in groups.items():
            # items 现在是 (name, eid) 的列表
            dz = self._DOMAIN_ZH_MAP.get(domain, domain)
            # 用第一个 eid 判断状态翻译策略（同组设备类型相同）
            rep_eid = items[0][1] if items and isinstance(items[0], tuple) else ""
            oz = self._fmt_state(domain, rep_eid, old_s)
            nz = self._fmt_state(domain, rep_eid, new_s)
            names = [it[0] if isinstance(it, tuple) else it for it in items]
            if len(names) == 1:
                lines.append(f"[{src}] {dz}「{names[0]}」{oz}→{nz}")
            else:
                # 多个设备同向变化：使用第一个设备名称带「」标记以保留房间信息，
                # 确保 inference.py 中 r"「\[(.*?)\]" 能正确提取 trigger_room，
                # 避免区域隔离和 per-room lock 因 trigger_room 为空而失效。
                first_name = names[0]
                rest_names = "、".join(names[1:3])
                suffix = f"等{len(names)}台" if len(names) > 2 else (f"、{rest_names}" if rest_names else "")
                lines.append(f"[{src}] {dz}「{first_name}」{suffix} {oz}→{nz}")

        lines.extend(unparsed)
        result = "同时发生：\n" + "\n".join(f"  · {l}" for l in lines)
        # 超 220 字则截取并提示
        if len(result) > 220:
            result = result[:218] + "…"
        return result

    # ── 快速通道 ──────────────────────────────────────────────────────────────

    def _get_time_brightness(self, hour: int) -> int:
        """Return appropriate brightness for the given hour, checking user rules first."""
        for content, locked in self._rules:
            m = self._TIME_RE.search(content)
            if not m:
                continue
            h1 = int(m.group(1))
            op = m.group(2) or ""
            h2 = int(m.group(3)) if m.group(3) else None
            applicable = False
            if op in ("以后", "之后", "后"):
                applicable = hour >= h1
            elif op in ("以前", "之前", "前"):
                applicable = hour < h1
            elif op in ("到", "至", "-") and h2 is not None:
                applicable = (h1 <= hour <= h2) if h1 <= h2 else (hour >= h1 or hour <= h2)
            if not applicable:
                continue
            bm = re.search(r'亮度[为到]?\s*(\d{1,3})\s*%?', content)
            if bm:
                return int(bm.group(1))
        for start, end, brightness in self._BRIGHTNESS_TABLE:
            if start <= hour < end:
                return brightness
        return 80

    def _find_room_lights(self, sensor_eid: str) -> list[str]:
        """Find light entities in the same room as the given sensor."""
        sensor_info = self.device_info.get(sensor_eid, {})
        sensor_room = sensor_info.get("room", "")
        if not sensor_room:
            sensor_room = self._get_entity_area(sensor_eid)
        lights = []
        for eid, info in self.device_info.items():
            if not eid.startswith("light."):
                continue
            dev_room = info.get("room", "")
            if not dev_room:
                dev_room = self._get_entity_area(eid)
            if sensor_room and dev_room and sensor_room == dev_room:
                lights.append(eid)
        return lights

    # ── 状态变化处理器 ────────────────────────────────────────────────────────

    def _build_addon_fast_path_snapshot(self, entity_id: str) -> dict[str, Any]:
        """Build the plain snapshot consumed by add-on Core fast-path decisions."""
        device_info = dict(getattr(self, "device_info", {}) or {})
        states: dict[str, str] = {}
        for eid in set(device_info.keys()) | {str(entity_id or "")}:
            if not eid:
                continue
            state = self.hass.states.get(eid)
            if state is not None:
                states[eid] = str(state.state or "")

        topology: dict[str, list[str]] = {}
        for room, neighbors in (getattr(self, "_room_topology_cache", {}) or {}).items():
            if isinstance(neighbors, (set, list, tuple)):
                topology[str(room)] = sorted({str(item) for item in neighbors if str(item or "").strip()})

        snapshot: dict[str, Any] = {
            "device_info": device_info,
            "states": states,
            "ai_scenes": list(getattr(self, "_ai_scenes_cache", []) or []),
            "behavior_patterns": list(getattr(self, "_behavior_patterns_cache", []) or []),
            "room_topology": topology,
            "mode": str(getattr(self, "_mode", "") or ""),
        }

        for key, getter_name in (
            ("space_snapshot", "get_space_runtime_snapshot"),
            ("presence_snapshot", "get_presence_snapshot"),
            ("device_capability_snapshot", "get_device_capability_snapshot"),
        ):
            getter = getattr(self, getter_name, None)
            if callable(getter):
                try:
                    value = getter()
                except Exception as exc:
                    _LOGGER.debug("[Listeners] %s failed for add-on snapshot: %s", getter_name, exc)
                    value = None
                if isinstance(value, dict):
                    snapshot[key] = value
        return snapshot

    async def _execute_fast_path_decision_result(
        self,
        result: dict[str, Any],
        *,
        entity_id: str,
        source_label: str,
    ) -> None:
        from .intent_verifier import CMD_SOURCE_SENSOR

        actions = result.get("actions", [])
        scene = result.get("scene", source_label)
        confidence = result.get("confidence", 90)
        room = result.get("trigger_room") or self.device_info.get(entity_id, {}).get("room", "")
        try:
            defer_seconds = int(result.get("defer_seconds", 0) or 0)
        except (TypeError, ValueError):
            defer_seconds = 0

        if defer_seconds > 0:
            await asyncio.sleep(defer_seconds)
            recheck = getattr(getattr(self, "_decision_pipeline", None), "_try_departure_cache", None)
            if callable(recheck) and recheck(entity_id, "off") is None:
                self._sys_log(
                    "INFO",
                    f"[{source_label}] delayed execution cancelled after {defer_seconds}s | room={room}",
                )
                return

        await self._execute_actions(
            actions if isinstance(actions, list) else [],
            trigger_summary=f"{source_label}[{scene}]",
            scene_desc=str(scene),
            confidence=confidence,
            trigger_room=room,
            is_global_cmd=False,
            cmd_source=CMD_SOURCE_SENSOR,
        )

    def _addon_fast_path_snapshot_diagnostics(self, snapshot: dict[str, Any], entity_id: str) -> dict[str, Any]:
        device_info = snapshot.get("device_info") if isinstance(snapshot.get("device_info"), dict) else {}
        topology = snapshot.get("room_topology") if isinstance(snapshot.get("room_topology"), dict) else {}
        capabilities = snapshot.get("device_capability_snapshot")
        capability_rows = 0
        if isinstance(capabilities, dict):
            rows = capabilities.get("devices", capabilities.get("items", capabilities.get("data", capabilities)))
            capability_rows = len(rows) if isinstance(rows, (dict, list, tuple, set)) else 0
        elif isinstance(capabilities, (list, tuple, set)):
            capability_rows = len(capabilities)

        active_space = ""
        for key in ("active_space_id", "space_id", "trigger_room", "room", "area"):
            active_space = str(snapshot.get(key) or "").strip()
            if active_space:
                break
        if not active_space:
            info = device_info.get(entity_id)
            if isinstance(info, dict):
                active_space = str(info.get("space_id") or info.get("room") or info.get("area") or "").strip()

        return {
            "active_space": active_space,
            "capability_rows": capability_rows,
            "device_info_count": len(device_info),
            "topology_count": len(topology),
        }

    def _emit_addon_fast_path_event(self, payload: dict[str, Any]) -> None:
        try:
            self.hass.bus.async_fire("smart_agent_decision_bubble", payload)
        except Exception as exc:
            _LOGGER.debug("[Listeners] smart_agent_decision_bubble emit failed: %s", exc)

    def _emit_listener_event(
        self,
        *,
        listener_action: str,
        entity_id: str,
        old_state: str = "",
        new_state: str = "",
        filter_reason: str = "",
        source_type: str = "",
        **extra: Any,
    ) -> None:
        try:
            now_ts = time.time()
            startup_elapsed = now_ts - float(getattr(self, "_startup_time", now_ts) or now_ts)
            startup_grace = int(getattr(self, "_startup_grace", 0) or 0)
            startup_remaining = max(0, int(startup_grace - startup_elapsed))
            payload: dict[str, Any] = {
                "listener_action": str(listener_action or "unknown"),
                "entity_id": str(entity_id or ""),
                "old_state": str(old_state or ""),
                "new_state": str(new_state or ""),
                "filter_reason": str(filter_reason or ""),
                "source_type": str(source_type or ""),
                "ai_enabled": bool(self._is_enabled()),
                "sensors_muted": bool(getattr(self, "_sensors_muted", False)),
                "startup_remaining": startup_remaining,
                "startup_cooldown": startup_remaining > 0,
                "mode": str(getattr(self, "_mode", "") or ""),
            }
            payload.update({key: value for key, value in extra.items() if value is not None})
            self._last_listener_event = payload
            if filter_reason:
                self._last_listener_filter_reason = str(filter_reason)
            self.hass.bus.async_fire("smart_agent_listener_event", payload)
        except Exception as exc:
            _LOGGER.debug("[Listeners] smart_agent_listener_event emit failed: %s", exc)

    async def _run_addon_fast_path_fail_closed(
        self,
        entity_id: str,
        new_state: str,
        old_state: str,
    ) -> None:
        should_fail_closed = True
        addon_client = getattr(self, "_addon_client", None)
        snapshot = self._build_addon_fast_path_snapshot(entity_id)
        snapshot_diag = self._addon_fast_path_snapshot_diagnostics(snapshot, entity_id)
        self._sys_log(
            "INFO",
            "[Add-on FastPath] request "
            f"entity={entity_id} old={old_state} new={new_state} "
            f"active_space={snapshot_diag.get('active_space') or '-'} "
            f"capability_rows={snapshot_diag.get('capability_rows', 0)} "
            f"device_info_count={snapshot_diag.get('device_info_count', 0)} "
            f"topology_count={snapshot_diag.get('topology_count', 0)}",
        )
        if addon_client is not None:
            try:
                response = await addon_client.run_decision_fast_path(
                    entity_id=entity_id,
                    new_state=new_state,
                    old_state=old_state,
                    snapshot=snapshot,
                )
            except Exception as exc:
                response = None
                _LOGGER.debug("[Listeners] add-on fast-path decision failed: %s", exc)
                self._sys_log(
                    "ERROR",
                    f"[Add-on FastPath] addon_unreachable fail-closed | entity={entity_id} "
                    f"reason=exception exception_type={type(exc).__name__}",
                )
                self._emit_addon_fast_path_event(
                    {
                        "source": "addon_fast_path",
                        "entity_id": entity_id,
                        "old_state": old_state,
                        "new_state": new_state,
                        "status": 0,
                        "matched": False,
                        "path_taken": "none",
                        "reason": "exception",
                        "exception_type": type(exc).__name__,
                        "fail_closed": True,
                        "snapshot": snapshot_diag,
                    }
                )
                return
            else:
                if isinstance(response, dict):
                    status = int(response.get("__status") or 0)
                    result = response.get("result")
                    matched = response.get("matched") is True
                    details = response.get("details") if isinstance(response.get("details"), dict) else {}
                    path_taken = str(response.get("path_taken") or details.get("path_taken") or "none")
                    reason = str(response.get("reason") or details.get("reason") or response.get("error") or "")
                    scene = ""
                    confidence = None
                    action_count = 0
                    actions: list[Any] = []
                    transaction_id = ""
                    if isinstance(result, dict):
                        scene = str(result.get("scene") or result.get("source") or "")
                        confidence = result.get("confidence")
                        raw_actions = result.get("actions")
                        if isinstance(raw_actions, list):
                            actions = raw_actions
                            action_count = len(raw_actions)
                        elif result.get("action"):
                            action_count = 1
                        transaction_id = str(result.get("transaction_id") or result.get("txn_id") or "")
                    self._sys_log(
                        "INFO",
                        "[Add-on FastPath] result "
                        f"status={status} matched={matched} path_taken={path_taken} "
                        f"reason={reason or '-'} scene={scene or '-'} "
                        f"confidence={confidence if confidence is not None else '-'} "
                        f"action_count={action_count} entity={entity_id}",
                    )
                    self._emit_addon_fast_path_event(
                        {
                            "source": "addon_fast_path",
                            "entity_id": entity_id,
                            "old_state": old_state,
                            "new_state": new_state,
                            "status": status,
                            "matched": matched,
                            "path_taken": path_taken,
                            "reason": reason,
                            "scene": scene,
                            "confidence": confidence,
                            "action_count": action_count,
                            "actions": actions,
                            "transaction_id": transaction_id,
                            "executed": matched,
                            "fail_closed": not (200 <= status < 300),
                            "snapshot": snapshot_diag,
                        }
                    )
                    if 200 <= status < 300 and matched and isinstance(result, dict):
                        self._sys_log("INFO", f"[Add-on FastPath] 命中规则: {result.get('scene', 'FastPath')}")
                        await self._execute_fast_path_decision_result(
                            result,
                            entity_id=entity_id,
                            source_label="AddonFastPath",
                        )
                        return
                    if 200 <= status < 300:
                        should_fail_closed = False
                        self._sys_log(
                            "INFO",
                            f"[Add-on FastPath] not matched; HA local decision skipped | status={status} matched={response.get('matched')}",
                        )
                    elif status == 409:
                        self._sys_log(
                            "WARN",
                            f"[Add-on FastPath] addon_fast_path_input_incomplete fail-closed | "
                            f"status={status} reason={reason or 'input_incomplete'} entity={entity_id}",
                        )
                        return
                    elif status > 0:
                        self._sys_log(
                            "INFO",
                            f"[Add-on FastPath] addon_unreachable fail-closed | "
                            f"status={status} matched={response.get('matched')} reason={reason or '-'}",
                        )
                        return

        if should_fail_closed:
            self._sys_log(
                "ERROR",
                f"[Add-on FastPath] addon_unreachable fail-closed | entity={entity_id} reason=unreachable",
            )
            self._emit_addon_fast_path_event(
                {
                    "source": "addon_fast_path",
                    "entity_id": entity_id,
                    "old_state": old_state,
                    "new_state": new_state,
                    "status": 0,
                    "matched": False,
                    "path_taken": "none",
                    "reason": "unreachable",
                    "fail_closed": True,
                    "snapshot": snapshot_diag,
                }
            )
        return

    def _make_state_handler(self):
        """Build the state-change callback."""
        @callback
        def _state_changed(ev) -> None:
            data = ev.data
            entity_id = data.get("entity_id")
            if not entity_id:
                return
            new = data.get("new_state")
            old = data.get("old_state")
            new_s = new.state if new else ""
            old_s = old.state if old else ""

            source_type = "物理/自动"
            if new and new.context:
                if new.context.user_id:
                    source_type = "用户界面"
                elif new.context.parent_id:
                    source_type = "自动化/脚本"

            self._sys_log("INFO", f"[事件] {entity_id}: {old_s} → {new_s} (来源: {source_type})")
            self._emit_listener_event(
                listener_action="received",
                entity_id=entity_id,
                old_state=old_s,
                new_state=new_s,
                source_type=source_type,
            )
            domain = entity_id.split(".")[0]

            # ── 传感器静默 ──
            if self._sensors_muted and domain in ("binary_sensor", "sensor"):
                self._sys_log("INFO", f"[传感器静默] {entity_id} {old_s}→{new_s}，静默中跳过")
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason="sensors_muted",
                    source_type=source_type,
                )
                return

            if domain == "sensor" and old_s and new_s:
                try:
                    delta = abs(float(new_s) - float(old_s))
                    eid_lower = entity_id.lower()
                    # Frigate person_count：启用 Frigate 时降低触发阈值到 1（0→1 是关键事件）
                    frigate_on = getattr(self, "_frigate_enabled", False)
                    is_person_count = frigate_on and any(kw in eid_lower for kw in self._PERSON_COUNT_KW)
                    threshold = 1 if is_person_count else 5
                    if delta < threshold:
                        self._sys_log("INFO", f"[过滤] 传感器变化 {delta:.1f} < {threshold}，跳过: {entity_id}")
                        self._emit_listener_event(
                            listener_action="filtered",
                            entity_id=entity_id,
                            old_state=old_s,
                            new_state=new_s,
                            filter_reason="numeric_deadband",
                            source_type=source_type,
                            delta=delta,
                            threshold=threshold,
                        )
                        return
                except (ValueError, TypeError):
                    pass

            # P0修复：AI 主开关检查必须先于场景快路和 FastBrain，
            # 否则关闭 AI 仍会执行设备控制动作。
            if not self._is_enabled():
                self._sys_log("INFO", f"[过滤] AI 已暂停，跳过场景快路/FastBrain: {entity_id}")
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason="ai_disabled",
                    source_type=source_type,
                )
                return
            # 启动冷却保护：系统初始化期间也不执行快路
            _startup_elapsed = time.time() - self._startup_time
            if _startup_elapsed < self._startup_grace:
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason="startup_cooldown",
                    source_type=source_type,
                    startup_remaining=max(0, int(self._startup_grace - _startup_elapsed)),
                )
                return

            # ── Step 0 + FastBrain: add-on 优先路径（B1 迁移：有 add-on 时直接调用，不先跑本地）──
            from .intent_verifier import CMD_SOURCE_SENSOR
            _pipeline = self._decision_pipeline
            self._emit_listener_event(
                listener_action="fast_path_scheduled",
                entity_id=entity_id,
                old_state=old_s,
                new_state=new_s,
                source_type=source_type,
            )
            self.hass.async_create_task(
                self._run_addon_fast_path_fail_closed(
                    entity_id,
                    new_s,
                    old_s,
                )
            )
            return
            # Legacy local execution below is intentionally unreachable after Phase B fail-closed.

            # ── Step 0: HA AI 场景优先路径（预设场景优先于 FastBrain 和 LLM）────────
            _scene_res = _pipeline.run_ha_scene_path(entity_id, new_s)
            if _scene_res:
                _s_actions = _scene_res.get("actions", [])
                _s_scene   = _scene_res.get("scene", "AI场景")
                _s_conf    = _scene_res.get("confidence", 85)
                _s_room    = _scene_res.get("trigger_room", "")
                self._sys_log("INFO", f"[Scene Path] 命中 AI 场景: {_s_scene}，直接执行（跳过 FastBrain/LLM）")
                self.hass.async_create_task(
                    self._execute_actions(
                        _s_actions,
                        trigger_summary=f"ScenePath[{_s_scene}]",
                        scene_desc=_s_scene,
                        confidence=_s_conf,
                        trigger_room=_s_room,
                        is_global_cmd=False,
                        cmd_source=CMD_SOURCE_SENSOR,
                    )
                )
                return
            # ── Step 0 结束 ─────────────────────────────────────────────────

            # ── 极速快脑 (FastBrain) 同步拦截 (Phase 9.6: DecisionPipeline 统一管道) ──
            # DecisionPipeline 内部完整执行：特征编码 → FastBrain 决策 → 双阶段意图验证
            # 展厅模式和静默学习模式在 DecisionPipeline.run_fast_path() 内部自动跳过
            _fb_res = _pipeline.run_fast_path(entity_id, new_s, old_s)
            if _fb_res:
                _actions = _fb_res.get("actions", [])
                _scene = _fb_res.get("scene", "FastBrain")
                _conf = _fb_res.get("confidence", 90)
                _room = _fb_res.get("trigger_room") or self.device_info.get(entity_id, {}).get("room", "")
                _defer_sec = _fb_res.get("defer_seconds", 0)

                if _defer_sec > 0:
                    # DepartureCache 离开确认延迟：等待 defer_seconds 后重验证，
                    # 若用户在等待期间返回（任意传感器变 on），自动取消。
                    _depart_eid = entity_id
                    _depart_pipeline = _pipeline

                    async def _deferred_departure(
                        _eid=_depart_eid,
                        _acts=_actions,
                        _sc=_scene,
                        _cf=_conf,
                        _rm=_room,
                        _ds=_defer_sec,
                        _pl=_depart_pipeline,
                    ) -> None:
                        await asyncio.sleep(_ds)
                        # 重验证：若用户已返回 _try_departure_cache 会因传感器变 on 返回 None
                        _recheck = _pl._try_departure_cache(_eid, "off")
                        if _recheck is None:
                            self._sys_log(
                                "INFO",
                                f"[DepartureCache] ⚡ 延迟 {_ds}s 后重验证未通过"
                                f"（用户已返回或状态变更），取消 room={_rm} 的离开动作",
                            )
                            return
                        self._sys_log(
                            "INFO",
                            f"[DepartureCache] ✅ 延迟 {_ds}s 确认无人，执行 {len(_acts)} 个动作"
                            f" room={_rm}",
                        )
                        await self._execute_actions(
                            _acts,
                            trigger_summary=f"DepartureCache[delayed_{_ds}s]",
                            scene_desc=_sc,
                            confidence=_cf,
                            trigger_room=_rm,
                            is_global_cmd=False,
                            cmd_source=CMD_SOURCE_SENSOR,
                        )

                    self.hass.async_create_task(_deferred_departure())
                else:
                    self._sys_log("INFO", f"[极速快脑+验证] 命中规则: {_scene}，立即执行 {len(_actions)} 个动作")
                    self.hass.async_create_task(
                        self._execute_actions(
                            _actions,
                            trigger_summary=f"FastBrain[{_scene}]",
                            scene_desc=_scene,
                            confidence=_conf,
                            trigger_room=_room,
                            is_global_cmd=False,
                            cmd_source=CMD_SOURCE_SENSOR,
                        )
                    )
                # 极速快脑 + 意图验证通过后，放弃抛给慢脑
                return
            # ── 极速快脑 (FastBrain) 拦截结束 ──────────────────────────

            # ── 存在传感器高频去抖 ──────────────────────────────────────────
            if domain == "binary_sensor":
                check_str = (self.device_info.get(entity_id, {}).get("name", "") + entity_id).lower()
                if any(kw in check_str for kw in self._PRESENCE_KW):
                    if self._learning_mode:
                        name = self.get_device_name(entity_id)
                        trigger = self._fmt_trigger("物理", "binary_sensor", name, entity_id, old_s, new_s)
                        self._sys_log("INFO", f"[静默学习] {entity_id} {old_s}→{new_s}，仅记录")
                        self.hass.async_add_executor_job(
                            self._record_event, "Learning", trigger, entity_id, new_s
                        )
                        return
                    if new_s == "on":
                        _suppressed, _remain = self._is_presence_flap_suppressed(entity_id)
                        if _suppressed:
                            self._sys_log(
                                "INFO",
                                f"[存在去抖] {entity_id} 处于抖动抑制期，跳过有人触发（剩余{_remain}s）",
                            )
                            return
                        self._record_presence_flap(entity_id)
                        _suppressed_after, _remain_after = self._is_presence_flap_suppressed(entity_id)
                        if _suppressed_after:
                            self._sys_log(
                                "INFO",
                                f"[存在去抖] {entity_id} 抖动风暴触发抑制，跳过有人触发（剩余{_remain_after}s）",
                            )
                            return
                        cancel = self._presence_off_timers.pop(entity_id, None)
                        if cancel:
                            try:
                                cancel()
                                self._sys_log("INFO", f"[存在去抖] {entity_id} 重新检测到人，取消离开确认")
                            except Exception as exc:
                                _LOGGER.debug("[Listeners] 取消离开确认计时器失败: %s", exc)
                        self._presence_on_start[entity_id] = time.time()
                        last_on = self._presence_last_on.get(entity_id, 0)
                        since = time.time() - last_on
                        if since < self._PRESENCE_ON_COOLDOWN:
                            self._sys_log("INFO", f"[存在去抖] {entity_id} 持续有人抑制（距上次 {int(since)}s < {self._PRESENCE_ON_COOLDOWN}s）")
                            return
                        _eid_on = entity_id
                        _old_s_on = old_s
                        @callback
                        def _confirm_present(_now, eid=_eid_on, o=_old_s_on) -> None:
                            cur = self.hass.states.get(eid)
                            if not cur or cur.state != "on":
                                self._sys_log("INFO", f"[存在去抖] {eid} on 持续不足 {self._PRESENCE_ON_MIN_HOLD}s 即离开（闪烁），跳过触发")
                                self._presence_on_start.pop(eid, None)
                                return
                            _suppressed_now, _remain_now = self._is_presence_flap_suppressed(eid)
                            if _suppressed_now:
                                self._sys_log(
                                    "INFO",
                                    f"[存在去抖] {eid} 确认在场时仍处于抖动抑制期，取消有人触发（剩余{_remain_now}s）",
                                )
                                self._presence_on_start.pop(eid, None)
                                return
                            _presence_snap = self._build_presence_snapshot_for_entity(
                                eid,
                                reasons=["presence_on_confirm"],
                            )
                            if _presence_snap.get("state") == "unknown":
                                self._sys_log(
                                    "INFO",
                                    f"[PresenceSnapshot] {eid} 状态未知，跳过有人触发，避免误开灯"
                                    f" | snapshot={_presence_snap}",
                                )
                                self._presence_on_start.pop(eid, None)
                                return
                            if not _presence_snap.get("enter_qualified", False):
                                self._sys_log(
                                    "INFO",
                                    f"[PresenceSnapshot] {eid} enter 未通过，跳过有人触发"
                                    f" | snapshot={_presence_snap}",
                                )
                                self._presence_on_start.pop(eid, None)
                                return
                            self._presence_last_on[eid] = time.time()
                            self._presence_on_start.pop(eid, None)
                            name = self.get_device_name(eid)
                            trig = self._fmt_trigger("物理", "binary_sensor", name, eid, o, "on")
                            self._sys_log("INFO", f"[存在去抖] {eid} 持续有人 {self._PRESENCE_ON_MIN_HOLD}s，确认在场，触发推理")
                            try:
                                self._schedule_inference(eid, trig, new_state="on")
                            except Exception as exc:
                                self._sys_log("ERROR", f"[存在去抖] 调度推理失败: {exc}")

                            # Phase 7G 备用路径：存在传感器确认有人时主动拉取摄像头帧做行为分析。
                            # _confirm_present 是 @callback，不能直接 await；用 async_create_task 调度。
                            if (getattr(self, "_vision_enabled", False)
                                    and getattr(self, "_frigate_enabled", False)
                                    and hasattr(self, "_async_analyze_on_presence")):
                                self.hass.async_create_task(
                                    self._async_analyze_on_presence(eid)
                                )

                            # Phase 0: 5 分钟后快照灯光状态，写入 arrival_baseline
                            _arrival_room = self.device_info.get(eid, {}).get("room", "")
                            if _arrival_room and hasattr(self, "_record_arrival_snapshot"):
                                _snap_eid = eid

                                @callback
                                def _do_arrival_snapshot(_now2, _r=_arrival_room, _s=_snap_eid) -> None:
                                    _STARTUP_SNAPSHOT_GUARD = 120
                                    if time.time() - getattr(self, "_startup_time", 0) < _STARTUP_SNAPSHOT_GUARD:
                                        self._sys_log("INFO", "[ArrivalBaseline] 启动恢复窗口内，跳过到达快照")
                                        return
                                    # 确认传感器仍在 on（人还在）才采样，避免误记「离开后状态」
                                    _cur2 = self.hass.states.get(_s)
                                    if _cur2 and _cur2.state == "on":
                                        # 在事件循环中预先捕获灯光状态，再派发到 executor，
                                        # 避免 executor 线程直接访问 HA 状态机（线程安全）
                                        _light_states: dict[str, str | None] = {}
                                        for _lid, _linfo in self.device_info.items():
                                            if not _lid.startswith("light."):
                                                continue
                                            if _linfo.get("room") != _r:
                                                continue
                                            _ls = self.hass.states.get(_lid)
                                            _light_states[_lid] = _ls.state if _ls else None
                                        self.hass.async_add_executor_job(
                                            self._record_arrival_snapshot,
                                            _r, _s, _light_states,
                                        )
                                        self._sys_log(
                                            "INFO",
                                            f"[ArrivalBaseline] 到达快照: room={_r} sensor={_s}"
                                            f" lights={len(_light_states)}",
                                        )

                                async_call_later(self.hass, 300, _do_arrival_snapshot)

                        async_call_later(self.hass, self._PRESENCE_ON_MIN_HOLD, _confirm_present)
                        self._sys_log("INFO", f"[存在去抖] {entity_id} 检测到人，{self._PRESENCE_ON_MIN_HOLD}s 后确认仍在场则触发")
                        return

                    elif new_s == "off":
                        _suppressed, _remain = self._is_presence_flap_suppressed(entity_id)
                        if _suppressed:
                            self._sys_log(
                                "INFO",
                                f"[存在去抖] {entity_id} 处于抖动抑制期，跳过离开确认（剩余{_remain}s）",
                            )
                            return
                        self._record_presence_flap(entity_id)
                        _suppressed_after, _remain_after = self._is_presence_flap_suppressed(entity_id)
                        if _suppressed_after:
                            self._sys_log(
                                "INFO",
                                f"[存在去抖] {entity_id} 抖动风暴触发抑制，跳过离开确认（剩余{_remain_after}s）",
                            )
                            return
                        if old_s in ("unavailable", "unknown", None, ""):
                            self._sys_log("INFO", f"[存在去抖] {entity_id} 从 {old_s} 恢复为 off（重启噪声），跳过离开确认")
                            return
                        on_start = self._presence_on_start.pop(entity_id, 0)
                        if on_start and (time.time() - on_start) < self._PRESENCE_ON_MIN_HOLD:
                            self._sys_log("INFO", f"[存在去抖] {entity_id} on→off 仅 {time.time() - on_start:.1f}s（<{self._PRESENCE_ON_MIN_HOLD}s 闪烁），跳过离开确认")
                            return
                        old_cancel = self._presence_off_timers.pop(entity_id, None)
                        if old_cancel:
                            try:
                                old_cancel()
                            except Exception as exc:
                                _LOGGER.debug("[Listeners] 取消离开确认计时器失败 (off): %s", exc)
                        _eid = entity_id
                        _old_s = old_s
                        @callback
                        def _confirm_left(_now, eid=_eid, o=_old_s) -> None:
                            self._presence_off_timers.pop(eid, None)
                            cur = self.hass.states.get(eid)
                            if not cur or cur.state != "off":
                                self._sys_log("INFO", f"[存在去抖] {eid} 已重新检测到人，取消离开触发")
                                return
                            self._presence_last_on.pop(eid, None)
                            dev_name = self.get_device_name(eid)
                            trig = self._fmt_trigger("物理", "binary_sensor", dev_name, eid, o, "off")
                            
                            # Phase 10.1: PIR 传感器特殊处理
                            # PIR 无法检测静止存在，其 off 信号不可信（人可能还在但没动）。
                            # 策略：PIR off 不主动触发 AI 推理（关灯），仅更新 PresenceInference 置信度。
                            info = self.device_info.get(eid, {})
                            if info.get("sensor_type") == "pir":
                                self._sys_log("INFO", f"[存在去抖] {eid} (PIR) 持续无人，仅记录状态，不触发关灯推理")
                                return

                            _presence_snap = self._build_presence_snapshot_for_entity(
                                eid,
                                reasons=["presence_off_confirm"],
                            )
                            if not _presence_snap.get("leave_qualified", False):
                                self._sys_log(
                                    "INFO",
                                    f"[PresenceSnapshot] {eid} leave 未通过，抑制离开推理"
                                    f" | snapshot={_presence_snap}",
                                )
                                return

                            self._sys_log("INFO", f"[存在去抖] {eid} 持续无人 {self._PRESENCE_OFF_DELAY}s，确认离开，触发推理")
                            # 5A-2: presence-off 事件驱动解锁 —— 清除该房间所有用户保护锁
                            _dev_room = (self.device_info.get(eid) or {}).get("room", "")
                            if _dev_room and hasattr(self, "_user_overrides"):
                                _now_ts = time.time()
                                with self._user_overrides_lock:
                                    _cleared = [
                                        _k for _k, _v in list(self._user_overrides.items())
                                        if (self.device_info.get(_k) or {}).get("room") == _dev_room
                                        and _now_ts - _v.get("time", 0) > 60
                                    ]
                                    for _k in _cleared:
                                        self._user_overrides.pop(_k, None)
                                if _cleared:
                                    self._sys_log("INFO",
                                        f"[5A-2 柔性保护] 房间「{_dev_room}」已无人，"
                                        f"清除 {len(_cleared)} 个超过 60s 的用户保护锁: {_cleared}")
                            _dev_room_l = _dev_room.lower() if _dev_room else ""
                            _is_bedroom = any(k in _dev_room_l for k in ("卧室", "bedroom", "master", "guest"))
                            if _is_bedroom:
                                _leave_map = getattr(self, "_bedroom_last_leave_ts", None)
                                if not isinstance(_leave_map, dict):
                                    _leave_map = {}
                                    self._bedroom_last_leave_ts = _leave_map
                                _leave_map[_dev_room] = time.time()
                                self._sys_log("INFO", f"[SleepGuard] 记录卧室离开时间戳: room={_dev_room}")
                            try:
                                self._schedule_inference(eid, trig, new_state="off")
                            except Exception as exc:
                                self._sys_log("ERROR", f"[存在去抖] 调度推理失败: {exc}")
                        # Frigate 摄像头生成的 binary_sensor（如 *_person_occupancy / cam_* occupancy）
                        # 因视角死角或遮挡会短暂误报无人，使用更长的离开确认时间：
                        #   - 普通 mmWave/PIR 传感器：30s（原值）
                        #   - Frigate 摄像头传感器：90s（减少误触关灯）
                        #   - Frigate 摄像头 + 房间近期由展厅反射弧开灯：180s（顾客短暂转身/走动不关灯）
                        _eid_lower_off = entity_id.lower()
                        _is_cam_off = (
                            "person_occupancy" in _eid_lower_off
                            or ("cam" in _eid_lower_off and "occupancy" in _eid_lower_off)
                        )
                        if _is_cam_off:
                            _room_off = (self.device_info.get(entity_id) or {}).get("room", "")
                            _reflex_ts = getattr(self, "_reflex_room_open_time", {}).get(_room_off, 0)
                            _reflex_recent = (time.time() - _reflex_ts) < 300  # 反射弧5分钟内开过灯
                            _off_delay = 180 if _reflex_recent else 90
                        else:
                            _off_delay = self._PRESENCE_OFF_DELAY
                        handle = async_call_later(self.hass, _off_delay, _confirm_left)
                        self._presence_off_timers[entity_id] = handle
                        self._sys_log("INFO", f"[存在去抖] {entity_id} 离开待确认，{_off_delay}s 后无人则触发")
                        return
            # ── 存在传感器去抖 END ─────────────────────────────────────────

            # ── 灯光/开关「同态跳变」过滤（on→on / off→off 仅属性变化，无需推理）──────
            # 场景激活时，所有已开启灯光会连续触发 on→on（亮度/色温变化），
            # 这类事件对 AI 决策无价值，是主要的 AI 算力浪费来源（日志显示 2908 次）。
            if domain in ("light", "switch") and old_s == new_s and old_s in ("on", "off"):
                self._sys_log("INFO", f"[过滤] {entity_id} 同态跳变（{old_s}→{new_s}，仅属性变化），跳过推理")
                return
            # ── 同态过滤 END ──────────────────────────────────────────────────────

            if not self._should_trigger(entity_id, old_s, new_s):
                return
            name = self.get_device_name(entity_id)
            controllable_domains = ("light", "switch", "fan", "cover", "climate", "media_player")
            location_domains = ("device_tracker", "person")
            
            # 记录到数据库时的来源标记 (BUG 1 修复)
            db_source = "system"

            if domain in controllable_domains:
                # ── 优先级系统：标准化来源分类 ──
                std_source = self._classify_source(entity_id, source_type)
                from .const import (
                    SOURCE_AUTOMATION, SOURCE_EMERGENCY,
                    SOURCE_PHYSICAL, SOURCE_DASHBOARD, SOURCE_VOICE,
                    PRIORITY_LABELS, SOURCE_LABELS,
                )
                
                # 识别用户手动操作
                if std_source in (SOURCE_PHYSICAL, SOURCE_DASHBOARD, SOURCE_VOICE):
                    db_source = "user"

                # P0 紧急事件检测（安全传感器激活）
                if std_source == SOURCE_EMERGENCY:
                    self._record_device_operation(entity_id, std_source, new_s, new.attributes if new else {})
                    self._trigger_emergency(entity_id, f"安全传感器 {entity_id} 触发告警 → {new_s}")

                if source_type == "自动化/脚本":
                    pri_rec = self._record_device_operation(entity_id, SOURCE_AUTOMATION, new_s)
                    self._sys_log("INFO", f"[自动化操作] {entity_id} → {new_s}（来源: 自动化/脚本，{pri_rec['priority_label']}）")
                    if entity_id in self._automation_managed_devices:
                        auto_names = self._automation_managed_devices[entity_id]
                        self._sys_log("INFO", f"[自动化避让] {entity_id} 由自动化操控（{', '.join(auto_names)}），跳过 AI 推理")
                        self.hass.async_add_executor_job(
                            self._record_event, "AutomationSkip", f"{entity_id} -> {new_s} (自动化)", entity_id, new_s
                        )
                        return
                elif source_type == "物理/自动" and new_s in self._OFF_STATES and self._is_occupancy_active(entity_id):
                    # 设备自动关闭（如定时器断电/Zigbee 联动关闭）→ 降级为 P2，不触发用户保护
                    pri_rec = self._record_device_operation(entity_id, SOURCE_AUTOMATION, new_s)
                    db_source = "system" # 修正：非用户操作，重置 db_source
                    self._sys_log("INFO", f"[设备自动关闭] {entity_id} → {new_s}（区域有人，判定为设备端自动关闭，{pri_rec['priority_label']}）")
                elif old_s == "unknown" and new_s in ("on", "open") and (
                    time.time() - self._startup_time < 120
                ):
                    # Phase 11.9: unknown→on 在启动恢复窗口（120s）内视为设备状态恢复，非用户操作。
                    # 根因：Lemesh/Zigbee 设备在 HA 重启后 60-80s 才恢复在线，此时启动冷却已结束，
                    # 设备恢复到上次状态（on）被误判为用户操作，导致记录 P1 保护 + corrections 污染。
                    pri_rec = self._record_device_operation(entity_id, SOURCE_AUTOMATION, new_s)
                    db_source = "system"
                    self._sys_log("INFO",
                        f"[状态恢复] {entity_id} unknown→{new_s}"
                        f"（启动恢复窗口 {int(time.time() - self._startup_time)}s，"
                        f"非用户操作，{pri_rec['priority_label']}）")
                else:
                    # 用户真实操作 → P1
                    pri_rec = self._record_device_operation(entity_id, std_source, new_s)
                    with self._user_overrides_lock:
                        self._user_overrides[entity_id] = {"state": new_s, "time": time.time()}
                    with self._user_manual_actions_lock:
                        self._user_manual_actions[entity_id] = {"state": new_s, "time": time.time()}
                    # Phase 10.0: 更新虚拟在场推断的设备操作痕迹（用户操作即在场证明）
                    if hasattr(self, "_presence_inference") and self._presence_inference is not None:
                        self._presence_inference.update_device_trace(entity_id, new_s, source=std_source)
                    self._sys_log("INFO",
                        f"[用户操作] 记录保护: {entity_id} → {new_s}"
                        f" (来源: {pri_rec['source_label']}，{pri_rec['priority_label']}，"
                        f"保护 {int(pri_rec['guard_until'] - time.time())}s)")
                trigger = self._fmt_trigger(source_type, domain, name, entity_id, old_s, new_s)
                self.hass.async_create_task(
                    async_call_service(self.hass, "homeassistant", "update_entity", {"entity_id": entity_id})
                )
                if self._learning_mode:
                    self.hass.async_add_executor_job(
                        self._record_event,
                        "Learning",
                        f"{trigger} [src:{source_type}]",
                        entity_id,
                        new_s,
                        db_source,
                    )
                else:
                    self.hass.async_add_executor_job(
                        self._record_event,
                        "DeviceOperation",
                        trigger,
                        entity_id,
                        new_s,
                        db_source,
                    )
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason="controllable_state_feedback",
                    source_type=source_type,
                )
                self._sys_log(
                    "INFO",
                    f"[可控设备回写] {entity_id} {old_s}→{new_s} 已记录为设备操作，不提交 fast-path",
                )
                return
            elif domain in location_domains:
                trigger = self._fmt_trigger("位置", domain, name, entity_id, old_s, new_s)
            else:
                # P0 紧急事件检测（binary_sensor 域的安全传感器）
                if domain == "binary_sensor" and new_s == "on":
                    eid_lower = entity_id.lower()
                    dev_name = self.device_info.get(entity_id, {}).get("name", "").lower()
                    from .const import SOURCE_EMERGENCY
                    _emg_kw = ("smoke", "gas", "leak", "flood", "alarm", "security", "fire", "co2",
                               "烟雾", "烟感", "燃气", "漏水", "水浸", "告警", "警报", "火灾", "安防")
                    if any(kw in eid_lower or kw in dev_name for kw in _emg_kw):
                        self._trigger_emergency(entity_id, f"安全传感器 {name}({entity_id}) 触发 → {new_s}")

                # Frigate person_count 生成语义化触发文本（仅在 Frigate 已启用时）
                eid_lower = entity_id.lower()
                if getattr(self, "_frigate_enabled", False) and any(kw in eid_lower for kw in self._PERSON_COUNT_KW):
                    try:
                        cnt_new = int(float(new_s))
                        cnt_old = int(float(old_s)) if old_s else 0
                    except (ValueError, TypeError):
                        cnt_new, cnt_old = 0, 0

                    # ── Frigate 人数传感器防抖 ────────────────────────────────
                    # 取消已有的待确认计时器（新的变化覆盖旧的）
                    old_cancel = self._frigate_count_timers.pop(entity_id, None)
                    if old_cancel:
                        try:
                            old_cancel()
                        except Exception as exc:
                            _LOGGER.debug("[Listeners] 取消 Frigate 防抖计时器失败: %s", exc)

                    # 冷却检查：相同值在 _FRIGATE_COUNT_COOLDOWN 内不重复触发
                    last_ts, last_cnt = self._frigate_count_last_trigger.get(entity_id, (0, -1))
                    if cnt_new == last_cnt and (time.time() - last_ts) < self._FRIGATE_COUNT_COOLDOWN:
                        self._sys_log(
                            "INFO",
                            f"[Frigate防抖] {entity_id} 值 {cnt_new} 与上次相同，"
                            f"冷却中（{int(time.time() - last_ts)}s < {self._FRIGATE_COUNT_COOLDOWN}s），跳过"
                        )
                        return

                    # 按变化方向选择确认延迟时长
                    if cnt_new > cnt_old:
                        hold = self._FRIGATE_COUNT_ON_HOLD
                        direction_log = f"人数增加 {cnt_old}→{cnt_new}"
                    elif cnt_new == 0:
                        hold = self._FRIGATE_COUNT_OFF_HOLD
                        direction_log = f"人数归零 {cnt_old}→0"
                    else:
                        hold = self._FRIGATE_COUNT_CHANGE_HOLD
                        direction_log = f"人数减少 {cnt_old}→{cnt_new}"

                    _eid = entity_id
                    _cnt_new = cnt_new
                    _cnt_old = cnt_old
                    _name = name

                    @callback
                    def _confirm_frigate_count(_now,
                                               eid=_eid,
                                               expected=_cnt_new,
                                               c_old=_cnt_old,
                                               dev_nm=_name) -> None:
                        """确认 Frigate 人数值稳定后才触发推理。"""
                        self._frigate_count_timers.pop(eid, None)
                        cur_state = self.hass.states.get(eid)
                        if not cur_state:
                            return
                        try:
                            cur_cnt = int(float(cur_state.state))
                        except (ValueError, TypeError):
                            return
                        if cur_cnt != expected:
                            self._sys_log(
                                "INFO",
                                f"[Frigate防抖] {eid} 确认时人数已变为 {cur_cnt}（期望 {expected}），丢弃，等待新事件"
                            )
                            return

                        # 二次冷却：确认时再检查一次（防止并发计时器残留）
                        ts_now = time.time()
                        last_t, last_c = self._frigate_count_last_trigger.get(eid, (0, -1))
                        if cur_cnt == last_c and (ts_now - last_t) < self._FRIGATE_COUNT_COOLDOWN:
                            self._sys_log("INFO", f"[Frigate防抖] {eid} 确认时仍在冷却中，跳过")
                            return

                        self._frigate_count_last_trigger[eid] = (ts_now, cur_cnt)
                        dev_room = self.device_info.get(eid, {}).get("room", "") or dev_nm
                        if cur_cnt > c_old:
                            trig = (
                                f"[视觉检测] Frigate 摄像头「{dev_room}」检测到人员进入"
                                f"（当前人数: {cur_cnt}，变化: {c_old}→{cur_cnt}）"
                            )
                        elif cur_cnt == 0:
                            trig = (
                                f"[视觉检测] Frigate 摄像头「{dev_room}」区域已无人"
                                f"（变化: {c_old}→0）"
                            )
                        else:
                            trig = (
                                f"[视觉检测] Frigate 摄像头「{dev_room}」人数变化"
                                f"（{c_old}→{cur_cnt}人）"
                            )
                        event_type_label = "Learning" if self._learning_mode else "Trigger"
                        self._sys_log("INFO", f"[Frigate防抖] {eid} 稳定确认，{event_type_label}: {trig}")
                        self.hass.async_add_executor_job(
                            self._record_event, event_type_label, trig, eid, str(cur_cnt)
                        )
                        if not self._learning_mode:
                            try:
                                self._schedule_inference(eid, trig, new_state=str(cur_cnt))
                            except Exception as exc:
                                self._sys_log("ERROR", f"[Frigate防抖] 调度推理失败: {exc}")

                    handle = async_call_later(self.hass, hold, _confirm_frigate_count)
                    self._frigate_count_timers[entity_id] = handle
                    self._sys_log(
                        "INFO",
                        f"[Frigate防抖] {entity_id} {direction_log}，等待 {hold}s 稳定确认"
                    )
                    return  # 不直接触发，由防抖回调决定是否触发
                    # ── Frigate 防抖 END ──────────────────────────────────────
                else:
                    trigger = self._fmt_trigger("物理", domain, name, entity_id, old_s, new_s)

            if self._learning_mode:
                # 静默学习：保留全部来源（用户手动、HA 自动化/脚本、物理传感器）
                # HA 自动化代表用户设定的偏好，物理传感器代表真实使用模式，均有训练价值；
                # 同时当传感器故障时，历史自动化触发记录可作为设备状态推断的兜底依据。
                # 在 detail 中嵌入来源标记，未来分析可据此区分并加权。
                _src_tag = f" [src:{source_type}]" if source_type != "物理/自动" else ""
                _learning_detail = f"{trigger}{_src_tag}"
                self._sys_log(
                    "INFO",
                    f"[静默学习] {entity_id} {old_s}→{new_s}，记录（来源: {source_type}）"
                )
                self.hass.async_add_executor_job(
                    self._record_event, "Learning", _learning_detail, entity_id, new_s, db_source
                )
                return
            self._sys_log("INFO", f"[触发] 调度推理: {trigger}")
            self.hass.async_add_executor_job(
                self._record_event, "Trigger", trigger, entity_id, new_s, db_source
            )
            try:
                self._schedule_inference(entity_id, trigger, new_state=new_s)
            except Exception as exc:
                self._sys_log("ERROR", f"[触发] 调度推理异常: {exc}")
                _LOGGER.exception("_schedule_inference failed")
        return _state_changed

    def _refresh_listeners(self) -> None:
        """Re-register state-change listeners after device list changes."""
        for remove in self._listener_removers:
            try:
                remove()
            except Exception:
                pass
        self._listener_removers.clear()
        entity_ids = [eid for eid in self.device_info
                      if eid.split(".")[0] in ("binary_sensor", "sensor", "device_tracker", "person",
                                               "light", "switch", "climate", "cover", "fan", "media_player")]
        if entity_ids:
            self._listener_removers.append(
                async_track_state_change_event(self.hass, entity_ids, self._make_state_handler())
            )
            self._sys_log("INFO", f"监听器已刷新，监听 {len(entity_ids)} 个实体: {', '.join(entity_ids[:5])}{'...' if len(entity_ids)>5 else ''}")
        else:
            self._sys_log("WARN", "监听器刷新：无可监听设备，请先添加设备")
