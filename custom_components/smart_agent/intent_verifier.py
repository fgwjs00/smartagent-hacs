"""
IntentVerifier — 双阶段意图验证管道 (Phase 9.5 / P2.2)。

将原先分散在 actions.py、inference.py、protection.py 中的 ad-hoc 验证逻辑
统一为两个阶段：

  Stage 1 — 语义防火墙 (Semantic Firewall)
    在 LLM 返回后、执行前，检查所有 actions 的语义合理性：
    - 有人 + 关灯 = 冲突（USER_EXPLICIT 指令可豁免）
    - 有人 + 关安防设备 = 危险
    - 无人区域 + 开灯 = 可疑
    - 同一实体同时出现 turn_on + turn_off = 自相矛盾
    - 不存在的 entity_id = 幻觉
    - 区域隔离（USER_EXPLICIT 指令可豁免跨区控制）

  Stage 2 — 物理验证器 (Deterministic Physical Validator)
    在 _execute_actions 前执行，确定性验证：
    - entity_id 是否在 device_info 中
    - domain 是否与 entity_id 前缀匹配
    - service 是否合法（不同 domain 有白名单）
    - 数值参数是否在合法范围内（brightness_pct: 0-100，temperature: 10-35）

指令来源常量（cmd_source）：
  - CMD_SOURCE_SENSOR       : 传感器自动触发（最严格验证）
  - CMD_SOURCE_SCHEDULE     : 定时/巡检触发
  - CMD_SOURCE_USER_EXPLICIT: 用户主动指令（面板/语音/展厅一次性，豁免部分检查）

参考：DS-IA 论文（双阶段验证，无效指令拒绝率从 60% → 87%）
"""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# ── 指令来源常量 ──────────────────────────────────────────────────────────────
# 用于区分自动触发与用户主动指令，控制验证严格程度

CMD_SOURCE_SENSOR = "SENSOR"
"""传感器自动触发，执行完整语义验证（最严格）。"""

CMD_SOURCE_SCHEDULE = "SCHEDULE"
"""定时/巡检触发，执行完整语义验证。"""

CMD_SOURCE_USER_EXPLICIT = "USER_EXPLICIT"
"""用户主动指令（面板操作/语音/展厅一次性指令），豁免区域隔离和有人关灯检查。"""

# ── 动作安全等级常量 ──────────────────────────────────────────────────────────
# 用于渐进式自治逻辑：先执行安全项，存疑项询问用户

SAFETY_LEVEL_SAFE = 1
"""安全可逆动作：灯光、窗帘、风扇、媒体播放等低成本操作。"""

SAFETY_LEVEL_HIGH_COST = 2
"""高成本/影响大动作：空调、新风、吸尘器、热水器等。"""

SAFETY_LEVEL_CRITICAL = 3
"""关键安全动作：门锁、安防模式、车库门等。"""

# ── 服务合法性白名单 ──────────────────────────────────────────────────────────

