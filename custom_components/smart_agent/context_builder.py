"""
ContextBuilder — 推理上下文序列化器（v4.9.1）。

架构职责：
  - 本模块保留在 HA 集成（明文），负责"HA 数据采集"
  - 将所有依赖 hass.states / SQLite 的调用提前执行
  - 输出 InferenceBundle 字典（纯 JSON 可序列化），发送给 smartagent-addon 执行推理
  - Add-on core/ 负责"Prompt 构建 + LLM 调用"（受 Cython 保护）

InferenceBundle 格式版本：1.0
  - 版本变更时需同步更新 smartagent-addon/core/inference_engine.py 中的 BUNDLE_VERSION
  - 保持向后兼容：Add-on 可选字段使用 bundle.get(..., default) 读取

隐私保证：
  - context_text / history 等字段来自 HA 本地数据库，不含个人身份信息
  - online_api_key 仅在本机 localhost 通信，不上传到任何外部服务
"""
from __future__ import annotations

import asyncio
import logging
import re
import time as _time
from datetime import datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)

# 不算作触发房间的标签集合（与 inference.py 保持一致）
# 注意：视觉检测 必须在此集合内，否则摄像头未绑定房间时会被误提取为触发房间
_NON_ROOM_TAGS = {"物理", "巡检", "定时", "脚本", "用户", "位置", "紧急", "自动化", "视觉检测"}

# InferenceBundle 格式版本（版本更新时同步修改 Add-on 端校验）
_BUNDLE_VERSION = "1.0"


def _extract_trigger_room(trigger: str) -> str:
    """从触发器文本中提取房间名。

    优先匹配「[房间]」格式（物理传感器触发）；
    其次扫描所有 [XXX] 标签，跳过来源标签和视觉检测标签；
    同时剥离「进入/离开/在区域=[...]」文本，防止将 Frigate 区域 ID 误判为房间名。

    :param trigger: 触发器描述字符串
    :return: 房间名，未能提取时返回空字符串
    """
    m = re.search(r"「\[(.*?)\]", trigger)
    if m:
        return m.group(1)
    # 剥离区域列表（如 进入区域=[Ct, Ctsy]），避免将 Frigate zone ID 误判为房间名
    clean = re.sub(r"(?:进入|离开|在)区域=\[.*?\]", "", trigger)
    for candidate in re.findall(r"\[(.*?)\]", clean):
        if candidate not in _NON_ROOM_TAGS:
            return candidate
    return ""


