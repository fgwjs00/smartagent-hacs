"""
ProtectionMixin — 保护机制层 + 动作优先级仲裁引擎。
负责：用户覆盖保护、HA 自动化冲突拦截、人员在场守卫、自动化资源自动发现、
     动作优先级判定与仲裁（P0-P4）。
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any

from .ha_adapter import async_call_service
from .const import (
    PRIORITY_EMERGENCY, PRIORITY_USER_DIRECT, PRIORITY_AUTOMATION,
    PRIORITY_AI_LOCKED, PRIORITY_AI_LEARNED,
    SOURCE_PHYSICAL, SOURCE_DASHBOARD, SOURCE_VOICE, SOURCE_AUTOMATION,
    SOURCE_AI_RULE, SOURCE_AI_INFER, SOURCE_EMERGENCY,
    SOURCE_PRIORITY_MAP, PRIORITY_GUARD_WINDOWS, PRIORITY_LABELS, SOURCE_LABELS,
    ESCALATION_WINDOW_MIN, ESCALATION_COUNT, ESCALATION_GUARD_SEC,
    ACTION_PARAM_KEYS_COMMON,
)

_PRIORITY_MAP_HARD_LIMIT = 500
_USER_OP_HISTORY_HARD_LIMIT = 500

# ── 安全关键词（用于识别 P0 紧急事件的传感器 entity_id / 名称） ──
_EMERGENCY_KEYWORDS = frozenset((
    "smoke", "gas", "leak", "flood", "alarm", "security", "fire", "co2",
    "烟雾", "烟感", "燃气", "漏水", "水浸", "告警", "警报", "火灾", "安防",
))

# 不应触发 P0 紧急的排除词（子字符串包含紧急关键词但语义无关）
_EMERGENCY_EXCLUDE = frozenset((
    "gas_meter", "gas_consumption", "gas_cost",  # 燃气表读数
    "alarm_clock", "alarm_volume",                # 闹钟
    "security_camera", "security_mode",           # 安防摄像头/模式
    "fire_tv", "fireplace",                       # Fire TV / 壁炉
))

# P2修复：数值型紧急阈值（传感器 device_class → 危险上限）
_EMERGENCY_THRESHOLDS: dict[str, float] = {
    "temperature": 55.0,    # °C，可能火灾
    "carbon_monoxide": 50.0,  # ppm
    "carbon_dioxide": 5000.0,  # ppm
    "gas": 20.0,            # %LEL
    "pm25": 500.0,          # µg/m³
}


class ProtectionMixin:
    """Mixin: 保护机制 — 自动化冲突硬拦截 + 人员在场守卫 + 优先级仲裁。"""

    _OFF_STATES = frozenset(("off", "closed", "idle", "standby", "locked"))

    _AUTOMATION_EXEC_WINDOW = 30
    _USER_OVERRIDE_PROTECTION = 120   # 代码层硬拦截：2分钟（防止 AI 立即反向）
    _USER_MANUAL_WINDOW = 1800        # P2 上下文展示窗口：30分钟（超出后不再向 AI 提示禁止反向）

    # ── HA 资源自动发现 ───────────────────────────────────────────────────────

    def _refresh_ha_resources(self) -> None:
        """Scan HA for available scripts, scenes, and active automations. Auto-discover managed entities."""
        scripts, scenes, autos = [], [], []
        managed_sensors: set[str] = set()
        managed_devices: dict[str, set[str]] = {}
        for s in self.hass.states.async_all("script"):
            name = s.attributes.get("friendly_name", s.entity_id)
            scripts.append({"entity_id": s.entity_id, "name": name})
        for s in self.hass.states.async_all("scene"):
            name = s.attributes.get("friendly_name", s.entity_id)
            scenes.append({"entity_id": s.entity_id, "name": name})
        for a in self.hass.states.async_all("automation"):
            name = a.attributes.get("friendly_name", a.entity_id)
            autos.append({"entity_id": a.entity_id, "name": name, "state": a.state})
        self._ha_scripts = scripts
        self._ha_scenes = scenes
        self._ha_automations = autos

        # ── 自动发现: 解析自动化配置，提取 trigger/action 中的 entity_id ──
        try:
            auto_configs = self.hass.data.get("automation.config", {})
            if not auto_configs:
                auto_configs = {}
            for auto_state in self.hass.states.async_all("automation"):
                if auto_state.state != "on":
                    continue
                auto_eid = auto_state.entity_id
                auto_name = auto_state.attributes.get("friendly_name", auto_eid)
                auto_id = auto_state.attributes.get("id", "")
                cfg = auto_configs.get(auto_id, {}) if auto_id else {}
                trigger_eids: set[str] = set()
                action_eids: set[str] = set()
                self._extract_entity_ids_from_config(cfg.get("trigger", cfg.get("triggers", [])), trigger_eids)
                self._extract_entity_ids_from_config(cfg.get("action", cfg.get("actions", [])), action_eids)
                self._extract_entity_ids_from_config(cfg.get("condition", cfg.get("conditions", [])), trigger_eids)
                for eid in trigger_eids:
                    if eid.startswith("binary_sensor.") or eid.startswith("sensor."):
                        managed_sensors.add(eid)
                for eid in action_eids:
                    domain = eid.split(".")[0]
                    if domain in ("light", "switch", "fan", "cover", "climate", "media_player", "script", "scene"):
                        if eid not in managed_devices:
                            managed_devices[eid] = set()
                        managed_devices[eid].add(auto_name)
        except Exception as exc:
            self._sys_log("WARN", f"[资源] 自动化配置解析出错（不影响核心功能）: {exc}")

        # ── 补充: 通过自动化名称中的关键词推断关联设备（备用策略）──
        _ASSOC_KW = {
            "开灯": "light", "关灯": "light", "灯光": "light",
            "开关": "switch", "空调": "climate", "窗帘": "cover",
            "风扇": "fan",
        }
        for auto_info in autos:
            if auto_info.get("state") != "on":
                continue
            auto_name = auto_info["name"]
            for kw, domain in _ASSOC_KW.items():
                if kw not in auto_name:
                    continue
                for eid in self.device_info:
                    if not eid.startswith(domain + "."):
                        continue
                    dev_name = self.device_info[eid].get("name", "")
                    dev_room = self.device_info[eid].get("room", "")
                    if dev_name and dev_name in auto_name:
                        managed_devices.setdefault(eid, set()).add(auto_name)
                    elif dev_room and dev_room in auto_name:
                        managed_devices.setdefault(eid, set()).add(auto_name)

        self._automation_managed_sensors = managed_sensors
        self._automation_managed_devices = managed_devices
        self._sys_log("INFO", f"[资源] HA资源刷新: 脚本={len(scripts)} 场景={len(scenes)} 自动化={len(autos)}"
                      f" | 管辖传感器={len(managed_sensors)} 管辖设备={len(managed_devices)}")
        if managed_devices:
            sample = list(managed_devices.items())[:5]
            for eid, autos_set in sample:
                self._sys_log("INFO", f"  ↳ {eid} ← 自动化: {', '.join(autos_set)}")

    @staticmethod
    def _extract_entity_ids_from_config(config_items: list | dict | None, out: set[str]) -> None:
        """Recursively extract entity_id strings from automation trigger/action/condition config."""
        if config_items is None:
            return
        if isinstance(config_items, dict):
            config_items = [config_items]
        if not isinstance(config_items, list):
            return
        for item in config_items:
            if not isinstance(item, dict):
                continue
            for key in ("entity_id", "device_id", "target"):
                val = item.get(key)
                if isinstance(val, str) and "." in val:
                    out.add(val)
                elif isinstance(val, list):
                    for v in val:
                        if isinstance(v, str) and "." in v:
                            out.add(v)
                elif isinstance(val, dict):
                    for v in val.values():
                        if isinstance(v, str) and "." in v:
                            out.add(v)
                        elif isinstance(v, list):
                            for vv in v:
                                if isinstance(vv, str) and "." in vv:
                                    out.add(vv)
            for sub_key in ("then", "else", "sequence", "action", "actions"):
                sub = item.get(sub_key)
                if sub:
                    ProtectionMixin._extract_entity_ids_from_config(sub, out)

    # Frigate person_count sensor 关键词（与 const.py 保持一致）
    _PERSON_COUNT_KW = ("person_count", "people_count", "person_detected", "人数")

    # ── 人员在场检测 ──────────────────────────────────────────────────────────

    def _get_room_person_counts(self) -> dict[str, int]:
        """
        从 Frigate person_count 传感器中读取各房间实际人数。
        结构：{room_name: count}
        """
        counts: dict[str, int] = {}
        for eid, dev in self.device_info.items():
            if not eid.startswith("sensor."):
                continue
            if not any(kw in eid.lower() for kw in self._PERSON_COUNT_KW):
                continue
            room = dev.get("room", "").strip()
            if not room:
                continue
            state = self.hass.states.get(eid)
            if not state:
                continue
            try:
                counts[room] = max(counts.get(room, 0), int(float(state.state)))
            except (ValueError, TypeError):
                pass
        return counts

    def _get_room_occupancy_map(self) -> dict[str, list[tuple[str, str]]]:
        """
        返回各房间的存在传感器状态映射（v4.8.8 虚拟在场推断 + Phase 12.0 融合域增强版）。

        结构：{room_name: [(entity_id, state), ...]}

        数据来源（按优先级）：
          0. 统一 Presence Snapshot（若可用）
          1. 融合域（PresenceFusionRegistry）：覆盖了某房间的域，优先使用域聚合状态
          2. PresenceInference 虚拟推断（无传感器家庭兜底）
          3. 原始传感器扫描（向后兼容）

        融合域优先的原因：
          单个子区传感器（如 Frigate zone）触发无人 ≠ 整个开间无人。
          融合域通过 OR/AND 策略汇聚多个传感器，给出整体存在判断。
        """
        # ── 0. 统一 Presence Snapshot（Wave 2 优先读取）
        _get_presence_snapshot = getattr(self, "get_presence_snapshot", None)
        if callable(_get_presence_snapshot):
            try:
                _snap = _get_presence_snapshot()
                if isinstance(_snap, dict):
                    _rooms = _snap.get("rooms")
                    if isinstance(_rooms, dict) and _rooms:
                        _mapped: dict[str, list[tuple[str, str]]] = {}
                        for _room, _info in _rooms.items():
                            if not isinstance(_info, dict):
                                continue
                            _state = str(_info.get("state", "")).lower()
                            if _state in ("occupied", "on", "present"):
                                _mapped[_room] = [("snapshot", "on")]
                            elif _state in ("vacant", "off", "empty"):
                                _mapped[_room] = [("snapshot", "off")]
                            elif _state in ("unknown", "uncertain"):
                                _mapped[_room] = [("snapshot", "unknown")]
                        if _mapped:
                            return _mapped
            except Exception as exc:
                _LOGGER.debug("[Protection] get_presence_snapshot 异常，降级: %s", exc)

        # ── 优先尝试使用 PresenceInference 引擎（包含硬件传感器判断和软推断兜底）
        if hasattr(self, "_presence_inference") and self._presence_inference is not None:
            try:
                inferred = self._presence_inference.to_occ_map()
                if inferred:
                    result = dict(inferred)
                    # Phase 12.0: 用融合域结果覆盖被域覆盖的房间
                    _fusion = getattr(self, "_fusion_registry", None)
                    if _fusion is not None and _fusion.has_scopes:
                        for scope in _fusion.scopes:
                            scope_state = _fusion.evaluate_scope(scope)
                            for room in scope.rooms:
                                result[room] = [(f"fusion:{scope.scope_id}", scope_state)]
                    return result
            except Exception as exc:
                _LOGGER.debug("[PresenceInference] to_occ_map 异常，降级到原始传感器扫描: %s", exc)

        # ── 兜底：原始传感器扫描（保持向后兼容）
        result: dict[str, list[tuple[str, str]]] = {}
        for eid, dev in self.device_info.items():
            # H1 修正：优先取 device_info 房间，回退到 HA 注册表，防止传感器未录入导致占用判断失效
            room = dev.get("room", "").strip()
            if not room and hasattr(self, "_get_entity_area"):
                room = self._get_entity_area(eid)

            if not room:
                continue

            if eid.startswith("binary_sensor."):
                if not any(kw.lower() in eid.lower() for kw in self._PRESENCE_KW):
                    continue
                state = self.hass.states.get(eid)
                cur_state = state.state if state else "unknown"
                result.setdefault(room, []).append((eid, cur_state))
            elif eid.startswith("sensor."):
                # Frigate person_count → 合成 on/off 状态
                if not any(kw in eid.lower() for kw in self._PERSON_COUNT_KW):
                    continue
                state = self.hass.states.get(eid)
                if not state:
                    continue
                try:
                    synthetic = "on" if int(float(state.state)) > 0 else "off"
                except (ValueError, TypeError):
                    synthetic = "unknown"
                result.setdefault(room, []).append((eid, synthetic))

        # Phase 12.0: 用融合域结果覆盖被域覆盖的房间（原始扫描路径）
        _fusion = getattr(self, "_fusion_registry", None)
        if _fusion is not None and _fusion.has_scopes:
            for scope in _fusion.scopes:
                scope_state = _fusion.evaluate_scope(scope)
                for room in scope.rooms:
                    result[room] = [(f"fusion:{scope.scope_id}", scope_state)]

        return result

    def _build_locked_people_rules(self) -> list[dict]:
        """预解析锁定规则中的人数阈值开灯条件。"""
        rules: list[dict] = []
        room_tokens = ("客厅", "餐厅", "展厅", "卧室", "办公室", "走廊", "门厅")
        global_tokens = ("所有", "全部", "全局")
        keyword_map = {
            "灯箱": ("灯箱", "deng_xiang", "lightbox"),
            "格栅": ("格栅", "ge_zha"),
            "射灯": ("射灯", "she_deng", "spot"),
            "灯带": ("灯带", "deng_dai", "strip"),
        }
        for content, locked in getattr(self, "_rules", []):
            if not locked:
                continue
            text = (content or "").strip()
            if not text:
                continue
            m_ge = re.search(r"(?:至少|不少于|>=|≥)\s*(\d+)\s*人", text)
            m_gt = re.search(r"(?:大于|超过|>)\s*(\d+)\s*人", text)
            threshold = None
            op = ""
            if m_ge:
                threshold = int(m_ge.group(1))
                op = "ge"
            elif m_gt:
                threshold = int(m_gt.group(1))
                op = "gt"
            if threshold is None:
                continue
            rules.append({
                "text": text,
                "threshold": threshold,
                "op": op,
                "room_tokens": room_tokens,
                "global_tokens": global_tokens,
                "keyword_map": keyword_map,
            })
        return rules

    def _is_light_blocked_by_people_rule(
        self,
        *,
        entity_id: str,
        room: str,
        person_count: int,
        parsed_rules: list[dict],
    ) -> tuple[bool, str]:
        """判断灯光动作是否被人数阈值锁定规则阻止。"""
        if not room or not parsed_rules:
            return False, ""
        entity_tail = entity_id.split(".", 1)[-1].lower() if "." in entity_id else entity_id.lower()
        dev_name = ((self.device_info.get(entity_id) or {}).get("name") or "").lower()

        for rule in parsed_rules:
            text = rule.get("text", "")
            threshold = int(rule.get("threshold", 0) or 0)
            op = rule.get("op", "")
            room_tokens = rule.get("room_tokens", ())
            global_tokens = rule.get("global_tokens", ())
            keyword_map = rule.get("keyword_map", {})

            mentions_entity = (entity_id in text) or (entity_tail in text)
            mentions_room = bool(room and room in text)
            mentions_global = any(t in text for t in global_tokens)
            foreign_room_mentioned = bool(room and any(t in text for t in room_tokens if t != room))

            keyword_hit = False
            for zh_kw, aliases in keyword_map.items():
                if any(a in entity_tail or a in dev_name for a in aliases):
                    if zh_kw in text:
                        keyword_hit = True
                        break

            if foreign_room_mentioned and not mentions_entity:
                continue
            if not (mentions_entity or (keyword_hit and (mentions_room or mentions_global))):
                continue

            enough = (person_count >= threshold) if op == "ge" else (person_count > threshold)
            if not enough:
                return True, f"{'>=' if op == 'ge' else '>'}{threshold}"
        return False, ""

    def _build_occupancy_section(self) -> str:
        """
        构建用于注入 Prompt 的「各区域实时人员状态」区块 (Phase 10.0 增强版)。
        支持虚拟在场推断：无传感器时显示推断置信度来源。
        """
        person_counts = self._get_room_person_counts() if getattr(self, "_frigate_enabled", False) else {}
        lines = ["【各区域实时人员状态（必须严格遵守）】"]

        # 优先使用 PresenceInference 引擎获取结构化结果
        if hasattr(self, "_presence_inference") and self._presence_inference is not None:
            try:
                all_presence = self._presence_inference.infer_all_rooms()
                for room, pres in all_presence.items():
                    count = person_counts.get(room)
                    if pres.level in ("high", "medium"):
                        if count is not None and count > 0:
                            symbol = f"✅ 有人 ({count}人)"
                        else:
                            symbol = "✅ 有人"
                        if pres.has_hw_sensor:
                            src = f"硬件传感器确认，置信度={pres.confidence:.0%}"
                        else:
                            src_list = [s[1] for s in pres.signals[:2]]
                            src = f"推断：{'，'.join(src_list)}，置信度={pres.confidence:.0%}"
                    elif pres.level == "low":
                        symbol = "⚠️ 不确定（谨慎操作）"
                        src = f"推断置信度={pres.confidence:.0%}，信号不足"
                    elif pres.level == "empty":
                        symbol = "❌ 无人"
                        src = "无人信号（传感器/推断）"
                    else:
                        symbol = "❓ 无数据"
                        src = "无传感器且无间接信号"
                    lines.append(f"- {room}：{symbol}（{src}）")

                lines.append(
                    "⚠️ 区域操作规则：\n"
                    "  ① 「✅ 有人」或「⚠️ 不确定」区域：禁止 turn_off 关灯，避免误关；\n"
                    "  ② 「❌ 无人」区域：禁止 turn_on 开灯/开设备；\n"
                    "  ③ 「❓ 无数据」区域：应根据时间/场景保守决策，倾向放行用户明确指令。"
                )
                return "\n".join(lines) + "\n"
            except Exception as exc:
                _LOGGER.debug("[PresenceInference] build_occupancy_section 异常，降级: %s", exc)

        # 降级到旧版传感器扫描
        occ_map = self._get_room_occupancy_map()
        if not occ_map:
            return ""
        for room, sensors in occ_map.items():
            occupied = any(s == "on" for _, s in sensors)
            count = person_counts.get(room)
            if occupied and count is not None and count > 0:
                symbol = f"✅ 有人 ({count}人)"
            elif occupied:
                symbol = "✅ 有人"
            else:
                symbol = "❌ 无人"
            sensor_str = ", ".join(f"{eid.split('.')[-1]}={s}" for eid, s in sensors[:3])
            lines.append(f"- {room}：{symbol}（{sensor_str}）")
        lines.append(
            "⚠️ 区域操作规则（系统强制执行，非 AI 自主判断）：\n"
            "  ① 「❌ 无人」区域：禁止 turn_on 开灯/开设备，禁止执行会导致开灯的 scene/script；\n"
            "  ② 「✅ 有人」区域：禁止 turn_off 关灯（以防 Frigate 漏检或传感器延迟误判），"
            "除非用户明确要求或节能规则明确覆盖；\n"
            "  ③ 关灯须双重确认：物理存在传感器 AND Frigate 人数均为 0 才执行，任一仍检测到有人则取消关灯。"
        )
        return "\n".join(lines) + "\n"

    def _guess_scene_room(self, scene_entity_id: str) -> str | None:
        """
        根据 scene/script 的 entity_id 和 friendly_name 推断其所属区域。
        匹配 device_info 中已登记的房间名称。
        返回 None 表示无法推断（放行）。
        """
        state = self.hass.states.get(scene_entity_id)
        check_str = scene_entity_id.lower()
        if state:
            check_str += " " + (state.attributes.get("friendly_name", "") or "").lower()
        rooms = {dev.get("room", "").strip() for dev in self.device_info.values() if dev.get("room", "").strip()}
        for room in rooms:
            if room.lower() in check_str:
                return room
        return None

    def _occupancy_guard_check(self, entity_id: str, service: str) -> tuple[bool, str]:
        """
        开灯前人员在场守卫：检查目标设备所在区域是否有人。
        返回 (should_block, reason)：
        - True  → 区域确认无人，应拒绝执行 turn_on
        - False → 有人或信息不足，放行
        仅对 light/switch 的 turn_on 生效；scene/script 由 Prompt 约束。
        """
        if "turn_on" not in service:
            return False, ""
        dev = self.device_info.get(entity_id, {})
        room = dev.get("room", "").strip()
        if not room:
            return False, ""
        occ_map = self._get_room_occupancy_map()
        sensors = occ_map.get(room, [])
        if not sensors:
            return False, ""  # 没有传感器信息，放行（给 AI benefit of doubt）
        occupied = any(s == "on" for _, s in sensors)
        if occupied:
            return False, ""
        # Frigate person_count 补充检查（仅在 Frigate 已启用时）
        if getattr(self, "_frigate_enabled", False):
            person_counts = self._get_room_person_counts()
            if person_counts.get(room, 0) > 0:
                return False, ""
        # 传感器状态不确定（离线/未知）时保守拒绝，避免在占用不可判定时误动作
        uncertain = any(s in ("unknown", "unavailable") for _, s in sensors)
        if uncertain:
            return True, f"区域「{room}」占用状态不确定（unknown/unavailable），按保守策略拒绝 turn_on"
        sensor_str = ", ".join(f"{eid}={s}" for eid, s in sensors[:2])
        return True, f"区域「{room}」所有存在传感器均为 off（{sensor_str}）"

    def _turnoff_presence_guard(self, entity_id: str, service: str) -> tuple[bool, str]:
        """
        关灯安全守卫：turn_off 执行前确认区域确实无人。

        背景：Frigate 视觉检测存在漏检（人在不显示），单纯依赖 Frigate 可能在人
        在房间时误关灯。本守卫综合以下两路信号，任意一路检测到有人即阻止关灯：
          1. 物理人体存在传感器（binary_sensor — mmWave 雷达/PIR/Frigate 占用传感器）
          2. Frigate person_count sensor（已进入 device_info 的传感器）
          3. Frigate MQTT 实时区域占用（_frigate_zone_occupancy，次要辅助）

        规则：
        - 仅对 light / switch 的 turn_off 生效（其他域不干预）
        - 仅家庭模式生效（展厅/演示模式由 AI 主导）
        - 所在区域无传感器 → 放行（无数据不能乱拦截）
        - 传感器 unknown/unavailable → 放行（数据不确定时允许关灯，更安全）
        - 物理传感器 on 或 Frigate 人数 > 0 → 阻止（确认有人）

        Returns:
            (should_block, reason)
        """
        if "turn_off" not in service:
            return False, ""
        if domain := entity_id.split(".")[0]:
            if domain not in ("light", "switch"):
                return False, ""

        from .const import MODE_SHOWROOM
        if self._mode == MODE_SHOWROOM:
            return False, ""

        dev = self.device_info.get(entity_id, {})
        room = dev.get("room", "").strip()
        if not room:
            return False, ""

        occ_map = self._get_room_occupancy_map()
        sensors = occ_map.get(room, [])
        if not sensors:
            return False, ""

        # 存在传感器 unknown/unavailable -> 保守阻止
        if any(s in ("unknown", "unavailable") for _, s in sensors):
            return True, f"区域「{room}」占用状态不确定（unknown/unavailable），按保守策略拒绝 turn_off"

        # 物理传感器检测到有人 → 阻止
        for eid, s in sensors:
            if s == "on":
                return True, f"物理存在传感器检测到有人：{eid.split('.')[-1]}=on（区域「{room}」)"

        # Frigate person_count 传感器补充检查
        person_counts = self._get_room_person_counts()
        room_count = person_counts.get(room, 0)
        if room_count > 0:
            return True, f"Frigate 人数传感器检测到有人：区域「{room}」= {room_count} 人"

        # Frigate MQTT 实时区域占用（camera.xxx 在同一房间）
        if getattr(self, "_frigate_enabled", False):
            frigate_occ: dict = getattr(self, "_frigate_zone_occupancy", {})
            for camera, zones in frigate_occ.items():
                cam_eid = f"camera.{camera}"
                cam_room = self.device_info.get(cam_eid, {}).get("room", "")
                if cam_room and cam_room != room:
                    continue
                total = sum(c for c in zones.values() if c > 0)
                if total > 0:
                    zone_detail = ", ".join(f"{z}={c}" for z, c in zones.items() if c > 0)
                    return True, f"Frigate 摄像头实时检测到有人：camera.{camera} [{zone_detail}]"

        return False, ""

    def _is_occupancy_active(self, entity_id: str) -> bool:
        """Check if any occupancy/presence sensor (binary or Frigate person_count) is active in the same room."""
        target_room = self.device_info.get(entity_id, {}).get("room", "")
        if not target_room:
            target_room = self._get_entity_area(entity_id)
        for eid, info in self.device_info.items():
            sensor_room = info.get("room", "")
            if not sensor_room:
                sensor_room = self._get_entity_area(eid)
            if target_room and sensor_room and target_room != sensor_room:
                continue
            if eid.startswith("binary_sensor."):
                eid_lower = eid.lower()
                name_lower = info.get("name", "").lower()
                if not any(kw in eid_lower or kw in name_lower for kw in self._PRESENCE_KW):
                    continue
                state = self.hass.states.get(eid)
                if state and state.state == "on":
                    return True
            elif eid.startswith("sensor."):
                # Frigate person_count: 有人数则认为有人
                if not any(kw in eid.lower() for kw in self._PERSON_COUNT_KW):
                    continue
                state = self.hass.states.get(eid)
                if not state:
                    continue
                try:
                    if int(float(state.state)) > 0:
                        return True
                except (ValueError, TypeError):
                    pass
        return False

    # ══════════════════════════════════════════════════════════════════════════
    # ── 动作优先级仲裁引擎 (Action Priority Arbiter) ────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _init_priority_system(self) -> None:
        """初始化优先级系统的运行时数据结构（在 coordinator.__init__ 中调用）。"""
        # 每个设备最后一次操作的优先级记录
        # {entity_id: {priority, source, time, state, guard_until}}
        self._device_priority_map: dict[str, dict] = {}

        # 连续操作计数器（用于升级保护）
        # {entity_id: [timestamp, timestamp, ...]}
        self._user_op_history: dict[str, list[float]] = {}

        # 全局抑制状态（如紧急事件期间全面抑制 AI 操作）
        self._global_suppress_until: float = 0.0
        self._global_suppress_reason: str = ""

    def _classify_source(self, entity_id: str, source_type: str,
                         context: dict | None = None) -> str:
        """将 HA 状态变化的 source_type 映射到标准化来源标识。

        Args:
            entity_id: 状态变化的实体 ID
            source_type: listeners 中识别的来源（"物理/自动", "用户界面", "自动化/脚本"）
            context: 额外上下文（如 user_id、parent_id）
        """
        ctx = context or {}
        eid_lower = entity_id.lower()
        name = self.device_info.get(entity_id, {}).get("name", "").lower()

        # P0 紧急检测：安全传感器触发（关键词匹配 + 排除词过滤）
        if any(kw in eid_lower or kw in name for kw in _EMERGENCY_KEYWORDS):
            # 排除已知的非紧急设备（如 gas_meter、alarm_clock、security_camera）
            if not any(ex in eid_lower for ex in _EMERGENCY_EXCLUDE):
                return SOURCE_EMERGENCY

        # P0 紧急检测：数值型传感器超过危险阈值
        state_obj = self.hass.states.get(entity_id)
        if state_obj and entity_id.startswith("sensor."):
            _dev_class = (state_obj.attributes.get("device_class") or "").lower()
            _threshold = _EMERGENCY_THRESHOLDS.get(_dev_class)
            if _threshold is not None:
                try:
                    if float(state_obj.state) >= _threshold:
                        return SOURCE_EMERGENCY
                except (ValueError, TypeError):
                    pass

        if source_type == "自动化/脚本":
            return SOURCE_AUTOMATION
        elif source_type == "用户界面":
            return SOURCE_DASHBOARD
        elif source_type == "语音":
            return SOURCE_VOICE
        else:
            return SOURCE_PHYSICAL

    def _get_device_priority(self, entity_id: str) -> dict | None:
        """获取设备当前的优先级记录，已过期则返回 None。"""
        rec = self._device_priority_map.get(entity_id)
        if not rec:
            return None
        if time.time() > rec.get("guard_until", 0):
            return None
        return rec

    def _record_device_operation(self, entity_id: str, source: str,
                                  new_state: str, params: dict | None = None) -> dict:
        """记录一次设备操作，更新优先级映射，返回优先级记录。"""
        now = time.time()
        priority = SOURCE_PRIORITY_MAP.get(source, PRIORITY_AI_LEARNED)

        # 计算保护窗口
        base_guard = PRIORITY_GUARD_WINDOWS.get(priority, 120)
        guard_until = now + base_guard

        # 用户直接操作 → 检测连续操作升级
        if priority == PRIORITY_USER_DIRECT:
            history = self._user_op_history.setdefault(entity_id, [])
            cutoff = now - ESCALATION_WINDOW_MIN * 60
            history[:] = [t for t in history if t > cutoff]
            history.append(now)

            if len(history) >= ESCALATION_COUNT:
                guard_until = now + ESCALATION_GUARD_SEC
                self._sys_log("WARN",
                    f"[优先级] {entity_id} 被用户连续操作 {len(history)} 次"
                    f"（{ESCALATION_WINDOW_MIN}min 内），保护升级至 {ESCALATION_GUARD_SEC // 60} 分钟")

        comparable_params = {
            k: v for k, v in (params or {}).items()
            if k in ACTION_PARAM_KEYS_COMMON
        }

        record = {
            "priority": priority,
            "source": source,
            "source_label": SOURCE_LABELS.get(source, source),
            "priority_label": PRIORITY_LABELS.get(priority, f"P{priority}"),
            "time": now,
            "state": new_state,
            "params": comparable_params,
            "guard_until": guard_until,
        }
        self._device_priority_map[entity_id] = record
        self._enforce_priority_storage_limits()
        return record

    def _params_conflict_for_same_direction(
        self,
        existing_state: str,
        existing_params: dict | None,
        ai_service: str,
        ai_params: dict | None,
    ) -> bool:
        """同优先级同方向时，若参数冲突则返回 True。"""
        if not ai_params:
            return False
        is_off = existing_state in self._OFF_STATES
        ai_turning_on = "turn_on" in ai_service or "open" in ai_service
        ai_turning_off = "turn_off" in ai_service or "close" in ai_service

        # 仅在同方向开启动作时比较参数；关闭动作不比较扩展参数
        if (is_off and ai_turning_on) or ((not is_off) and ai_turning_on):
            lhs = dict(existing_params or {})
            rhs = {
                k: v for k, v in ai_params.items()
                if k in ACTION_PARAM_KEYS_COMMON
            }
            for key in set(lhs.keys()) & set(rhs.keys()):
                if lhs.get(key) != rhs.get(key):
                    return True
        if ai_turning_off:
            return False
        return False

    def _arbitrate(self, entity_id: str, ai_source: str,
                   ai_service: str, ai_params: dict | None = None) -> tuple[bool, str]:
        """优先级仲裁：AI 尝试操作设备前调用。

        Args:
            entity_id: 目标设备
            ai_source: AI 操作来源（SOURCE_AI_RULE / SOURCE_AI_INFER）
            ai_service: 拟执行的服务（如 "turn_on", "turn_off"）

        Returns:
            (allowed, reason): allowed=True 表示放行, reason 为日志原因
        """
        now = time.time()

        # [P3] 环境常识提醒（放行操作，但通过 TTS/通知提醒用户存在的物理矛盾）
        self._environmental_mutex_check(entity_id, ai_service)

        # 全局抑制检查（紧急事件期间）
        if now < self._global_suppress_until:
            remaining = int(self._global_suppress_until - now)
            return False, (
                f"[P0 全局抑制] {self._global_suppress_reason}"
                f"（剩余 {remaining}s）"
            )

        ai_priority = SOURCE_PRIORITY_MAP.get(ai_source, PRIORITY_AI_LEARNED)
        existing = self._get_device_priority(entity_id)

        if not existing:
            return True, ""

        existing_priority = existing["priority"]
        remaining = int(existing["guard_until"] - now)

        # 更高优先级（数值更小）→ 放行；同优先级不放行，防止 AI 覆盖用户操作
        if ai_priority < existing_priority:
            return True, ""

        # 低优先级尝试操作高优先级保护的设备
        existing_state = existing.get("state", "")
        is_reversing = self._is_reverse_op(existing_state, ai_service)

        if is_reversing:
            return False, (
                f"[优先级仲裁] {PRIORITY_LABELS.get(ai_priority, '')} 尝试反向操作 {entity_id}"
                f"（当前由 {existing['source_label']} 控制 → {existing_state}，"
                f"保护剩余 {remaining}s）"
            )

        if ai_priority == existing_priority and self._params_conflict_for_same_direction(
            existing_state,
            existing.get("params"),
            ai_service,
            ai_params,
        ):
            return False, (
                f"[优先级仲裁] 同优先级参数冲突：{entity_id}"
                f"（当前由 {existing['source_label']} 保持参数，保护剩余 {remaining}s）"
            )

        # 非反向操作（同方向）→ 放行（如用户开灯后 AI 也想开灯，是协同非冲突）
        return True, ""

    def _environmental_mutex_check(self, entity_id: str, service: str) -> None:
        """P3 跨域常识提醒（不拦截，只提醒）。

        检测物理矛盾场景，放行操作但主动通过 TTS 和 HA 通知提醒用户。
        例如：开着窗户时操控空调 → 放行空调，但语音提醒"窗户还开着哦"。
        """
        domain = entity_id.split(".")[0] if "." in entity_id else ""

        # 规则1：开窗状态下操控空调 → 放行 + 提醒关窗
        if domain == "climate" and service in ("turn_on", "set_temperature", "set_hvac_mode"):
            dev_info = self.device_info.get(entity_id, {})
            room = dev_info.get("room", "")
            if not room:
                return

            window_kws = ("窗", "window")
            open_windows = []
            for state in self.hass.states.async_all("binary_sensor"):
                if state.state != "on":
                    continue
                eid = state.entity_id.lower()
                name = state.attributes.get("friendly_name", eid).lower()

                if not any(kw in eid or kw in name for kw in window_kws):
                    continue

                s_dev_info = self.device_info.get(state.entity_id, {})
                s_room = s_dev_info.get("room", "").lower()

                if s_room == room.lower() or room.lower() in eid or room.lower() in name:
                    friendly = state.attributes.get("friendly_name", state.entity_id)
                    open_windows.append(friendly)

            if open_windows:
                window_names = "、".join(open_windows[:3])
                warn_msg = f"温馨提示：检测到{room}的{window_names}当前处于开启状态，建议先关闭窗户再使用空调，以节省能源。"
                self._sys_log("WARN", f"[环境提醒] {warn_msg}")

                # 通过 TTS 语音提醒用户
                try:
                    self.hass.async_create_task(
                        self._tts_speak(warn_msg)
                    )
                except Exception:
                    pass

                # 同时发送 HA 持久通知
                try:
                    self.hass.async_create_task(
                        async_call_service(
                            self.hass,
                            "persistent_notification", "create",
                            {"title": "🪟 环境提醒", "message": warn_msg},
                        )
                    )
                except Exception:
                    pass

    def _trigger_emergency(self, entity_id: str, reason: str,
                           suppress_seconds: int = 300) -> None:
        """触发 P0 紧急事件：设置全局抑制，停止所有 AI 操作。"""
        now = time.time()
        self._global_suppress_until = now + suppress_seconds
        self._global_suppress_reason = reason
        self._record_device_operation(entity_id, SOURCE_EMERGENCY, "alert")
        self._sys_log("ERROR",
            f"[🚨 P0 紧急] {reason} — 全局 AI 抑制 {suppress_seconds}s | 触发: {entity_id}")

    def _is_reverse_op(self, current_state: str, service: str) -> bool:
        """判断 AI 操作是否与设备当前状态相反。"""
        is_off = current_state in self._OFF_STATES
        ai_turning_on = "turn_on" in service or "open" in service
        ai_turning_off = "turn_off" in service or "close" in service
        return (is_off and ai_turning_on) or (not is_off and ai_turning_off)

    def _get_priority_summary(self) -> list[dict]:
        """返回当前所有活跃优先级保护的设备列表（供前端展示）。"""
        now = time.time()
        result = []
        for eid, rec in self._device_priority_map.items():
            if now > rec.get("guard_until", 0):
                continue
            remaining = int(rec["guard_until"] - now)
            name = self.device_info.get(eid, {}).get("name", eid)
            result.append({
                "entity_id": eid,
                "name": name,
                "priority": rec["priority"],
                "priority_label": rec["priority_label"],
                "source_label": rec["source_label"],
                "state": rec["state"],
                "remaining_sec": remaining,
            })
        result.sort(key=lambda x: (x["priority"], -x["remaining_sec"]))
        return result

    def _build_priority_prompt_section(self) -> str:
        """构建注入 AI Prompt 的优先级保护上下文。"""
        active = self._get_priority_summary()
        if not active:
            return ""
        lines = ["【设备操作优先级保护（系统强制执行，AI 不可违背）】"]
        for item in active[:15]:
            lines.append(
                f"- {item['name']}({item['entity_id']})："
                f"当前由「{item['source_label']}」控制 → {item['state']}，"
                f"{item['priority_label']}保护中（剩余 {item['remaining_sec']}s）"
                f"→ **禁止 AI 反向操作**"
            )
        if self._global_suppress_until > time.time():
            remaining = int(self._global_suppress_until - time.time())
            lines.append(
                f"⚠️ 全局安全抑制中（{self._global_suppress_reason}，剩余 {remaining}s）"
                f"→ **禁止一切 AI 主动操作**"
            )
        lines.append(
            "📌 规则：高优先级来源的操作不可被低优先级覆盖。"
            "用户物理操作 > HA自动化 > AI锁定规则 > AI推理。"
            "如用户刚关灯，即使环境变化也不要开灯，请在 reason 中说明'尊重用户操作'。"
        )
        return "\n".join(lines) + "\n"

    def _enforce_priority_storage_limits(self) -> None:
        """兜底限制优先级运行时字典大小，防止周期清理异常时无上限增长。"""
        if len(self._device_priority_map) > _PRIORITY_MAP_HARD_LIMIT:
            ordered = sorted(
                self._device_priority_map.items(),
                key=lambda kv: kv[1].get("guard_until", 0),
            )
            drop_count = len(self._device_priority_map) - _PRIORITY_MAP_HARD_LIMIT
            for eid, _ in ordered[:drop_count]:
                self._device_priority_map.pop(eid, None)
            self._sys_log("WARN", f"[优先级] _device_priority_map 超限，已清理 {drop_count} 条旧记录")

        if len(self._user_op_history) > _USER_OP_HISTORY_HARD_LIMIT:
            ordered = sorted(
                self._user_op_history.items(),
                key=lambda kv: max(kv[1]) if kv[1] else 0,
            )
            drop_count = len(self._user_op_history) - _USER_OP_HISTORY_HARD_LIMIT
            for eid, _ in ordered[:drop_count]:
                self._user_op_history.pop(eid, None)
            self._sys_log("WARN", f"[优先级] _user_op_history 超限，已清理 {drop_count} 条旧记录")

    def _cleanup_expired_priorities(self) -> None:
        """清理已过期的优先级记录（在周期性更新中调用）。"""
        now = time.time()
        expired = [eid for eid, rec in self._device_priority_map.items()
                   if now > rec.get("guard_until", 0)]
        for eid in expired:
            del self._device_priority_map[eid]

        # 清理操作历史中超过统计窗口的记录
        cutoff = now - ESCALATION_WINDOW_MIN * 60
        empty = []
        for eid, history in self._user_op_history.items():
            history[:] = [t for t in history if t > cutoff]
            if not history:
                empty.append(eid)
        for eid in empty:
            del self._user_op_history[eid]