_VALID_SERVICES: dict[str, set[str]] = {
    # ── 灯光/开关 ───────────────────────────────────────────────────────────
    "light":         {"turn_on", "turn_off", "toggle"},
    "switch":        {"turn_on", "turn_off", "toggle"},
    # ── 气候/环境 ────────────────────────────────────────────────────────────
    "climate":       {"set_temperature", "set_hvac_mode", "set_fan_mode",
                      "set_humidity", "set_preset_mode", "turn_on", "turn_off"},
    "water_heater":  {"turn_on", "turn_off", "set_temperature", "set_operation_mode"},
    "humidifier":    {"turn_on", "turn_off", "set_humidity", "set_mode"},
    # ── 遮光/窗帘 ────────────────────────────────────────────────────────────
    "cover":         {"open_cover", "close_cover", "stop_cover",
                      "set_cover_position", "toggle"},
    # ── 风扇 ──────────────────────────────────────────────────────────────────
    "fan":           {"turn_on", "turn_off", "set_percentage",
                      "set_direction", "oscillate", "toggle"},
    # ── 场景/脚本 ────────────────────────────────────────────────────────────
    "script":        {"turn_on", "turn_off"},
    "scene":         {"turn_on"},
    # ── 媒体 ──────────────────────────────────────────────────────────────────
    "media_player":  {"media_play", "media_pause", "media_stop", "media_next_track",
                      "media_previous_track", "volume_set", "volume_up", "volume_down",
                      "volume_mute", "select_source", "turn_on", "turn_off"},
    # ── 扫地机器人 ──────────────────────────────────────────────────────────
    "vacuum":        {"start", "pause", "stop", "return_to_base",
                      "turn_on", "turn_off"},
    # ── 输入控件 ──────────────────────────────────────────────────────────────
    "input_boolean": {"turn_on", "turn_off", "toggle"},
    "input_number":  {"set_value"},
    "input_select":  {"select_option", "select_next", "select_previous"},
    # ── HA 原生辅助实体 ──────────────────────────────────────────────────────
    "number":        {"set_value"},
    "select":        {"select_option"},
    "button":        {"press"},
    # ── 注意：lock / alarm_control_panel / garage_door 属 CRITICAL 级别，
    #    不在此白名单中（Stage 2 会将其拒绝），避免 AI 误控安防设备。
    #    如需支持，须在产品层单独设计确认流程后再添加。
}

# ── 参数范围检查 ──────────────────────────────────────────────────────────────

_PARAM_RANGES: dict[str, tuple[float, float]] = {
    "brightness_pct": (0, 100),
    "brightness": (0, 255),
    "temperature": (10, 35),        # climate 目标温度（°C），仅在 climate domain 验证
    "color_temp_kelvin": (1000, 10000),  # 灯光色温（Kelvin）
    "color_temp": (153, 500),       # 灯光色温（mireds，HA 原生单位）
    "position": (0, 100),
    "percentage": (0, 100),
    "volume_level": (0.0, 1.0),
    "humidity": (0, 100),           # 加湿器/除湿器目标湿度
    "target_humidity": (0, 100),
    "speed": (0, 100),              # 风扇转速百分比
    "fan_speed": (0, 100),
}

# temperature 参数仅对 climate domain 进行范围检查；
# light domain 使用 color_temp_kelvin / color_temp，不应触发气候温度校验。
_CLIMATE_ONLY_PARAMS = {"temperature"}


