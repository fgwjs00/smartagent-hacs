"""
PatrolMixin — 巡检与行为分析层。
负责：定时环境巡检、行为模式分析、习惯主动建议、到家预测。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import Counter, defaultdict

from .action_mapping import entities_to_actions
from .ha_adapter import async_call_service
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

_LOGGER = logging.getLogger(__name__)


class PatrolMixin:
    """Mixin: 巡检 & 行为分析 — 定时扫描 / 习惯建议 / 规律挖掘。"""

    # 各时段巡检间隔（分钟）：0 表示该时段不巡检（深夜保护 + 1h 后再检查）
    _SCAN_INTERVALS: dict[str, int] = {
        "sleep":   0,    # 0-6 点深度睡眠，不巡检（传感器触发仍正常工作）
        "morning": 20,   # 6-9 点起床期
        "day":     15,   # 9-18 点白天活动
        "evening": 10,   # 18-23 点晚间高频
        "night":   15,   # 23-0 点入睡过渡
    }

    # ── 巡检调度 ──────────────────────────────────────────────────────────────

    def _get_scan_interval(self) -> int:
        """根据当前时段返回巡检间隔（分钟）。"""
        from .const import MODE_SHOWROOM
        h = datetime.now().hour
        
        if self._mode == MODE_SHOWROOM:
            # 展厅模式：营业时间 5min，非营业时间 15min（分钟级精度判断）
            now_min = h * 60 + datetime.now().minute
            if self.showroom_biz_start_min <= now_min < self.showroom_biz_end_min:
                return 5
            return 15
        
        if 0 <= h < 6:
            return self._SCAN_INTERVALS["sleep"]
        if 6 <= h < 9:
            return self._SCAN_INTERVALS["morning"]
        if 9 <= h < 18:
            return self._SCAN_INTERVALS["day"]
        if 18 <= h < 23:
            return self._SCAN_INTERVALS["evening"]
        return self._SCAN_INTERVALS["night"]

    def _schedule_next_scan(self) -> None:
        """根据当前时段动态调度下一次巡检。"""
        interval = self._get_scan_interval()
        if interval == 0:
            interval = 60  # 深夜时段：1 小时后再检查是否该恢复
        self._scan_timer_unsub = async_call_later(
            self.hass, interval * 60, self._on_scan_timer
        )

    @callback
    def _on_scan_timer(self, _now: Any) -> None:
        """动态间隔巡检入口：执行巡检后自动调度下一次。"""
        self._scan_timer_unsub = None
        self.hass.async_create_task(self._do_scan_and_reschedule())

    async def _do_scan_and_reschedule(self) -> None:
        """执行巡检 + 回查待验证动作 + 环境反馈检查 + 刷新质量统计缓存 + 调度下一次。

        使用 try/finally 确保无论扫描过程是否出现异常，_schedule_next_scan 一定会被调用，
        防止巡检链因单次异常而永久中断。
        """
        try:
            await self._verify_pending_actions()
            await self._check_env_feedback_tasks()

            # Phase 9.9: 回查并验证训练样本（30 分钟无修正标记为正样本）
            verified_count = await self.hass.async_add_executor_job(self._verify_training_samples)
            if verified_count > 0:
                self._sys_log("INFO", f"[TrainingData] 已验证并归档 {verified_count} 条正向训练样本")

            await self._run_periodic_scan()

            # Phase 11.2: 无人+灯亮持续异常检测——防止死亡螺旋无人发现
            await self._check_empty_lights_anomaly()

            self._action_quality_cache = await self.hass.async_add_executor_job(self._get_action_quality_stats)
        except Exception as exc:
            _LOGGER.exception("[Patrol] 巡检执行异常: %s", exc)
            self._sys_log("ERROR", f"[巡检] 本次扫描异常已捕获，将继续调度下一次: {exc}")
        finally:
            # 无论是否出现异常，都必须重新调度，防止巡检链永久中断
            self._schedule_next_scan()

    async def _run_periodic_scan(self) -> None:
        """环境感知巡检：汇报可控设备状态 + 传感器读数 + 人员位置，让 AI 综合决策。"""
        # ── Phase 7D: 定时自动化场景触发 ──
        await self._check_and_trigger_scheduled_scenes()

        from .const import MODE_SHOWROOM
        if not self._is_enabled():
            return

        # ── P0: 操作员指令抑制窗口 ──
        # 若最近 60 秒内执行过操作员一次性指令，暂时抑制巡检推理，防止灯光状态被立即重置
        if self._mode == MODE_SHOWROOM:
            _elapsed_since_cmd = time.time() - getattr(self, "_last_showroom_cmd_time", 0)
            if _elapsed_since_cmd < 60:
                self._sys_log("INFO", f"[巡检抑制] 操作员指令执行不久({int(_elapsed_since_cmd)}s < 60s)，跳过本次巡检")
                return

        if self._learning_mode:
            # 静默学习模式：不执行 AI 推理，但记录一份环境快照用于行为分析
            await self._record_learning_snapshot()
            return
        # 每次巡检时刷新 HA 脚本/场景/自动化资源
        self._refresh_ha_resources()

        interval = self._get_scan_interval()
        if interval == 0:
            return

        # ── 1. 可控设备状态快照 ──
        CONTROLLABLE = ("light", "switch", "fan", "climate", "cover")
        active_parts: list[str] = []
        standby_parts: list[str] = []
        for eid, info in self.device_info.items():
            domain = eid.split(".")[0]
            if domain not in CONTROLLABLE:
                continue
            state = self.hass.states.get(eid)
            if not state or state.state in ("unavailable", "unknown"):
                continue
            name = info.get("name", eid)
            is_active = state.state not in ("off", "closed", "idle")
            detail = ""
            if domain == "light" and state.attributes.get("brightness"):
                pct = round(state.attributes["brightness"] / 255 * 100)
                detail = f" 亮度{pct}%"
            elif domain == "climate":
                temp = state.attributes.get("temperature", "?")
                cur = state.attributes.get("current_temperature", "?")
                detail = f" 当前{cur}°C/目标{temp}°C 模式={state.state}"
            if is_active:
                active_parts.append(f"  🟢 {name}({eid}){detail}")
            else:
                standby_parts.append(f"  ⚪ {name}({eid}) 已关闭")

        # ── 2. 环境传感器读数 ──
        sensor_parts: list[str] = []
        for eid, info in self.device_info.items():
            domain = eid.split(".")[0]
            if domain not in ("sensor", "binary_sensor"):
                continue
            state = self.hass.states.get(eid)
            if not state or state.state in ("unavailable", "unknown"):
                continue
            name = info.get("name", eid)
            if domain == "binary_sensor":
                label = "有人/检测到" if state.state == "on" else "无人/未检测"
                sensor_parts.append(f"  📊 {name}: {label}")
            else:
                unit = state.attributes.get("unit_of_measurement", "")
                sensor_parts.append(f"  📊 {name}: {state.state}{unit}")

        # ── 3. 人员位置（device_tracker）──
        person_parts: list[str] = []
        for eid, info in self.device_info.items():
            if not eid.startswith("device_tracker.") and not eid.startswith("person."):
                continue
            state = self.hass.states.get(eid)
            if state:
                person_parts.append(f"  👤 {info.get('name', eid)}: {state.state}")

        # ── 4. 实时人员占用状态摘要 ──
        occ_map = self._get_room_occupancy_map()

        # Phase 11.3+: 巡检冷却窗口按房间过滤（不再整轮跳过）
        _DEPARTURE_COOLDOWN = 300  # 5 分钟（秒）
        _departure_cooldowns = getattr(self, "_last_departure_turnoff_time", {})
        _cooled_rooms: set[str] = set()
        if _departure_cooldowns:
            _now = time.time()
            _scan_rooms = set(occ_map.keys())
            _cooled_rooms = {
                r for r, ts in _departure_cooldowns.items()
                if _now - ts < _DEPARTURE_COOLDOWN and r in _scan_rooms
            }
            if _cooled_rooms:
                _remaining = [
                    f"{r}({int(_DEPARTURE_COOLDOWN - (_now - _departure_cooldowns[r]))}s)"
                    for r in sorted(_cooled_rooms)
                ]
                self._sys_log("INFO",
                    f"[冷却保护] 巡检将跳过冷却房间，其余房间继续推理: {', '.join(_remaining)}")

        occ_summary = []
        for room, sensors in occ_map.items():
            if room in _cooled_rooms:
                continue
            is_occ = any(s == "on" for _, s in sensors)
            is_unavail = all(s in ("unknown", "unavailable") for _, s in sensors)
            status = "有人" if is_occ else ("未知" if is_unavail else "无人")
            occ_summary.append(f"  - {room}: {status}")

        if not active_parts and not sensor_parts and not standby_parts and not person_parts:
            return

        # ── Phase 11.4b：巡检焦点房间检测 ─────────────────────────────────────
        # 从本次巡检数据中找出最值得 AI 关注的房间，嵌入「[room]」标记到 trigger 首行。
        # context_builder._extract_trigger_room() 识别该标记后，将触发 focus_room 压缩模式，
        # 将巡检 Prompt 从全量设备列表（可能 100+ 行）压缩至目标房间 + 其他房间摘要。
        # 优先级：① 无人+灯亮（最常见的需要 AI 干预的异常）
        #         ② 有人+大量设备活跃（值得优化建议）
        #         ③ 无房间特别值得关注时 → 不嵌入标记（保持全量巡检）
        _focus_room_for_patrol = ""
        _anomaly_rooms: list[tuple[int, str]] = []  # (优先级得分, 房间名)

        for room, sensors in occ_map.items():
            if room in _cooled_rooms:
                continue
            is_occ = any(s == "on" for _, s in sensors)
            # 传感器全部失联时跳过（无法判断真实在场状态，不应触发异常标记）
            is_unavail = all(s in ("unknown", "unavailable") for _, s in sensors)
            if is_unavail:
                continue
            # 收集该房间开启的可控设备数（缓存 state 对象，避免双重字典查找）
            _room_active = 0
            for eid, info in self.device_info.items():
                if info.get("room") != room or eid.split(".")[0] not in CONTROLLABLE:
                    continue
                _st = self.hass.states.get(eid)
                if _st and _st.state not in ("off", "closed", "idle", "unavailable", "unknown"):
                    _room_active += 1
            if not is_occ and _room_active > 0:
                # 无人+有设备开启：最高优先（异常，AI 需要决策是否关闭）
                _anomaly_rooms.append((100 + _room_active, room))
            elif is_occ and _room_active > 3:
                # 有人+多设备活跃：中优先（可能需要场景调整建议）
                _anomaly_rooms.append((50 + _room_active, room))

        if _anomaly_rooms:
            _anomaly_rooms.sort(reverse=True)
            _focus_room_for_patrol = _anomaly_rooms[0][1]

        # 构建触发器文本，当有焦点房间时在首行嵌入「[room]」标记
        _patrol_header = (
            f"[巡检] 「[{_focus_room_for_patrol}]」环境感知巡检（焦点：{_focus_room_for_patrol}异常）"
            if _focus_room_for_patrol
            else "[巡检] 环境感知巡检"
        )
        report_lines = [_patrol_header]
        if occ_summary:
            report_lines.append("【各区域实时人员状态】")
            report_lines.extend(occ_summary)
        if active_parts:
            report_lines.append("【正在运行的设备】")
            report_lines.extend(active_parts)
        if standby_parts:
            report_lines.append("【已关闭/待机的可控设备】")
            report_lines.extend(standby_parts)
        if sensor_parts:
            report_lines.append("【传感器读数】")
            report_lines.extend(sensor_parts)
        if person_parts:
            report_lines.append("【人员位置】")
            report_lines.extend(person_parts)

        arrival_hint = self._get_arrival_prediction()
        if arrival_hint:
            report_lines.append("【到家预测】")
            report_lines.append(f"  {arrival_hint}")

        trigger = "\n".join(report_lines)
        self._sys_log("INFO",
            f"[巡检] 间隔={interval}min 活跃={len(active_parts)} 待机={len(standby_parts)}"
            f" 传感器={len(sensor_parts)}"
            + (f" 焦点={_focus_room_for_patrol}" if _focus_room_for_patrol else "")
        )

        # ── 基线采样：记录当前设备状态供偏好学习使用 ─────────────────────────
        # 展厅模式：仅在营业时间内采样（反映展示场景下的灯光使用习惯）
        # 家庭模式：仅在有人在场（全局）时采样（避免无人状态污染基线）
        await self.hass.async_add_executor_job(self._do_baseline_sample)

        # ── 无变化跳过优化：连续 N 次巡检设备快照一致则跳过推理 ──────────────
        # 构造简洁的状态指纹（仅 entity_id + state 拼接），避免 Prompt 完整比较
        snapshot_parts = sorted(
            f"{eid}={self.hass.states.get(eid).state if self.hass.states.get(eid) else '?'}"
            for eid in self.device_info
        )
        snapshot_hash = hash(tuple(snapshot_parts))
        if str(snapshot_hash) == self._last_patrol_snapshot:
            self._patrol_no_change_count += 1
            # 展厅模式允许连续跳过 2 次（10min），家庭模式允许 3 次（45min）
            max_skip = 2 if self._mode == MODE_SHOWROOM else 3
            if self._patrol_no_change_count <= max_skip:
                self._sys_log("INFO",
                    f"[巡检] 设备状态与上次完全一致（连续 {self._patrol_no_change_count} 次），跳过 AI 推理以节省算力")
                return
            else:
                self._sys_log("INFO",
                    f"[巡检] 设备状态虽无变化但已达最大跳过次数 {max_skip}，执行保底巡检")
                self._patrol_no_change_count = 0
        else:
            self._patrol_no_change_count = 0
        self._last_patrol_snapshot = str(snapshot_hash)

        # 如果有存在传感器正在去抖（刚变化，待确认），延迟让去抖推理优先
        debouncing_on = {eid for eid, ts in self._presence_on_start.items()
                         if time.time() - ts < self._PRESENCE_ON_MIN_HOLD + 1}
        debouncing_off = set(self._presence_off_timers.keys())
        pending_debounce = debouncing_on | debouncing_off
        if pending_debounce:
            self._sys_log("INFO",
                f"[巡检] 跳过本次推理：存在传感器正在去抖中 {pending_debounce}，等待去抖完成后由其触发推理")
            return

        # 如果推理队列中已有待合并的触发器，也跳过（避免几秒内双重推理）
        with self._pending_triggers_lock:
            _pending_count = len(self._pending_triggers)
        if _pending_count:
            self._sys_log("INFO",
                f"[巡检] 跳过本次推理：推理队列中已有 {_pending_count} 个待合并触发")
            return

        # ── Phase 13.P: 昼夜节律巡检精调（可选，用户可在设置中开关）──────────────
        # 在 AI 推理之前，先检查已开灯光是否偏离节律曲线，
        # 若偏差明显则直接生成带 transition=30 的渐变调整动作（不经过 LLM）。
        _circadian = getattr(self, "_circadian_engine", None)
        _auto_adj = getattr(self, "_circadian_auto_adjust", False)
        if _circadian and _auto_adj and _circadian.enabled:
            try:
                _adj_actions: list[dict] = []
                for eid, info in self.device_info.items():
                    if not eid.startswith("light."):
                        continue
                    _st = self.hass.states.get(eid)
                    if not _st or _st.state != "on":
                        continue
                    _a = _st.attributes or {}
                    _cur_bri = _a.get("brightness")
                    if _cur_bri is not None:
                        _cur_bri = round(_cur_bri / 255 * 100)
                    _cur_ct = _a.get("color_temp_kelvin")
                    _room = info.get("room", "")
                    _adj = _circadian.should_adjust(eid, _cur_bri, _cur_ct, room=_room)
                    if _adj:
                        # 裁剪色温到设备支持范围
                        _min_ct = _a.get("min_color_temp_kelvin")
                        _max_ct = _a.get("max_color_temp_kelvin")
                        if _min_ct is not None and _max_ct is not None:
                            _t_ct = _adj["params"].get("color_temp_kelvin", 0)
                            _adj["params"]["color_temp_kelvin"] = max(_min_ct, min(_max_ct, _t_ct))
                        _adj_actions.append(_adj)
                if _adj_actions:
                    self._sys_log(
                        "INFO",
                        f"[昼夜节律] 巡检精调：{len(_adj_actions)} 盏灯偏离节律曲线，"
                        f"执行渐变调整（transition=30s）",
                    )
                    await self._execute_actions(
                        _adj_actions,
                        trigger_summary="CircadianPatrol",
                        scene_desc="昼夜节律巡检精调",
                        confidence=90,
                    )
            except Exception as _exc:
                _LOGGER.warning("[Circadian] 巡检精调异常: %s", _exc)

        await self._run_inference(trigger)

        # ── ReAct-Lite (9.10)：巡检后置验证 ─────────────────────────────────────
        # 若本次巡检推理确认执行了 turn_on / turn_off 动作（executed > 0），
        # 在 45 秒后异步检查设备是否实际响应，检测继电器失联/命令超时等问题。
        # _last_executed_actions_for_verify 只在 inference.py 确认 executed>0 后才赋值，
        # 避免低置信度未执行时产生误报。
        _acts_to_verify = getattr(self, "_last_executed_actions_for_verify", [])
        _cmd_time = getattr(self, "_patrol_cmd_time", 0.0)
        if _acts_to_verify and _cmd_time:
            self._last_executed_actions_for_verify = []
            self._patrol_cmd_time = 0.0
            self.hass.async_create_task(
                self._verify_patrol_actions_delayed(
                    list(_acts_to_verify), cmd_time=_cmd_time, delay_sec=45
                )
            )

        # 每次巡检也检查习惯主动建议（家庭模式）
        if self._mode != MODE_SHOWROOM and self._habit_proactive:
            await self._run_habit_proactive_check()

        # 清理过期数据
        await self.hass.async_add_executor_job(self._cleanup_old_memory)

        # Phase 11.5: Smart Memory Guard 三道防线（每 6 小时运行一次）
        if not hasattr(self, "_last_memory_guard_time"):
            self._last_memory_guard_time: float = 0.0
        _MEMORY_GUARD_INTERVAL = 6 * 3600  # 6 小时
        if time.time() - self._last_memory_guard_time >= _MEMORY_GUARD_INTERVAL:
            await self.hass.async_add_executor_job(self._run_smart_memory_guard)
            self._last_memory_guard_time = time.time()

    async def _record_learning_snapshot(self) -> None:
        """
        静默学习模式下，巡检时记录当前设备状态快照。
        仅记录开启状态的可控设备，为后续行为规律分析提供定时采样数据。
        """
        CONTROLLABLE = ("light", "switch", "fan", "climate", "cover")
        on_devices = []
        for eid, info in self.device_info.items():
            if eid.split(".")[0] not in CONTROLLABLE:
                continue
            st = self.hass.states.get(eid)
            if not st or st.state in ("unavailable", "unknown"):
                continue
            if st.state in ("on", "open", "cool", "heat", "dry", "fan_only", "auto", "playing"):
                on_devices.append(f"{info.get('name', eid)}({st.state})")
        if on_devices:
            detail = f"[静默学习快照] 当前开启设备: {', '.join(on_devices[:10])}"
            for eid, info in self.device_info.items():
                if eid.split(".")[0] not in CONTROLLABLE:
                    continue
                st = self.hass.states.get(eid)
                if st and st.state in ("on", "open", "cool", "heat", "dry", "fan_only", "auto", "playing"):
                    await self.hass.async_add_executor_job(
                        self._record_event, "Learning", detail, eid, st.state
                    )
            self._sys_log("INFO", f"[静默学习] 巡检快照：{len(on_devices)} 个设备处于开启状态")

    # ── 日常行为模式分析 ──────────────────────────────────────────────────────

    def _do_baseline_sample(self) -> None:
        """巡检采样：将当前灯光状态写入 device_baseline 表。

        展厅模式：仅在营业时间内采样（保证采样数据代表展示场景）。
        家庭模式：仅在全局判断有人（至少一个区域有人或有人员在家）时采样，
                  避免无人状态（关灯）被大量采集而拉低基线。
        """
        from .const import MODE_SHOWROOM

        try:
            # ── 采样条件过滤 ──────────────────────────────────────────────────
            if self._mode == MODE_SHOWROOM:
                _now = datetime.now()
                now_min = _now.hour * 60 + _now.minute
                should_sample = self.showroom_biz_start_min <= now_min < self.showroom_biz_end_min
            else:
                # 家庭模式：检查全局是否有人在场
                occ_map = self._get_room_occupancy_map()
                someone_home = any(
                    any(s == "on" for _, s in sensors)
                    for sensors in occ_map.values()
                    if sensors
                )
                if not someone_home:
                    # GPS / person 作为兜底
                    people = [
                        self.hass.states.get(eid)
                        for eid in self.device_info
                        if eid.startswith("person.")
                    ]
                    someone_home = any(p and p.state == "home" for p in people)
                should_sample = someone_home

            if not should_sample:
                return

            # ── 对所有受控灯光设备进行采样 ───────────────────────────────────
            sampled = 0
            for eid, info in self.device_info.items():
                if not eid.startswith("light."):
                    continue
                st = self.hass.states.get(eid)
                if not st or st.state in ("unavailable", "unknown"):
                    continue
                is_on = st.state == "on"
                brightness = 0
                if is_on and st.attributes.get("brightness"):
                    brightness = round(st.attributes["brightness"] / 255 * 100)
                self._sample_device_baseline(eid, is_on, brightness)
                sampled += 1

            if sampled > 0:
                _LOGGER.debug("[Baseline] 采样 %d 台灯光设备", sampled)
        except Exception as e:
            _LOGGER.warning("[Baseline] 采样异常: %s", e)

    async def _check_and_trigger_scheduled_scenes(self) -> None:
        """Phase 7D: 检查当前时间是否需要触发已激活的 AI 场景，并处理展厅开/下班自动关灯。"""
        from .const import MODE_SHOWROOM
        now = datetime.now()
        hour = now.hour
        now_min = hour * 60 + now.minute

        # ── 展厅模式：分钟级营业时间边界检测 ────────────────────────────────────
        if self._mode == MODE_SHOWROOM:
            await self._check_showroom_biz_boundary(now_min)

        # 确保同一小时内只触发一次
        last_h = getattr(self, "_last_scheduled_hour", -1)
        if last_h == hour:
            return
        self._last_scheduled_hour = hour

        # SQLite %w 格式：0=日,1=一,...,6=六；Python weekday() 0=Mon → (wd+1)%7 = SQLite wd
        _sqlite_wd = str((now.weekday() + 1) % 7)
        _wd_mask_default = "0123456"

        for scene in getattr(self, "_ai_scenes_cache", []):
            if scene.get("status") != "active":
                continue
            
            s_hour = scene.get("hour_start")
            # 精确在 hour_start 小时触发一次；同时检查星期掩码（SQLite %w 格式，修复工作日 Bug）
            wd_mask = scene.get("weekday_mask", _wd_mask_default)
            if s_hour == hour and _sqlite_wd in wd_mask:
                scene_id = scene["id"]
                self._sys_log("INFO", f"[Phase 7D] 到点自动触发 AI 场景: {scene['name']} (scene.ai_{scene_id})")
                try:
                    from .ha_adapter import async_execute_command_envelope

                    result = await async_execute_command_envelope(self.hass, {
                        "request_id": f"scheduled-scene:{scene_id}:{hour}",
                        "commands": [{
                            "entity_id": f"scene.ai_{scene_id}",
                            "domain": "scene",
                            "service": "turn_on",
                            "data": {},
                        }],
                        "execution_policy": {"stop_on_first_error": True},
                        "safety": {
                            "risk_level": "safe",
                            "requires_confirmation": False,
                            "reason": f"[Phase 7D] 定时触发 AI 场景: {scene['name']}",
                        },
                    })
                    if isinstance(result, dict) and result.get("ok"):
                        continue
                    raise RuntimeError(
                        result.get("error") or result.get("error_type") or "command_envelope_failed"
                        if isinstance(result, dict)
                        else "command_envelope_failed"
                    )
                except Exception as e:
                    self._sys_log("ERROR", f"[Phase 7D] 触发定时场景失败: {e}")
                    _LOGGER.warning("Failed to trigger scheduled scene: %s", e)

    async def _check_showroom_biz_boundary(self, now_min: int) -> None:
        """检测展厅营业时间边界并主动触发开/关灯推理。

        每次巡检比较当前分钟数与上次巡检的状态，检测到边界切换时立即触发推理：
        - 进入营业时间：主动开灯，积极展示
        - 进入非营业时间：若无人则主动关闭所有展厅灯光

        :param now_min: 当前距午夜的分钟数
        """
        from .const import format_biz_time
        is_biz = self.showroom_biz_start_min <= now_min < self.showroom_biz_end_min
        last_was_biz = getattr(self, "_showroom_last_was_biz", None)

        # 首次运行，只记录状态，不触发
        if last_was_biz is None:
            self._showroom_last_was_biz = is_biz
            return

        biz_changed = (last_was_biz != is_biz)
        self._showroom_last_was_biz = is_biz

        if not biz_changed:
            return

        biz_start_str = format_biz_time(self.showroom_biz_start_min)
        biz_end_str   = format_biz_time(self.showroom_biz_end_min)

        if is_biz:
            # 刚进入营业时间 → 主动开灯
            trigger = f"[展厅] 营业时间开始（{biz_start_str}），请开启展厅灯光，积极展示智能家居"
            self._sys_log("INFO", f"[展厅开班] 到达营业开始时间 {biz_start_str}，主动触发开灯推理")
        else:
            # 刚进入非营业时间 → 直接关灯（时间规则，不依赖人员状态）
            # 注意：不再使用"若展厅无人"的条件措辞，避免 AI 因区域状态未知而保守拒绝执行。
            # 摄像头漏检/传感器缺失时应默认允许关灯，若摄像头实时确认有人则调暗至 30% 即可。
            trigger = (
                f"[展厅] 营业时间已结束（{biz_end_str}），这是时间规则：请立即关闭所有展厅区域灯光。"
                f"若摄像头此刻确认展厅内有人，则改为将灯光调暗至30%而非完全关闭；"
                f"若无法确认是否有人，则视为无人并执行关闭。"
            )
            self._sys_log("INFO", f"[展厅下班] 到达营业结束时间 {biz_end_str}，主动触发关灯推理")

        try:
            await self._run_inference(trigger)
        except Exception as exc:
            self._sys_log("ERROR", f"[展厅边界] 触发推理失败: {exc}")
            _LOGGER.exception("[展厅边界] 推理异常: %s", exc)

    def _on_daily_pattern_analysis(self, _now: datetime) -> None:
        """每天凌晨 3:00 (UTC 19:00) 触发行为规律分析 + 能耗分析 + 记忆衰减维护。

        三项任务串行执行：避免并发写 DB 导致 SQLite 锁竞争，
        同时防止 _analysis_lock 可重入问题。
        """
        self.hass.loop.call_soon_threadsafe(
            lambda: self.hass.async_create_task(self._async_daily_analysis())
        )

    async def _async_daily_analysis(self) -> None:
        """凌晨分析任务主体：串行运行三项 executor 任务，持 _analysis_lock 防止与手动分析重叠。"""
        if self._analysis_lock.locked():
            self._sys_log("INFO", "[凌晨分析] 分析锁被占用，跳过本次定时触发")
            return
        async with self._analysis_lock:
            self._sys_log("INFO", "[凌晨分析] 开始行为规律分析...")
            await self.hass.async_add_executor_job(self._analyze_patterns)
            self._sys_log("INFO", "[凌晨分析] 行为分析完成，开始能耗分析...")
            await self.hass.async_add_executor_job(self._analyze_energy_usage)
            self._sys_log("INFO", "[凌晨分析] 能耗分析完成，开始记忆衰减维护...")
            await self.hass.async_add_executor_job(self._scheduled_memory_decay_maintenance)
            # 每周日：本地 ML 训练不可用时，用在线大模型从训练样本中提炼行为规律
            await self._async_llm_behavior_learn()
            # 每周日：用 LLM 从 7 天操作历史中发现多设备联动的语义场景
            await self._async_llm_scene_discovery()
            self._sys_log("INFO", "[凌晨分析] 所有凌晨分析任务完成")

    async def _async_llm_behavior_learn(self) -> None:
        """每周日：当本地 scikit-learn 不可用时，调用在线大模型从已验证训练样本中提炼行为规律。

        触发条件（同时满足）：
          - 今天是周日（与本地 ML 训练同步）
          - 在线 AI 已配置（online_api_key 和 online_base_url 非空）
          - 已验证训练样本 ≥ 50 条
          - 本地模型文件不存在（scikit-learn 不可用时未生成）
        结果写入 behavior_patterns 表，同步刷新 FastBrain 内存缓存。
        """
        import json as _json
        from datetime import datetime as _dt

        if _dt.now().weekday() != 6:
            return

        api_key = getattr(self, "_online_api_key", None) or ""
        base_url = getattr(self, "online_base_url", None) or ""
        if not api_key or not base_url:
            return

        # 检查本地模型是否已存在（已存在说明 scikit-learn 可用，无需 LLM 替补）
        try:
            import os as _os
            from .model_trainer import resolve_model_path
            _mp = resolve_model_path(getattr(self, "_config_dir", None))
            if _os.path.exists(_mp):
                return
        except Exception:
            pass

        # 读取已验证的训练样本
        rows = await self.hass.async_add_executor_job(
            self._query_events,
            "SELECT feature_json, decision_json, label FROM training_data "
            "WHERE is_verified=1 AND label IS NOT NULL AND feature_json IS NOT NULL "
            "ORDER BY id DESC LIMIT 120",
        )
        if not rows or len(rows) < 50:
            _LOGGER.info("[LLM行为学习] 已验证样本 %d 条，不足 50 条，跳过", len(rows) if rows else 0)
            return

        # 构建样本摘要（紧凑格式，控制 token 量）
        sample_lines: list[str] = []
        for r in rows[:80]:
            try:
                feat = _json.loads(r["feature_json"])
                dec = _json.loads(r["decision_json"])
                actions = dec.get("actions", [])
                if not actions:
                    continue
                best = max(actions, key=lambda a: a.get("confidence", 0) if isinstance(a, dict) else 0)
                eid = best.get("entity_id", "")
                svc = best.get("service", "")
                if not eid or not svc:
                    continue
                is_correction = (r.get("label") == 0)
                tag = "[修正]" if is_correction else "[确认]"
                sample_lines.append(
                    f"{tag} {eid}→{svc} "
                    f"时段={feat.get('time_hour','?')}h "
                    f"周末={feat.get('is_weekend',0)} "
                    f"在场={feat.get('room_person_count','?')}人"
                )
            except Exception:
                continue

        if len(sample_lines) < 30:
            return

        sys_prompt = (
            "你是智能家居行为习惯分析专家。根据以下用户设备操作记录，提炼出最多10条高置信度习惯规律。\n"
            "直接返回合法 JSON，格式：\n"
            "{\"patterns\":[{\"entity_id\":\"light.xxx\",\"expected_state\":\"on\","
            "\"hour_start\":18,\"hour_end\":22,\"weekday_mask\":\"12345\","
            "\"confidence\":75,\"reason\":\"工作日晚归开灯\"}]}\n"
            "weekday_mask 用数字字符串表示（0=周日,1=周一…6=周六），工作日='12345'，"
            "周末='06'，每天='0123456'。confidence 范围 50-90。"
        )
        user_prompt = (
            f"以下是近期 {len(sample_lines)} 条用户设备操作记录（已由用户确认或修正），"
            f"请提炼行为习惯规律：\n\n" + "\n".join(sample_lines)
        )

        self._sys_log("INFO", f"[LLM行为学习] 开始分析 {len(sample_lines)} 条训练样本...")
        try:
            import aiohttp as _aiohttp
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": getattr(self, "online_model", None) or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 1200,
            }
            # Qwen3/DashScope 特殊参数
            _base_lower = base_url.lower()
            if "qwen3" in (getattr(self, "online_model", "") or "").lower() and (
                "dashscope" in _base_lower or "aliyuncs" in _base_lower
            ):
                payload["enable_thinking"] = False

            api_url = f"{base_url}/chat/completions"
            async with _aiohttp.ClientSession() as _sess:
                async with _sess.post(
                    api_url, json=payload, headers=headers,
                    timeout=_aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status >= 400:
                        self._sys_log("WARN", f"[LLM行为学习] API 返回 {resp.status}，跳过")
                        return
                    res = await resp.json()
                    raw = res.get("choices", [{}])[0].get("message", {}).get("content", "")

            patterns = self._parse_llm_behavior_patterns(raw)
            if patterns:
                await self.hass.async_add_executor_job(self._save_llm_patterns, patterns)
                self._sys_log(
                    "INFO",
                    f"[LLM行为学习] 从 {len(sample_lines)} 条样本中提炼出 {len(patterns)} 条行为规律，已写入 behavior_patterns",
                )
            else:
                self._sys_log("INFO", "[LLM行为学习] 模型未返回有效规律，跳过写入")
        except Exception as exc:
            self._sys_log("WARN", f"[LLM行为学习] 调用失败（不影响系统运行）: {exc}")

    # ── 5C-1: LLM 语义场景发现 ────────────────────────────────────────────────

    async def _async_llm_scene_discovery(self) -> None:
        """每周日：调用 LLM 从近 7 天操作历史中发现语义场景规律，写入 ai_scenes 表。

        与 _async_llm_behavior_learn() 并列运行：后者提炼单设备行为习惯，
        本方法发现多设备联动的"场景"（如"工作日晚归"、"周末午休"、"睡前模式"）。
        生成的场景使用 source='llm'，以区分统计共现产生的 source='auto' 场景。
        """
        from datetime import datetime as _dt

        if _dt.now().weekday() != 6:
            return

        api_key = getattr(self, "_online_api_key", None) or ""
        base_url = getattr(self, "online_base_url", None) or ""
        if not api_key or not base_url:
            return

        # 读取近 7 天设备操作事件（Learning + AI_Action），LIMIT 与后续处理上限对齐
        rows = await self.hass.async_add_executor_job(
            self._query_events,
            "SELECT time, type, entity, state, area FROM events "
            "WHERE type IN ('Learning','AI_Action') "
            "  AND entity IS NOT NULL AND state IS NOT NULL "
            "  AND time >= datetime('now', '-7 days') "
            "ORDER BY time DESC LIMIT 200",
        )
        if not rows or len(rows) < 20:
            _LOGGER.info("[LLM场景发现] 近7天操作记录 %d 条，不足20条，跳过", len(rows) if rows else 0)
            return

        # 构建事件摘要（按 日期类型+星期+时段+房间 格式聚合）
        event_lines: list[str] = []
        _wd_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for r in rows:
            eid = (r.get("entity") or "").strip()
            area = (r.get("area") or "").strip()
            new_state = (r.get("state") or "").strip()
            ts = (r.get("time") or "").strip()
            if not eid or not ts:
                continue
            dev_name = (self.device_info.get(eid) or {}).get("name") or eid.split(".")[-1]
            if not area:
                area = (self.device_info.get(eid) or {}).get("room", "")
            try:
                _t = _dt.fromisoformat(ts[:16])
                hour = _t.hour
                wd_label = _wd_labels[_t.weekday()]
                day_type = "工作日" if _t.weekday() < 5 else "周末"
            except Exception:
                continue
            state_cn = "开" if new_state in ("on", "open", "heat", "cool", "auto") else "关"
            event_lines.append(
                f"{day_type} {wd_label} {hour:02d}时"
                + (f" [{area}]" if area else "")
                + f": {dev_name}→{state_cn}"
            )

        if len(event_lines) < 15:
            _LOGGER.info("[LLM场景发现] 有效事件行 %d 条，不足15条，跳过", len(event_lines))
            return

        sys_prompt = (
            "你是智能家居场景分析专家。根据以下7天的设备操作记录，识别用户重复性的场景习惯。\n"
            "每个场景需要包含：\n"
            "- name: 简洁有意义的场景名（2-6字，如：工作日晚归、周末午休、睡前模式、观影模式）\n"
            "- description: 一句话描述（15字以内）\n"
            "- trigger: 触发条件（如：工作日18-20点客厅检测到有人）\n"
            "- room: 主要房间名（中文，如：客厅、卧室、书房）\n"
            "- hour_start: 开始时段（0-23整数）\n"
            "- hour_end: 结束时段（0-23整数）\n"
            "- weekday_mask: 适用星期字符串（0=周日,1=周一…6=周六，工作日='12345'，"
            "周末='06'，每天='0123456'）\n"
            "- entities: 涉及设备列表，每项含 entity_id 和 state（on 或 off）\n"
            "- confidence: 置信度 50-90\n\n"
            "直接返回合法 JSON 对象，格式：{\"scenes\":[...]}，最多 8 个场景。\n"
            "示例：{\"scenes\":[{\"name\":\"工作日晚归\",\"description\":\"下班回家自动开灯\","
            "\"trigger\":\"工作日18-21点客厅有人\",\"room\":\"客厅\","
            "\"hour_start\":18,\"hour_end\":21,\"weekday_mask\":\"12345\","
            "\"entities\":[{\"entity_id\":\"light.living_room\",\"state\":\"on\"}],"
            "\"confidence\":80}]}"
        )
        user_prompt = (
            f"以下是近7天 {len(event_lines)} 条设备操作记录，请识别场景习惯：\n\n"
            + "\n".join(event_lines[:150])
        )

        self._sys_log("INFO", f"[LLM场景发现] 开始分析 {len(event_lines)} 条操作记录...")
        try:
            import aiohttp as _aiohttp

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            _base_lower = base_url.lower()
            _model = getattr(self, "online_model", None) or "gpt-4o-mini"
            payload: dict = {
                "model": _model,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 1600,
                "temperature": 0.3,
            }
            # Qwen3/DashScope 不支持 response_format=json_object 时省略；
            # 其他 OpenAI 兼容端用 json_object 提高格式稳定性
            if "qwen3" in _model.lower() and (
                "dashscope" in _base_lower or "aliyuncs" in _base_lower
            ):
                payload["enable_thinking"] = False
            else:
                payload["response_format"] = {"type": "json_object"}

            api_url = f"{base_url}/chat/completions"
            async with _aiohttp.ClientSession() as _sess:
                async with _sess.post(
                    api_url, json=payload, headers=headers,
                    timeout=_aiohttp.ClientTimeout(total=90),
                ) as resp:
                    if resp.status >= 400:
                        self._sys_log("WARN", f"[LLM场景发现] API 返回 {resp.status}，跳过")
                        return
                    res = await resp.json()
                    raw = res.get("choices", [{}])[0].get("message", {}).get("content", "")

            scenes = self._parse_llm_scene_discovery(raw)
            if scenes:
                await self.hass.async_add_executor_job(self._save_llm_discovered_scenes, scenes)
                self._sys_log(
                    "INFO",
                    f"[LLM场景发现] 发现 {len(scenes)} 个语义场景，已写入 ai_scenes（等待用户确认）",
                )
                # 通过 executor 刷新内存缓存（_query_ai_scenes 是同步 DB 操作，不能在事件循环中直接调用）
                await self.hass.async_add_executor_job(self._refresh_ai_scenes_cache)
                self._notify_new_ai_scenes(len(scenes))
            else:
                self._sys_log("INFO", "[LLM场景发现] 模型未返回有效场景，跳过")
        except Exception as exc:
            self._sys_log("WARN", f"[LLM场景发现] 调用失败（不影响系统运行）: {exc}")

    def _parse_llm_scene_discovery(self, raw: str) -> list[dict]:
        """解析 LLM 返回的场景发现 JSON，返回验证后的场景列表。"""
        import json as _json

        try:
            data = _json.loads(raw)
        except Exception:
            # 尝试提取 JSON 数组
            import re as _re
            m = _re.search(r"\[.*\]", raw, _re.DOTALL)
            if not m:
                return []
            try:
                data = _json.loads(m.group())
            except Exception:
                return []

        # LLM 可能把数组包在对象里（如 {"scenes": [...]}）
        # 优先取 "scenes" 键，避免 next(values()) 误取其他 list 字段
        if isinstance(data, dict):
            if isinstance(data.get("scenes"), list):
                data = data["scenes"]
            else:
                data = next((v for v in data.values() if isinstance(v, list)), [])
        if not isinstance(data, list):
            return []

        valid: list[dict] = []
        for s in data:
            if not isinstance(s, dict):
                continue
            name = str(s.get("name") or "").strip()[:50]
            if not name:
                continue
            entities = s.get("entities") or []
            if not isinstance(entities, list) or not entities:
                continue
            # 过滤无效 entity
            clean_entities = [
                e for e in entities
                if isinstance(e, dict)
                and str(e.get("entity_id", "")).strip()
                and "." in str(e.get("entity_id", ""))
            ]
            if not clean_entities:
                continue
            raw_mask = str(s.get("weekday_mask", "0123456"))
            mask = "".join(c for c in raw_mask if c in "0123456") or "0123456"
            valid.append({
                "name": name,
                "description": str(s.get("description") or "")[:100],
                "trigger": str(s.get("trigger") or "")[:120],
                "room": str(s.get("room") or "")[:30],
                "hour_start": max(0, min(23, int(s.get("hour_start") or 0))),
                "hour_end": max(0, min(23, int(s.get("hour_end") or 23))),
                "weekday_mask": mask,
                "entities": clean_entities,
                "confidence": min(90, max(50, int(s.get("confidence") or 65))),
            })
        return valid[:8]

    def _save_llm_discovered_scenes(self, scenes: list[dict]) -> None:
        """将 LLM 发现的语义场景写入 ai_scenes 表（在 executor 线程中调用）。

        使用 source='llm' 以区别统计共现产生的 source='auto' 场景。
        已存在 active/rejected 状态的同名场景不覆盖。
        """
        import json as _json
        from datetime import datetime as _dt

        now_ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        saved = 0
        for scene in scenes:
            try:
                name = scene["name"]
                entities_json = _json.dumps(scene["entities"], ensure_ascii=False)
                trigger_context = scene.get("trigger") or f"{scene['hour_start']:02d}时"
                description = scene.get("description") or trigger_context

                rows = self._db.query(
                    "SELECT id, status FROM ai_scenes WHERE name=?", (name,)
                )
                if rows:
                    existing = rows[0]
                    if existing["status"] in ("active", "rejected"):
                        _ok = self._db_exec(
                            "UPDATE ai_scenes SET hit_count=hit_count+1, updated=? WHERE name=?",
                            (now_ts, name),
                        )
                        if not _ok:
                            _LOGGER.warning("[LLM场景发现] 命中计数更新失败: name=%s status=%s", name, existing["status"])
                            continue
                    else:
                        _ok = self._db_exec(
                            "UPDATE ai_scenes SET description=?, entities_json=?, "
                            "trigger_context=?, hour_start=?, hour_end=?, weekday_mask=?, "
                            "confidence=?, source='llm', updated=? WHERE name=?",
                            (
                                description, entities_json, trigger_context,
                                scene["hour_start"], scene["hour_end"], scene["weekday_mask"],
                                scene["confidence"], now_ts, name,
                            ),
                        )
                        if not _ok:
                            _LOGGER.warning("[LLM场景发现] 场景更新失败: name=%s", name)
                            continue
                else:
                    _ok = self._db_exec(
                        "INSERT INTO ai_scenes "
                        "(name,description,entities_json,trigger_context,"
                        "hour_start,hour_end,weekday_mask,confidence,hit_count,"
                        "status,source,created,updated) "
                        "VALUES (?,?,?,?,?,?,?,?,0,'pending','llm',?,?)",
                        (
                            name, description, entities_json, trigger_context,
                            scene["hour_start"], scene["hour_end"], scene["weekday_mask"],
                            scene["confidence"], now_ts, now_ts,
                        ),
                    )
                    if not _ok:
                        _LOGGER.warning("[LLM场景发现] 场景插入失败: name=%s", name)
                        continue
                saved += 1
            except Exception as exc:
                _LOGGER.warning("[LLM场景发现] 场景写入失败 (%s): %s", scene.get("name"), exc)
        if saved:
            _LOGGER.info("[LLM场景发现] 已写入 %d 个 LLM 语义场景到 ai_scenes", saved)

    def _parse_llm_behavior_patterns(self, raw: str) -> list[dict]:
        """解析 LLM 返回的行为规律 JSON，返回有效规律列表。"""
        import json as _json
        try:
            data = _json.loads(raw)
            if isinstance(data, list):
                candidates = data
            elif isinstance(data, dict):
                # 可能被包在任意 key 下（如 {"patterns": [...]}）
                candidates = next(
                    (v for v in data.values() if isinstance(v, list)), []
                )
            else:
                return []

            valid: list[dict] = []
            for p in candidates:
                if not isinstance(p, dict):
                    continue
                eid = str(p.get("entity_id", "")).strip()
                state = str(p.get("expected_state", "")).strip()
                if not eid or not state or "." not in eid:
                    continue
                # weekday_mask 归一化：只保留 0-6 的数字字符
                raw_mask = str(p.get("weekday_mask", "0123456"))
                mask = "".join(c for c in raw_mask if c in "0123456") or "0123456"
                valid.append({
                    "entity_id": eid,
                    "expected_state": state,
                    "hour_start": max(0, min(23, int(p.get("hour_start", 0)))),
                    "hour_end": max(0, min(23, int(p.get("hour_end", 23)))),
                    "weekday_mask": mask,
                    "confidence": min(90, max(50, int(p.get("confidence", 65)))),
                    "reason": str(p.get("reason", "LLM提炼"))[:100],
                })
            return valid
        except Exception as exc:
            _LOGGER.warning("[PatrolMixin] _parse_llm_behavior_patterns 解析失败: %s", exc)
            return []

    def _save_llm_patterns(self, patterns: list[dict]) -> None:
        """将 LLM 提炼的行为规律写入 behavior_patterns 表（在 executor 线程中调用）。"""
        from datetime import datetime as _dt
        now_ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        saved = 0
        for p in patterns:
            try:
                _ok = self._db_exec(
                    "INSERT OR REPLACE INTO behavior_patterns "
                    "(entity_id, expected_state, hour_start, hour_end, weekday_mask, "
                    "confidence, hit_count, last_updated, last_reinforced) "
                    "VALUES (?,?,?,?,?,?,0,?,?)",
                    (
                        p["entity_id"], p["expected_state"],
                        p["hour_start"], p["hour_end"],
                        p["weekday_mask"], p["confidence"],
                        now_ts, now_ts,
                    ),
                )
                if not _ok:
                    _LOGGER.warning(
                        "[PatrolMixin] LLM 行为规律写入失败: entity=%s state=%s",
                        p.get("entity_id"),
                        p.get("expected_state"),
                    )
                    continue
                saved += 1
            except Exception as e:
                _LOGGER.warning("[PatrolMixin] LLM 行为规律写入失败: %s", e)
        if saved:
            self._refresh_behavior_patterns_cache()
            _LOGGER.info("[PatrolMixin] LLM 行为规律已写入 %d 条", saved)

    def _scheduled_memory_decay_maintenance(self) -> None:
        """
        Phase 7C: 每日定时执行认知记忆衰减维护。

        包含：
          - 更新 corrections 表的 decay_score
          - 清除得分极低的弱修正记录（防止过时记忆干扰）
          - 将高权重强修正自动升级为 P1 锁定规则
          - 对长期未命中的行为模式降低置信度
          - 删除过时的低置信度行为模式
        """
        self._sys_log("INFO", "[记忆衰减] 开始每日认知记忆维护...")
        try:
            report = self._run_memory_decay_maintenance()
            promoted = report.get("corrections_promoted", 0)
            downgraded = report.get("rules_downgraded", 0)
            deleted = report.get("rules_deleted", 0)
            self._sys_log(
                "INFO",
                f"[记忆衰减] 维护完成 | "
                f"修正更新={report['corrections_updated']} "
                f"修正清除={report['corrections_pruned']} "
                f"规则升级P1={promoted} 规则降级P3={downgraded} 规则删除={deleted} "
                f"模式衰减={report['patterns_decayed']} "
                f"模式清除={report['patterns_pruned']}"
            )
            if promoted > 0:
                self._sys_log("WARN",
                    f"[记忆强化] ⚠️ {promoted} 条用户修正已自动升级为 P1 铁律规则")
            if downgraded > 0:
                self._sys_log("INFO",
                    f"[记忆衰减] 📉 {downgraded} 条 P1 规则因修正记忆衰减，已降级为 P3 普通规则")
            if deleted > 0:
                self._sys_log("INFO",
                    f"[记忆衰减] 🗑️ {deleted} 条过时自动规则已删除（用户行为已发生变化）")
        except Exception as e:
            self._sys_log("ERROR", f"[记忆衰减] 维护异常: {e}")

    def _analyze_patterns(self) -> None:
        """
        每天凌晨 3 点自动调用（通过 executor 运行），统计历史行为规律并生成摘要。
        包含：活跃时段、用户覆盖频率、AI 执行次数、到家时间规律、行为模式写入 behavior_patterns。
        """
        self._cleanup_old_memory()
        row = self._query_events(
            "SELECT COUNT(*) AS cnt, COUNT(DISTINCT substr(time,1,10)) AS days FROM events",
            max_rows=0,
        )
        total = row[0]["cnt"] if row else 0
        days_covered = row[0]["days"] if row else 0
        if total < 20:
            self._pattern_summary = (
                f"历史数据不足（{total} 条/{days_covered} 天）。"
                f"AI 场景需要至少 20 条事件和 2 天数据，请保持系统正常运行积累数据。"
            )
            self._save_pattern_summary(self._pattern_summary)
            self._sys_log("INFO", f"[行为分析] {self._pattern_summary}")
            return

        parts = [f"统计周期 {days_covered} 天，共 {total} 条事件"]

        # 最活跃时段 TOP3
        trigger_rows = self._query_events(
            "SELECT CAST(substr(time,12,2) AS INTEGER) AS h, COUNT(*) AS cnt "
            "FROM events WHERE type='Trigger' GROUP BY h ORDER BY cnt DESC LIMIT 3",
            max_rows=0,
        )
        if trigger_rows:
            parts.append("家中最活跃时段：" + "/".join(str(r["h"]) + "时" for r in trigger_rows))

        # 用户覆盖（手动推翻 AI）的高发时段
        override_rows = self._query_events(
            "SELECT CAST(substr(time,12,2) AS INTEGER) AS h FROM events WHERE type='Override'"
        )
        if override_rows:
            override_hours = [r["h"] for r in override_rows]
            top_hour, top_count = Counter(override_hours).most_common(1)[0]
            parts.append(
                f"主人最常在 {top_hour}:00 手动推翻AI决策（共{top_count}次）"
                f"——AI 在该时段应主动降低置信度"
            )

        # AI 累计执行次数
        ai_rows = self._query_events(
            "SELECT COUNT(*) AS cnt FROM events WHERE type='AI_Action'",
            max_rows=0,
        )
        ai_count = ai_rows[0]["cnt"] if ai_rows else 0
        if ai_count:
            parts.append(f"AI 累计自动执行了 {ai_count} 次操作")

        # 到家时间规律分析
        arrival_rows = self._query_events(
            "SELECT CAST(substr(time,12,2) AS INTEGER) AS h, "
            "CAST(substr(time,15,2) AS INTEGER) AS m, "
            "CAST(strftime('%w', time) AS INTEGER) AS wd "
            "FROM events WHERE type='Trigger' "
            "AND (entity LIKE 'person.%' OR entity LIKE 'device_tracker.%') "
            "AND state='home'"
        )
        if arrival_rows and len(arrival_rows) >= 3:
            wd_arrivals = [r for r in arrival_rows if r["wd"] not in (0, 6)]
            we_arrivals = [r for r in arrival_rows if r["wd"] in (0, 6)]
            for label, rows in [("工作日", wd_arrivals), ("休息日", we_arrivals)]:
                if len(rows) >= 2:
                    hours = [r["h"] * 60 + r["m"] for r in rows]
                    avg_min = sum(hours) // len(hours)
                    avg_h, avg_m = divmod(avg_min, 60)
                    earliest = min(hours)
                    e_h, e_m = divmod(earliest, 60)
                    parts.append(
                        f"{label}主人通常 {avg_h}:{avg_m:02d} 左右到家"
                        f"（最早 {e_h}:{e_m:02d}，共{len(rows)}次记录）"
                    )

        # 到家前习惯分析（主人是否习惯提前远程开空调等）
        pre_arrival_rows = self._query_events(
            "SELECT e2.entity, COUNT(*) AS cnt FROM events e1 "
            "JOIN events e2 ON e2.time BETWEEN datetime(e1.time, '-30 minutes') AND e1.time "
            "WHERE e1.type='Trigger' "
            "AND (e1.entity LIKE 'person.%' OR e1.entity LIKE 'device_tracker.%') "
            "AND e1.state='home' "
            "AND e2.type IN ('AI_Action','Trigger','Override','Learning') "
            "AND (e2.entity LIKE 'climate.%' OR e2.entity LIKE 'light.%' OR e2.entity LIKE 'switch.%') "
            "AND e2.state='on' "
            "GROUP BY e2.entity HAVING cnt >= 2 "
            "ORDER BY cnt DESC LIMIT 3",
            max_rows=0,
        )
        if pre_arrival_rows:
            for r in pre_arrival_rows:
                name = self.device_info.get(r["entity"], {}).get("name", r["entity"])
                parts.append(f"主人回家前经常提前开启{name}（{r['cnt']}次）")

        # 提取行为规律写入 behavior_patterns
        # 5D-2: AI_Action 样本仅使用 verified=1 且 success=1 的执行结果，避免失败动作污染习惯学习
        verified_ai_rows = self._get_verified_success_ai_actions(days=60)
        verified_ai_map: dict[tuple[str, str, int, int], int] = {
            (r["entity"], r["state"], r["h"], r["wd"]): int(r.get("cnt") or 0)
            for r in verified_ai_rows
        }
        verified_ai_entity_hour_wd = {
            (r["entity"], r["h"], r["wd"]) for r in verified_ai_rows
        }
        pattern_rows = self._query_events(
            "SELECT entity, state, CAST(substr(time,12,2) AS INTEGER) AS h, "
            "CAST(strftime('%w', time) AS INTEGER) AS wd, COUNT(*) AS cnt "
            "FROM events WHERE type IN ('Trigger','AI_Action','Override','Learning') AND entity != '' "
            "AND (entity LIKE 'light.%' OR entity LIKE 'switch.%' OR entity LIKE 'climate.%' "
            "OR entity LIKE 'cover.%' OR entity LIKE 'fan.%') "
            "GROUP BY entity, state, h, wd",
            max_rows=0,
        )
        agg: dict[tuple, list[tuple[str, int]]] = defaultdict(list)
        filtered_ai_drop = 0
        for r in pattern_rows:
            if verified_ai_map:
                key_ai = (r["entity"], r["state"], r["h"], r["wd"])
                key_entity_hour_wd = (r["entity"], r["h"], r["wd"])
                # 若该实体在该时段有验证样本，则仅保留 verified+success 的状态口径
                if key_entity_hour_wd in verified_ai_entity_hour_wd and verified_ai_map.get(key_ai, 0) <= 0:
                    filtered_ai_drop += int(r.get("cnt") or 0)
                    continue
            key = (r["entity"], r["h"], r["wd"])
            agg[key].append((r["state"], r["cnt"]))
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        patterns_written = 0
        for (entity_id, hour, wd), state_counts in agg.items():
            total_cnt = sum(c for _, c in state_counts)
            if total_cnt < 3:
                continue
            best_state, best_cnt = max(state_counts, key=lambda x: x[1])
            if best_cnt / total_cnt < 0.6:
                continue
            confidence = min(90, 50 + 5 * (best_cnt - 3))
            weekday_mask = str(wd)
            try:
                _ok = self._db_exec(
                    "INSERT OR REPLACE INTO behavior_patterns "
                    "(entity_id, expected_state, hour_start, hour_end, weekday_mask, confidence, hit_count, last_updated, last_reinforced) "
                    "VALUES (?,?,?,?,?,?,0,?,?)",
                    (entity_id, best_state, hour, hour, weekday_mask, confidence, now_ts, now_ts),
                )
                if not _ok:
                    _LOGGER.warning(
                        "[PatrolMixin] Upsert pattern write failed: entity=%s hour=%s wd=%s state=%s",
                        entity_id,
                        hour,
                        wd,
                        best_state,
                    )
                    continue
                patterns_written += 1
            except Exception as e:
                _LOGGER.warning("[PatrolMixin] Upsert pattern failed: %s", e)
        if patterns_written:
            self._sys_log("INFO", f"[行为分析] 已提取 {patterns_written} 条习惯规律写入 behavior_patterns")
            self._refresh_behavior_patterns_cache()
        if filtered_ai_drop > 0:
            self._sys_log("INFO", f"[行为分析] 已过滤 {filtered_ai_drop} 条未通过验证的 AI_Action 统计样本")

        self._pattern_summary = "；".join(parts) + "。"
        self._save_pattern_summary(self._pattern_summary)
        self._sys_log("INFO", f"[行为分析] {self._pattern_summary}")

        # Phase 4: 多设备联动规律 → 候选场景
        self._generate_candidate_scenes()

        # P1-1: 每日凌晨触发本地模型重训练（原为每周日）
        try:
            self._sys_log("INFO", "[ML训练] 每日定期触发本地决策树重训练...")
            from .model_trainer import LocalModelTrainer, resolve_model_path
            _mp = resolve_model_path(getattr(self, "_config_dir", None))
            trainer = LocalModelTrainer(self._query_events, model_path=_mp)
            success = trainer.train()
            if success:
                self._sys_log("INFO", f"[ML训练] 本地个性化模型训练完成 → {_mp}")
            else:
                self._sys_log("INFO", "[ML训练] 样本不足，本次跳过训练（需 ≥50 条已验证样本）")
        except Exception as _ml_exc:
            self._sys_log("WARN", f"[ML训练] 训练异常（不影响系统运行）: {_ml_exc}")

    # ── Phase 4: 多设备共现检测 + 场景生成引擎 ───────────────────────────────

    def _detect_cooccurrence_patterns(self) -> list[dict]:
        """检测多设备联动规律：在同一时间窗口内高频同时出现的设备组合。

        算法升级（v4.8.37）：
        ─────────────────────────────────────────────────────────────────────
        原算法的两大缺陷已修复：

        缺陷 1 ► 按具体星期（周一=1, 周二=2...）分组
          问题：周一和周二是同一习惯，但被视为不同组，永远凑不到 2 天。
          修复：改为按「工作日」vs「休息日」两类分组，工作日任意一天都算同类。

        缺陷 2 ► 要求完全相同的设备集合（frozenset 精确匹配）
          问题：周一开 A+B+C，周二开 A+B（习惯稍有差异），frozenset 不同 → 永不匹配。
          修复：子集拓展——对每个桶中的设备组合，提取所有大小 ≥ MIN_DEVICES 的子集，
                并在聚合时为每个子集计票。A+B 在多天中都出现就能达到阈值。

        其他改进：
          - 按每个设备在各匹配日期中的「多数状态」确定场景建议状态（取 on/off 中出现多的）
          - 添加诊断日志，帮助用户了解为什么还没有生成场景
        ─────────────────────────────────────────────────────────────────────

        事件来源：AI_Action / Trigger / Override / Learning（含用户操作和 HA 自动化触发，
        都代表真实用量模式，对模型训练和传感器故障兜底同样有价值）。

        展示区过滤（v4.11.14）：
          如果某个设备所在区域的角色为 ZONE_ROLE_DISPLAY（展示区），则它受展厅规则自动控制，
          不代表真实用户习惯。当候选场景中 >50% 的设备属于展示区时，跳过该候选，
          避免将"每天开店时开展板射灯"这类规则行为误识别为用户习惯场景。
        """
        import itertools as _iter
        from .const import (
            AI_SCENE_COOCCUR_WINDOW_MIN,
            AI_SCENE_MIN_DATES,
            AI_SCENE_MIN_DEVICES,
            ZONE_ROLE_DISPLAY,
        )

        # 预构建 entity_id → area_name 映射（在 executor 线程中调用，HA registry 读取是线程安全的）
        _entity_area_cache: dict[str, str] = {}

        rows = self._query_events(
            "SELECT substr(time,1,10) AS date, "
            "CAST(substr(time,12,2) AS INTEGER) AS h, "
            f"CAST(CAST(substr(time,15,2) AS INTEGER)/{max(1, int(AI_SCENE_COOCCUR_WINDOW_MIN))} AS INTEGER) AS slot, "
            "CAST(strftime('%w', time) AS INTEGER) AS wd, "
            "entity, state "
            "FROM events WHERE type IN ('Trigger','Override','Learning') "
            "AND entity != '' AND ("
            "entity LIKE 'light.%' OR entity LIKE 'switch.%' OR "
            "entity LIKE 'climate.%' OR entity LIKE 'cover.%' OR entity LIKE 'fan.%'"
            ") ORDER BY time"
        )
        total_rows = len(rows)
        if total_rows < 10:
            self._sys_log("INFO",
                f"[AI场景] 共现检测：原始事件 {total_rows} 条（< 10），数据不足，跳过场景生成")
            return []

        # ── 早期展示区过滤：在组合爆炸之前剔除展示区设备 ─────────────────────
        # 展示区设备由展厅规则自动控制（营业时间开/关），不代表用户真实习惯。
        # 在事件数据阶段提前排除，可大幅减少后续组合数量（从数十万→数千），
        # 避免 CPU 浪费和日志膨胀。
        display_zone_eids: set[str] = set()
        all_eids_in_rows = set(r["entity"] for r in rows)
        for eid_chk in all_eids_in_rows:
            if eid_chk not in _entity_area_cache:
                _entity_area_cache[eid_chk] = self._get_entity_area(eid_chk)
            area_chk = _entity_area_cache[eid_chk]
            if area_chk and self.get_zone_role(area_chk) == ZONE_ROLE_DISPLAY:
                display_zone_eids.add(eid_chk)
        if display_zone_eids:
            rows = [r for r in rows if r["entity"] not in display_zone_eids]
            self._sys_log("INFO",
                f"[AI场景] 早期过滤：排除 {len(display_zone_eids)} 个展示区设备"
                f"，剩余事件 {len(rows)} 条（减少 {total_rows - len(rows)} 条）")
            total_rows = len(rows)
            if total_rows < 10:
                self._sys_log("INFO", "[AI场景] 排除展示区后事件不足 10 条，跳过场景生成")
                return []

        # ── 分桶：(date, h, slot) → {entity: 多数状态} ───────────────────────
        # 同一桶内同一设备可能出现多次（on/off 变化），保留最后一个状态（代表最终状态）
        buckets: dict[tuple, dict] = defaultdict(dict)
        bucket_wd: dict[tuple, int] = {}
        for r in rows:
            key = (r["date"], r["h"], r["slot"])
            buckets[key][r["entity"]] = r["state"]
            bucket_wd[key] = r["wd"]

        valid_buckets = sum(1 for v in buckets.values() if len(v) >= AI_SCENE_MIN_DEVICES)
        self._sys_log("INFO",
            f"[AI场景] 共现检测：{total_rows} 条事件 → {len(buckets)} 个时间槽"
            f"，其中 {valid_buckets} 个槽含 ≥{AI_SCENE_MIN_DEVICES} 台设备")

        if valid_buckets == 0:
            self._sys_log("INFO",
                "[AI场景] 共现检测：没有任何时间槽中有多台设备同时活跃，"
                "请确保多个设备在相近时间（同一窗口内）被操作")
            return []

        # ── 聚合：(hour_range_2h, wd_type) → {frozenset_eids → {date: {eid: [states]}}} ──
        # 修复 1：按「工作日/休息日」而非具体星期（0-6）分组
        #         这样周一 + 周二同一习惯可以合计，不再需要在同一天（如两个周一）重复出现
        # 修复 2：子集拓展——每个含 N 台设备的桶，展开为所有大小 2~min(N,4) 的子集
        #         这样「周一 A+B+C」和「周二 A+B」都能贡献到 A+B 的计数
        MAX_SUBSET_SIZE = 4   # 子集拓展上限，防止大场景组合爆炸
        # wd_type: 0 = 休息日（周日/周六），1 = 工作日（周一~周五）
        # pattern_votes[(hour_range, wd_type)][frozenset_eids][date][eid] = [state1, state2...]
        pattern_votes: dict = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        )

        for key, dev_states in buckets.items():
            date, hour, _ = key
            raw_wd = bucket_wd.get(key, 1)   # SQLite %w: 0=Sun, 1=Mon...6=Sat
            wd_type = 0 if raw_wd in (0, 6) else 1  # 0=休息日, 1=工作日
            hour_range = (hour // 2) * 2             # 归并到 2 小时段

            eids = list(dev_states.keys())
            n = len(eids)
            if n < AI_SCENE_MIN_DEVICES:
                continue

            # 子集拓展：产生所有大小 MIN_DEVICES ~ min(n, MAX_SUBSET_SIZE) 的子集
            max_sz = min(n, MAX_SUBSET_SIZE)
            for sz in range(AI_SCENE_MIN_DEVICES, max_sz + 1):
                for combo in _iter.combinations(eids, sz):
                    fs = frozenset(combo)
                    for eid in combo:
                        pattern_votes[(hour_range, wd_type)][fs][date][eid].append(
                            dev_states[eid]
                        )

        # ── 筛选达到阈值的候选场景 ────────────────────────────────────────────
        below_threshold = 0
        candidates: list[dict] = []

        for (hour_range, wd_type), fs_dates in pattern_votes.items():
            wd_label = "休息日" if wd_type == 0 else "工作日"
            wd_mask  = "06"    if wd_type == 0 else "12345"

            for fs_eids, date_eid_states in fs_dates.items():
                date_count = len(date_eid_states)
                if date_count < AI_SCENE_MIN_DATES:
                    below_threshold += 1
                    continue

                dev_count = len(fs_eids)
                if dev_count < AI_SCENE_MIN_DEVICES:
                    continue

                # 每台设备取多数状态（在所有匹配日期中出现次数最多的状态）
                entities = []
                for eid in sorted(fs_eids):
                    all_states: list[str] = []
                    for date_states in date_eid_states.values():
                        all_states.extend(date_states.get(eid, []))
                    if not all_states:
                        continue
                    majority_state = Counter(all_states).most_common(1)[0][0]
                    entities.append({"entity_id": eid, "state": majority_state})

                if len(entities) < AI_SCENE_MIN_DEVICES:
                    continue

                # ── 展示区过滤：跳过由展厅规则自动驱动的模式 ────────────────────
                # 展示区设备每天按营业时间自动开关，产生的 events 记录不代表用户真实习惯
                display_count = 0
                for e in entities:
                    eid = e["entity_id"]
                    if eid not in _entity_area_cache:
                        _entity_area_cache[eid] = self._get_entity_area(eid)
                    area_name = _entity_area_cache[eid]
                    if area_name and self.get_zone_role(area_name) == ZONE_ROLE_DISPLAY:
                        display_count += 1
                if display_count > len(entities) // 2:
                    self._sys_log("DEBUG",
                        f"[AI场景] 跳过展示区主导候选：{[e['entity_id'] for e in entities]}"
                        f"（{display_count}/{len(entities)} 台设备在展示区，由展厅规则控制）"
                    )
                    continue

                # 置信度：基础 40 + 日期贡献 + 设备数贡献
                confidence = min(95, 40 + date_count * 8 + dev_count * 5)
                candidates.append({
                    "entities": entities,
                    "hour_start": hour_range,
                    "hour_end": min(23, hour_range + 2),
                    "wd_label": wd_label,
                    "weekday_mask": wd_mask,
                    "confidence": confidence,
                    "hit_count": date_count,
                })

        self._sys_log("INFO",
            f"[AI场景] 共现检测完成：候选 {len(candidates)} 个"
            f"，{below_threshold} 个模式因出现天数不足 {AI_SCENE_MIN_DATES} 天被过滤"
            + (f"（提示：继续正常使用 {AI_SCENE_MIN_DATES - 1} 天后即可生成场景）"
               if below_threshold > 0 and len(candidates) == 0 else "")
        )

        # ── 去重：同一组设备 + 同一工作日类型只保留置信度最高的 ─────────────────
        seen: dict[tuple[frozenset, str], dict] = {}
        for cand in sorted(candidates, key=lambda x: -x["confidence"]):
            key_fs = frozenset(e["entity_id"] for e in cand["entities"])
            dedup_key = (key_fs, cand.get("weekday_mask", "0123456"))
            if dedup_key not in seen:
                seen[dedup_key] = cand
        return list(seen.values())

    def _generate_candidate_scenes(self) -> None:
        """将共现规律转化为候选场景写入 ai_scenes 表，并刷新内存缓存。

        Bug 修复（v4.11.17）：
          - 原实现对每个候选都执行 SELECT+INSERT/UPDATE，31万候选 = 31万次 DB 操作
          - 根本原因：场景名只有"时段+星期+设备域"，最多240个唯一名字，
            31万候选反复 upsert 同一行，造成巨量无意义 I/O
          - 修复：先按场景名去重（保留置信度最高的候选），再写入 DB
          - 加入 AI_SCENE_MAX_PER_RUN 安全上限，防止极端情况下数据库膨胀
        """
        import json as _json
        from .const import AI_SCENE_CONFIDENCE_THRESHOLD, AI_SCENE_MAX_PER_RUN

        candidates = self._detect_cooccurrence_patterns()
        if not candidates:
            self._sys_log("INFO",
                "[AI场景] 未找到满足条件的设备共现规律，暂不生成候选场景。"
                "可在「面板 → AI 场景」中手动触发分析，或等待次日凌晨自动分析。"
            )
            return

        # ── Step 1：置信度过滤 ────────────────────────────────────────────────
        before_filter = len(candidates)
        candidates = [c for c in candidates if c["confidence"] >= AI_SCENE_CONFIDENCE_THRESHOLD]
        below_conf = before_filter - len(candidates)
        if below_conf:
            self._sys_log("INFO",
                f"[AI场景] {below_conf} 个候选因置信度 < {AI_SCENE_CONFIDENCE_THRESHOLD} 被过滤"
                f"（需要在更多天重复出现才能提升置信度）"
            )

        # ── Step 2：按场景名去重（关键 Bug 修复）────────────────────────────────
        # 场景名 = "AI_{时段}{星期}{设备域}联动"，最多只有约 240 个唯一值。
        # 原代码对 31 万候选逐一写入，对同一 name 反复 SELECT+UPDATE，
        # 造成数十万次无意义 DB 操作。现在先去重，每个 name 只保留置信度最高的候选。
        domain_cn_map = {"light": "灯光", "switch": "开关", "climate": "空调",
                         "cover": "窗帘", "fan": "风扇"}

        def _scene_space_label(cand: dict) -> str:
            room_counter: Counter[str] = Counter()
            for e in cand.get("entities", []):
                eid = e.get("entity_id", "")
                if not eid:
                    continue
                if eid not in _entity_area_cache:
                    _entity_area_cache[eid] = self._get_entity_area(eid)
                area = (_entity_area_cache.get(eid) or "").strip()
                room_counter[area or "未分区"] += 1
            if not room_counter:
                return "未分区"
            if len(room_counter) == 1:
                return room_counter.most_common(1)[0][0]
            return "跨房间"

        name_best: dict[str, dict] = {}
        for cand in sorted(candidates, key=lambda x: -x["confidence"]):
            entity_domains = Counter(e["entity_id"].split(".")[0] for e in cand["entities"])
            dominant_domain = entity_domains.most_common(1)[0][0]
            domain_cn = domain_cn_map.get(dominant_domain, dominant_domain)
            hour_label = f"{cand['hour_start']:02d}点"
            scene_space = _scene_space_label(cand)
            scene_name = f"AI_{hour_label}{cand['wd_label']}{scene_space}{domain_cn}联动"
            if scene_name not in name_best:
                name_best[scene_name] = cand  # 已按置信度排序，第一个即最优

        total_unique = len(name_best)
        if total_unique != before_filter:
            self._sys_log("INFO",
                f"[AI场景] 场景名去重：{before_filter} 个候选 → {total_unique} 个唯一场景名"
                f"（避免了 {before_filter - total_unique} 次重复 DB 写入）"
            )

        # ── Step 3：安全上限截断 ─────────────────────────────────────────────
        if total_unique > AI_SCENE_MAX_PER_RUN:
            # 按置信度倒序截取前 N 个
            sorted_scenes = sorted(name_best.items(), key=lambda kv: -kv[1]["confidence"])
            name_best = dict(sorted_scenes[:AI_SCENE_MAX_PER_RUN])
            self._sys_log("INFO",
                f"[AI场景] 超出单次上限 {AI_SCENE_MAX_PER_RUN}，截取置信度最高的 {AI_SCENE_MAX_PER_RUN} 个"
            )

        # ── Step 4：写入 DB ──────────────────────────────────────────────────
        generated = 0
        for scene_name, cand in name_best.items():
            # 生成描述
            entity_descs = []
            for e in cand["entities"]:
                dev_name = self.device_info.get(e["entity_id"], {}).get("name", e["entity_id"])
                state_cn = "开" if e["state"] in ("on", "open", "heat", "cool", "auto") else "关"
                entity_descs.append(f"{dev_name} → {state_cn}")
            hour_label = f"{cand['hour_start']:02d}点"
            description = (
                f"在 {hour_label}–{cand['hour_end']:02d}点{cand['wd_label']}，"
                f"历史 {cand['hit_count']} 次自动触发：{'，'.join(entity_descs)}"
            )
            trigger_context = f"{hour_label} {cand['wd_label']}"

            actions = entities_to_actions(
                cand["entities"],
                device_info=self.device_info,
                on_states=("on", "open", "heat", "cool", "auto"),
            )

            self._upsert_ai_scene(
                name=scene_name,
                description=description,
                entities_json=_json.dumps(cand["entities"], ensure_ascii=False),
                actions_json=_json.dumps(actions, ensure_ascii=False),
                trigger_context=trigger_context,
                hour_start=cand["hour_start"],
                hour_end=cand["hour_end"],
                weekday_mask=cand["weekday_mask"],
                confidence=cand["confidence"],
                hit_count=cand["hit_count"],
            )
            generated += 1

        if generated:
            self._sys_log("INFO", f"[行为分析] Phase 4: 生成/更新 {generated} 个候选 AI 场景，等待用户确认")
            # 刷新内存缓存
            self._ai_scenes_cache = self._query_ai_scenes()
            # 推送 HA 持久通知，提醒用户前往面板确认
            self._notify_new_ai_scenes(generated)

    def _notify_new_ai_scenes(self, count: int) -> None:
        """推送 HA persistent_notification，提醒用户查看新候选 AI 场景。

        此方法可能从 executor 线程调用（_analyze_patterns 在 executor 中执行），
        必须使用 call_soon_threadsafe 安全调度回事件循环，不能直接调用 async_create_task。
        """
        title = f"SmartAgent 发现 {count} 个新场景规律"
        message = (
            f"SmartAgent 从您的历史行为中挖掘出 **{count}** 个设备联动规律，"
            f"已生成为候选场景，等待您确认。\n\n"
            f"请前往 **SmartAgent 面板 → AI 场景** 标签页查看、确认或拒绝。"
        )
        notify_data = {
            "title": title,
            "message": message,
            "notification_id": "smart_agent_new_ai_scenes",
        }
        try:
            self.hass.loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(
                    async_call_service(
                        self.hass,
                        "persistent_notification", "create", notify_data
                    )
                )
            )
        except Exception as exc:
            self._sys_log("WARN", f"[AI场景] 推送通知失败: {exc}")

    # ── 到家预测 ──────────────────────────────────────────────────────────────

    def _get_arrival_prediction(self) -> str:
        """Predict if the user is about to arrive home based on historical patterns."""
        now = datetime.now()
        current_min = now.hour * 60 + now.minute
        is_weekday = now.weekday() < 5
        # SAFETY: wd_filter 仅取两个硬编码字面量，无用户输入，不存在注入风险
        wd_filter = "AND CAST(strftime('%w', time) AS INTEGER) NOT IN (0,6)" if is_weekday else "AND CAST(strftime('%w', time) AS INTEGER) IN (0,6)"

        rows = self._query_events(
            f"SELECT CAST(substr(time,12,2) AS INTEGER) AS h, "
            f"CAST(substr(time,15,2) AS INTEGER) AS m "
            f"FROM events WHERE type='Trigger' "
            f"AND detail LIKE '%home%' {wd_filter} "
            f"AND time > ? ORDER BY id DESC LIMIT 30",
            ((datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"),),
            max_rows=0,
        )
        if len(rows) < 5:
            return ""
        arrival_mins = [r["h"] * 60 + r["m"] for r in rows]
        avg = sum(arrival_mins) / len(arrival_mins)
        spread = (sum((x - avg) ** 2 for x in arrival_mins) / len(arrival_mins)) ** 0.5
        if spread > 90:
            return ""
        diff = avg - current_min
        if 0 <= diff <= 45:
            return f"根据历史规律，主人通常在约 {int(avg // 60):02d}:{int(avg % 60):02d} 到家（±{int(spread)}min），请提前准备。"
        if -15 <= diff < 0:
            return f"主人可能正在回家途中（历史平均到家时间 {int(avg // 60):02d}:{int(avg % 60):02d}）。"
        return ""

    # ── 习惯主动建议 ──────────────────────────────────────────────────────────

    def _schedule_next_habit_check(self) -> None:
        from .const import HABIT_CHECK_INTERVAL_MIN
        if self._habit_check_timer_unsub:
            try:
                self._habit_check_timer_unsub()
            except Exception as exc:
                _LOGGER.debug("[Patrol] 取消习惯检查计时器失败: %s", exc)
        self._habit_check_timer_unsub = async_call_later(
            self.hass, HABIT_CHECK_INTERVAL_MIN * 60, self._on_habit_check_timer
        )

    @callback
    def _on_habit_check_timer(self, _now: Any) -> None:
        self._habit_check_timer_unsub = None
        if self._habit_proactive:
            self.hass.async_create_task(self._run_habit_proactive_check())
        self._schedule_next_habit_check()

    @callback
    def _on_habit_suggest_timeout(self, _now: Any) -> None:
        """习惯建议超时：取消并清空待确认建议。"""
        self._habit_suggest_timeout_handle = None
        if self._pending_habit_suggestion:
            self._sys_log("INFO", "[习惯询问] 超时未确认，已取消")
            self._pending_habit_suggestion = None

    async def _run_habit_proactive_check(self) -> None:
        """定时习惯检查：匹配当前时段与星期的行为规律，若设备状态与习惯不符则询问用户。"""
        from .const import HABIT_SUGGEST_COOLDOWN_SEC, HABIT_SUGGEST_TIMEOUT_SEC
        if not self._habit_proactive:
            return
        if self._learning_mode:
            return
        if self._pending_habit_suggestion:
            return
        now = datetime.now()
        hour = now.hour
        # SQLite %w: 0=Sun, 1=Mon, ..., 6=Sat. Python weekday(): 0=Mon, 6=Sun -> (weekday()+1)%7
        wd = (now.weekday() + 1) % 7
        rows = await self.hass.async_add_executor_job(
            self._query_events,
            "SELECT entity_id, expected_state, confidence FROM behavior_patterns "
            "WHERE hour_start <= ? AND hour_end >= ? AND weekday_mask LIKE ? AND confidence >= 60 "
            "ORDER BY confidence DESC",
            (hour, hour, f"%{wd}%"),
        )
        if not rows:
            return
        for r in rows:
            entity_id = r["entity_id"]
            if entity_id not in self.device_info:
                continue
            cooldown_until = self._habit_suggest_cooldown.get(entity_id, 0)
            if time.time() - cooldown_until < HABIT_SUGGEST_COOLDOWN_SEC:
                continue
            state = self.hass.states.get(entity_id)
            current = (state.state if state else "").strip().lower()
            expected = (r["expected_state"] or "").strip().lower()
            if current == expected:
                continue
            domain = entity_id.split(".")[0]
            if domain not in ("light", "switch", "fan", "climate", "cover"):
                continue
            on_states = ("on", "open", "playing", "heat", "cool", "auto")
            want_on = expected in on_states
            service = "turn_on" if want_on else "turn_off"
            name = self.device_info.get(entity_id, {}).get("name", entity_id)
            action_cn = "开启" if want_on else "关闭"
            message = f"根据您的习惯，此时通常会{action_cn}「{name}」。是否现在执行？"
            actions = [
                {
                    "domain": domain, "service": service, "entity_id": entity_id,
                    "params": {}, "reason": f"习惯建议：{action_cn}{name}", "delay_seconds": 0,
                }
            ]
            self._pending_habit_suggestion = {
                "actions": actions, "message": message,
                "created": time.time(), "timeout": HABIT_SUGGEST_TIMEOUT_SEC,
            }
            self._habit_suggest_cooldown[entity_id] = time.time()
            self._sys_log("INFO", f"[习惯询问] {message}")
            await self._habit_notify(message)
            self._habit_suggest_timeout_handle = async_call_later(
                self.hass, HABIT_SUGGEST_TIMEOUT_SEC, self._on_habit_suggest_timeout
            )
            return  # 一次只询问一条

    async def _check_env_feedback_tasks(self) -> None:
        """检查环境效果反馈任务列表，对到期任务评估环境指标是否朝预期方向变化。

        任务结构:
          entity_id   — 被操作的设备（climate/fan/switch 等）
          action      — "on"/"off"
          target_temp — 目标温度（仅 climate 有效）
          temp_sensor — 相关温度传感器实体 ID
          humi_sensor — 相关湿度传感器（可选）
          base_temp   — 操作时的基准温度
          base_humi   — 操作时的基准湿度
          check_at    — 应检查的时间戳
          checked     — 是否已检查（防重复）
        """
        now = time.time()
        async with self._env_feedback_lock:
            tasks = list(self._env_feedback_tasks)
            self._env_feedback_tasks = []
        if not tasks:
            return

        remaining: list[dict] = []
        try:
            for task in tasks:
                if task.get("checked"):
                    continue
                if now < task["check_at"]:
                    remaining.append(task)
                    continue

                eid = task["entity_id"]
                action = task["action"]
                base_temp = task.get("base_temp")
                target_temp = task.get("target_temp")
                temp_sensor = task.get("temp_sensor", "")
                base_humi = task.get("base_humi")
                humi_sensor = task.get("humi_sensor", "")

                task["checked"] = True

                # 设备当前状态
                dev_state = self.hass.states.get(eid)
                if not dev_state or dev_state.state in ("unavailable", "unknown"):
                    self._sys_log("INFO", f"[反馈] {eid} 当前不可用，跳过反馈检查")
                    # 设计意图：环境反馈任务为一次性检查，设备失联时无法获取传感器数据，
                    # 重试无意义（数据将过时）。此处 continue 为主动丢弃，非 bug。
                    continue

                # 若设备已被用户关闭则无需检查
                dev_on = dev_state.state not in ("off", "idle", "unavailable")
                if action == "on" and not dev_on:
                    self._sys_log("INFO", f"[反馈] {eid} 已被关闭，环境效果检查取消")
                    # 设计意图：用户主动关闭说明场景需求已变化，继续检查环境效果无价值。
                    continue

                problems: list[str] = []
                details: list[str] = []

                # ── 温度效果检查 ──────────────────────────────────────────────────
                if temp_sensor:
                    ts_state = self.hass.states.get(temp_sensor)
                    if ts_state and ts_state.state not in ("unavailable", "unknown"):
                        try:
                            cur_temp = float(ts_state.state)
                            if base_temp is not None and target_temp is not None:
                                # 判断温度是否向目标温度方向移动了至少 0.3°C
                                initial_gap = abs(base_temp - target_temp)
                                current_gap = abs(cur_temp - target_temp)
                                moved = base_temp - cur_temp  # 正：降温；负：升温

                                if initial_gap <= 0.5:
                                    details.append(f"温度已在目标范围附近（当前 {cur_temp}°C，目标 {target_temp}°C）")
                                elif current_gap >= initial_gap - 0.3:
                                    # 没有明显向目标移动
                                    direction = "降温" if target_temp < base_temp else "升温"
                                    problems.append(
                                        f"空调{direction}效果不明显：开启时 {base_temp}°C → "
                                        f"现在 {cur_temp}°C，目标 {target_temp}°C，差距未缩小"
                                    )
                                else:
                                    delta = round(abs(moved), 1)
                                    details.append(f"温度已朝目标变化 {delta}°C（{base_temp}°C → {cur_temp}°C，目标 {target_temp}°C）")
                            elif base_temp is not None:
                                details.append(f"温度: {base_temp}°C → {cur_temp}°C")
                        except (ValueError, TypeError):
                            pass

                # ── 湿度效果检查（除湿/加湿）──────────────────────────────────────
                if humi_sensor:
                    hs_state = self.hass.states.get(humi_sensor)
                    if hs_state and hs_state.state not in ("unavailable", "unknown"):
                        try:
                            cur_humi = float(hs_state.state)
                            if base_humi is not None:
                                delta_h = round(abs(cur_humi - base_humi), 1)
                                details.append(f"湿度: {base_humi}% → {cur_humi}%（变化 {delta_h}%）")
                        except (ValueError, TypeError):
                            pass

                # ── 输出结果 ──────────────────────────────────────────────────────
                dev_name = self.get_device_name(eid)
                elapsed_min = int((now - (task["check_at"] - task.get("check_after", 600))) / 60)

                if problems:
                    msg = f"[环境反馈] {dev_name} 执行 {elapsed_min} 分钟后：{'；'.join(problems)}"
                    self._sys_log("WARN", msg)
                    # 通知用户
                    notify_msg = f"**{dev_name}** 已开启 {elapsed_min} 分钟，但效果不明显：\n\n{'；'.join(problems)}"
                    if details:
                        notify_msg += f"\n\n({' | '.join(details)})"
                    self._notify_dedup(notify_msg, "SmartAgent 效果反馈")
                    # TTS 播报（Level 2）
                    from .const import TTS_LEVEL_ACTIONS
                    await self._tts_speak(f"{dev_name}开启{elapsed_min}分钟后效果不明显，请检查是否正常工作。",
                                          min_level=TTS_LEVEL_ACTIONS)
                else:
                    detail_str = "；".join(details) if details else "无可用传感器数据"
                    self._sys_log("INFO", f"[反馈✓] {dev_name} 效果正常 — {detail_str}")
        finally:
            # 保证未到期任务回写，即使循环中途抛出异常也不会永久丢失
            kept = [t for t in remaining if now - t.get("check_at", 0) < 7200]
            async with self._env_feedback_lock:
                self._env_feedback_tasks.extend(kept)

    def _analyze_energy_usage(self) -> None:
        """（同步，跑在 executor）分析近 7 天设备能耗，更新 _energy_stats 缓存。

        检测"空房间浪费"：设备开启但没有存在感传感器显示有人。
        结果缓存到 self._energy_stats，由 get_config_attributes 暴露给前端。
        如果浪费时间 > 30 分钟，发 HA 通知提醒。
        """
        try:
            stats = self._get_device_usage_stats(days=7)
        except Exception as exc:
            self._sys_log("WARN", f"[能耗分析] 统计失败: {exc}")
            return

        self._energy_stats = stats
        # 从 executor 线程安全地调度 UI 更新回事件循环。
        # get_config_attributes() 需在事件循环中调用（读取 _rules/_habits 等共享状态），
        # 使用 lambda 推迟执行，确保整个调用发生在事件循环线程中。
        self.hass.loop.call_soon_threadsafe(
            lambda: self.async_set_updated_data(self.get_config_attributes())
        )
        self._sys_log("INFO", f"[能耗分析] 分析完成，共 {len(stats)} 台设备")

        # 找出浪费 > 30 分钟的设备
        wasteful = [s for s in stats if s["waste_minutes"] > 30]
        if wasteful:
            lines = []
            for s in wasteful[:5]:
                name = s["entity_id"].split(".")[-1].replace("_", " ")
                wh = int(s["waste_minutes"] // 60)
                wm = int(s["waste_minutes"] % 60)
                t = f"{wh}小时{wm}分钟" if wh else f"{wm}分钟"
                lines.append(f"- **{name}**：无人时开启 {t}")
            msg = "SmartAgent 检测到以下设备在无人情况下长时间开启，建议关闭或添加自动化规则：\n\n"
            msg += "\n".join(lines)
            msg += "\n\n前往 **SmartAgent 面板 → 能耗分析** 查看完整报告。"
            try:
                # _analyze_energy_usage 运行在 executor 线程，必须通过 call_soon_threadsafe
                # 将协程调度回事件循环，不能直接调用 async_create_task
                notify_data = {
                    "title": f"SmartAgent 节能建议（{len(wasteful)} 台设备）",
                    "message": msg,
                    "notification_id": "smart_agent_energy_warning",
                }
                self.hass.loop.call_soon_threadsafe(
                    lambda: self.hass.async_create_task(
                        async_call_service(
                            self.hass,
                            "persistent_notification", "create", notify_data
                        )
                    )
                )
            except Exception as exc:
                self._sys_log("WARN", f"[能耗分析] 推送通知失败: {exc}")

    async def _habit_notify(self, message: str) -> None:
        """发送习惯询问通知，同时通过 _tts_speak 支持语音播报（Level 3）。"""
        from .const import TTS_LEVEL_ALL
        self._notify_dedup(message, "智能习惯建议")
        await self._tts_speak(message, min_level=TTS_LEVEL_ALL)

    async def async_confirm_habit(self) -> None:
        """用户确认执行当前待确认的习惯建议。"""
        if not self._pending_habit_suggestion:
            self._sys_log("INFO", "[习惯询问] 无待确认建议")
            return
        if self._habit_suggest_timeout_handle:
            self._habit_suggest_timeout_handle()
            self._habit_suggest_timeout_handle = None
        actions = self._pending_habit_suggestion["actions"]
        self._pending_habit_suggestion = None
        executed = await self._execute_actions(actions, is_global_cmd=True)
        self._sys_log("INFO", f"[习惯询问] 已确认执行 {executed} 个动作")
        self._notify_dedup("已按习惯执行。", "智能习惯建议")

    async def async_cancel_habit(self) -> None:
        """用户取消当前待确认的习惯建议。"""
        if self._habit_suggest_timeout_handle:
            self._habit_suggest_timeout_handle()
            self._habit_suggest_timeout_handle = None
        if self._pending_habit_suggestion:
            self._sys_log("INFO", "[习惯询问] 用户取消建议")
            self._pending_habit_suggestion = None

    # ── 行为规律缓存 ──────────────────────────────────────────────────────────

    async def _check_empty_lights_anomaly(self) -> None:
        """
        Phase 11.2: 无人+灯亮持续异常检测（死亡螺旋告警）。

        如果某个房间连续 3 次巡检处于"无人+灯亮"且 AI 未执行关灯动作，
        记录告警日志并通知用户检查修正抑制规则是否过于激进。

        使用实例属性 _empty_lights_counter 跟踪各房间的连续异常次数，
        超过阈值时发出 WARN 并重置计数（避免日志刷屏）。
        """
        if not hasattr(self, "_empty_lights_counter"):
            self._empty_lights_counter: dict[str, int] = {}

        ANOMALY_THRESHOLD = 3  # 连续 N 次巡检无人有灯才告警
        occ_map = self._get_room_occupancy_map()

        # Phase 11.8: 展厅模式下，营业时间内"无人有灯"是设计行为，不应报警
        from .const import MODE_SHOWROOM
        _is_showroom = getattr(self, "_mode", None) == MODE_SHOWROOM
        if _is_showroom:
            from datetime import datetime as _dt
            _now_min = _dt.now().hour * 60 + _dt.now().minute
            _biz_start = getattr(self, "showroom_biz_start_min", 0)
            _biz_end = getattr(self, "showroom_biz_end_min", 1439)
            _in_biz_hours = _biz_start <= _now_min < _biz_end
        else:
            _in_biz_hours = False

        for room, sensors in occ_map.items():
            if not sensors:
                continue

            # 展厅模式 + 营业时间：展厅区域无人有灯是正确展示行为，跳过异常检测
            if _is_showroom and _in_biz_hours:
                _showroom_area = getattr(self, "showroom_area_name", "")
                if room == _showroom_area:
                    self._empty_lights_counter.pop(room, None)
                    continue

            # 仅关注传感器明确显示无人的房间（unknown/unavailable 不算）
            all_off = all(s == "off" for _, s in sensors)
            if not all_off:
                self._empty_lights_counter.pop(room, None)
                continue

            # 检查该房间是否有灯处于开启状态
            lights_on = []
            for eid, info in self.device_info.items():
                if eid.split(".")[0] != "light":
                    continue
                if info.get("room", "") != room:
                    continue
                state = self.hass.states.get(eid)
                if state and state.state == "on":
                    lights_on.append(info.get("name", eid))

            if not lights_on:
                self._empty_lights_counter.pop(room, None)
                continue

            # 累计无人有灯次数
            count = self._empty_lights_counter.get(room, 0) + 1
            self._empty_lights_counter[room] = count

            if count >= ANOMALY_THRESHOLD:
                self._sys_log("WARN",
                    f"[异常检测] ⚠️ {room} 连续{count}次巡检发现无人有灯未处理: "
                    f"{', '.join(lights_on)}。请检查修正抑制规则是否过激。"
                )
                # 重置计数，避免每次巡检都重复告警
                self._empty_lights_counter[room] = 0

    def _refresh_behavior_patterns_cache(self) -> None:
        """在 executor 中同步刷新行为规律缓存（非事件循环线程）。"""
        self._behavior_patterns_cache = self._get_behavior_patterns_snapshot()
        self._refresh_room_topology_cache()

    def _refresh_room_topology_cache(self) -> None:
        """P1-2: 从 add-on room topology projection 刷新只读缓存。"""
        topo: dict[str, set[str]] = {}
        addon_client = getattr(self, "_addon_client", None)
        loop = getattr(getattr(self, "hass", None), "loop", None)
        if addon_client is None or loop is None:
            self._room_topology_cache = topo
            self._room_topology_cache_updated_at = time.monotonic()
            return
        try:
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            if running_loop is loop:
                _LOGGER.debug("[Topology] skip sync refresh on event loop thread")
                if not getattr(self, "_room_topology_refresh_pending", False):
                    self._room_topology_refresh_pending = True
                    task = self.hass.async_create_task(self._async_refresh_room_topology_cache())
                    if hasattr(task, "add_done_callback"):
                        task.add_done_callback(
                            lambda _task: setattr(self, "_room_topology_refresh_pending", False)
                        )
                    else:
                        self._room_topology_refresh_pending = False
                return

            future = asyncio.run_coroutine_threadsafe(addon_client.get_rooms_topology(), loop)
            rows_payload = future.result(timeout=5)
            topo = self._coerce_room_topology_payload(rows_payload)
        except Exception as exc:
            _LOGGER.debug("[Topology] 加载房间拓扑失败: %s", exc)
        self._room_topology_cache = topo
        self._room_topology_cache_updated_at = time.monotonic()

    async def _async_refresh_room_topology_cache(self) -> None:
        """Refresh room topology from add-on without blocking the HA event loop."""
        topo: dict[str, set[str]] = {}
        addon_client = getattr(self, "_addon_client", None)
        if addon_client is None:
            self._room_topology_cache = topo
            self._room_topology_cache_updated_at = time.monotonic()
            return
        try:
            rows_payload = await addon_client.get_rooms_topology()
            topo = self._coerce_room_topology_payload(rows_payload)
        except Exception as exc:
            _LOGGER.debug("[Topology] 加载房间拓扑失败: %s", exc)
        self._room_topology_cache = topo
        self._room_topology_cache_updated_at = time.monotonic()

    @staticmethod
    def _coerce_room_topology_payload(rows_payload: Any) -> dict[str, set[str]]:
        topo: dict[str, set[str]] = {}
        if isinstance(rows_payload, dict):
            rows = rows_payload.get("topology") or rows_payload.get("relations") or rows_payload.get("data") or []
        elif isinstance(rows_payload, list):
            rows = rows_payload
        else:
            rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            room_a = str(row.get("room_a") or row.get("source") or row.get("from") or "").strip()
            room_b = str(row.get("room_b") or row.get("target") or row.get("to") or "").strip()
            if not room_a or not room_b or room_a == room_b:
                continue
            topo.setdefault(room_a, set()).add(room_b)
            topo.setdefault(room_b, set()).add(room_a)
        return topo

    def _get_behavior_patterns_snapshot(self) -> list[dict]:
        """同步读取 behavior_patterns 表（仅在 executor 线程调用）。"""
        _WD_NAMES = {
            "0": "周日", "1": "周一", "2": "周二", "3": "周三",
            "4": "周四", "5": "周五", "6": "周六",
        }
        try:
            rows = self._query_events(
                "SELECT id, entity_id, expected_state, hour_start, hour_end, weekday_mask, confidence, hit_count, last_updated "
                "FROM behavior_patterns ORDER BY confidence DESC, entity_id"
            )
            result = []
            for r in rows:
                eid = r["entity_id"]
                name = self.device_info.get(eid, {}).get("name", eid)
                wd_mask = r.get("weekday_mask") or "0123456"
                wd_label = "".join(_WD_NAMES.get(c, c) for c in wd_mask)
                hour_s = r["hour_start"]
                hour_e = r["hour_end"]
                time_label = f"{hour_s}:00" if hour_s == hour_e else f"{hour_s}:00-{hour_e}:00"
                state_cn = {
                    "on": "开启", "off": "关闭", "open": "打开", "closed": "关闭",
                }.get((r["expected_state"] or "").lower(), r["expected_state"])
                result.append({
                    "id": r["id"], "entity_id": eid, "name": name,
                    "expected_state": r["expected_state"], "state_cn": state_cn,
                    "time_label": time_label, "weekday": wd_label,
                    "confidence": r["confidence"], "hit_count": r["hit_count"] or 0,
                    "last_updated": (r["last_updated"] or "")[:10],
                })
            return result
        except Exception as e:
            _LOGGER.warning("[PatrolMixin] Failed to read behavior_patterns: %s", e)
            return []

    # ── ReAct-Lite (9.10)：巡检后置验证 ──────────────────────────────────────

    async def _verify_patrol_actions_delayed(
        self,
        executed_actions: list[dict],
        cmd_time: float,
        delay_sec: int = 45,
    ) -> None:
        """ReAct-Lite：延迟验证巡检执行的 turn_on/turn_off 动作是否实际生效。

        核心判断逻辑（基于时间戳，避免用户手动干预被误报为设备不响应）：
          - 若 state.last_changed < cmd_time：设备状态自命令下发前从未改变 → 确认为不响应
          - 若 state.last_changed >= cmd_time：设备响应过（无论之后是否被用户改回）→ 不报警

        说明：仅做诊断日志，不重复发送动作（防止循环触发）。

        :param executed_actions: inference.py 确认执行后保存的 turn_on/turn_off 动作列表
        :param cmd_time:         动作下发时的 Unix 时间戳（time.time()）
        :param delay_sec:        等待时间（秒），留足设备响应 + HA 状态刷新的时间
        """
        await asyncio.sleep(delay_sec)

        _ON_STATES = ("on", "open", "heat", "cool", "dry", "fan_only", "auto", "playing")
        _OFF_STATES = ("off", "closed", "idle")
        _SKIP_STATES = ("unavailable", "unknown")

        # 命令下发时刻（UTC-aware），用于与 state.last_changed 比较
        cmd_dt = datetime.fromtimestamp(cmd_time, tz=timezone.utc)

        mismatches: list[str] = []
        mismatch_actions: list[dict] = []  # ReAct Turn2: 跟踪真正不响应的动作原始数据
        user_overrides: int = 0
        verified: int = 0

        for action in executed_actions:
            eid = action.get("entity_id")
            if not eid:
                continue
            service = action.get("service", "")
            if "turn_on" in service:
                expected_on = True
            elif "turn_off" in service:
                expected_on = False
            else:
                continue

            st = self.hass.states.get(eid)
            if not st or st.state in _SKIP_STATES:
                continue

            actual = st.state
            dev_name = self.device_info.get(eid, {}).get("name", eid)

            # 判断设备是否曾经响应过命令：state.last_changed >= cmd_dt 说明状态变过
            _lc = getattr(st, "last_changed", None)
            _device_responded = _lc is not None and _lc >= cmd_dt

            if _device_responded:
                # 设备在命令下发后改变了状态，计为"已响应"（即使后被用户改回也不报警）
                verified += 1
                if (expected_on and actual not in _ON_STATES) or \
                   (not expected_on and actual not in _OFF_STATES):
                    user_overrides += 1
                continue

            # _device_responded = False：命令后状态从未改变
            if expected_on and actual not in _ON_STATES:
                # 应开而未开 —— 真正不响应
                mismatches.append(f"{dev_name}（{eid}）期望=开启 实际={actual}")
                mismatch_actions.append({"entity_id": eid, "expected_on": True, **action})
            elif not expected_on and actual not in _OFF_STATES:
                # 应关而未关 —— 真正不响应
                mismatches.append(f"{dev_name}（{eid}）期望=关闭 实际={actual}")
                mismatch_actions.append({"entity_id": eid, "expected_on": False, **action})
            else:
                # 状态未变但恰好已经是期望状态（命令冗余），也算"无需响应"
                verified += 1

        if mismatches:
            self._sys_log(
                "WARN",
                f"[ReAct验证] 巡检执行 {delay_sec}s 后，{len(mismatches)}/{len(mismatches) + verified} 个设备未响应命令"
                f"（可能原因：继电器失联/Zigbee 丢包/命令超时）:\n"
                + "\n".join(f"  ⚠ {m}" for m in mismatches),
            )

            # ── ReAct Turn 2：二次确认 + 补偿重试（v4.10.3）────────────────────────
            # 安全保障：仅对"从未响应"的设备重试一次，防止与用户手动覆盖冲突
            # 等待 15 秒：排除设备延迟响应（某些 Zigbee 节点需要 30-60s 才刷新状态）
            await asyncio.sleep(15)

            still_unresponsive: list[dict] = []
            for _ma in mismatch_actions:
                _eid = _ma["entity_id"]
                _st2 = self.hass.states.get(_eid)
                if not _st2 or _st2.state in _SKIP_STATES:
                    continue
                _lc2 = getattr(_st2, "last_changed", None)
                # 若设备在等待期间响应了（last_changed 更新），跳过
                if _lc2 is not None and _lc2 > cmd_dt:
                    continue
                _exp_on = _ma["expected_on"]
                _actual2 = _st2.state
                _still_wrong = (
                    (_exp_on and _actual2 not in _ON_STATES) or
                    (not _exp_on and _actual2 not in _OFF_STATES)
                )
                if _still_wrong:
                    still_unresponsive.append(_ma)

            if not still_unresponsive:
                self._sys_log(
                    "INFO",
                    f"[ReAct Turn2] 等待后设备已自愈（延迟响应），共 {len(mismatch_actions)} 个"
                )
            else:
                # 发送补偿命令
                self._sys_log(
                    "WARN",
                    f"[ReAct Turn2] {len(still_unresponsive)} 个设备持续未响应，触发补偿重试..."
                )
                from .ha_adapter import async_execute_command_envelope

                compensation_commands: list[dict[str, Any]] = []
                for _ma in still_unresponsive:
                    _eid = _ma["entity_id"]
                    _domain = _eid.split(".")[0] if "." in _eid else ""
                    if not _domain:
                        continue
                    _service = "turn_on" if _ma["expected_on"] else "turn_off"
                    _svc_data = (
                        {
                            k: v for k, v in _ma.items()
                            if k not in ("entity_id", "domain", "service", "expected_on", "reason")
                        }
                        if _ma["expected_on"]
                        else {}
                    )
                    compensation_commands.append({
                        "entity_id": _eid,
                        "domain": _domain,
                        "service": _service,
                        "data": _svc_data,
                    })
                try:
                    compensation_result = await async_execute_command_envelope(self.hass, {
                        "request_id": f"react-turn2-compensation:{int(cmd_time)}",
                        "commands": compensation_commands,
                        "execution_policy": {"stop_on_first_error": False},
                        "safety": {
                            "risk_level": "safe",
                            "requires_confirmation": False,
                            "reason": "[ReAct Turn2] 设备未响应补偿重试",
                        },
                    })
                    for _item in (
                        compensation_result.get("results", [])
                        if isinstance(compensation_result, dict)
                        else []
                    ):
                        if not _item.get("ok"):
                            _LOGGER.warning(
                                "[ReAct Turn2] 补偿命令失败 %s: %s",
                                _item.get("entity_id"),
                                _item.get("error") or _item.get("status"),
                            )
                except Exception as _retry_exc:
                    _LOGGER.warning("[ReAct Turn2] 补偿命令批量提交失败: %s", _retry_exc)

                # 等待并验证最终补偿结果
                await asyncio.sleep(20)
                recovered: list[str] = []
                escalations: list[str] = []

                for _ma in still_unresponsive:
                    _eid = _ma["entity_id"]
                    _dev_name = self.device_info.get(_eid, {}).get("name", _eid)
                    _st3 = self.hass.states.get(_eid)
                    if not _st3 or _st3.state in _SKIP_STATES:
                        escalations.append(f"{_dev_name} 状态不可用")
                        continue
                    _exp_on = _ma["expected_on"]
                    _final = _st3.state
                    if (_exp_on and _final in _ON_STATES) or (not _exp_on and _final in _OFF_STATES):
                        recovered.append(_dev_name)
                    else:
                        escalations.append(
                            f"{_dev_name}（{_eid}）期望={'开' if _exp_on else '关'} 实际={_final}"
                        )

                if recovered:
                    self._sys_log(
                        "INFO",
                        f"[ReAct Turn2] 补偿成功 ✅: {', '.join(recovered)}"
                    )
                if escalations:
                    self._sys_log(
                        "WARN",
                        f"[ReAct Turn2] 补偿后仍无响应，可能存在硬件故障，建议人工排查:\n"
                        + "\n".join(f"  ⚠ {e}" for e in escalations)
                    )
        else:
            _info = f"[ReAct验证] 巡检执行 {delay_sec}s 后验证：{verified} 个设备均已响应"
            if user_overrides:
                _info += f"（其中 {user_overrides} 个后被用户手动更改，属正常行为）"
            if verified > 0:
                self._sys_log("INFO", _info)