def _sanitize_one_off(one_off_prompt: str) -> str:
    """对一次性指令进行安全脱敏，防止 Prompt 注入。

    :param one_off_prompt: 原始指令文本
    :return: 脱敏后的指令文本（最长 200 字符）
    """
    if not one_off_prompt:
        return ""
    safe = re.sub(r"[{}[\]'\"\n\r【】『』「」]", "", one_off_prompt)
    return safe[:200].strip()


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文≈1.5字/token，其他≈4字/token）。"""
    if not text:
        return 0
    cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
    non_cn_chars = len(text) - cn_chars
    return int(cn_chars / 1.5 + non_cn_chars / 4)


def _clip_text_with_notice(text: str, target_chars: int, label: str) -> str:
    """按目标字符数裁剪文本并附带提示。"""
    if not text or target_chars <= 0:
        return ""
    if len(text) <= target_chars:
        return text
    notice = f"\n  …（{label}超预算，已裁剪）"
    if target_chars <= len(notice) + 8:
        return notice[:target_chars]
    keep_chars = target_chars - len(notice)
    cutoff = text.rfind("\n", 0, keep_chars)
    if cutoff < int(keep_chars * 0.5):
        cutoff = keep_chars
    return text[:cutoff].rstrip() + notice


def _enforce_context_bundle_budget(
    fields: list[dict[str, Any]],
    total_budget: int,
) -> tuple[dict[str, str], int, list[str]]:
    """按优先级对 context bundle 字段执行硬预算裁剪。"""
    ordered = sorted(fields, key=lambda x: x.get("priority", 100))
    values: dict[str, str] = {f["name"]: f.get("text", "") or "" for f in ordered}

    def _render() -> str:
        return "".join(values[f["name"]] for f in ordered)

    total_tokens = _estimate_tokens(_render())
    logs: list[str] = []
    if total_tokens <= total_budget:
        return values, total_tokens, logs

    for field in ordered:
        name = field["name"]
        text = values.get(name, "")
        if not text:
            continue
        base_len = len(text)
        min_ratio = float(field.get("min_ratio", 0.2))
        trim_step = float(field.get("trim_step", 0.15))
        min_chars = max(int(field.get("hard_min_chars", 80)), int(base_len * min_ratio))

        current = text
        while total_tokens > total_budget and len(current) > min_chars:
            cur_len = len(current)
            drop_chars = max(80, int(cur_len * trim_step))
            target_len = max(min_chars, cur_len - drop_chars)
            before = total_tokens
            clipped = _clip_text_with_notice(current, target_len, name)
            if clipped == current:
                break
            values[name] = clipped
            current = clipped
            total_tokens = _estimate_tokens(_render())
            logs.append(f"{name}: {before}->{total_tokens} tok, chars {cur_len}->{len(current)}")

        if total_tokens <= total_budget:
            break

    return values, total_tokens, logs


class ContextBuilder:
    """将所有 HA/DB 依赖调用集中化，输出纯 JSON 可序列化的 InferenceBundle。

    使用方式：
        bundle = await ContextBuilder(coordinator).build(trigger, one_off_prompt)
        decision = await addon_client.infer(bundle)
    """

    def __init__(self, coordinator: Any) -> None:
        """初始化。

        :param coordinator: SmartAgentCoordinator 实例（拥有所有 Mixin 方法）
        """
        self._c = coordinator

    async def build(
        self,
        trigger: str,
        one_off_prompt: str = "",
        is_voice: bool = False,
    ) -> dict[str, Any]:
        """构建并返回 InferenceBundle。

        :param trigger: 触发器描述字符串
        :param one_off_prompt: 一次性展厅指令（可选）
        :param is_voice: 是否为语音指令
        :return: 纯 JSON 可序列化的上下文字典
        """
        c = self._c
        from .const import MODE_SHOWROOM, SHOWROOM_SCENES

        now = datetime.now()
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        # ── 基本信息 ─────────────────────────────────────────────────────────
        is_showroom = c._mode == MODE_SHOWROOM
        trigger_room = _extract_trigger_room(trigger)
        safe_one_off = _sanitize_one_off(one_off_prompt)

        is_global = bool(
            ("所有" in trigger or "全部" in trigger)
            or (one_off_prompt and ("所有" in one_off_prompt or "全部" in one_off_prompt))
        )

        # ── 时间信息（展厅模式使用虚拟时间）──────────────────────────────────
        if is_showroom and getattr(c, "_showroom_scene", None):
            _eff_scenes = getattr(c, "_effective_showroom_scenes", {})
            time_str = _eff_scenes.get(c._showroom_scene, {}).get("virtual_time", "18:00")
            # 展厅模式不在 SHOWROOM_SCENES 中时降级使用实际时间
            if c._showroom_scene not in SHOWROOM_SCENES:
                time_str = now.strftime("%H:%M")
        else:
            time_str = now.strftime("%H:%M")
        day_str = weekdays[now.weekday()]

        # 规则时间注解使用与 AI 看到的 time_str 一致的小时数
        try:
            anno_hour = int(time_str.split(":")[0])
        except (ValueError, IndexError):
            anno_hour = now.hour

        # ── 场景描述 ──────────────────────────────────────────────────────────
        if safe_one_off:
            scene_desc = f"[展厅·一次性指令] {safe_one_off}"
        else:
            # v4.11.0：传入 trigger_room 以支持工作区按家庭模式生成场景描述
            if hasattr(c, "_detect_scene"):
                scene_desc = c._detect_scene(trigger_room=trigger_room)
            else:
                scene_desc = "未知场景"

        # ── 规则/习惯文本（带时间注解）──────────────────────────────────────
        locked_rules = c._annotate_time(c._get_locked_rules_text(), anno_hour)
        locked_habits = c._annotate_time(c._get_locked_habits_text(), anno_hour)
        normal_rules = c._annotate_time(c._get_normal_rules_text(), anno_hour)
        normal_habits = c._annotate_time(c._get_normal_habits_text(), anno_hour)

        # ── 近期手动操作 ──────────────────────────────────────────────────────
        manual_actions_text = self._build_manual_actions_text(c)

        # ── 优先级保护摘要 ────────────────────────────────────────────────────
        priority_section = ""
        if hasattr(c, "_build_priority_prompt_section"):
            priority_section = c._build_priority_prompt_section() or ""

        # ── AI 场景提示（同步）────────────────────────────────────────────────
        ai_scenes_hint = c._get_active_ai_scenes_hint() if hasattr(c, "_get_active_ai_scenes_hint") else ""

        # ── Reflexion 反面教材（同步）────────────────────────────────────────
        reflexion_antipatterns = ""
        try:
            reflexion_antipatterns = c._get_reflexion_antipatterns_for_prompt() or ""
        except AttributeError:
            pass

        # ── 在场状态（同步，使用 hass.states）───────────────────────────────
        occupancy_section = c._build_occupancy_section() if hasattr(c, "_build_occupancy_section") else ""

        # ── 视觉感知上下文（同步，使用 hass.states）──────────────────────────
        vision_context = ""
        if getattr(c, "_frigate_enabled", False) or getattr(c, "_vision_enabled", False):
            if hasattr(c, "_build_vision_context"):
                vision_context = c._build_vision_context()

        # ── 设备名称对照表（供 Add-on 构建 System Prompt）────────────────────
        device_table = c._build_device_name_table() if hasattr(c, "_build_device_name_table") else ""

        # ── 异步数据采集（并发执行，加速 bundle 构建）─────────────────────────

        async def _empty() -> str:
            return ""

        # Phase 11.4: corrections_text 已从 _build_context() 中移除，改为按房间过滤后单独传递
        # 这里采集房间级修正记录，通过 bundle 传递给 Add-on 推理
        async def _get_room_corrections() -> str:
            """异步获取按触发房间过滤的修正记录文本。"""
            if not hasattr(c, "_get_corrections_for_prompt"):
                return ""
            try:
                # 推断当前在场状态
                _cur_pres = None
                if trigger_room and hasattr(c, "_get_room_occupancy_map"):
                    _occ = c._get_room_occupancy_map()
                    _sens = _occ.get(trigger_room, [])
                    if _sens:
                        if any(s == "on" for _, s in _sens):
                            _cur_pres = "occupied"
                        elif all(s == "off" for _, s in _sens):
                            _cur_pres = "empty"
                return await c.hass.async_add_executor_job(
                    c._get_corrections_for_prompt,
                    None,  # involved_entities
                    trigger_room or None,
                    _cur_pres,
                )
            except Exception as _exc:
                _LOGGER.debug("[ContextBuilder] 修正记录采集失败: %s", _exc)
                return ""

        # Phase 11.4b: _get_realtime_habits 和 _build_context 传入 focus_room
        # 按触发房间过滤，减少无关设备/习惯的 Token 占用
        # Phase 2 v2: 当有 trigger_room 时，_build_baseline_hint 的结果会被
        # memory_narrative（get_room_context 已含 baseline）覆盖清空；
        # 仅在无 trigger_room 时才执行 _build_baseline_hint（全局模式回退用途）。
        _baseline_hint_coro = (
            c.hass.async_add_executor_job(c._build_baseline_hint, trigger_room)
            if not trigger_room
            else _empty()
        )
        # T2 修复（v4.9.5）：_get_room_corrections() 移出 gather，改为 MemoryStore 失败后的串行 fallback。
        # 原因：MemoryStore 成功时 corrections_text 在 Add-on 端不被使用（memory_narrative 已含修正）。
        # 并发预取 + 丢弃只增加一次无用 DB 查询；改为串行后，成功路径零冗余，失败路径仍有保障。
        gather_results = await asyncio.gather(
            c._get_history_context(trigger_room=trigger_room),
            c._get_realtime_habits(focus_room=trigger_room),
            c._get_recent_overrides(),
            c._detect_and_run_tools(trigger),
            # Phase 8E: 传入 trigger 字符串，_build_context 内部据此折叠已在期望状态的设备
            c._build_context(focus_room=trigger_room, trigger=trigger),
            _baseline_hint_coro,
            return_exceptions=True,
        )

        def _safe(val: Any, default: str = "") -> str:
            """处理 gather 中的异常，返回默认值。"""
            if isinstance(val, Exception):
                _LOGGER.debug("[ContextBuilder] 异步采集失败: %s", val)
                return default
            return val or default

        history = _safe(gather_results[0])
        realtime_habits = _safe(gather_results[1])
        recent_overrides = _safe(gather_results[2])
        tool_results = _safe(gather_results[3])
        context_text = _safe(gather_results[4])
        baseline_hint = _safe(gather_results[5])

        # ── MemoryStore 房间上下文（Phase 2 v2，异步，executor）─────────────
        # 包含：房间叙事 + baseline摘要 + presence修正（三合一）
        # Phase 2 v2: memory_narrative 已内含 baseline_hint，当其非空时
        # 将 bundle["baseline_hint"] 置空，避免 Add-on 端双重注入。
        memory_narrative = await self._build_memory_narrative(c, trigger, trigger_room, now)
        if memory_narrative:
            # baseline 已内嵌于 memory_narrative，清除单独字段防止重复
            baseline_hint = ""
            # MemoryStore 成功：corrections_text 不需要（memory_narrative 已含 presence 修正），跳过 DB 查询
            corrections_text = ""
        else:
            # MemoryStore 失败（罕见）：串行 fallback 采集房间级修正记录与基线摘要
            corrections_text = await _get_room_corrections()
            if trigger_room and hasattr(c, "_build_baseline_hint"):
                try:
                    baseline_hint = await c.hass.async_add_executor_job(
                        c._build_baseline_hint, trigger_room
                    )
                except Exception as _exc:
                    _LOGGER.debug("[ContextBuilder] baseline fallback 采集失败: %s", _exc)
                    baseline_hint = ""

        # ── RAG 条件性检索（Phase RAG）────────────────────────────────────────
        rag_context = ""
        if trigger_room and hasattr(c, "_db"):
            try:
                from .rag_retriever import RAGRetriever
                from .inference import _detect_cache_trigger_type
                _rag_trigger_type = _detect_cache_trigger_type(trigger)
                _occ_pres = ""
                if hasattr(c, "_get_room_occupancy_map"):
                    _occ = c._get_room_occupancy_map()
                    _sens = _occ.get(trigger_room, [])
                    if any(s == "on" for _, s in _sens):
                        _occ_pres = "occupied"
                    elif _sens and all(s == "off" for _, s in _sens):
                        _occ_pres = "empty"
                _rag = RAGRetriever(
                    db_query_func=c._db.query,
                    device_info=c.device_info,
                    get_device_name_func=getattr(c, "get_device_name", None),
                )
                rag_context = await c.hass.async_add_executor_job(
                    _rag.retrieve,
                    trigger_room,
                    _rag_trigger_type,
                    now.hour,
                    now.weekday(),
                    now.weekday() >= 5,
                    _occ_pres,
                )
            except Exception as _rag_exc:
                _LOGGER.debug("[ContextBuilder] RAG 检索失败（忽略）: %s", _rag_exc)

        # ── 展厅分层 Prompt（异步）────────────────────────────────────────────
        showroom_tiered_prompt = ""
        if is_showroom and hasattr(c, "_build_showroom_tiered_prompt"):
            try:
                showroom_tiered_prompt = await c._build_showroom_tiered_prompt() or ""
            except Exception as exc:
                _LOGGER.debug("[ContextBuilder] 展厅分层 prompt 获取失败: %s", exc)

        # ── 展厅营业时间 ──────────────────────────────────────────────────────
        showroom_biz_start = getattr(c, "showroom_biz_start_min", 540)
        showroom_biz_end = getattr(c, "showroom_biz_end_min", 1200)
        is_biz_time = False
        if is_showroom:
            _now_min = now.hour * 60 + now.minute
            is_biz_time = showroom_biz_start <= _now_min < showroom_biz_end

        # Top3: Context 预算硬保护（组装后强校验，超预算逐段裁剪并重估）
        context_budget = 8_000
        context_fields = [
            {
                "name": "tool_results",
                "text": tool_results,
                "priority": 0,
                "trim_step": 0.25,
                "min_ratio": 0.0,
                "hard_min_chars": 0,
            },
            {
                "name": "history",
                "text": history,
                "priority": 1,
                "trim_step": 0.18,
                "min_ratio": 0.30,
                "hard_min_chars": 120,
            },
            {
                "name": "context_text",
                "text": context_text,
                "priority": 2,
                "trim_step": 0.15,
                "min_ratio": 0.35,
                "hard_min_chars": 180,
            },
            {
                "name": "rag_context",
                "text": rag_context,
                "priority": 3,
                "trim_step": 0.20,
                "min_ratio": 0.20,
                "hard_min_chars": 80,
            },
            {
                "name": "realtime_habits",
                "text": realtime_habits,
                "priority": 4,
                "trim_step": 0.18,
                "min_ratio": 0.28,
                "hard_min_chars": 80,
            },
            {
                "name": "recent_overrides",
                "text": recent_overrides,
                "priority": 5,
                "trim_step": 0.20,
                "min_ratio": 0.25,
                "hard_min_chars": 60,
            },
            {
                "name": "baseline_hint",
                "text": baseline_hint,
                "priority": 6,
                "trim_step": 0.25,
                "min_ratio": 0.0,
                "hard_min_chars": 0,
            },
            {
                "name": "corrections_text",
                "text": corrections_text,
                "priority": 7,
                "trim_step": 0.20,
                "min_ratio": 0.20,
                "hard_min_chars": 60,
            },
            {
                "name": "memory_narrative",
                "text": memory_narrative,
                "priority": 8,
                "trim_step": 0.10,
                "min_ratio": 0.55,
                "hard_min_chars": 200,
            },
            {
                "name": "manual_actions_text",
                "text": manual_actions_text,
                "priority": 9,
                "trim_step": 0.20,
                "min_ratio": 0.25,
                "hard_min_chars": 60,
            },
            {
                "name": "reflexion_antipatterns",
                "text": reflexion_antipatterns,
                "priority": 10,
                "trim_step": 0.22,
                "min_ratio": 0.20,
                "hard_min_chars": 60,
            },
            {
                "name": "ai_scenes_hint",
                "text": ai_scenes_hint,
                "priority": 11,
                "trim_step": 0.25,
                "min_ratio": 0.0,
                "hard_min_chars": 0,
            },
            {
                "name": "priority_section",
                "text": priority_section,
                "priority": 50,
                "trim_step": 0.0,
                "min_ratio": 1.0,
                "hard_min_chars": len(priority_section),
            },
            {
                "name": "occupancy_section",
                "text": occupancy_section,
                "priority": 51,
                "trim_step": 0.0,
                "min_ratio": 1.0,
                "hard_min_chars": len(occupancy_section),
            },
            {
                "name": "vision_context",
                "text": vision_context,
                "priority": 52,
                "trim_step": 0.0,
                "min_ratio": 1.0,
                "hard_min_chars": len(vision_context),
            },
            {
                "name": "showroom_tiered_prompt",
                "text": showroom_tiered_prompt,
                "priority": 53,
                "trim_step": 0.0,
                "min_ratio": 1.0,
                "hard_min_chars": len(showroom_tiered_prompt),
            },
            {
                "name": "device_table",
                "text": device_table,
                "priority": 54,
                "trim_step": 0.0,
                "min_ratio": 1.0,
                "hard_min_chars": len(device_table),
            },
        ]

        raw_context_tokens = _estimate_tokens("".join((f.get("text") or "") for f in sorted(context_fields, key=lambda x: x.get("priority", 100))))
        clipped_map, clipped_tokens, clip_logs = _enforce_context_bundle_budget(context_fields, context_budget)

        history = clipped_map.get("history", history)
        tool_results = clipped_map.get("tool_results", tool_results)
        context_text = clipped_map.get("context_text", context_text)
        rag_context = clipped_map.get("rag_context", rag_context)
        realtime_habits = clipped_map.get("realtime_habits", realtime_habits)
        recent_overrides = clipped_map.get("recent_overrides", recent_overrides)
        baseline_hint = clipped_map.get("baseline_hint", baseline_hint)
        corrections_text = clipped_map.get("corrections_text", corrections_text)
        memory_narrative = clipped_map.get("memory_narrative", memory_narrative)
        manual_actions_text = clipped_map.get("manual_actions_text", manual_actions_text)
        reflexion_antipatterns = clipped_map.get("reflexion_antipatterns", reflexion_antipatterns)
        ai_scenes_hint = clipped_map.get("ai_scenes_hint", ai_scenes_hint)

        if clip_logs:
            _LOGGER.warning(
                "[ContextBuilder] Token预算裁剪触发 | before≈%dtok after≈%dtok budget=%d | %s",
                raw_context_tokens,
                clipped_tokens,
                context_budget,
                " | ".join(clip_logs[:8]),
            )
            if len(clip_logs) > 8:
                _LOGGER.info("[ContextBuilder] 裁剪日志省略 %d 条", len(clip_logs) - 8)

        if clipped_tokens > context_budget:
            _LOGGER.error(
                "[ContextBuilder] Token预算仍超限（不可裁段占用过高）: ~%dtok > %dtok",
                clipped_tokens,
                context_budget,
            )
            # last_resort: 最小幅度裁剪低优先段，确保最终落入预算
            lr_fields = sorted(context_fields, key=lambda x: x.get("priority", 100))
            lr_map = {str(f.get("name")): clipped_map.get(str(f.get("name")), "") for f in lr_fields}
            _remaining = _estimate_tokens("\n".join(str(lr_map.get(str(f.get("name")), "")) for f in lr_fields))
            lr_logs: list[str] = []
            for f in lr_fields:
                if _remaining <= context_budget:
                    break
                n = str(f.get("name"))
                # 保留 P1/关键观测段，不做兜底裁剪
                if n in {"priority_section", "occupancy_section", "vision_context", "showroom_tiered_prompt", "device_table"}:
                    continue
                curr = str(lr_map.get(n, "") or "")
                if not curr:
                    continue
                prev_chars = len(curr)
                next_chars = max(80, int(prev_chars * 0.85))
                if next_chars >= prev_chars:
                    continue
                lr_map[n] = _clip_text_with_notice(curr, next_chars, n)
                before_tok = _remaining
                _remaining = _estimate_tokens("\n".join(str(lr_map.get(str(ff.get("name")), "")) for ff in lr_fields))
                lr_logs.append(f"{n}(last_resort): {before_tok}->{_remaining} tok, chars {prev_chars}->{len(lr_map[n])}")

            if lr_logs:
                _LOGGER.warning(
                    "[ContextBuilder] last_resort裁剪触发 | before≈%dtok after≈%dtok budget=%d | %s",
                    clipped_tokens,
                    _remaining,
                    context_budget,
                    " | ".join(lr_logs[:8]),
                )
            clipped_map = lr_map
            clipped_tokens = _remaining

        bundle: dict[str, Any] = {
            "_bundle_version": _BUNDLE_VERSION,
            # 触发信息
            "trigger": trigger,
            "one_off_prompt": safe_one_off,
            "is_voice": is_voice,
            "is_global": is_global,
            "trigger_room": trigger_room,
            # 时间
            "time_str": time_str,
            "day_str": day_str,
            "anno_hour": anno_hour,
            # 场景
            "scene_desc": scene_desc,
            # 模式
            "is_showroom": is_showroom,
            "is_biz_time": is_biz_time,
            "showroom_biz_start": showroom_biz_start,
            "showroom_biz_end": showroom_biz_end,
            "showroom_scene": getattr(c, "_showroom_scene", ""),
            "deploy_name": getattr(c, "deploy_name", ""),
            # 规则与习惯（带时间注解，用户数据，非 IP）
            "locked_rules": locked_rules,
            "locked_habits": locked_habits,
            "normal_rules": normal_rules,
            "normal_habits": normal_habits,
            # 动态文本片段（来自 HA/DB，非 IP）
            # Phase 11.4: corrections_text 从 context_text 中独立出来，按房间过滤后单独传递
            "corrections_text": corrections_text,
            "context_text": context_text,
            "history": history,
            "manual_actions_text": manual_actions_text,
            "realtime_habits": realtime_habits,
            "recent_overrides": recent_overrides,
            "baseline_hint": baseline_hint,
            "memory_narrative": memory_narrative,
            "rag_context": rag_context,
            "reflexion_antipatterns": reflexion_antipatterns,
            "ai_scenes_hint": ai_scenes_hint,
            "priority_section": priority_section,
            "showroom_tiered_prompt": showroom_tiered_prompt,
            "tool_results": tool_results,
            "occupancy_section": occupancy_section,
            "vision_context": vision_context,
            # 设备名称对照表（供 Add-on 构建 System Prompt 静态部分）
            "device_table": device_table,
            # LLM 配置（Add-on 调用 LLM 所需）
            "engine": getattr(c, "engine", "online"),
            "ollama_url": getattr(c, "ollama_url", ""),
            "ollama_model": getattr(c, "ollama_model", ""),
            "online_base_url": getattr(c, "online_base_url", ""),
            "online_model": getattr(c, "online_model", ""),
            "cloud_fallback": getattr(c, "_cloud_fallback", False),
        }

        _LOGGER.info(
            "[ContextBuilder] Bundle 构建完成 | 触发: %s | 房间: %s | 大小: ~%d chars",
            trigger[:50],
            trigger_room,
            sum(len(str(v)) for v in bundle.values()),
        )
        return bundle

    # ── 私有辅助方法 ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_manual_actions_text(coordinator: Any) -> str:
        """构建近期手动操作提示文本。

        :param coordinator: 协调器实例
        :return: 格式化文本，无操作时返回空字符串
        """
        _manual_lock = getattr(coordinator, "_user_manual_actions_lock", None)
        if _manual_lock is not None:
            with _manual_lock:
                user_manual_actions = dict(getattr(coordinator, "_user_manual_actions", {}))
        else:
            user_manual_actions = dict(getattr(coordinator, "_user_manual_actions", {}))

        user_manual_window = getattr(coordinator, "_USER_MANUAL_WINDOW", 1800)
        if not user_manual_actions:
            return ""

        now_ts = _time.time()
        m_lines: list[str] = []
        for entity_id, v in user_manual_actions.items():
            age_s = now_ts - v["time"]
            if age_s > user_manual_window:
                continue
            age_m = int(age_s / 60)
            if age_s <= 300:
                hint = "禁止反向"
            elif age_s <= 900:
                hint = "建议保持当前状态"
            else:
                hint = "仅供参考"
            dev_name = (
                coordinator.get_device_name(entity_id)
                if hasattr(coordinator, "get_device_name")
                else entity_id
            )
            m_lines.append(f"- {dev_name}({entity_id}): {age_m}min前手动操作（{hint}）")

        return "【近期手动操作】\n" + "\n".join(m_lines) if m_lines else ""

    @staticmethod
    async def _build_memory_narrative(
        coordinator: Any,
        trigger: str,
        trigger_room: str,
        now: datetime,
    ) -> str:
        """构建触发房间的 MemoryStore 历史上下文（Phase 2 v2 整合入口）。

        Phase 2 v2：改为调用 MemoryStore.get_room_context()，整合：
          - 房间历史记忆叙事（narrative）
          - 设备使用基线摘要（baseline hint）
          - 在场感知修正记录（presence_context 感知）

        相比 v1 的 get_room_narrative()，减少了 context_builder 需要分别调用
        _build_baseline_hint 的情况（baseline 现已内嵌）。

        :param coordinator: 协调器实例
        :param trigger: 触发器文本（用于判断触发类型）
        :param trigger_room: 触发房间名
        :param now: 当前时间
        :return: 房间历史上下文文本，无数据时返回空字符串
        """
        if not trigger_room or not hasattr(coordinator, "_db"):
            return ""
        try:
            from .memory_store import MemoryStore
            from .inference import _detect_cache_trigger_type

            ms_trigger_type = _detect_cache_trigger_type(trigger)

            # 推断当前在场状态用于 presence_context 感知修正过滤
            current_presence = ""
            if hasattr(coordinator, "_get_room_occupancy_map"):
                try:
                    occ_map = coordinator._get_room_occupancy_map()
                    sensors = occ_map.get(trigger_room, [])
                    if sensors:
                        if any(s == "on" for _, s in sensors):
                            current_presence = "occupied"
                        elif all(s == "off" for _, s in sensors):
                            current_presence = "empty"
                except Exception:
                    pass

            ms = MemoryStore(
                db_query_func=coordinator._db.query,
                device_info=coordinator.device_info,
                get_device_name_func=getattr(coordinator, "get_device_name", None),
            )
            # Phase 2 v2: 使用 get_room_context() 整合叙事 + 基线 + presence 修正
            context_text = await coordinator.hass.async_add_executor_job(
                ms.get_room_context,
                trigger_room,
                ms_trigger_type,
                now.hour,
                current_presence,
            )
            return context_text or ""
        except Exception as exc:
            _LOGGER.debug("[ContextBuilder] MemoryStore 上下文获取失败（忽略）: %s", exc)
            return ""
