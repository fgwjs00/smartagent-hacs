from __future__ import annotations
import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


class FastBrainEngine:
    """
    Phase 8A / P4 / P2-ML: System 1 (Reflex Engine 极速快脑)。

    三阶段进化决策：
      阶段 0 (< 50 条已验证样本): behavior_patterns 启发式匹配（旧逻辑，始终保留作兜底）
      阶段 1 (50~200 条):         本地 DecisionTree(depth=4)，置信度 ≥ 70% 才采纳
      阶段 2 (> 200 条):          本地 DecisionTree(depth=8)，完全个性化

    响应延迟：
      ML 推理 < 1ms，behavior_patterns 匹配 < 5ms，均远低于 LLM 的 1-5s。
    """

    def __init__(
        self,
        hass,
        device_info,
        behavior_patterns: list[dict] | None = None,
        sys_log_func=None,
        get_baseline_func=None,
        get_arrival_baseline_func=None,
    ):
        self.hass = hass
        self.device_info = device_info
        # behavior_patterns 缓存（从 coordinator._behavior_patterns_cache 注入）
        self._patterns: list[dict] = behavior_patterns or []
        self._sys_log = sys_log_func
        # 基线查询函数（由 coordinator._get_baseline 注入，executor 线程调用）
        self._get_baseline = get_baseline_func
        # Phase 0: 到达基线查询函数（优先于 device_baseline）
        self._get_arrival_baseline = get_arrival_baseline_func

    def _log(self, level: str, msg: str) -> None:
        """内部辅助：同时记录面板日志和原生日志。"""
        if self._sys_log:
            self._sys_log(level, msg)
        else:
            if level == "ERROR": _LOGGER.error(msg)
            elif level == "WARN": _LOGGER.warning(msg)
            else: _LOGGER.info(msg)

    def _apply_color_temp(self, entity_id: str, params: dict, color_temp: int | None) -> None:
        """将色温写入 params，自动裁剪到设备支持的 Kelvin 范围。

        若设备不支持色温属性则不写入，保证 params 的类型安全。

        Args:
            entity_id: 灯光实体 ID。
            params: 待修改的参数字典（in-place 修改）。
            color_temp: 目标色温（Kelvin），None 表示不设置色温。
        """
        if color_temp is None:
            return
        _st = self.hass.states.get(entity_id)
        if not _st:
            return
        _attrs = _st.attributes
        _supports_ct = (
            _attrs.get("min_color_temp_kelvin") is not None
            or _attrs.get("color_temp") is not None
            or "color_temp" in (_attrs.get("supported_color_modes") or [])
        )
        if _supports_ct:
            # 使用 or 兜底：若 HA 属性 key 存在但值为 None，get() 返回 None 而非默认值，
            # 须用 "or 默认值" 确保 max/min 计算不因 None 抛 TypeError。
            _min_ct = _attrs.get("min_color_temp_kelvin") or 2000
            _max_ct = _attrs.get("max_color_temp_kelvin") or 6500
            try:
                params["color_temp_kelvin"] = max(int(_min_ct), min(int(_max_ct), int(color_temp)))
            except (TypeError, ValueError):
                params["color_temp_kelvin"] = color_temp

    def decide(
        self,
        entity_id: str,
        new_state: str,
        old_state: str = "",
    ) -> dict | None:
        """
        统一快脑决策入口（P2-ML 三阶段进化版）。

        决策顺序：
          1. FeatureEncoder → 特征编码
          2. 本地 ML 模型预测（若模型存在且置信度 ≥ 70%）
          3. behavior_patterns 习惯匹配（ML 未命中时）
          4. 启发式三级瀑布兜底（无习惯数据时）
          → None → 交给慢脑 LLM

        Args:
            entity_id: 触发实体 ID
            new_state: 新状态字符串
            old_state: 旧状态字符串（可选）

        Returns:
            包含 actions/confidence/scene 的字典，或 None（交由慢脑处理）
        """
        try:
            from .feature_encoder import FeatureEncoder
            encoder = FeatureEncoder(
                self.hass, self.device_info,
                db_query_func=getattr(self, "_db", None) and self._db.query,
                room_topology=getattr(self, "_room_topology_cache", None),
            )
            features = encoder.encode(entity_id, new_state, old_state)

            # ── 优先：本地 ML 模型预测 ──────────────────────────────────────
            ml_result = self._try_ml_predict(features)
            if ml_result:
                return ml_result

            # ── 降级：behavior_patterns + 启发式瀑布 ────────────────────────
            return self.predict(features)
        except Exception as exc:
            self._log("WARN", f"[FastBrain] decide() 异常: {exc}")
            return None

    def _try_ml_predict(self, features: dict) -> dict | None:
        """
        尝试用本地 ML 模型预测动作。

        Args:
            features: FeatureEncoder.encode() 的输出

        Returns:
            动作字典（含 actions/confidence/scene）或 None
        """
        try:
            from .model_trainer import LocalModelTrainer, resolve_model_path
            _mp = resolve_model_path(
                getattr(self.hass.config, "config_dir", None)
            )
            label, proba = LocalModelTrainer.predict(features, model_path=_mp)
            if not label or ":" not in label:
                return None
            # 过滤 "nothing:xxx" 标签（负样本学到的"不动作"预测）
            if label.startswith("nothing:"):
                self._log("INFO", f"[FastBrain ML] 模型预测无需动作 ({proba * 100:.0f}%)，保持现状")
                return None

            entity_id, service = label.split(":", 1)

            # H1: 房间/设备有效性校验——预测实体必须在当前触发房间可控设备内
            room_devices = features.get("room_devices", {})
            room_lights = features.get("room_lights", {})
            scope = room_devices if room_devices else room_lights
            if not scope or entity_id not in scope:
                self._log("WARN",
                    f"[FastBrain ML] 预测实体 {entity_id} 不在当前房间可控设备列表中（room_devices={'空' if not room_devices else '存在'}），降级到启发式"
                )
                return None
            _current_state = scope.get(entity_id, "")
            # 非二值状态（如 climate=heat/cool）不做 on/off 已满足判定
            if _current_state in ("on", "off"):
                if service == "turn_on" and _current_state == "on":
                    self._log("INFO", f"[FastBrain ML] 预测实体 {entity_id} 已处于 on 状态，跳过")
                    return None
                if service == "turn_off" and _current_state == "off":
                    self._log("INFO", f"[FastBrain ML] 预测实体 {entity_id} 已处于 off 状态，跳过")
                    return None

            hour = features.get("time_hour", 12)
            trigger_room = features.get("trigger_room", "")
            brightness, color_temp, _ = self._get_room_light_context(trigger_room) if trigger_room else (self._get_time_brightness(hour), None, 2)

            # M1: brightness_pct / color_temp_kelvin 仅对灯光实体有效
            _domain = entity_id.split(".")[0] if "." in entity_id else "light"
            _params: dict = {}
            if service == "turn_on" and _domain == "light":
                _params = {"brightness_pct": brightness}
                self._apply_color_temp(entity_id, _params, color_temp)

            self._log("INFO",
                f"[FastBrain ML] 本地模型命中: {entity_id} → {service} (置信度 {proba * 100:.0f}%)",
            )
            return {
                "scene": f"ML个性化预测（置信度 {proba:.0%}）",
                "confidence": int(proba * 100),
                "actions": [{
                    "domain": _domain,
                    "service": service,
                    "entity_id": entity_id,
                    "params": _params,
                    "reason": (
                        f"[本地ML] 个性化决策树预测，置信度 {proba:.0%}，"
                        f"基于用户历史行为学习"
                    ),
                    "delay_seconds": 0,
                }],
            }
        except Exception as exc:
            self._log("WARN", f"[FastBrain] ML 预测异常（降级到启发式）: {exc}")
            return None

    def predict(self, features: dict) -> dict | None:
        """
        评估特征字典，生成快速决策。
        返回包含 'actions', 'confidence', 'scene' 的字典，如果不确定则返回 None。
        """
        trigger_domain = features.get("trigger_domain")
        trigger_state = features.get("trigger_state")
        trigger_entity = features.get("trigger_entity", "")

        # 多模态"有人到达"检测：PIR/mmWave binary_sensor 或 Frigate 人数传感器
        is_pir_trigger = (trigger_domain == "binary_sensor" and trigger_state == "on")
        is_camera_trigger = (
            trigger_domain == "sensor"
            and "person" in trigger_entity
            and trigger_state not in ("0", "unknown", "unavailable")
        )

        if not (is_pir_trigger or is_camera_trigger):
            return None

        room = features.get("trigger_room", "")
        if not room:
            return None

        room_lights = features.get("room_lights", {})
        if not room_lights:
            return None

        # 安全防线：若房间全部灯光已开启（或有未知状态），说明无需开灯，
        # 交给慢脑判断是否需要调光/调色温等复杂操作。
        # 修正：只要有任意一盏灯是 "off"，说明还有灯可以开，允许 FastBrain 处理。
        all_on = all(s != "off" for s in room_lights.values())
        if all_on:
            return None

        # hour 在场景路由和习惯匹配中均需使用，统一在此提前提取
        # features["time_hour"] 可能为显式 None，需二次兜底
        hour = features.get("time_hour") or 12
        now = datetime.now()

        # ── 5A-1: 场景路由前移 ─────────────────────────────────────────────
        # 优先检查是否有激活的 AI 场景或 HA 人工场景匹配当前房间+时段。
        # 若匹配，直接路由到 scene.turn_on，避免逐灯操作并尊重用户精心设置的场景。
        _scene_route = self._find_room_scene(room, hour)
        if _scene_route:
            _scene_reason = (
                f"[SceneRoute] FastBrain 场景路由：{room}检测到人员，激活场景 {_scene_route}"
            )
            return {
                "scene": f"{room}人员进入→场景路由（{_scene_route}）",
                "confidence": 90,
                "actions": [{
                    "domain": "scene",
                    "service": "turn_on",
                    "entity_id": _scene_route,
                    "params": {"transition": 1},
                    "reason": _scene_reason,
                    "delay_seconds": 0,
                }],
            }

        # ── P4 核心：从行为模式数据库选择灯光 ──────────────────────────────
        # SQLite %w: 0=Sun, 1=Mon,...,6=Sat. Python weekday(): 0=Mon → (wd+1)%7
        weekday_str = str((now.weekday() + 1) % 7)

        habit_lights = self._get_habit_lights(room_lights, hour, weekday_str)

        if habit_lights:
            # 有历史习惯数据：直接遵循用户偏好
            selected_lights = habit_lights["lights"]
            confidence = habit_lights["confidence"]
            source_tag = "习惯驱动"
        else:
            # 无习惯数据：尝试 arrival_baseline（到达场景数据驱动）
            # 5E-1: 移除 device_baseline 阈值兜底和启发式关键词兜底，
            # 无数据时直接交给 LLM 慢脑，避免 FastBrain 在无用户数据时瞎猜。
            baseline_lights = self._baseline_select(room_lights)
            if baseline_lights:
                selected_lights = baseline_lights
                confidence = 78   # 基线选灯置信度低于习惯驱动，避免过度自信
                source_tag = "基线偏好"
            else:
                # arrival_baseline 无数据或到达时不需要开灯：交给 LLM 慢脑决策
                self._log(
                    "INFO",
                    f"[FastBrain] {room} 无习惯/基线数据，移交 LLM 慢脑决策（5E-1 启发式已移除）",
                )
                return None

        # 获取房间场景建议亮度、色温和过渡时长
        brightness, color_temp, transition = self._get_room_light_context(room)

        actions = []
        for lid in selected_lights:
            if room_lights.get(lid) != "off":
                continue
            _params: dict = {"brightness_pct": brightness, "transition": transition}
            self._apply_color_temp(lid, _params, color_temp)
            actions.append({
                "domain": "light",
                "service": "turn_on",
                "entity_id": lid,
                "params": _params,
                "reason": (
                    f"[Reflex Engine] 极速快脑（{source_tag}）：{room}检测到人员，"
                    f"开启灯光至 {brightness}%"
                    + (f" / {color_temp}K" if color_temp else "")
                    + f" / {transition}s渐变"
                ),
                "delay_seconds": 0,
            })

        if not actions:
            return None

        return {
            "scene": f"{room}人员进入极速开灯（{source_tag}）",
            "confidence": confidence,
            "actions": actions,
        }

    def _find_room_scene(self, room: str, hour: int) -> str | None:
        """5A-1: 查找匹配当前房间+时段的激活 AI 场景或 HA 人工到达场景。

        优先级：
          1. 激活的 AI 场景（status=active，时段匹配，包含本房间设备）
          2. HA 人工场景（名称含房间名 + 到达/回家/进入/开灯关键字）

        由调用方（decision_pipeline.py）注入 _ai_scenes_cache / _ha_scenes_cache 属性。

        :returns: scene entity_id 字符串，或 None（无匹配）
        """
        import json as _json
        from datetime import datetime as _dt

        room_lower = room.lower()
        _now = _dt.now()
        # 使用调用方传入的 hour（来自触发特征），保证与 predict() 上下文一致
        _hour = hour if hour is not None else _now.hour
        _weekday = _now.weekday()

        # ── 1. 激活的 AI 场景 ────────────────────────────────────────────
        try:
            from .const import AI_SCENE_STATUS_ACTIVE, ai_scene_matches_now
            ai_scenes = getattr(self, "_ai_scenes_cache", None) or []
            for sc in ai_scenes:
                if sc.get("status") != AI_SCENE_STATUS_ACTIVE:
                    continue
                if not ai_scene_matches_now(sc, _hour, _weekday):
                    continue
                try:
                    ents = _json.loads(sc.get("entities_json", "[]"))
                except Exception:
                    continue
                # P2修复：收紧场景匹配 — 要求 >=50% 设备属于触发房间
                _room_count = sum(
                    1 for e in ents
                    if room_lower in (
                        self.device_info.get(e.get("entity_id", ""), {}).get("room") or ""
                    ).lower()
                )
                if _room_count == 0 or (len(ents) > 1 and _room_count < len(ents) * 0.5):
                    continue
                ha_eid = f"scene.ai_{sc['id']}"
                if self.hass.states.get(ha_eid) is not None:
                    self._log(
                        "INFO",
                        f"[FastBrain SceneRoute] {room} → 激活 AI 场景: {sc['name']} ({ha_eid})",
                    )
                    return ha_eid
        except Exception:
            pass

        # ── 2. HA 人工场景（到达类）────────────────────────────────────────
        _arrival_kw = ("回家", "到达", "进入", "arrival", "enter", "welcome", "开灯")
        ha_scenes = getattr(self, "_ha_scenes_cache", None) or []
        for sc in ha_scenes:
            cname = sc.get("name", "").lower()
            if room_lower not in cname:
                continue
            if not any(kw in cname for kw in _arrival_kw):
                continue
            ha_eid = sc.get("entity_id", "")
            if ha_eid and self.hass.states.get(ha_eid) is not None:
                self._log(
                    "INFO",
                    f"[FastBrain SceneRoute] {room} → HA 人工场景: {sc['name']} ({ha_eid})",
                )
                return ha_eid

        return None

    def _get_habit_lights(
        self, room_lights: dict, hour: int, weekday_str: str
    ) -> dict | None:
        """
        P4 核心方法：从 behavior_patterns 缓存匹配当前时段+星期的用户历史开灯习惯。

        匹配逻辑：
          1. 遍历缓存中所有 expected_state == 'on' 且属于本房间灯的记录
          2. 过滤出 hour_start <= hour <= hour_end 且 weekday_mask 包含当前星期
          3. 按 confidence 倒序，取置信度最高的灯作为主选灯
          4. 置信度门槛 >= 55 才采用（防止弱信号误判）

        Returns:
            {"lights": [lid, ...], "confidence": int} 或 None（无匹配）
        """
        if not self._patterns:
            return None

        CONFIDENCE_THRESHOLD = 55  # 低于此阈值的历史规律不采用

        matched: list[tuple[int, str]] = []  # (confidence, entity_id)

        for p in self._patterns:
            eid = p.get("entity_id", "")
            # 只看属于本房间的灯
            if eid not in room_lights:
                continue
            # 只看"开启"方向的规律
            if (p.get("expected_state") or "").lower() not in ("on", "open"):
                continue
            # 置信度门槛
            conf = p.get("confidence", 0)
            if conf < CONFIDENCE_THRESHOLD:
                continue
            # 时段匹配
            h_start = p.get("hour_start", 0)
            h_end = p.get("hour_end", 23)
            if not (h_start <= hour <= h_end):
                continue
            # 星期匹配
            wd_mask = str(p.get("weekday_mask") or "0123456")
            if weekday_str not in wd_mask:
                continue

            matched.append((conf, eid))

        if not matched:
            return None

        # 按置信度倒序，只选最高置信度的那个（不强制多灯联开，把控制权给用户）
        matched.sort(reverse=True)
        top_confidence = matched[0][0]
        # 选出置信度与最高一致或相差 10 以内的灯（容许多灯同时习惯开）
        selected = [eid for conf, eid in matched if top_confidence - conf <= 10]

        _LOGGER.debug(
            "[FastBrain P4] 命中历史习惯: %d 条模式 → 选灯 %s (置信度 %d)",
            len(matched), selected, top_confidence,
        )

        return {"lights": selected, "confidence": min(97, 80 + top_confidence // 10)}

    def _baseline_select(self, room_lights: dict) -> list[str]:
        """基于设备使用基线选灯（介于习惯驱动和启发式之间）。

        优先级：
          1. arrival_baseline（到达场景基线，语义最准确）
          2. device_baseline（全天使用率，回退兜底）

        :param room_lights: 房间灯光状态字典 {entity_id: state}
        :return: 应该开启的灯 entity_id 列表，可能为空
        """
        # ── 1. 优先使用 arrival_baseline ────────────────────────────────────
        if self._get_arrival_baseline is not None:
            # 推断房间（所有 room_lights 的灯应属于同一房间）
            room = ""
            for lid in room_lights:
                room = self.device_info.get(lid, {}).get("room", "")
                if room:
                    break
            if room:
                hour_now = datetime.now().hour
                try:
                    arrival_rows = self._get_arrival_baseline(
                        room, hour_bucket=hour_now, min_samples=3
                    )
                except Exception:
                    arrival_rows = []

                if arrival_rows:
                    # arrival_baseline 有数据时，完全信任它，不回退到 device_baseline。
                    # 若所有灯 turn_on_ratio < 0.5，说明「到达时通常不开灯」，返回空列表而非回退。
                    arrival_map = {
                        r["entity_id"]: r["turn_on_ratio"]
                        for r in arrival_rows
                        if r["entity_id"] in room_lights and r["turn_on_ratio"] >= 0.5
                    }
                    if arrival_map:
                        selected = sorted(arrival_map.items(), key=lambda x: -x[1])[:3]
                        result = [eid for eid, _ in selected]
                        self._log(
                            "INFO",
                            f"[FastBrain ArrivalBaseline] 到达基线选灯 {len(result)} 盏: "
                            f"{[(round(r, 2), e) for e, r in selected]}",
                        )
                        return result
                    else:
                        # 有到达数据但全部低于阈值：尊重「到达时不开灯」的历史习惯
                        self._log(
                            "INFO",
                            f"[FastBrain ArrivalBaseline] 到达基线显示该时段无需开灯"
                            f"（{len(arrival_rows)} 条记录均低于阈值 50%），遵从用户习惯",
                        )
                        return []

        # 5E-1 后续修正（用户明确要求）：无 arrival 数据时，
        # 不直接返回空（导致全交 LLM），而是用关键词三级瀑布（灯带→主灯→射灯）
        # 给出一个合理的最小照明方案，避免有人进门却黑灯等 LLM。
        # LLM 慢脑仍然并发运行，若其判断更佳则会在 200-2000ms 后覆盖此结果。
        return self._heuristic_select(room_lights)

    def _heuristic_select(self, room_lights: dict) -> list[str]:
        """
        关键词三级瀑布选灯（无习惯/基线数据时的最终兜底）。

        优先级（用户明确要求）：
          Tier 1: 灯带 / 氛围灯 / strip  — 基础环境照明，优先柔和渐入
          Tier 2: 主灯 / 顶灯 / 普通灯   — 无灯带时的主照明
          Tier 3: 射灯 / 筒灯             — 再无主灯才使用补光灯
          兜底:   取列表第一个灯           — 确保不黑灯

        同名称匹配多个词时，先命中的层级优先（Tier 1 > Tier 2 > Tier 3）。
        entity_id 末段（拼音片段）也纳入关键字检查，兼容国产设备命名习惯。
        """
        # 关键字列表同时匹配 name（中英文）和 entity_id 末段（拼音）
        _STRIP_KW = (
            "灯带", "strip", "ambient", "氛围", "夜灯", "nightlight",
            "deng_dai", "rgb", "led_strip",
        )
        _MAIN_KW = (
            "主灯", "顶灯", "吸顶灯", "客厅灯", "ceiling", "main", "overhead",
            "zhu_deng", "ding_deng",
        )
        _SPOT_KW = (
            "射灯", "筒灯", "格栅", "spotlight", "downlight", "spot",
            "she_deng", "tong_deng", "ge_zha",
        )

        tier1, tier2, tier3 = [], [], []
        for lid in room_lights:
            info  = self.device_info.get(lid, {})
            # 拼接 name + entity_id 末段一起检索，提高命中率
            name  = (info.get("name", "") + " " + lid.split(".")[-1]).lower()
            if any(kw in name for kw in _STRIP_KW):
                tier1.append(lid)
            elif any(kw in name for kw in _MAIN_KW):
                tier2.append(lid)
            elif any(kw in name for kw in _SPOT_KW):
                tier3.append(lid)
            else:
                tier2.append(lid)  # 未识别类型归入主灯层

        result = tier1 or tier2 or tier3 or list(room_lights.keys())[:1]
        self._log(
            "INFO",
            "[FastBrain 关键词选灯] 灯带%d / 主灯%d / 射灯%d → 选中 %s"
            % (len(tier1), len(tier2), len(tier3), [r.split(".")[-1] for r in result]),
        )
        return result

    def _get_room_light_context(self, room: str) -> tuple[int, int | None, int]:
        """根据房间名称返回建议的 (亮度%, 色温K | None, 过渡秒数)。

        Phase 13: 优先使用 CircadianEngine（若已注入），回退到静态表 + 时段默认值。
        深夜（0-6 时）始终覆盖为低亮度，避免扰眠。

        :param room: 房间名称（中文或英文）
        :return: (brightness_pct, color_temp_kelvin | None, transition_seconds)
        """
        # Phase 13: 优先使用昼夜节律引擎（必须 enabled=True 才接入，否则回退静态表）
        _circadian = getattr(self, "_circadian_engine", None)
        if _circadian is not None and _circadian.enabled:
            try:
                target = _circadian.get_target(room)
                return target["brightness_pct"], target["color_temp_kelvin"], target["transition"]
            except Exception:
                pass  # 回退到静态表

        from .const import ROOM_LIGHT_CONTEXT
        hour = datetime.now().hour
        if hour < 6:
            return 20, None, 10

        room_lower = room.lower()
        for kw, (bri, ct, _desc) in ROOM_LIGHT_CONTEXT.items():
            if kw in room_lower:
                if hour >= 21:
                    bri = min(bri, 50)
                    ct = min(ct, 4000)
                transition = self._get_time_transition(hour)
                return bri, ct, transition

        return self._get_time_brightness(hour), None, self._get_time_transition(hour)

    def _get_time_brightness(self, hour: int) -> int:
        """根据当前时段决定合适的开灯亮度（无房间情景时的兜底）。

        时段对应：
          6-8  清晨过渡 → 70%（眼睛未完全适应）
          8-18 白天工作 → 100%（充足照明）
          18-21 傍晚/晚间 → 80%（舒适偏暖）
          21-23 深夜前 → 50%（放松准备）
          0-6  深夜/凌晨 → 20%（不打扰睡眠）

        TODO: 可接入照度传感器(lux)动态调整，lux>200 时降低目标亮度。
        """
        if 6 <= hour < 8:   return 70
        if 8 <= hour < 18:  return 100
        if 18 <= hour < 21: return 80
        if 21 <= hour < 23: return 50
        return 20  # 23:00 ~ 06:00 深夜模式

    @staticmethod
    def _get_time_transition(hour: int) -> int:
        """根据时段返回建议的灯光过渡时长（秒）。

        深夜/清晨：长过渡避免突然强光
        白天：快速响应
        晚间：中等过渡渐入放松
        """
        if 0 <= hour < 6:   return 10
        if 6 <= hour < 8:   return 5
        if 8 <= hour < 18:  return 2
        if 18 <= hour < 21: return 3
        return 8  # 21:00 ~ 23:59
