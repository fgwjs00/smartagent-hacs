"""
ActionsMixin — 动作执行层。
负责：动作标准化、实体模糊匹配、Action Router（脚本/场景路由）、
      服务调用保护、动作验证与自动重试。
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from homeassistant.helpers.event import async_call_later
from homeassistant.exceptions import ServiceNotFound

from .const import (
    ACTION_PARAM_KEYS_COLOR,
    ACTION_PARAM_KEYS_LIGHT_SCENE,
    ACTION_PARAM_KEYS_USELESS_WHEN_OFF,
    MODE_SHOWROOM,
)

_LOGGER = logging.getLogger(__name__)


class ActionsMixin:
    """Mixin: 动作执行 — 路由 / 保护 / 验证 / 重试。"""

    # 合法的设备管辖域值（DatabaseMixin 也定义了此常量，MRO 取第一个即可）
    _VALID_CONTROL_MODES = frozenset({"ai", "ha", "shared"})

    # 设备管辖域标签（用于日志）
    _CONTROL_MODE_LABELS = {"ai": "AI全权", "ha": "HA优先", "shared": "共享"}

    # 安全白名单：AI 允许操作的 HA 域和禁止调用的危险服务
    _ALLOWED_DOMAINS = frozenset({
        "light", "switch", "climate", "cover", "fan",
        "media_player", "script", "scene",
        "input_boolean", "input_number", "input_select",
    })
    _BLOCKED_SERVICES = frozenset({
        "reload", "restart", "stop", "delete", "remove",
        "enable", "disable",
    })

    # 动作验证参数
    _ACTION_VERIFY_DELAY = 5    # 执行后 N 秒回查状态
    _ACTION_RETRY_MAX = 1       # 最大自动重试次数
    _VERIFY_QUEUE_MAX = 50      # 待验证队列上限
    _VERIFY_EXPIRE_SEC = 120    # 超过 N 秒未验证完成的条目强制丢弃

    # 场景/脚本重复执行冷却
    _SCENE_COOLDOWN = 60        # 同一场景/脚本 N 秒内不重复执行

    # ── 动作标准化 ────────────────────────────────────────────────────────────

    def _normalize_action(self, action: dict) -> dict:
        """Normalize AI action dict to canonical field names."""
        _target = action.get("target")
        _target_eid = _target.get("entity_id", "") if isinstance(_target, dict) else ""
        entity_id = action.get("entity_id") or action.get("entity") or _target_eid
        service_raw = action.get("service") or action.get("action") or action.get("command") or ""
        # Support "light.turn_on" format
        if "." in service_raw and not action.get("domain"):
            parts = service_raw.split(".", 1)
            domain = parts[0]
            service = parts[1]
        else:
            domain = action.get("domain") or (entity_id.split(".")[0] if entity_id else "")
            service = service_raw
        params = action.get("params") or action.get("data") or action.get("service_data") or {}

        # entity_id 校验与修正：AI 有时返回设备名而非合法 entity_id
        if entity_id and not self.hass.states.get(entity_id):
            matched = self._fuzzy_match_entity(entity_id, domain)
            if matched:
                self._sys_log("WARN", f"[动作修正] AI 返回无效 entity_id「{entity_id}」→ 修正为「{matched}」")
                entity_id = matched
                domain = entity_id.split(".")[0]
            else:
                self._sys_log("ERROR", f"[动作修正] AI 返回无效 entity_id「{entity_id}」且无法匹配到已知设备，将跳过")
                entity_id = ""  # 置空使守卫生效，真正跳过

        # brightness_pct=0 的 turn_on 等同于关灯，规范化为 turn_off 以统一走守卫逻辑
        # AI 有时用此手段绕过 P1 "禁止 turn_off 展厅灯" 的限制，必须在此拦截
        if service == "turn_on" and domain == "light" and params.get("brightness_pct") == 0:
            self._sys_log("WARN",
                f"[动作规范化] {entity_id} turn_on(brightness_pct=0) 等效关灯，转换为 turn_off"
                "（防止绕过 P1 保护）")
            service = "turn_off"
            params = {}

        # turn_off / close 时清理无意义的亮度/温度参数
        if service in ("turn_off", "close_cover", "lock") and params:
            cleaned = {k: v for k, v in params.items() if k not in ACTION_PARAM_KEYS_USELESS_WHEN_OFF}
            if len(cleaned) != len(params):
                self._sys_log("INFO", f"[动作清理] {service} 移除无效参数: "
                              f"{set(params.keys()) - set(cleaned.keys())}")
            params = cleaned

        return {"entity_id": entity_id, "domain": domain, "service": service,
                "params": params, "reason": action.get("reason", ""),
                "delay_seconds": action.get("delay_seconds", 0)}

    def _fuzzy_match_entity(self, bad_id: str, domain_hint: str) -> str | None:
        """Try to match a bad entity_id (device name) to a real entity_id."""
        bad_lower = bad_id.lower().replace("（", "(").replace("）", ")")
        # 先按空格/括号拆分，再按 . 和 _ 进一步拆分（支持 light.zhan_ting_zhong_jian → zhong, jian 等片段）
        raw_parts = bad_lower.replace("[", " ").replace("]", " ").replace("(", " ").replace(")", " ").split()
        keywords: list[str] = []
        for part in raw_parts:
            # 按 . 和 _ 拆分，取 长度≥2 的片段
            sub = [s for s in part.replace(".", "_").split("_") if len(s) >= 2]
            keywords.extend(sub if sub else [part])
        keywords = list(dict.fromkeys(keywords))  # 去重保序
        best_match = ""
        best_score = 0
        for eid, info in self.device_info.items():
            if domain_hint and not eid.startswith(domain_hint + "."):
                continue
            name = info.get("name", "").lower()
            score = sum(1 for kw in keywords if kw in name or kw in eid.lower())
            if score > best_score:
                best_score = score
                best_match = eid
        # script/scene 不在 device_info 中，需额外搜索 HA 状态
        if not best_match and domain_hint in ("script", "scene"):
            for state in self.hass.states.async_all(domain_hint):
                name = (state.attributes.get("friendly_name") or "").lower()
                score = sum(1 for kw in keywords if kw in name or kw in state.entity_id.lower())
                if score > best_score:
                    best_score = score
                    best_match = state.entity_id
        return best_match if best_score > 0 else None

    # ── Action Router ─────────────────────────────────────────────────────────

    def _find_associated_script(self, entity_id: str, service: str) -> str | None:
        """Action Router: 根据设备 entity_id 和 service 查找最匹配的 HA 脚本/场景。

        优先级：
          1. 激活的 AI 场景（包含此设备 + 当前时段匹配）→ 直接路由至 scene.ai_<id>
          2. 人工 HA 脚本/场景（名称模糊匹配）
        """
        import json as _json
        from datetime import datetime as _dt
        from .const import AI_SCENE_STATUS_ACTIVE, ai_scene_matches_now

        is_on = "turn_on" in service or "open" in service

        # ── 1. 检查激活的 AI 场景（时段匹配 + 包含此设备 + 方向一致）────────
        # 使用 ai_scene_matches_now() 统一星期格式（SQLite %w，0=日），
        # 修复之前直接用 Python weekday（0=Mon）导致工作日匹配失效的 Bug。
        if is_on:
            _now = _dt.now()
            for sc in getattr(self, "_ai_scenes_cache", []):
                if sc.get("status") != AI_SCENE_STATUS_ACTIVE:
                    continue
                if not ai_scene_matches_now(sc, _now.hour, _now.weekday()):
                    continue
                # 包含目标设备检查
                try:
                    ents = _json.loads(sc.get("entities_json", "[]"))
                except Exception:
                    continue
                if not any(e.get("entity_id") == entity_id for e in ents):
                    continue
                # 确认对应 HA 场景实体存在
                ha_eid = f"scene.ai_{sc['id']}"
                if self.hass.states.get(ha_eid) is not None:
                    self._sys_log(
                        "INFO",
                        f"[Action Router] {entity_id} → 匹配激活 AI 场景 {sc['name']} → {ha_eid}"
                    )
                    return ha_eid

        # ── 2. 搜索 HA 脚本和人工场景（原有逻辑）────────────────────────────
        dev = self.device_info.get(entity_id, {})
        dev_name = dev.get("name", "").lower()
        dev_room = dev.get("room", "").lower()
        domain = entity_id.split(".")[0]
        is_off = "turn_off" in service or "close" in service
        on_kw = ("开", "turn_on", "open", "亮", "_on")
        off_kw = ("关", "turn_off", "close", "暗", "_off")
        candidates = self._ha_scripts + self._ha_scenes
        best: str | None = None
        best_score = 0
        for cand in candidates:
            ceid = cand["entity_id"]
            cname = cand["name"].lower()
            score = 0
            # 脚本/场景名含设备名 → 强匹配（设备名至少 2 字符才视为有效匹配）
            if dev_name and len(dev_name) >= 2 and dev_name in cname:
                score += 10
            # 脚本/场景名含房间名 → 中等匹配（房间名至少 2 字符）
            elif dev_room and len(dev_room) >= 2 and dev_room in cname:
                score += 5
            # 方向匹配（开/关）
            if is_on and any(k in cname for k in on_kw):
                score += 3
            elif is_off and any(k in cname for k in off_kw):
                score += 3
            # 域名匹配
            if domain in cname or (domain == "light" and "灯" in cname):
                score += 2
            if score >= 8 and score > best_score:
                best_score = score
                best = ceid
        return best

    # ── 动作执行主入口 ────────────────────────────────────────────────────────

    async def _execute_actions(
        self,
        actions: list,
        trigger_summary: str = "",
        scene_desc: str = "",
        confidence: int = 0,
        trigger_room: str = "",
        is_global_cmd: bool = False,
        cmd_source: str = "",
    ) -> int:
        """Execute a list of AI actions with transaction tracking."""
        import json as _json

        if not actions:
            return 0

        # ── 区域隔离守卫校验 (AI-03) ──
        # 若有明确触发区域且非全局指令，过滤掉不属于该区域且非全局属性的动作
        # 允许的例外：巡检、位置变化、Frigate视觉触发（通常涉及多区域）
        # USER_EXPLICIT（用户主动指令/一次性场景/语音）豁免区域隔离，与 IntentVerifier 保持一致
        _SKIP_ISOLATION = ("巡检", "位置变化", "视觉检测")
        try:
            from .intent_verifier import CMD_SOURCE_USER_EXPLICIT as _USER_EXPLICIT
        except Exception:
            _USER_EXPLICIT = "user_explicit"
        _is_user_explicit = (cmd_source == _USER_EXPLICIT)
        should_isolate = bool(
            trigger_room
            and not is_global_cmd
            and not _is_user_explicit
            and not any(k in trigger_summary for k in _SKIP_ISOLATION)
        )
        
        if should_isolate:
            filtered_actions = []
            for a in actions:
                eid = a.get("entity_id") or a.get("entity")
                if not eid: continue
                dev_info = self.device_info.get(eid, {})
                dev_room = dev_info.get("room", "").strip()
                if not dev_room and hasattr(self, "_get_entity_area"):
                    dev_room = self._get_entity_area(eid)
                
                # 隔离规则（与 IntentVerifier._stage1_semantic_check 保持完全一致）：
                # 1. 设备所在房间匹配触发房间 -> 放行
                # 2. 豁免域 (climate/cover/scene/script/vacuum) -> 放行
                # 3. action 本身标记了 is_global (LLM 合法跨区指令) -> 放行
                # 4. 房间信息经 device_info + Registry 双重查找后仍为空 -> 放行（全局设备）
                #    注意：仅靠 device_info 为空就豁免是不安全的，已在 _get_entity_area 回退后才豁免
                _domain = (a.get("domain") or eid.split(".")[0]) if isinstance(eid, str) else ""
                is_exempt = (
                    not dev_room   # device_info + HA registry 均无区域信息，视为全局设备
                    or dev_room == trigger_room
                    or _domain in ("climate", "cover", "scene", "script", "vacuum")
                    or a.get("is_global", False)
                )

                if is_exempt:
                    filtered_actions.append(a)
                else:
                    self._sys_log("WARN", f"[区域隔离] 拦截跨区域操作: {eid}(属于{dev_room})，本次触发于「{trigger_room}」")
            
            if len(filtered_actions) < len(actions):
                self._sys_log("INFO", f"[区域隔离] 动作集已精简: {len(actions)} -> {len(filtered_actions)} (拦截了 {len(actions)-len(filtered_actions)} 个跨区域动作)")
                actions = filtered_actions

        if not actions:
            return 0

        # ── 自触发保护快速预过滤 ────────────────────────────────────────────────
        # 在动作执行前提前过滤掉触发了本次推理的可控设备，避免浪费完整 LLM 推理后才在
        # _do_call_service 逐设备拦截（该拦截仍保留作最后一道防线）。
        # 注意：仅过滤 turn_on（防止触发灯被 AI 原地开回）；turn_off 通常是合理的关灯指令。
        if self._batch_trigger_controllable:
            _pre_filtered = []
            _pre_blocked = []
            for _a in actions:
                _eid = _a.get("entity_id") or _a.get("entity")
                _svc = _a.get("service", "")
                if _eid and _svc == "turn_on" and _eid in self._batch_trigger_controllable:
                    _pre_blocked.append(_eid)
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
                return 0

        # ── 1. 执行前：快照目标设备当前状态 ─────────────────────────────────
        pre_states: dict[str, str] = {}
        for raw in actions:
            eid = raw.get("entity_id", "")
            if eid and isinstance(eid, str) and "." in eid:
                st = self.hass.states.get(eid)
                if st:
                    pre_states[eid] = st.state

        # ── 2. 写入事务记录（pending）────────────────────────────────────────
        txn_id: int = await self.hass.async_add_executor_job(
            self._begin_transaction_db,
            trigger_summary,
            scene_desc,
            confidence,
            len(actions),
            _json.dumps(pre_states, ensure_ascii=False),
            _json.dumps(actions, ensure_ascii=False, default=str),
        )
        if not txn_id:
            self._sys_log("WARN", "[事务] 事务记录写入失败（DB锁/磁盘等），已中止动作执行以保持审计一致性")
            return 0

        # ── 3. 执行所有动作，收集结果 ────────────────────────────────────────
        executed = 0
        blocked_count = 0
        failed_count = 0
        results: list[dict] = []

        # P1 优化：提前获取在场状态、展厅灯光层级与人数锁定规则，避免循环内重复调用
        occ_map = self._get_room_occupancy_map()
        people_counts_by_room = self._get_room_person_counts() if hasattr(self, "_get_room_person_counts") else {}
        parsed_people_rules = self._build_locked_people_rules() if hasattr(self, "_build_locked_people_rules") else []

        _now = datetime.now()
        _now_min = _now.hour * 60 + _now.minute
        is_working_hour = self.showroom_biz_start_min <= _now_min < self.showroom_biz_end_min
        
        # 预取展厅有人状态
        is_showroom_occupied = False
        showroom_light_tiers = {}
        if self._mode == MODE_SHOWROOM:
            _showroom_area = self.showroom_area_name
            showroom_sensors = occ_map.get(_showroom_area, []) if _showroom_area else []
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

        # ── P2: 动作节拍控制 (Action Pacing) ──
        # 若动作数较多，每个动作之间加入微小延迟，缓解 Zigbee 拥塞
        _is_bulk = len(actions) > 5
        _pacing_delay = 0.2 if _is_bulk else 0.0

        for idx, raw_action in enumerate(actions):
            action_seq = idx + 1
            if idx > 0 and _pacing_delay > 0:
                await asyncio.sleep(_pacing_delay)

            action = self._normalize_action(raw_action)
            domain = action.get("domain")
            service = action.get("service")
            entity_id = action.get("entity_id")
            params = action.get("params", {})
            reason = action.get("reason", "")
            try:
                delay = max(0, int(action.get("delay_seconds", 0)))
            except (ValueError, TypeError):
                delay = 0
            if not all([domain, service, entity_id]):
                self._sys_log("WARN", f"[动作] 字段缺失，跳过: {raw_action} → 标准化后: {action}")
                continue
            if domain not in self._ALLOWED_DOMAINS:
                self._sys_log("WARN", f"[安全] 拒绝 AI 操作不在白名单中的域: {domain}.{service}({entity_id})")
                continue
            if service in self._BLOCKED_SERVICES:
                self._sys_log("WARN", f"[安全] 拒绝 AI 执行危险服务: {domain}.{service}({entity_id})")
                continue
            # ─── 设备管辖域 (Action Router) ───────────────────────────────────
            if domain not in ("script", "scene"):
                ctrl_mode = self.device_info.get(entity_id, {}).get("control_mode", "shared")
                if ctrl_mode == "ha":
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
                    if ctrl_mode == "shared" and domain in ("light", "switch", "cover", "fan", "climate") \
                            and service in ("turn_on", "turn_off", "open", "close", "toggle") \
                            and not _is_simple_off_with_params and not _has_precise_light_params:
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

            # script / scene 直接调用 HA 服务，不走 _do_call_service 的覆盖保护逻辑
            if domain in ("script", "scene"):
                # 拦截全局场景：entity_id 的本地部分（domain 后）以全局关键词开头才拦截
                # 例如 scene.quan_bu_off / scene.all_off → 拦截
                # 例如 scene.yi_lou_zhan_ting_suo_you_deng_guang_0_scene_0 → 放行（含房间前缀）
                _eid_local = entity_id.split(".", 1)[-1].lower()
                _GLOBAL_KW = ("turn_all", "all_on", "all_off", "quan_bu", "suo_you", "全部", "所有")
                if any(_eid_local == kw or _eid_local.startswith(kw + "_") for kw in _GLOBAL_KW):
                    self._sys_log("WARN", f"[全局场景拦截] 拒绝执行 {entity_id}（以全局关键词开头），请使用区域场景替代")
                    continue
                # 场景/脚本人员在场守卫（家庭模式）
                if self._mode != MODE_SHOWROOM:
                    scene_room = self._guess_scene_room(entity_id)
                    if scene_room:
                        sensors = occ_map.get(scene_room, [])
                        if sensors:
                            occupied = any(s == "on" for _, s in sensors)
                            uncertain = any(s in ("unknown", "unavailable") for _, s in sensors)
                            if not occupied and not uncertain:
                                sensor_str = ", ".join(f"{eid}={s}" for eid, s in sensors[:2])
                                self._sys_log("WARN", f"[场景守卫] 拒绝 {domain}.turn_on({entity_id})：区域「{scene_room}」无人（{sensor_str}）")
                                continue
                # 场景/脚本重复执行冷却
                now_ts = time.time()
                last_exec = self._scene_last_exec.get(entity_id, 0)
                if now_ts - last_exec < self._SCENE_COOLDOWN:
                    remain = int(self._SCENE_COOLDOWN - (now_ts - last_exec))
                    self._sys_log("INFO", f"[场景冷却] {entity_id} 距上次执行 {int(now_ts - last_exec)}s < {self._SCENE_COOLDOWN}s，跳过（{remain}s 后可再执行）")
                    continue
                self._sys_log("INFO", f"[动作] 场景/脚本通过前置守卫，转交统一保护链: {domain}.{service}({entity_id})")

            self._sys_log("INFO", f"[动作] 准备执行: {domain}.{service}({entity_id}) params={params} reason={reason}")
            state = self.hass.states.get(entity_id)
            if state:
                if service == "turn_off" and state.state == "off":
                    self._sys_log("INFO", f"[动作] 跳过(已是off): {entity_id}")
                    results.append({"entity_id": entity_id, "service": service, "status": "skip", "msg": "already off"})
                    continue
                if service == "turn_on" and state.state == "on" and not params:
                    self._sys_log("INFO", f"[动作] 跳过(已是on): {entity_id}")
                    results.append({"entity_id": entity_id, "service": service, "status": "skip", "msg": "already on"})
                    continue
            # 人员在场守卫：light/switch turn_on 前确认区域有人（仅家庭模式）
            if domain in ("light", "switch") and self._mode != MODE_SHOWROOM:
                guard_blocked, guard_reason = self._occupancy_guard_check(entity_id, service)
                if guard_blocked:
                    self._sys_log("WARN", f"[人员守卫] 拒绝 {domain}.turn_on({entity_id})：{guard_reason}（无人区域禁止开灯）")
                    blocked_count += 1
                    results.append({"entity_id": entity_id, "service": service, "status": "blocked", "msg": guard_reason})
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
            # 展厅灯 P1 铁律硬保护：展厅模式下上班时间实施分层保护
            # 这是为了让 P1 铁律更智能：有人时全保，无人时按学习到的层级（Core/Display/Auxiliary）进行差异化保护
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

                if _is_showroom_light:
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
                        # 【非营业时间 + 无人状态】完全释放 P1 保护，允许 AI 关闭所有灯光
                        self._sys_log("INFO", f"[展厅下班] 非营业时间且无人，放行对 {entity_id} 的操作")

            # 关灯安全守卫：light/switch turn_off 前双重确认区域无人
            # 因 Frigate 存在漏检，优先以物理人体传感器为准；任意一路检测到有人则阻止关灯
            if domain in ("light", "switch") and self._mode != MODE_SHOWROOM:
                off_blocked, off_reason = self._turnoff_presence_guard(entity_id, service)
                if off_blocked:
                    self._sys_log("WARN",
                        f"[关灯守卫] 阻止 {domain}.turn_off({entity_id})：{off_reason}")
                    blocked_count += 1
                    results.append({"entity_id": entity_id, "service": service,
                                    "status": "blocked_person", "msg": off_reason})
                    continue
            if entity_id in self._active_timers:
                try:
                    self._active_timers[entity_id]()
                except Exception as exc:
                    _LOGGER.debug("[Actions] 取消定时任务失败 %s: %s", entity_id, exc)
                del self._active_timers[entity_id]
            if delay > 0:
                # 在闭包中捕获 scene_desc/trigger_summary，保证延迟执行时仍用正确的上下文
                # 避免并发推理时 self._current_scene_desc 被其他房间的推理覆盖
                def _delayed(
                    d: str, s: str, eid: str, p: dict, r: str,
                    sc: str, trig: str, txid: int, aseq: int, _: datetime,
                ) -> None:
                    self.hass.async_create_task(
                        self._do_call_service(d, s, eid, p, r, sc, trig, txid, aseq)
                    )

                handle = async_call_later(
                    self.hass, delay,
                    lambda dt, d=domain, s=service, e=entity_id, p=params, r=reason,
                           sc=scene_desc, trig=trigger_summary, txid=txn_id, aseq=action_seq:
                        _delayed(d, s, e, p, r, sc, trig, txid, aseq, dt),
                )
                self._active_timers[entity_id] = handle
                executed += 1  # 延迟动作视为已调度
                results.append({"entity_id": entity_id, "service": service, "status": "delayed", "delay": delay})
            else:
                ok = await self._do_call_service(
                    domain, service, entity_id, params, reason, scene_desc, trigger_summary, txn_id, action_seq
                )
                if ok:
                    executed += 1
                    results.append({"entity_id": entity_id, "service": service, "status": "ok"})
                else:
                    failed_count += 1
                    results.append({"entity_id": entity_id, "service": service, "status": "blocked_or_error"})

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
            # 刷新内存事务缓存以便前端立即显示
            self._transactions_cache = await self.hass.async_add_executor_job(
                self._query_recent_transactions, 30
            )
        return executed

    # ── 服务调用 + 保护机制 ───────────────────────────────────────────────────

    async def _do_call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        params: dict,
        reason: str,
        scene_desc: str = "",
        trigger_text: str = "",
        transaction_id: int = 0,
        action_seq: int = 0,
    ) -> bool:
        """Call HA service and record AI action for override detection. Returns True if executed.

        Args:
            scene_desc:   本次推理的场景描述，写入 _last_ai_actions 供纠错 UI 展示。
                          并发推理时通过参数传递，避免多房间竞争 self._current_scene_desc。
            trigger_text: 本次推理的触发文本，同上。
        """
        state = self.hass.states.get(entity_id)
        if state and service == "turn_off" and state.state == "off":
            return True
        # 自触发保护：如果该设备的状态变化触发了本次推理，禁止 AI 操作同一设备
        if entity_id in self._batch_trigger_controllable:
            self._sys_log("WARN", f"[自触发保护] {entity_id} 触发了本次推理，拒绝 AI 操作该设备 → {service}（防止死循环）")
            return False
        now_ts = time.time()
        # ── 自动化冲突硬拦截：若设备被 HA 自动化管辖且自动化近期执行过，拒绝 AI 操作 ──
        auto_names = self._automation_managed_devices.get(entity_id)
        if auto_names:
            recent_auto = False
            for a_state in self.hass.states.async_all("automation"):
                a_name = a_state.attributes.get("friendly_name", "")
                if a_name not in auto_names:
                    continue
                last_triggered = a_state.attributes.get("last_triggered")
                if last_triggered:
                    try:
                        if hasattr(last_triggered, "timestamp"):
                            lt_ts = last_triggered.timestamp()
                        else:
                            from datetime import datetime as _dt
                            lt_ts = _dt.fromisoformat(str(last_triggered).replace("Z", "+00:00")).timestamp()
                        if now_ts - lt_ts < self._AUTOMATION_EXEC_WINDOW:
                            recent_auto = True
                            self._sys_log("WARN", f"[自动化避让] {entity_id} 被自动化「{a_name}」管辖，"
                                          f"该自动化 {int(now_ts - lt_ts)}s 前刚触发，AI 退让 → {service}（{self._AUTOMATION_EXEC_WINDOW}s 窗口）")
                            break
                    except Exception as exc:
                        _LOGGER.debug("[Actions] 自动化避让时间解析失败: %s", exc)
            if recent_auto:
                return False
        # ── 优先级仲裁（P0-P4 分级控制）──
        from .const import MODE_HOME, SOURCE_AI_INFER, SOURCE_AI_RULE
        ai_source = SOURCE_AI_INFER
        if "🔒" in reason or "锁定" in reason:
            ai_source = SOURCE_AI_RULE

        # P0 全局安全抑制在任何模式下都必须执行
        if time.time() < self._global_suppress_until:
            remaining = int(self._global_suppress_until - time.time())
            self._sys_log("WARN", f"[P0 全局抑制] {self._global_suppress_reason}（剩余 {remaining}s）→ 拒绝 {entity_id}.{service}")
            return False

        if self._mode == MODE_HOME:
            allowed, arb_reason = self._arbitrate(entity_id, ai_source, service, params)
            if not allowed:
                self._sys_log("WARN", arb_reason)
                return False

            # 兼容旧的用户覆盖保护（对未接入优先级系统的边界情况兜底）
            with self._user_overrides_lock:
                override = self._user_overrides.get(entity_id)
            if override:
                age = now_ts - override["time"]
                if age < self._USER_OVERRIDE_PROTECTION:
                    user_off = override["state"] in self._OFF_STATES
                    ai_on = "turn_on" in service or "open" in service
                    ai_off = "turn_off" in service or "close" in service
                    reversing = (user_off and ai_on) or (not user_off and ai_off)
                    if reversing:
                        self._sys_log("WARN", f"[保护] 用户 {int(age)}s 前手动将 {entity_id} 设为 {override['state']}，"
                                      f"拒绝 AI 反向操作 → {service}（剩余保护 {int(self._USER_OVERRIDE_PROTECTION - age)}s）")
                        return False
                else:
                    with self._user_overrides_lock:
                        self._user_overrides.pop(entity_id, None)
        self._last_inference[entity_id] = now_ts
        ai_new_state = "on" if "turn_on" in service else "off"
        self._last_ai_actions[entity_id] = {
            "state": ai_new_state,
            "time": now_ts,
            "service": f"{domain}.{service}",
            "scene": scene_desc,
            "trigger": trigger_text,
        }
        # 记录 AI 操作的优先级（供后续仲裁使用）
        self._record_device_operation(entity_id, ai_source, ai_new_state, params)
        # AI 成功执行时清除该设备的用户覆盖记录
        with self._user_overrides_lock:
            self._user_overrides.pop(entity_id, None)
        safe_params = {k: v for k, v in params.items() if k != "entity_id"}
        # HA 2024+ 已废弃 color_temp(mireds)，统一改为 color_temp_kelvin(Kelvin)
        # 若 AI 仍输出旧格式，自动转换以避免 schema 报错
        if "color_temp" in safe_params and "color_temp_kelvin" not in safe_params:
            mired_val = safe_params.pop("color_temp")
            if mired_val and mired_val > 0:
                safe_params["color_temp_kelvin"] = round(1_000_000 / mired_val)
                self._sys_log("INFO", f"[动作] {entity_id} color_temp({mired_val}mireds)"
                              f" → color_temp_kelvin({safe_params['color_temp_kelvin']}K) 自动转换")
        service_data = {**safe_params, "entity_id": entity_id}
        try:
            await self.hass.services.async_call(domain, service, service_data)
            if domain in ("scene", "script") and service == "turn_on":
                self._scene_last_exec[entity_id] = time.time()
        except Exception as call_err:
            err_str = str(call_err).lower()
            # 部分设备不支持某些扩展参数，尝试智能降级：
            # 优先仅剔除色温参数保留亮度，若仍失败再去除全部扩展参数
            extra_keys = [k for k in safe_params]
            if extra_keys and ("extra keys" in err_str or "not allowed" in err_str or "unexpected" in err_str):
                color_keys_present = [k for k in extra_keys if k in ACTION_PARAM_KEYS_COLOR]
                non_color_params = {k: v for k, v in safe_params.items() if k not in ACTION_PARAM_KEYS_COLOR}
                if color_keys_present and non_color_params:
                    # 先尝试：去掉色温，保留亮度等其他参数
                    self._sys_log("WARN", f"[动作] {entity_id} 不支持色温参数 {color_keys_present}，"
                                  f"保留亮度重试: {non_color_params}")
                    try:
                        await self.hass.services.async_call(
                            domain, service, {"entity_id": entity_id, **non_color_params}
                        )
                    except vol.Invalid:
                        # 再退一步：去除全部扩展参数
                        self._sys_log("WARN", f"[动作] {entity_id} 亮度参数也失败，去除全部扩展参数重试")
                        try:
                            await self.hass.services.async_call(domain, service, {"entity_id": entity_id})
                        except ServiceNotFound:
                            raise
                        except Exception as retry_err:
                            self._sys_log("ERROR", f"[动作] {entity_id} 服务调用重试失败: {retry_err}")
                            return False
                    except ServiceNotFound:
                        raise
                    except Exception as retry_err:
                        self._sys_log("ERROR", f"[动作] {entity_id} 保留亮度重试失败: {retry_err}")
                        return False
                else:
                    # 没有可保留的参数，直接裸调用
                    self._sys_log("WARN", f"[动作] {entity_id} 不支持参数 {extra_keys}，去除后重试")
                    try:
                        await self.hass.services.async_call(domain, service, {"entity_id": entity_id})
                    except ServiceNotFound:
                        raise
                    except Exception as retry_err:
                        self._sys_log("ERROR", f"[动作] {entity_id} 服务调用重试失败: {retry_err}")
                        return False
            elif "not found" in err_str or "unknown" in err_str or "does not exist" in err_str:
                self._sys_log("ERROR", f"[动作] {domain}.{service}({entity_id}) 实体/服务不存在，跳过。"
                              f"请检查设备是否在线或名称是否正确。原始错误: {call_err}")
                return False
            else:
                self._sys_log("ERROR", f"[动作] {entity_id} 服务调用失败: {call_err}")
                return False
        self.hass.async_add_executor_job(
            self._record_event, "AI_Action", f"{entity_id} -> {service}",
            entity_id, "on" if "turn_on" in service else "off", "ai", None,
            transaction_id, action_seq,
        )
        # Phase 11.3: 若为 turn_off 且触发文本包含离开/departure，记录该房间冷却时间戳
        # 巡检将在冷却期（5分钟）内跳过对该房间的推理，防止巡检覆盖离开决策
        if service == "turn_off" and trigger_text:
            _trig_lower = trigger_text.lower()
            if any(kw in _trig_lower for kw in ("离开", "departure", "无人", "empty", "人员离开")):
                _room = (self.device_info.get(entity_id) or {}).get("room", "")
                if _room and hasattr(self, "_last_departure_turnoff_time"):
                    self._last_departure_turnoff_time[_room] = time.time()
                    self._sys_log("INFO",
                        f"[冷却保护] {_room} 检测到离开关灯，设置5分钟巡检冷却窗口")
        await self._async_update_status("运行中", f"{self.get_device_name(entity_id)} → {service}（{reason[:30]}）")
        # ── 注册延迟状态验证 ──
        expected = "on" if ("turn_on" in service or "open" in service) else "off"
        if len(self._pending_verifications) < self._VERIFY_QUEUE_MAX:
            self._pending_verifications.append({
                "entity_id": entity_id, "domain": domain, "service": service,
                "expected_state": expected, "reason": reason,
                "fire_time": time.time(), "retry": 0,
                "transaction_id": transaction_id,
                "action_seq": action_seq,
            })

        # ── 注册环境效果反馈检查（climate 设备：10 分钟后检验温度变化）──
        if domain == "climate" and "turn_on" in service:
            await self._register_env_feedback(entity_id)

        return True

    async def _register_env_feedback(self, entity_id: str, check_after_secs: int = 600) -> None:
        """为 climate 设备注册一次环境效果反馈检查任务。

        尝试通过房间名称匹配找出相关温湿度传感器：
        - climate.living_room_ac → sensor.*living_room*temp*
        - 兜底：遍历 device_info 中的 sensor 实体，选名称/ID 含同一房间关键词的
        """

        # 取当前设备状态（基准值）
        dev_state = self.hass.states.get(entity_id)
        if not dev_state:
            return

        base_temp: float | None = None
        target_temp: float | None = None
        try:
            base_temp = float(dev_state.attributes.get("current_temperature", 0) or 0) or None
            target_temp = float(dev_state.attributes.get("temperature", 0) or 0) or None
        except (TypeError, ValueError):
            pass

        # 通过房间关键词匹配相关传感器
        room_kw = self._guess_room_from_entity(entity_id)
        temp_sensor = ""
        humi_sensor = ""
        base_humi: float | None = None

        for eid in self.device_info:
            if not eid.startswith("sensor."):
                continue
            eid_lower = eid.lower()
            if room_kw and room_kw not in eid_lower:
                continue
            if any(k in eid_lower for k in ("temp", "temperature", "温度")):
                if not temp_sensor:
                    st = self.hass.states.get(eid)
                    if st and st.state not in ("unavailable", "unknown"):
                        try:
                            base_temp = float(st.state)
                            temp_sensor = eid
                        except (ValueError, TypeError):
                            pass
            elif any(k in eid_lower for k in ("humid", "humidity", "湿度")):
                if not humi_sensor:
                    st = self.hass.states.get(eid)
                    if st and st.state not in ("unavailable", "unknown"):
                        try:
                            base_humi = float(st.state)
                            humi_sensor = eid
                        except (ValueError, TypeError):
                            pass

        new_task = {
            "entity_id": entity_id,
            "action": "on",
            "base_temp": base_temp,
            "target_temp": target_temp,
            "temp_sensor": temp_sensor,
            "base_humi": base_humi,
            "humi_sensor": humi_sensor,
            "check_at": time.time() + check_after_secs,
            "check_after": check_after_secs,
            "checked": False,
        }
        async with self._env_feedback_lock:
            self._env_feedback_tasks.append(new_task)
        self._sys_log("INFO",
                      f"[反馈] 已为 {entity_id} 注册环境效果检查（{check_after_secs // 60} 分钟后）"
                      + (f"，关联传感器: {temp_sensor}" if temp_sensor else "，未找到温度传感器"))

    def _guess_room_from_entity(self, entity_id: str) -> str:
        """从实体 ID 中提取房间关键词（小写），用于传感器匹配。"""
        _ROOM_KW = (
            "living", "bedroom", "kitchen", "bathroom", "toilet", "study",
            "office", "hall", "balcony", "garage", "basement",
            "客厅", "卧室", "厨房", "浴室", "书房", "走廊", "阳台", "茶室",
        )
        eid_lower = entity_id.lower().replace(".", "_")
        for kw in _ROOM_KW:
            if kw in eid_lower:
                return kw
        # 取 domain 后第一个 _ 分隔词
        parts = entity_id.split(".")[-1].split("_")
        if parts:
            return parts[0].lower()
        return ""

    # ── 动作验证与重试 ────────────────────────────────────────────────────────

    # ── 动作验证与重试 ────────────────────────────────────────────────────────

    async def _verify_pending_actions(self) -> None:
        """回查已执行动作的设备状态，确认是否生效。由巡检循环定期调用。"""
        if not self._pending_verifications:
            return
        now = time.time()
        # 过期清理
        self._pending_verifications = [
            v for v in self._pending_verifications
            if now - v["fire_time"] < self._VERIFY_EXPIRE_SEC
        ]
        remaining: list[dict] = []
        snapshot = list(self._pending_verifications)
        for item in snapshot:
            elapsed = now - item["fire_time"]
            if elapsed < self._ACTION_VERIFY_DELAY:
                remaining.append(item)
                continue
            eid = item["entity_id"]
            expected = item["expected_state"]
            state_obj = self.hass.states.get(eid)
            actual = state_obj.state if state_obj else "unknown"
            # unavailable/unknown 视为验证不可判定 — 跳过本次，等下一轮
            if actual in ("unavailable", "unknown"):
                if now - item["fire_time"] < self._VERIFY_EXPIRE_SEC:
                    remaining.append(item)
                continue
            ok = (expected == "on" and actual not in self._OFF_STATES) or \
                 (expected == "off" and actual in self._OFF_STATES)
            latency = int(elapsed * 1000)
            # 记录到 DB
            self.hass.async_add_executor_job(
                self._record_action_result,
                eid, item["domain"], item["service"], expected, actual,
                1 if ok else 0, item["retry"], latency, item["reason"],
                item.get("transaction_id", 0), item.get("action_seq", 0),
            )
            if ok:
                self._sys_log("INFO", f"[验证✓] {eid} 期望={expected} 实际={actual}（{latency}ms）")
            else:
                if item["retry"] < self._ACTION_RETRY_MAX:
                    self._sys_log("WARN", f"[验证✗] {eid} 期望={expected} 实际={actual}，自动重试第 {item['retry']+1} 次")
                    try:
                        # 临时记住队列长度，_do_call_service 会追加新验证条目，需在调用后删除
                        q_len_before = len(self._pending_verifications)
                        ok_retry = await self._do_call_service(
                            item["domain"], item["service"], eid, {}, f"验证重试({expected})",
                            transaction_id=item.get("transaction_id", 0),
                            action_seq=item.get("action_seq", 0),
                        )
                        # 删除 _do_call_service 追加的重复验证条目
                        if len(self._pending_verifications) > q_len_before:
                            self._pending_verifications = self._pending_verifications[:q_len_before]
                        if ok_retry:
                            item["retry"] += 1
                            item["fire_time"] = time.time()
                            remaining.append(item)
                        else:
                            self._sys_log("WARN", f"[验证重试] {eid} 被保护机制拦截，放弃重试")
                    except Exception as e:
                        self._sys_log("ERROR", f"[验证重试] {eid} 重试失败: {e}")
                else:
                    self._sys_log("ERROR", f"[验证✗] {eid} 期望={expected} 实际={actual}，已达最大重试次数")
        self._pending_verifications = remaining