class IntentVerifier:
    """
    双阶段意图验证管道。

    使用方法：
        verifier = IntentVerifier(hass, device_info, occ_map)
        clean_actions, rejected = verifier.verify(raw_actions, trigger_room)
    """

    def __init__(
        self,
        hass,
        device_info: dict,
        occ_map: dict | None = None,
        sys_log_func: Callable | None = None,
        suppress_check_func: Callable | None = None,
    ):
        """
        Args:
            hass: Home Assistant 实例
            device_info: 当前注册的设备信息字典 {entity_id: {name, room, ...}}
            occ_map: 当前区域在场状态 {room: [(sensor_id, state), ...]}
            sys_log_func: 外部系统日志函数（注入自 coordinator._sys_log）
            suppress_check_func: 修正历史查询函数，签名为
                (entity_id: str, service: str, hour: int) -> (bool, int, float)
                由 coordinator._should_suppress_action 注入。
                返回 (suppress, count, score)；suppress=True 时硬拒绝动作。
                None 时跳过修正历史查询。
        """
        self.hass = hass
        self.device_info = device_info
        self._occ_map: dict[str, list[tuple[str, str]]] = occ_map or {}
        self._sys_log = sys_log_func
        self._suppress_check = suppress_check_func

    def _is_adjacent_room(self, room_a: str, room_b: str) -> bool:
        """P1-2: 检查两个房间是否相邻（从 coordinator 注入的拓扑缓存查询）。"""
        topo = getattr(self, "_room_topology", None)
        if not topo:
            # 通过 DOMAIN 直接获取 coordinator，避免遍历 hass.data
            try:
                from .const import DOMAIN
                entry = next(iter(self.hass.data.get(DOMAIN, {}).values()), None)
                if hasattr(entry, "_room_topology_cache"):
                    topo = entry._room_topology_cache
            except Exception:
                pass
        if not topo:
            return False
        return room_b in topo.get(room_a, set())

    def _get_room_person_count(self, room: str) -> int:
        """读取房间人数（基于已注册 sensor 的 person_count 类实体）。"""
        if not room:
            return 0
        room_l = room.lower()
        total = 0
        for eid in self.device_info.keys():
            if not eid.startswith("sensor."):
                continue
            eid_l = eid.lower()
            if (
                "person_count" not in eid_l
                and "people_count" not in eid_l
                and "person_detected" not in eid_l
                and "人数" not in eid
            ):
                continue
            if room_l not in eid_l:
                continue
            st = self.hass.states.get(eid)
            if st is None:
                continue
            try:
                total += int(float(getattr(st, "state", 0) or 0))
            except (TypeError, ValueError):
                continue
        return total

    def _is_blocked_by_locked_people_rule(self, action: dict, action_room: str) -> tuple[bool, str]:
        """P1 人数阈值锁定规则校验（开灯动作）。"""
        if action.get("domain") != "light" or action.get("service") != "turn_on":
            return False, ""

        rules = getattr(self, "_locked_people_rules", []) or []
        if not rules:
            return False, ""

        dev_name = str((self.device_info.get(action.get("entity_id", "")) or {}).get("name", ""))
        eid = str(action.get("entity_id", ""))
        text = f"{dev_name} {eid}".lower()

        for rule in rules:
            rule_room = str(rule.get("room", "") or "")
            if rule_room and action_room and rule_room != action_room:
                continue

            keywords = [str(k).lower() for k in (rule.get("keywords") or []) if str(k).strip()]
            if keywords and not any(k in text for k in keywords):
                continue

            threshold = int(rule.get("threshold", 0) or 0)
            op = str(rule.get("operator", ">=") or ">=")
            people = self._get_room_person_count(action_room or rule_room)

            allowed = True
            if op in (">=", "≥"):
                allowed = people >= threshold
            elif op in (">",):
                allowed = people > threshold
            else:
                allowed = people >= threshold

            if not allowed:
                return True, f"P1人数锁定: 需要{op}{threshold}人，当前{people}人"

        return False, ""

    def _log(self, level: str, msg: str) -> None:
        """内部辅助：同时记录面板日志和原生日志。"""
        if self._sys_log:
            self._sys_log(level, msg)
        else:
            if level == "ERROR": _LOGGER.error(msg)
            elif level == "WARN": _LOGGER.warning(msg)
            else: _LOGGER.info(msg)

    def verify(
        self,
        actions: list[dict],
        trigger_room: str = "",
        is_global_cmd: bool = False,
        cmd_source: str = CMD_SOURCE_SENSOR,
    ) -> tuple[list[dict], list[dict]]:
        """
        执行完整的双阶段验证。

        Args:
            actions: 原始 actions 列表（来自 LLM 输出）
            trigger_room: 触发传感器所在区域（用于区域隔离检查）
            is_global_cmd: True 时跳过区域隔离检查（语音全局指令等）
            cmd_source: 指令来源（CMD_SOURCE_SENSOR / CMD_SOURCE_USER_EXPLICIT 等）
                - USER_EXPLICIT 时，豁免区域隔离和有人区域关灯检查

        Returns:
            (clean_actions, rejected_actions)
              - clean_actions: 通过验证的动作列表
              - rejected_actions: 被拒绝的动作列表（含 reject_reason 字段）
        """
        if not actions:
            return [], []

        try:
            # Stage 1: 语义防火墙
            after_s1, s1_rejected = self._stage1_semantic_check(
                actions, trigger_room, is_global_cmd, cmd_source
            )

            # Stage 2: 物理验证
            clean, s2_rejected = self._stage2_physical_check(after_s1)
        except Exception as exc:
            # Fail-closed：验证器异常时拒绝全部动作，不放行
            self._log("ERROR", f"[意图验证] 验证器内部异常，拒绝全部动作: {exc}")
            rejected_all = [dict(a, reject_reason=f"验证器异常: {exc}") for a in actions]
            return [], rejected_all

        all_rejected = s1_rejected + s2_rejected
        if all_rejected:
            detail = ", ".join(
                "{eid}({reason})".format(
                    eid=a.get("entity_id", "?"),
                    reason=a.get("reject_reason", ""),
                )
                for a in all_rejected
            )
            self._log("INFO", f"[意图验证] 共拒绝 {len(all_rejected)} 个动作: [{detail}]")

        return clean, all_rejected

    def grade_action_safety(self, action: dict) -> int:
        """
        对动作进行安全/成本评级。

        Returns:
            SAFETY_LEVEL_SAFE / SAFETY_LEVEL_HIGH_COST / SAFETY_LEVEL_CRITICAL
        """
        domain = action.get("domain", "")
        if domain in ("light", "cover", "fan", "media_player", "input_boolean", "input_select", "input_button"):
            return SAFETY_LEVEL_SAFE
        
        if domain in ("climate", "vacuum", "water_heater", "humidifier", "dehumidifier"):
            return SAFETY_LEVEL_HIGH_COST
        
        if domain in ("lock", "alarm_control_panel", "garage_door"):
            return SAFETY_LEVEL_CRITICAL
            
        # 兜底：未知领域视为高成本
        return SAFETY_LEVEL_HIGH_COST

    def split_actions_by_safety(self, actions: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
        """
        将动作列表按评级拆分为三组。

        Returns:
            (safe_actions, high_cost_actions, critical_actions)
        """
        safe, high, critical = [], [], []
        for a in actions:
            lvl = self.grade_action_safety(a)
            if lvl == SAFETY_LEVEL_SAFE:
                safe.append(a)
            elif lvl == SAFETY_LEVEL_HIGH_COST:
                high.append(a)
            else:
                critical.append(a)
        return safe, high, critical

    # ── Stage 1: 语义防火墙 ─────────────────────────────────────────────────

    def _stage1_semantic_check(
        self,
        actions: list[dict],
        trigger_room: str,
        is_global_cmd: bool,
        cmd_source: str = CMD_SOURCE_SENSOR,
    ) -> tuple[list[dict], list[dict]]:
        """
        Stage 1 语义合理性检查。

        检查项（当前状态）：
          1. entity_id 不在 device_info → 拒绝（防幻觉，永久保留）
          2. 同一 entity 同时有 turn_on + turn_off → 拒绝矛盾指令（永久保留）
          3. 区域隔离：非豁免跨区动作硬拒绝；
             豁免域名（climate/cover/scene/script/vacuum）及 USER_EXPLICIT/is_global 仍放行。
          4. 有人区域 + 关灯：AI 主动关灯硬拒绝；USER_EXPLICIT 关灯放行。
          5. 修正历史：用户多次纠正过的动作硬拒绝（USER_EXPLICIT 豁免）。

        USER_EXPLICIT 豁免说明：
          用户主动发出的指令（面板/语音/展厅一次性）应被优先执行。
          跨区控制（如"展厅有人→开客厅灯带"）和显式关灯命令不受自动规则拦截。
        """
        clean: list[dict] = []
        rejected: list[dict] = []

        # 预先构建：已占用区域 set 和无人区域 set
        occupied_rooms: set[str] = set()
        empty_rooms: set[str] = set()
        for room, sensors in self._occ_map.items():
            if any(s in ("unknown", "unavailable") for _, s in sensors):
                occupied_rooms.add(room)  # fail-closed: 占用不确定按有人处理
            elif any(s == "on" for _, s in sensors):
                occupied_rooms.add(room)
            elif all(s == "off" for _, s in sensors):
                empty_rooms.add(room)

        # 检测自相矛盾：同一 entity 同时出现 turn_on 和 turn_off
        entity_services: dict[str, list[str]] = {}
        for a in actions:
            eid = a.get("entity_id", "")
            svc = a.get("service", "")
            entity_services.setdefault(eid, []).append(svc)

        contradicted_entities: set[str] = {
            eid for eid, svcs in entity_services.items()
            if "turn_on" in svcs and "turn_off" in svcs
        }

        for action in actions:
            eid = action.get("entity_id", "")
            domain = action.get("domain", "")
            service = action.get("service", "")
            action_room = (self.device_info.get(eid) or {}).get("room", "")

            # 检查 1: entity_id 不在 device_info（防止幻觉）
            if eid not in self.device_info:
                _reason = f"实体不存在: {eid}"
                rejected.append({**action, "reject_reason": _reason})
                continue

            # 检查 2: 自相矛盾指令
            if eid in contradicted_entities:
                _reason = f"同一实体同时 turn_on 和 turn_off，矛盾指令"
                rejected.append({**action, "reject_reason": _reason})
                continue

            # 检查 3: 区域隔离 — 非豁免跨区动作硬拦截
            # 豁免：climate/cover/scene/script/vacuum、USER_EXPLICIT、is_global、相邻房间
            if not action_room and hasattr(self, "_get_entity_area") and eid:
                action_room = self._get_entity_area(eid) or ""
            if not is_global_cmd and trigger_room and action_room and action_room != trigger_room:
                is_exempt = (
                    domain in ("climate", "cover", "scene", "script", "vacuum")
                    or cmd_source == CMD_SOURCE_USER_EXPLICIT
                    or action.get("is_global", False)
                    or self._is_adjacent_room(trigger_room, action_room)
                )
                if not is_exempt:
                    _reason = (
                        f"跨区操控拒绝: 触发={trigger_room}，设备区域={action_room}"
                    )
                    self._log("WARN",
                        f"[意图验证] ⛔{eid}: {_reason}"
                    )
                    rejected.append({**action, "reject_reason": _reason})
                    continue

            # 检查 4: 有人区域 + 关灯 — AI 主动关灯硬拦截（USER_EXPLICIT 豁免）
            if domain == "light" and service == "turn_off" and action_room in occupied_rooms:
                if cmd_source == CMD_SOURCE_USER_EXPLICIT:
                    self._log("WARN",
                        f"[意图验证] 用户主动关灯 {eid}，区域 {action_room} 有人在场，已放行（USER_EXPLICIT）"
                    )
                else:
                    _reason = f"有人在场关灯拒绝: 区域 {action_room} 有人在场"
                    self._log("WARN",
                        f"[意图验证] ⛔{eid}: {_reason}"
                    )
                    rejected.append({**action, "reject_reason": _reason})
                    continue

            # 检查 5: P1 人数阈值锁定（开灯）
            _blocked, _blocked_reason = self._is_blocked_by_locked_people_rule(action, action_room)
            if _blocked:
                self._log("WARN", f"[意图验证] ⛔{eid}: {_blocked_reason}")
                rejected.append({**action, "reject_reason": _blocked_reason})
                continue

            # 检查 6: 修正历史硬拦截 — 用户多次纠正过的动作直接拒绝（USER_EXPLICIT 豁免）
            # _suppress_check 返回 True 时表示用户曾多次纠正该操作，代码层硬拦截。
            if (
                service == "turn_on"
                and cmd_source != CMD_SOURCE_USER_EXPLICIT
                and self._suppress_check is not None
            ):
                _cur_presence = "empty"
                if action_room in occupied_rooms:
                    _cur_presence = "occupied"
                elif action_room not in empty_rooms:
                    _cur_presence = "any"

                try:
                    _suppress, _count, _score = self._suppress_check(
                        eid, service, current_presence=_cur_presence, room=action_room
                    )
                except TypeError:
                    _suppress, _count, _score = self._suppress_check(eid, service)

                if _suppress:
                    _reason = (
                        f"修正历史抑制: 用户曾纠正{_count}次(权重={_score:.2f}) "
                        f"在场={_cur_presence}"
                    )
                    self._log("WARN",
                        f"[意图验证] ⛔{eid}: {_reason}"
                    )
                    rejected.append({**action, "reject_reason": _reason})
                    continue

            clean.append(action)

        return clean, rejected

    # ── Stage 2: 物理验证器 ──────────────────────────────────────────────────

    def _stage2_physical_check(
        self,
        actions: list[dict],
    ) -> tuple[list[dict], list[dict]]:
        """
        Stage 2 确定性物理验证。

        检查项：
          1. domain 与 entity_id 前缀是否匹配
          2. service 是否在该 domain 的白名单中
          3. params 中的数值参数是否在合法范围内
        """
        clean: list[dict] = []
        rejected: list[dict] = []

        for action in actions:
            eid = action.get("entity_id", "")
            domain = action.get("domain", "")
            service = action.get("service", "")
            params = action.get("params") or {}

            # 检查 1: domain 与 entity_id 前缀匹配
            expected_domain = eid.split(".")[0] if "." in eid else ""
            if not expected_domain:
                _reason = f"entity_id 格式错误（缺少 domain 前缀）: {eid}"
                rejected.append({**action, "reject_reason": _reason})
                continue
            if not domain:
                domain = expected_domain
                action["domain"] = domain
            if expected_domain != domain:
                _reason = f"domain 不匹配: entity_id 前缀={expected_domain}，声明 domain={domain}"
                rejected.append({**action, "reject_reason": _reason})
                continue

            # 检查 2: service 合法性
            # 未知 domain 不在白名单时，同样拒绝不认识的 service（fail-closed）
            valid_svcs = _VALID_SERVICES.get(domain, set())
            if not valid_svcs or service not in valid_svcs:
                _reason = (
                    f"非法 service '{service}'（domain={domain}，未在服务白名单中）"
                    if not valid_svcs
                    else f"非法 service '{service}'（domain={domain}）"
                )
                rejected.append({**action, "reject_reason": _reason})
                continue

            # 检查 3: 参数范围（传入 domain 以跳过非适用参数）
            param_error = self._check_param_ranges(params, domain)
            if param_error:
                _reason = f"参数超出范围: {param_error}"
                rejected.append({**action, "reject_reason": _reason})
                continue

            clean.append(action)

        return clean, rejected

    def _check_param_ranges(self, params: dict[str, Any], domain: str = "") -> str:
        """
        检查 params 中的数值参数是否在合法范围内。

        Args:
            params: action 的 params 字典
            domain: 动作所属 domain（用于跳过与当前 domain 不匹配的参数校验）

        Returns:
            错误描述字符串，通过则返回空字符串
        """
        for key, value in params.items():
            if key not in _PARAM_RANGES:
                continue
            # temperature 范围仅适用于 climate domain；
            # light 等 domain 应使用 color_temp_kelvin / color_temp，
            # 若误用 temperature 键则不做范围拦截，避免误杀。
            if key in _CLIMATE_ONLY_PARAMS and domain != "climate":
                continue
            try:
                v = float(value)
            except (TypeError, ValueError):
                return f"{key} 不是数值: {value!r}"
            lo, hi = _PARAM_RANGES[key]
            if not (lo <= v <= hi):
                return f"{key}={v} 超出合法范围 [{lo}, {hi}]"
        return ""
