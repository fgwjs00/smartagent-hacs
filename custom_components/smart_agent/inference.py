"""
InferenceMixin — AI 推理引擎。
负责：Prompt 构建、AI API 调用（Ollama / 云端）、JSON 解析、
      习惯/规则文本工具、场景检测、历史上下文查询。
"""
from __future__ import annotations

import json
import logging
import re
import time as _time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import aiohttp
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from .action_mapping import entities_to_actions, normalize_raw_actions
from .const import ENGINE_LOCAL, ENGINE_ONLINE
from .context_builder import _extract_trigger_room

_LOGGER = logging.getLogger(__name__)

# Phase 8E: 状态感知设备折叠的常量
# 仅对这两个简单 on/off 域应用折叠；climate/cover 等始终完整展示
_8E_SIMPLE_DOMAINS: frozenset[str] = frozenset({"light", "switch"})
# light/switch 唯一的 "已开" 状态值（其他域的 open/heat 等不适用，不列入）
_8E_ON_STATE: str = "on"


def _detect_cache_trigger_type(trigger: str) -> str:
    """从触发器文本推断缓存触发类型。

    :param trigger: 触发器描述字符串，如 "[物理] 传感器「[展厅] 展厅人体」变为 on"
    :return: 'arrival' | 'departure' | 'other'

    规则：
    - 传感器/存在感应变为 on / 有人 / 检测到人 → 'arrival'
    - 传感器/存在感应变为 off / 无人 / 离开   → 'departure'
    - 其余                                   → 'other'（不入缓存）
    """
    _ARRIVAL_KEYWORDS = ("变为 on", "检测到人", "有人进入", "人员到达", "person_count", "活跃人数")
    _DEPARTURE_KEYWORDS = ("变为 off", "无人", "人员离开", "离开检测", "人数为0", "人数=0")
    t_lower = trigger.lower()
    for kw in _ARRIVAL_KEYWORDS:
        if kw in trigger or kw.lower() in t_lower:
            return "arrival"
    for kw in _DEPARTURE_KEYWORDS:
        if kw in trigger or kw.lower() in t_lower:
            return "departure"
    return "other"


def _estimate_prompt_tokens(text: str) -> int:
    """粗略估算 prompt token 数（中文≈1.5字/token，其他≈4字/token）。"""
    if not text:
        return 0
    cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
    non_cn_chars = len(text) - cn_chars
    return int(cn_chars / 1.5 + non_cn_chars / 4)


def _clip_with_tail_notice(text: str, target_chars: int, label: str) -> str:
    """将文本裁剪到目标长度，并附带统一裁剪提示。"""
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


def _enforce_token_budget_hard(
    sections: list[dict[str, Any]],
    total_budget: int,
    estimate_fn: Callable[[str], int],
) -> tuple[dict[str, str], int, list[str]]:
    """按优先级对可裁剪段执行硬预算，直到总 token 估算落入预算。

    sections 元素格式：
      {
        "name": "section_name",
        "text": "...",
        "trim_step": 0.15,      # 每轮裁剪比例
        "min_ratio": 0.20,       # 最低保留比例
        "hard_min_chars": 120,   # 最低保留字符硬下限
        "priority": 0            # 数值越小越先裁
      }
    """
    ordered = sorted(sections, key=lambda x: x.get("priority", 100))
    texts: dict[str, str] = {s["name"]: s.get("text", "") or "" for s in ordered}

    def _render() -> str:
        return "".join(texts[s["name"]] for s in ordered)

    total_tokens = estimate_fn(_render())
    logs: list[str] = []
    if total_tokens <= total_budget:
        return texts, total_tokens, logs

    for section in ordered:
        name = section["name"]
        original_text = texts.get(name, "")
        if not original_text:
            continue

        base_len = len(original_text)
        min_ratio = float(section.get("min_ratio", 0.2))
        trim_step = float(section.get("trim_step", 0.15))
        hard_min_chars = int(section.get("hard_min_chars", 80))
        min_chars = max(hard_min_chars, int(base_len * min_ratio))

        current_text = texts[name]
        while total_tokens > total_budget and len(current_text) > min_chars:
            cur_len = len(current_text)
            drop_chars = max(80, int(cur_len * trim_step))
            target_len = max(min_chars, cur_len - drop_chars)
            before_tokens = total_tokens
            clipped_text = _clip_with_tail_notice(current_text, target_len, name)
            if clipped_text == current_text:
                break
            texts[name] = clipped_text
            current_text = clipped_text
            total_tokens = estimate_fn(_render())
            logs.append(
                f"{name}: {before_tokens}->{total_tokens} tok, chars {cur_len}->{len(current_text)}"
            )

        if total_tokens <= total_budget:
            break

    return texts, total_tokens, logs


class InferenceMixin:
    """Mixin: AI 推理引擎 — Prompt 组装、API 调用、决策执行。"""

    # 时间表达式正则（用于规则/习惯的时间适用性标注）
    _TIME_RE = re.compile(
        r'(\d{1,2})\s*[点时：:]\s*'
        r'(?:(以后|之后|后|以前|之前|前|到|至|-)\s*'
        r'(?:(\d{1,2})\s*[点时：:]?\s*)?)?'
    )

    # ── 习惯/规则文本工具 ─────────────────────────────────────────────────────

    def _redact_sensitive(self, text: str) -> str:
        """从日志文本中脱敏 API Key 等敏感信息。"""
        api_key = getattr(self, "_online_api_key", "") or ""
        if api_key and len(api_key) > 8 and api_key in text:
            text = text.replace(api_key, api_key[:4] + "***" + api_key[-4:])
        return text

    def _get_habits_text(self) -> str:
        lines = [self._item_display(c, lk) for c, lk in self._habits]
        return "\n".join(lines) if lines else "暂无配置"

    def _get_locked_habits_text(self) -> str:
        return "\n".join(c for c, lk in self._habits if lk)

    def _get_normal_habits_text(self) -> str:
        return "\n".join(c for c, lk in self._habits if not lk)

    def _get_rules_text(self) -> str:
        return "\n".join(self._item_display(c, lk) for c, lk in self._rules)

    def _get_locked_rules_text(self) -> str:
        return "\n".join(c for c, lk in self._rules if lk)

    def _get_normal_rules_text(self) -> str:
        return "\n".join(c for c, lk in self._rules if not lk)

    @staticmethod
    def _item_display(content: str, locked: bool) -> str:
        """习惯/规则统一显示格式。"""
        return f"🔒 {content}" if locked else content

    # 向后兼容别名
    _habit_display = _item_display
    _rule_display = _item_display

    def _find_item_idx(self, items: list, display_text: str) -> int:
        """在 items（[(content, locked), ...]）中按显示文本查找索引。"""
        clean = display_text.lstrip("🔒 ").strip()
        for i, (c, lk) in enumerate(items):
            if c == clean or display_text == self._item_display(c, lk):
                return i
        return -1

    def _find_habit_idx(self, display_text: str) -> int:
        return self._find_item_idx(self._habits, display_text)

    def _find_rule_idx(self, display_text: str) -> int:
        return self._find_item_idx(self._rules, display_text)

    def _load_pattern_summary(self) -> str:
        """从磁盘加载行为模式摘要。必须在 executor 线程中调用，不可在协程中直接调用。"""
        import os
        try:
            if os.path.exists(self._pattern_file):
                with open(self._pattern_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("summary", "")
        except Exception as e:
            _LOGGER.debug("[InferenceMixin] 加载行为模式摘要失败: %s", e)
        return ""

    # ── 联网与工具（Phase 5） ──────────────────────────────────────────────────

    async def _detect_and_run_tools(self, trigger: str) -> str:
        """检测触发内容是否需要调用联网工具，并返回工具执行结果。"""
        if not hasattr(self, "_tools") or not self._tools:
            return ""

        if trigger.startswith("[巡检]"):
            return ""

        _WEATHER_KW = ("天气", "几度", "下雨", "气温", "穿什么", "温度", "weather", "temp")
        _SEARCH_KW = ("搜", "查询", "什么是", "怎么", "最近", "新闻", "电影", "百科", "search", "who", "what", "how", "解释", "推荐")
        
        lower_trigger = trigger.lower()
        is_weather = any(kw in lower_trigger for kw in _WEATHER_KW)
        is_search = any(kw in lower_trigger for kw in _SEARCH_KW)
        
        if not (is_weather or is_search):
            return ""

        tool_name = ""
        tool_query = ""
        
        if is_weather:
            tool_name = "weather"
            tool_query = "local"
        elif is_search:
            tool_name = "search"
            tool_query = re.sub(r"^(请|帮我|想|我想)?(搜一下|搜索|查询|搜|查|找|问下|问问|问|what is|how to|search for|解释下|解释一下|给我推荐|推荐下)\s*", "", trigger)
            tool_query = tool_query.strip(" ?？")

        if tool_name:
            # M4: 清洗工具查询内容，防止注入，限制长度
            tool_query = re.sub(r"[\n\r【】『』「」{}]", " ", tool_query).strip()[:150]
            self._sys_log("INFO", f"[工具] 准备调用 {tool_name} | 参数: {tool_query}")
            res = await self._tools.call_tool(tool_name, tool_query)
            if res:
                self._sys_log("INFO", f"[工具] 返回结果片段: {res[:50]}...")
                return f"\n【实时联网信息】\n来自工具({tool_name})的反馈：{res}\n"
        
        return ""

    def _save_pattern_summary(self, summary: str) -> None:
        """将行为模式摘要写入磁盘。必须在 executor 线程中调用，不可在协程中直接调用。"""
        import os
        try:
            with open(self._pattern_file, "w", encoding="utf-8") as f:
                json.dump({"summary": summary, "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                          f, ensure_ascii=False, indent=2)
        except Exception as e:
            _LOGGER.warning("Pattern save failed: %s", e)

    def _annotate_time(self, text: str, cur_hour: int) -> str:
        """Annotate each line with time-applicability if it contains time conditions."""
        if not text:
            return text
        out = []
        for line in text.split("\n"):
            m = self._TIME_RE.search(line)
            if not m:
                out.append(line)
                continue
            h1 = int(m.group(1))
            op = m.group(2) or ""
            h2 = int(m.group(3)) if m.group(3) else None
            applicable = True
            if op in ("以后", "之后", "后"):
                applicable = cur_hour >= h1
            elif op in ("以前", "之前", "前"):
                applicable = cur_hour < h1
            elif op in ("到", "至", "-") and h2 is not None:
                if h1 <= h2:
                    applicable = h1 <= cur_hour <= h2
                else:
                    applicable = cur_hour >= h1 or cur_hour <= h2
            if applicable:
                out.append(f"{line}  ✅[当前{cur_hour}点，在适用时间内]")
            else:
                out.append(f"{line}  ❌[当前{cur_hour}点，不在适用时间内，跳过此条]")
        return "\n".join(out)

    # ── 历史上下文查询 ────────────────────────────────────────────────────────

    async def _get_history_context(self, trigger_room: str = "") -> str:
        """智能历史上下文构建（Phase P0-3）。

        三段式：近期事件（区分来源）+ 今日活动摘要 + 触发房间近 1 小时。
        替代原始 8 条事件的平铺列表，信息密度更高。
        """
        sections: list[str] = []

        # 1. 最近 5 条事件（即时感知，区分来源）
        recent = await self._async_query(
            "SELECT time, detail, source FROM events ORDER BY id DESC LIMIT 5",
            max_rows=0,
        )
        if recent:
            sections.append("近期事件：")
            for r in recent:
                tag = {"user": "\U0001f464", "ai": "\U0001f916"}.get(r.get("source", ""), "\u2699\ufe0f")
                sections.append(f"  {tag} [{r['time'][-8:]}] {r['detail']}")

        # 2. 今日行为摘要（按房间统计）
        summary = await self._async_query(
            "SELECT area, COUNT(*) as cnt FROM events "
            "WHERE time >= date('now') AND area != '' "
            "GROUP BY area ORDER BY cnt DESC LIMIT 5",
            max_rows=0,
        )
        if summary:
            sections.append("今日活动：" + "，".join(
                f"{s['area']}{s['cnt']}次" for s in summary
            ))

        # 3. 触发房间近 1 小时（如有）
        if trigger_room:
            room_evts = await self._async_query(
                "SELECT time, detail, source FROM events "
                "WHERE area = ? AND time >= datetime('now', '-1 hour') "
                "ORDER BY id DESC LIMIT 5",
                (trigger_room,),
                max_rows=0,
            )
            if room_evts:
                sections.append(f"{trigger_room}近1小时：")
                for r in room_evts:
                    tag = {"user": "\U0001f464", "ai": "\U0001f916"}.get(r.get("source", ""), "")
                    sections.append(f"  {tag} [{r['time'][-8:]}] {r['detail']}")

        return "\n".join(sections) if sections else "暂无近期活动记录。"

    async def _get_realtime_habits(self, focus_room: str = "") -> str:
        """Query behavioral patterns for current hour with time-decay weighting.

        :param focus_room: 按房间过滤（Phase 11.4b）。非空时只返回该房间设备的习惯，
                           最多 5 条；空时返回全局 Top-6（向后兼容）。
        """
        now = datetime.now()
        hour, wd = now.hour, now.weekday()
        rows = await self._async_query(
            "SELECT entity, state, COUNT(*) as cnt, MAX(time) as last_time "
            "FROM events WHERE type IN ('Trigger','Override','Learning') "
            "AND entity!='' AND CAST(strftime('%H', time) AS INTEGER) BETWEEN ? AND ? "
            "AND CAST(strftime('%w', time) AS INTEGER) = ? "
            "AND time >= datetime('now', '-90 days') "
            "GROUP BY entity, state ORDER BY cnt DESC LIMIT 50",
            (max(0, hour - 1), min(23, hour + 1), (wd + 1) % 7),
        )
        if not rows:
            return ""

        # 当提供 focus_room 时，预建该房间内设备 ID 集合加速过滤
        room_entities: set[str] = set()
        if focus_room:
            room_entities = {
                eid for eid, info in self.device_info.items()
                if info.get("room", "") == focus_room
            }

        total_by_entity: dict[str, float] = {}
        weighted_by_entity_state: dict[tuple, float] = {}
        for r in rows:
            last_time = r.get("last_time") or now.strftime("%Y-%m-%d %H:%M:%S")
            decay = self._compute_memory_decay_score(last_time, r["cnt"])
            weighted_cnt = r["cnt"] * decay
            key = (r["entity"], r["state"])
            weighted_by_entity_state[key] = weighted_cnt
            total_by_entity[r["entity"]] = total_by_entity.get(r["entity"], 0) + weighted_cnt

        lines: list[str] = []
        seen: set[str] = set()
        sorted_items = sorted(weighted_by_entity_state.items(), key=lambda x: x[1], reverse=True)
        # focus_room 时最多 5 条，全局时最多 6 条
        max_lines = 5 if focus_room else 6
        for (eid, state), w_cnt in sorted_items:
            if eid not in self.device_info or eid in seen:
                continue
            # focus_room 过滤：只保留目标房间设备
            if focus_room and eid not in room_entities:
                continue
            name = self.device_info[eid].get("name", eid)
            total = total_by_entity.get(eid, 1)
            pct = round(w_cnt / total * 100) if total > 0 else 0
            if pct < 55:
                continue
            seen.add(eid)
            state_cn = "开启" if state in ("on", "open", "playing") else "关闭"
            condition = "（用户在场时）" if state_cn == "开启" else ""
            lines.append(f"- 此时段{condition}{pct}% 概率{state_cn}{name}")
            if len(lines) >= max_lines:
                break
        return "\n".join(lines)

    async def _get_recent_overrides(self) -> str:
        """Query recent user overrides (async, runs SQLite in executor)."""
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        rows = await self._async_query(
            "SELECT time, entity, detail FROM events WHERE type='Override' AND time > ? ORDER BY id DESC LIMIT 12",
            (cutoff,),
            max_rows=0,
        )
        if not rows:
            return ""
        
        from collections import Counter
        eids = [r["entity"] for r in rows]
        counts = Counter(eids)
        
        lines: list[str] = []
        for r in rows:
            eid = r["entity"]
            name = self.device_info.get(eid, {}).get("name", eid)
            manual_count = counts.get(eid, 1)
            freq_hint = f"（警告：该设备近期已被你错误操作并被用户推翻 {manual_count} 次！）" if manual_count >= 2 else ""
            lines.append(f"- [{r['time'][-11:]}] {name}：{r['detail']}{freq_hint}")
        
        return "⚠️ 【重要：用户修正记录】\n" + "\n".join(lines)

    def _build_baseline_hint(self, trigger_room: str = "") -> str:
        """构建设备使用基线的 Prompt 提示文本（P2 级别）。

        向 AI 展示用户在当前模式下实际使用哪些灯、哪些灯基本不用，
        让 AI 主动维持用户常态而非靠规则约束。

        :param trigger_room: 触发房间名（优先展示该房间基线，其次全局）
        :return: 基线提示文本
        """
        from .const import MODE_SHOWROOM
        try:
            lines: list[str] = []

            # 确定要查询的房间列表
            rooms_to_query: list[str] = []
            if trigger_room:
                rooms_to_query.append(trigger_room)
            # 展厅模式额外加展厅区域
            if self._mode == MODE_SHOWROOM and self.showroom_area_name:
                if self.showroom_area_name not in rooms_to_query:
                    rooms_to_query.append(self.showroom_area_name)
            # 家庭模式 trigger_room 为空时（全局触发），
            # 收集 device_info 中所有出现过的房间（去重），最多取前 2 个
            if not rooms_to_query:
                seen: list[str] = []
                for _info in self.device_info.values():
                    _r = (_info.get("room") or "").strip()
                    if _r and _r not in seen:
                        seen.append(_r)
                    if len(seen) >= 2:
                        break
                rooms_to_query = seen

            if not rooms_to_query:
                return ""

            room_hints: list[str] = []
            for room in rooms_to_query[:3]:  # 最多 3 个房间，防止 prompt 过长
                rows = self._get_baseline_for_room(room, min_samples=3)
                if not rows:
                    continue
                high = [r for r in rows if r["on_ratio"] >= 0.6]   # 常用灯
                low  = [r for r in rows if r["on_ratio"] < 0.25]   # 基本不用的灯

                room_lines: list[str] = []
                if high:
                    names = [
                        self.get_device_name(r["entity_id"]) if hasattr(self, "get_device_name")
                        else r["entity_id"]
                        for r in high[:8]
                    ]
                    room_lines.append(f"  ✅ 用户常开的灯（使用率≥60%，可正常开启）: {', '.join(names)}")
                if low:
                    names = [
                        self.get_device_name(r["entity_id"]) if hasattr(self, "get_device_name")
                        else r["entity_id"]
                        for r in low[:8]
                    ]
                    room_lines.append(f"  🚫 用户基本不开的灯（使用率<25%，禁止主动 turn_on）: {', '.join(names)}")

                if room_lines:
                    room_hints.append(f"【{room}】\n" + "\n".join(room_lines))

            if room_hints:
                lines.append(
                    "⚠️【P1 设备使用基线 — 强制遵守，优先级高于展厅展示规则】\n"
                    "以下基于用户实际使用习惯，✅标注的灯可正常开启，🚫标注的灯禁止AI主动开启："
                )
                lines.extend(room_hints)

            return "\n".join(lines) if lines else ""
        except Exception as e:
            _LOGGER.debug("[Baseline] 构建 hint 失败: %s", e)
            return ""

    def _get_active_ai_scenes_hint(self) -> str:
        """构建当前时段内可用的 AI 场景提示文本。"""
        from .const import AI_SCENE_STATUS_ACTIVE
        active = [
            s for s in getattr(self, "_ai_scenes_cache", [])
            if s.get("status") == AI_SCENE_STATUS_ACTIVE
        ]
        if not active:
            return ""

        now_hour = datetime.now().hour
        matched: list[str] = []
        other: list[str] = []

        for s in active:
            desc_short = s.get("description", "")[:60]
            line = f"- 【{s['name']}】{desc_short}（置信度 {s['confidence']}%）"
            if s.get("hour_start", 0) <= now_hour <= s.get("hour_end", 23):
                matched.append(f"★ {line}")
            else:
                other.append(line)

        parts: list[str] = []
        if matched:
            parts.append("当前时段适用 AI 场景（用户已确认，优先参考）：\n" + "\n".join(matched))
        if other:
            parts.append("其他 AI 场景（非当前时段）：\n" + "\n".join(other))

        return "\n".join(parts) if parts else ""

    async def _parse_scene_from_text(self, user_text: str) -> dict | None:
        """一句话生成场景：将用户自然语言描述解析为结构化场景参数。

        :param user_text: 用户描述，如"下午 2 点到 6 点，工作日，打开客厅的灯和空调，亮度 80%"
        :return: 结构化场景参数字典，或 None（解析失败）

        返回格式：
        {
            "name": "下午工作模式",
            "description": "工作日下午开客厅灯和空调",
            "entities": [
                {"entity_id": "light.xxx", "state": "on", "brightness_pct": 80},
                {"entity_id": "climate.xxx", "state": "cool", "temperature": 24}
            ],
            "hour_start": 14,
            "hour_end": 18,
            "weekday_mask": "12345"
        }
        """
        if not user_text or not user_text.strip():
            return None

        # 构建设备列表供 LLM 参考（防止幻觉）
        device_lines: list[str] = []
        for eid, info in self.device_info.items():
            if len(device_lines) >= 80:
                break
            name = info.get("name", eid)
            room = info.get("room", "")
            domain = eid.split(".")[0]
            device_lines.append(f"- {name}（{room}）entity_id={eid} domain={domain}")
        device_list = "\n".join(device_lines)

        system_prompt = (
            "你是智能家居场景解析助手。用户会用自然语言描述一个场景，你需要将其解析为结构化 JSON。\n\n"
            "【输出格式】严格输出以下 JSON，不要有任何额外文字：\n"
            "{\n"
            '  "name": "场景名称（简短，10字以内）",\n'
            '  "description": "场景描述（20字以内）",\n'
            '  "entities": [\n'
            '    {"entity_id": "light.xxx", "state": "on", "brightness_pct": 80},\n'
            '    {"entity_id": "climate.xxx", "state": "cool", "temperature": 24}\n'
            "  ],\n"
            '  "hour_start": 14,\n'
            '  "hour_end": 18,\n'
            '  "weekday_mask": "12345"\n'
            "}\n\n"
            "【weekday_mask 规则】使用 SQLite %w 格式（0=周日,1=周一,...,6=周六）：\n"
            '- 工作日："12345"\n'
            '- 周末：  "06"\n'
            '- 每天：  "0123456"\n\n'
            "【entity_id 规则】必须从下方设备列表中选取，禁止编造不存在的 entity_id。\n"
            "【state 规则】light 用 on/off，climate 用 cool/heat/auto/off，cover 用 open/close，switch 用 on/off。\n"
            "【可选参数】light 可附加 brightness_pct(0-100)、color_temp_kelvin；climate 可附加 temperature(16-30)。\n"
            "【时段规则】若用户未指定时段，hour_start=0, hour_end=23；若未指定星期，weekday_mask=\"0123456\"。\n\n"
            f"【当前可用设备列表】\n{device_list}"
        )

        user_prompt = f"请解析以下场景描述：\n{user_text.strip()[:300]}"

        engine: str = getattr(self, "engine", "local")
        try:
            async with aiohttp.ClientSession() as session:
                if engine == "local":
                    ollama_url: str = getattr(self, "ollama_url", "http://127.0.0.1:11434")
                    model: str = getattr(self, "ollama_model", "qwen3-smarthome")
                    payload = {
                        "model": model,
                        "stream": False,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "options": {"temperature": 0.1},
                    }
                    async with session.post(
                        f"{ollama_url}/api/chat",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            self._sys_log("WARN", f"[场景解析] Ollama 返回 HTTP {resp.status}")
                            return None
                        res = await resp.json()
                        raw = (res.get("message", {}).get("content") or "").strip()
                else:
                    api_key: str = getattr(self, "_online_api_key", "")
                    base_url: str = getattr(self, "online_base_url", "")
                    model = getattr(self, "online_model", "qwen3.5-flash")
                    if not api_key:
                        self._sys_log("WARN", "[场景解析] 云端引擎未配置 API Key")
                        return None
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                    }
                    async with session.post(
                        f"{base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            self._sys_log("WARN", f"[场景解析] 云端 API 返回 HTTP {resp.status}")
                            return None
                        res = await resp.json()
                        raw = (
                            res.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                            or ""
                        ).strip()

            # 提取 JSON（支持嵌套大括号，找到第一个平衡的 {} 块）
            _json_start = raw.find("{")
            if _json_start < 0:
                self._sys_log("WARN", f"[场景解析] LLM 未返回有效 JSON: {raw[:100]}")
                return None
            _depth = 0
            _json_end = -1
            for _i, _ch in enumerate(raw[_json_start:], _json_start):
                if _ch == "{":
                    _depth += 1
                elif _ch == "}":
                    _depth -= 1
                    if _depth == 0:
                        _json_end = _i + 1
                        break
            if _json_end < 0:
                self._sys_log("WARN", f"[场景解析] JSON 大括号不平衡: {raw[:100]}")
                return None
            parsed = json.loads(raw[_json_start:_json_end])

            # 基本字段校验
            if not parsed.get("name") or not parsed.get("entities"):
                self._sys_log("WARN", "[场景解析] 解析结果缺少必要字段")
                return None

            # 过滤不存在于 device_info 的 entity_id（防幻觉）
            valid_entities = [
                e for e in parsed["entities"]
                if e.get("entity_id") in self.device_info
            ]
            if not valid_entities:
                self._sys_log("WARN", "[场景解析] 解析出的设备均不在 device_info 中")
                return None
            parsed["entities"] = valid_entities

            # 标准化 actions（优先使用 LLM 给出的 actions；否则由 entities 推导）
            raw_actions = parsed.get("actions") if isinstance(parsed.get("actions"), list) else []
            valid_actions = normalize_raw_actions(raw_actions, device_info=self.device_info)
            if not valid_actions:
                valid_actions = entities_to_actions(
                    valid_entities,
                    device_info=self.device_info,
                    on_states=("on", "open", "heat", "cool", "auto"),
                )
            parsed["actions"] = valid_actions

            # 确保时段字段有效
            parsed.setdefault("hour_start", 0)
            parsed.setdefault("hour_end", 23)
            parsed.setdefault("weekday_mask", "0123456")
            parsed.setdefault("description", user_text.strip()[:50])

            self._sys_log("INFO", f"[场景解析] 成功解析场景「{parsed['name']}」，{len(valid_entities)} 个设备")
            return parsed

        except json.JSONDecodeError as e:
            self._sys_log("WARN", f"[场景解析] JSON 解析失败: {e}")
            return None
        except Exception as e:
            self._sys_log("WARN", f"[场景解析] 解析异常: {e}")
            return None

    # ── Frigate 视觉感知上下文 ─────────────────────────────────────────────────

    def _build_vision_context(self) -> str:
        """构建 Frigate 视觉感知上下文区块（Phase 7G：含行为识别标签）。

        输出结构：
          【视觉感知（Frigate 摄像头）】
          - 客厅：1 人在场（摄像头确认）| 行为：阅读（坐在沙发看书）
          - 展厅：无人（摄像头确认）
          ↑ ...
        """
        import time as _t
        from .const import FRIGATE_PERSON_COUNT_KW

        # ── 1. 从 Frigate 传感器汇总各房间人数 ────────────────────────────────
        room_counts: dict[str, int] = {}
        for eid, dev in self.device_info.items():
            if not eid.startswith("sensor."):
                continue
            if not any(kw in eid.lower() for kw in FRIGATE_PERSON_COUNT_KW):
                continue
            room = dev.get("room", "").strip() or dev.get("name", eid)
            state = self.hass.states.get(eid)
            if not state:
                continue
            try:
                count = int(float(state.state))
                room_counts[room] = max(room_counts.get(room, 0), count)
            except (ValueError, TypeError):
                pass

        # ── 2. 汇总各摄像头最新行为标签（Phase 7G），按房间索引 ────────────────
        # _frigate_camera_activity: {camera_id: {label, desc, ts}}
        # _get_frigate_camera_room: camera_id -> room_name（FrigateMixin 提供）
        _now = _t.time()
        room_activity: dict[str, dict] = {}
        camera_activity: dict[str, dict] = getattr(self, "_frigate_camera_activity", {})
        for cam_id, act in camera_activity.items():
            if _now - act.get("ts", 0) > 600:  # 10 分钟内有效
                continue
            room_name = ""
            if hasattr(self, "_get_frigate_camera_room"):
                room_name = self._get_frigate_camera_room(cam_id)
            if room_name and room_name not in room_activity:
                room_activity[room_name] = act  # 每个房间取最新一条

        if not room_counts and not room_activity:
            return ""

        lines = ["【视觉感知（Frigate 摄像头）】"]

        # ── 3. 输出各房间：人数 + 行为标签（若有）────────────────────────────
        visited_rooms: set[str] = set()
        for room, count in room_counts.items():
            visited_rooms.add(room)
            act = room_activity.get(room, {})
            act_label = act.get("label", "")
            act_desc  = act.get("desc", "")
            behavior_text = ""
            if act_label and act_label not in ("无人", "未知"):
                behavior_text = f" | 行为：{act_label}"
                if act_desc:
                    behavior_text += f"（{act_desc}）"
            if count > 0:
                lines.append(f"- {room}：{count} 人在场（摄像头确认）{behavior_text}")
            else:
                lines.append(f"- {room}：无人（摄像头确认）")

        # 行为数据有但无对应传感器记录的房间（仅展示行为，不重复）
        for room_name, act in room_activity.items():
            if room_name in visited_rooms:
                continue
            act_label = act.get("label", "")
            act_desc  = act.get("desc", "")
            if act_label and act_label not in ("无人", "未知"):
                desc_part = f"（{act_desc}）" if act_desc else ""
                lines.append(f"- {room_name}：行为分析 → {act_label}{desc_part}")

        lines.append("↑ 以上为摄像头实时感知数据，人数和行为标签优先级高于普通传感器。")
        return "\n".join(lines) + "\n"

    # ── 场景检测 ──────────────────────────────────────────────────────────────

    @property
    def _effective_showroom_scenes(self) -> dict:
        """Return showroom scenes merged with any user-defined overrides."""
        from .const import SHOWROOM_SCENES
        import copy
        result = {}
        for k, v in SHOWROOM_SCENES.items():
            s = copy.copy(v)
            _ov = self._showroom_scene_overrides.get(k) if isinstance(self._showroom_scene_overrides, dict) else None
            if isinstance(_ov, dict):
                s.update({ck: cv for ck, cv in _ov.items() if cv})
            result[k] = s
        return result

    def _detect_scene(self, trigger_room: str = "") -> str:
        """Return current scene description. In showroom mode use virtual scene.

        v4.11.0：新增 trigger_room 参数，当触发来自工作区（ZONE_ROLE_WORK）时，
        返回普通家庭模式场景描述，使 AI 按家庭逻辑处理该区域，完全不受展厅规则影响。
        """
        from .const import MODE_SHOWROOM, ZONE_ROLE_WORK
        if self._mode == MODE_SHOWROOM:
            # 工作区触发：脱离展厅规则，返回家庭模式场景描述
            if trigger_room and hasattr(self, "get_zone_role"):
                if self.get_zone_role(trigger_room) == ZONE_ROLE_WORK:
                    # fall through 到下方家庭模式场景逻辑
                    pass
                else:
                    return self._detect_showroom_scene()
            else:
                return self._detect_showroom_scene()

        now = datetime.now()
        h, wd = now.hour, now.weekday()
        is_weekday = wd < 5
        day = "工作日" if is_weekday else "休息日"
        t = f"{h}:{now.minute:02d}"
        if is_weekday and 6 <= h < 8:
            return f"{day} {t}·起床准备出门，需要柔和低亮度灯光（30-40%）"
        if is_weekday and 8 <= h < 18:
            return f"{day} {t}·工作日日间，若无传感器确认有人，家中可能无人；请以实时传感器数据为准，不可贸然操作"
        if is_weekday and 18 <= h < 20:
            return f"{day} {t}·下班回家时段，主人疲惫，灯光宜温馨（40-50%）"
        if is_weekday and 20 <= h < 22:
            return f"{day} {t}·工作日晚间居家放松，主人在家，灯光宜柔和（40-60%）"
        if is_weekday and 22 <= h < 24:
            return f"{day} {t}·工作日睡前时段，灯光应逐渐调暗至10-20%，不宜主动开灯"
        if not is_weekday and 8 <= h < 11:
            return f"{day} {t}·周末慵懒早晨，主人可能还在床上，勿打扰"
        if not is_weekday and 11 <= h < 18:
            return f"{day} {t}·周末白天，主人在家活动"
        if not is_weekday and 18 <= h < 22:
            return f"{day} {t}·周末晚间居家放松，主人在家，灯光宜柔和（40-60%）"
        if not is_weekday and 22 <= h < 24:
            return f"{day} {t}·周末深夜，主人仍可能在活动，灯光维持40%，不宜主动关灯"
        if 0 <= h < 6:
            return f"{day} {t}·深夜，主人应在熟睡，严禁任何主动操作，除非检测到起夜"
        return f"{day} {t}"

    def _detect_showroom_scene(self) -> str:
        """返回展厅模式下的场景描述（不含工作区逻辑）。"""
        from .const import SHOWROOM_SCENES, format_biz_time
        now = datetime.now()
        now_min = now.hour * 60 + now.minute
        is_biz = self.showroom_biz_start_min <= now_min < self.showroom_biz_end_min
        biz_str = "营业时间" if is_biz else "非营业时间"
        biz_start_str = format_biz_time(self.showroom_biz_start_min)
        biz_end_str   = format_biz_time(self.showroom_biz_end_min)

        if self._showroom_custom_prompt:
            return f"[展厅·自定义·{biz_str}] {self._showroom_custom_prompt}"
        if self._showroom_scene and self._showroom_scene in SHOWROOM_SCENES:
            s = self._effective_showroom_scenes[self._showroom_scene]
            return f"[展厅·{s['label']}·{biz_str}] {s['scene_desc']}。AI行为要点：{s['hint']}"

        if is_biz:
            return f"[展厅·营业时间] 当前处于营业时段({biz_start_str}-{biz_end_str})，请保持灯光开启并积极展示智能家居能力。"
        return f"[展厅·非营业时间] 当前已过营业时间({biz_end_str}后)，若展厅内无人，应关闭所有灯光以节能；若检测到有人，应保持灯光开启。"

    def _build_zone_role_hint(self) -> str:
        """构建三区分治的区域角色说明文本，注入到 System Prompt 展厅附加规则中。

        动态读取 coordinator 的 zone map，生成可读的区域分类列表。
        若未配置则显示通用说明。
        """
        from .const import ZONE_ROLE_DISPLAY, ZONE_ROLE_WORK
        display_zones: list[str] = []
        experience_zones: list[str] = []
        work_zones: list[str] = []

        if self.showroom_area_name:
            display_zones.append(self.showroom_area_name)

        zone_map: dict[str, str] = getattr(self, "_showroom_zone_map", {})
        for zone, role in zone_map.items():
            if zone == self.showroom_area_name:
                continue
            if role == ZONE_ROLE_DISPLAY:
                display_zones.append(zone)
            elif role == ZONE_ROLE_WORK:
                work_zones.append(zone)
            else:
                experience_zones.append(zone)

        if not display_zones and not experience_zones and not work_zones:
            return (
                "【区域角色】未配置区域映射，所有非展厅区域默认按体验区（有人开灯/无人关灯）处理。"
            )

        lines = ["【📍 区域角色映射（严格遵守）】"]
        if display_zones:
            lines.append(f"  🟢 展示区（保持灯光）：{', '.join(display_zones)}")
        if experience_zones:
            lines.append(f"  🟡 体验区（有人演示/无人关灯）：{', '.join(experience_zones)}")
        if work_zones:
            lines.append(f"  ⚪ 工作区（完全家庭模式）：{', '.join(work_zones)}")
        return "\n".join(lines)

    # ── 设备状态上下文 ────────────────────────────────────────────────────────

    async def _build_context(self, focus_room: str = "", trigger: str = "") -> str:
        """Build device state context for AI.

        :param focus_room: 触发房间（Phase 11.4b）。非空时：
            - 可控设备只列出该房间设备
            - 传感器/在场设备保留全量（用于全局决策参考）
            - 对无关房间返回简要统计摘要而非完整列表
            这可将 Token 从 ~800 字节/设备 降至 ~200 字节。
        :param trigger: 触发描述（Phase 8E state-aware）。非空时：
            - arrival 触发：OFF 设备完整展示（turn_on 候选），ON 设备折叠为摘要行
            - departure 触发：ON 设备完整展示（turn_off 候选），OFF 设备折叠为摘要行
            - 仅对 light/switch 等简单 on/off 域应用折叠，climate/cover/fan 始终全展示
            预计节省 30-50% context_text Token（当房间设备多半已在期望状态时）。
        """
        # 8E: 检测触发类型用于后续设备分组折叠
        _trigger_type_8e = _detect_cache_trigger_type(trigger) if trigger else "other"
        from .const import MODE_SHOWROOM
        lines = []

        physical_present = False
        active_sensors: list[str] = []
        presence_kw = ("occupancy", "presence", "motion", "人体", "存在", "有人", "移动")
        for eid, info in self.device_info.items():
            if not eid.startswith("binary_sensor."):
                continue
            bs = self.hass.states.get(eid)
            if bs and bs.state == "on":
                name_lower = (info.get("name", "") + eid).lower()
                if any(kw in name_lower for kw in presence_kw):
                    physical_present = True
                    active_sensors.append(f"{info.get('name', eid)}({info.get('room', '')})")
        
        lines.append("【家中在场状态（⚠️ 核心判断依据）】")
        if self._mode == MODE_SHOWROOM:
            _now_min = datetime.now().hour * 60 + datetime.now().minute
            is_biz = self.showroom_biz_start_min <= _now_min < self.showroom_biz_end_min
            if is_biz:
                lines.append("✅ [展厅模式·营业中] 展厅内视为有客户在场。")
            else:
                lines.append("🌙 [展厅模式·非营业时间] 展厅进入非营业时段，请根据下方实时传感器判断有无人。")

            occ_map = self._get_room_occupancy_map()
            if occ_map:
                for room, sensors in occ_map.items():
                    occupied = any(s == "on" for _, s in sensors)
                    uncertain = any(s in ("unknown", "unavailable") for _, s in sensors)
                    symbol = "有人" if occupied else ("传感器状态不明(可能有人)" if uncertain else "无人")
                    lines.append(f"  - {room}：{symbol}")
        elif physical_present:
            lines.append(f"✅ 有人在场（物理传感器确认）: {', '.join(active_sensors[:5])}")
        else:
            people = self.hass.states.async_all("person")
            gps_home = any(p.state == "home" for p in people) if people else False
            if gps_home:
                lines.append("✅ 有人在场（GPS 定位确认）")
            else:
                lines.append("❓ 暂未检测到有人")

        if self.device_info:
            _CTRL_DOMAINS = {"light", "switch", "climate", "cover", "fan", "media_player", "vacuum"}
            _CTRL_DOMAINS_SET = _CTRL_DOMAINS

            # ── Phase 11.4b：focus_room 过滤 ─────────────────────────────────
            # 当提供 focus_room 时，可控设备按房间分两组：
            #   - focus_room 设备 → 完整列表
            #   - 其他房间设备 → 仅汇总「N 个设备，M 个开启」
            # 传感器/person 等只读实体保持全量（用于在场判断）
            if focus_room:
                _focus_devs = [
                    (e, i) for e, i in self.device_info.items()
                    if i.get("room", "") == focus_room and e.split(".")[0] in _CTRL_DOMAINS_SET
                ]
                _other_ctrl_devs = [
                    (e, i) for e, i in self.device_info.items()
                    if i.get("room", "") != focus_room and e.split(".")[0] in _CTRL_DOMAINS_SET
                ]
                _all_dev = _focus_devs  # 完整列表只构建 focus_room 的设备
            else:
                _all_dev = list(self.device_info.items())
                _focus_devs = []
                _other_ctrl_devs = []

            # H2: User Prompt 设备状态列表上限保护
            _MAX_CTX_DEVICES = 150 if not focus_room else 60
            _omitted = 0
            _all_dev_count = len(_all_dev)
            if _all_dev_count > _MAX_CTX_DEVICES:
                _ctrl = [(e, i) for e, i in _all_dev if e.split(".")[0] in _CTRL_DOMAINS_SET]
                _rest = [(e, i) for e, i in _all_dev if e.split(".")[0] not in _CTRL_DOMAINS_SET]
                _all_dev = (_ctrl + _rest)[:_MAX_CTX_DEVICES]
                # focus_room 模式：_omitted 基于该房间过滤后的数量（非全局总量）
                _omitted = _all_dev_count - _MAX_CTX_DEVICES

            # 三段式设备列表：可控 / 只读(修正抑制中) / 传感器
            _suppress_check = getattr(self, "_should_suppress_action", None)
            controllable_lines: list[str] = []
            readonly_lines: list[str] = []

            # Phase 8E: 状态感知折叠 — 仅对 focus_room + arrival/departure 生效
            # 对 light/switch 等简单开关域：已在期望状态的设备折叠为单行摘要，节省 Token
            # climate/cover/fan 等有属性的设备始终完整展示（AI 可能需要调整参数）
            # 常量 _8E_SIMPLE_DOMAINS / _8E_ON_STATE 已提升至模块级（v4.10.2 M2修复）
            _do_8e = focus_room and _trigger_type_8e in ("arrival", "departure")
            _8e_compact_names: list[str] = []  # 折叠设备的中文名

            def _make_device_line(entity_id: str, info: dict) -> str:
                state = self.hass.states.get(entity_id)
                st = state.state if state else "unknown"
                attrs = []
                if state and state.attributes:
                    a = state.attributes
                    # 灯光
                    if "brightness" in a and a["brightness"] is not None:
                        attrs.append(f"亮度={round(a['brightness'] / 255 * 100)}%")
                    if "color_temp_kelvin" in a and a["color_temp_kelvin"] is not None:
                        attrs.append(f"色温={a['color_temp_kelvin']}K")
                    # 窗帘
                    if "current_position" in a and a["current_position"] is not None:
                        attrs.append(f"位置={a['current_position']}%")
                    # 空调：同时显示当前模式、当前温度、目标温度
                    if "hvac_mode" in a and a["hvac_mode"] is not None:
                        _mode_cn = {"cool": "制冷", "heat": "制热", "fan_only": "送风",
                                    "dry": "除湿", "off": "关机", "auto": "自动"}.get(
                                        str(a["hvac_mode"]), str(a["hvac_mode"]))
                        attrs.append(f"模式={_mode_cn}")
                    if "current_temperature" in a and a["current_temperature"] is not None:
                        attrs.append(f"室温={a['current_temperature']}°C")
                    if "temperature" in a and a["temperature"] is not None:
                        attrs.append(f"目标={a['temperature']}°C")
                    # 媒体播放器：播放状态 + 音量
                    if "media_title" in a and a["media_title"]:
                        attrs.append(f"播放={str(a['media_title'])[:20]}")
                    elif st in ("playing", "paused", "idle"):
                        _st_cn = {"playing": "播放中", "paused": "已暂停", "idle": "空闲"}.get(st, st)
                        attrs.append(f"状态={_st_cn}")
                    if "volume_level" in a and a["volume_level"] is not None:
                        attrs.append(f"音量={round(float(a['volume_level']) * 100)}%")
                    # 风扇转速
                    if "percentage" in a and a["percentage"] is not None:
                        attrs.append(f"风速={a['percentage']}%")
                attr_str = f" [{', '.join(attrs)}]" if attrs else ""
                ctrl_mode = info.get("control_mode", "shared")
                ctrl_tag = ""
                if ctrl_mode == "ha":
                    ctrl_tag = " [HA优先⚠️]"
                elif ctrl_mode == "ai":
                    ctrl_tag = " [AI全权]"
                return f"- [{info['room']}] {info['name']}({entity_id}): {st}{attr_str}{ctrl_tag}"

            for entity_id, info in _all_dev:
                # 仅对可控域设备检查修正抑制（传感器不需要）
                _domain = entity_id.split(".")[0] if "." in entity_id else ""
                if _domain in _CTRL_DOMAINS_SET and _suppress_check is not None:
                    try:
                        _suppress, _count, _score = _suppress_check(entity_id, "turn_on")
                    except Exception:
                        _suppress, _count, _score = False, 0, 0.0
                    if _suppress:
                        readonly_lines.append(
                            f"- [{info['room']}] {info['name']}({entity_id}) "
                            f"⛔[AI禁止主动操控·用户已纠正{_count}次]"
                        )
                        continue

                # Phase 8E: 简单开关域 + arrival/departure → 折叠已在期望状态的设备
                if _do_8e and _domain in _8E_SIMPLE_DOMAINS:
                    _st_obj = self.hass.states.get(entity_id)
                    _st_val = _st_obj.state if _st_obj else "unavailable"
                    # M1修复(v4.10.2): 只信任明确状态，"unavailable"/"unknown" 始终全展示
                    # arrival: 明确已 on → 折叠（无需 turn_on）
                    # departure: 明确已 off → 折叠（无需 turn_off）
                    # unavailable/unknown: 不折叠，让 AI 看到完整状态后自行判断
                    _is_already_correct = (
                        (_trigger_type_8e == "arrival" and _st_val == _8E_ON_STATE) or
                        (_trigger_type_8e == "departure" and _st_val == "off")
                    )
                    if _is_already_correct:
                        _8e_compact_names.append(info.get("name", entity_id))
                        continue  # 跳过完整行，稍后追加摘要

                controllable_lines.append(_make_device_line(entity_id, info))

            # Phase 8E: 追加折叠摘要行（最多展示 8 个名称，超出部分用计数表示）
            if _8e_compact_names:
                _8e_label = "已开" if _trigger_type_8e == "arrival" else "已关"
                _show_names = _8e_compact_names[:8]
                _extra = f"等共 {len(_8e_compact_names)} 个" if len(_8e_compact_names) > 8 else f"共 {len(_8e_compact_names)} 个"
                controllable_lines.append(
                    f"（{_8e_label}·无需操作: {', '.join(_show_names)}"
                    + ("..." if len(_8e_compact_names) > 8 else "")
                    + f" {_extra}）"
                )

            _ctrl_header = f"\n【{focus_room}可控设备 — AI 可主动操控】" if focus_room else "\n【可控设备 — AI 可主动操控】"
            lines.append(_ctrl_header)
            if controllable_lines:
                lines.extend(controllable_lines)
            else:
                lines.append("（无）")

            if readonly_lines:
                _ro_header = (
                    f"\n【{focus_room}只读设备 — AI 禁止主动 turn_on，仅接受用户直接指令】"
                    if focus_room
                    else "\n【只读设备 — AI 禁止主动 turn_on，仅接受用户直接指令】"
                )
                lines.append(_ro_header)
                lines.append("⚠️ 以下设备用户已多次纠正AI的开灯行为，AI不得自主 turn_on，"
                             "仅当用户明确指令时才可执行：")
                lines.extend(readonly_lines)

            # ── 其他房间设备摘要（focus_room 模式，减少无关 Token）────────────
            if focus_room and _other_ctrl_devs:
                # 按房间分组，仅汇总开启数量
                _other_room_summary: dict[str, list[str]] = {}
                for eid, inf in _other_ctrl_devs:
                    room = inf.get("room", "未知")
                    st = self.hass.states.get(eid)
                    if st and st.state in ("on", "open", "playing"):
                        _other_room_summary.setdefault(room, []).append(inf.get("name", eid))
                if _other_room_summary:
                    lines.append("\n【其他房间（摘要）】")
                    for room, on_devs in _other_room_summary.items():
                        lines.append(f"  - {room}: {len(on_devs)} 个设备开启（{', '.join(on_devs[:3])}{'...' if len(on_devs) > 3 else ''}）")
                else:
                    lines.append(f"\n【其他房间（摘要）】所有房间设备均已关闭")

            # ── 8E item-3：最近 5 分钟状态变化设备（全局，focus_room 模式追加）─
            # 无论焦点房间是哪里，AI 都需要知道哪些设备"刚刚"发生了变化，
            # 以便判断是否是用户手动操作还是传感器触发。
            if focus_room:
                _recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                _recent_changed: list[str] = []
                for eid, inf in self.device_info.items():
                    _st = self.hass.states.get(eid)
                    if not _st or _st.state in ("unavailable", "unknown"):
                        continue
                    _lc = getattr(_st, "last_changed", None)
                    if _lc and _lc >= _recent_cutoff:
                        _room = inf.get("room", "")
                        _name = inf.get("name", eid)
                        _recent_changed.append(f"  - {_name}（{_room or eid}）: {_st.state}")
                if _recent_changed:
                    lines.append("\n【最近 5 分钟变化设备（全局）】")
                    lines.extend(_recent_changed[:10])  # 最多 10 条，避免 Token 过多

            if _omitted > 0:
                lines.append(f"（另有 {_omitted} 个传感器/辅助设备状态已省略）")

        # Frigate 视觉摘要（Frigate 集成启用时）
        if getattr(self, "_frigate_enabled", False):
            try:
                frigate_summary = self.get_frigate_zone_summary()
                if frigate_summary:
                    lines.append(f"\n{frigate_summary}")
            except Exception:
                pass

        # 注: 用户修正记录已移至 _call_ai_engine 的 P2 section（Phase 11.4 房间过滤）
        # _build_context 不再注入修正记录，避免与 P2 section 重复

        # 家庭成员状态（HA person 实体，帮助 AI 判断离家/在家/访客）
        try:
            person_eids = self.hass.states.async_entity_ids("person")
            if person_eids:
                person_lines = []
                home_count = 0
                for peid in person_eids:
                    pstate = self.hass.states.get(peid)
                    if pstate:
                        pname = pstate.attributes.get("friendly_name") or peid.split(".", 1)[-1]
                        pstatus = "在家" if pstate.state == "home" else "不在家"
                        if pstate.state == "home":
                            home_count += 1
                        person_lines.append(f"  - {pname}: {pstatus}")
                if person_lines:
                    summary = f"（{home_count}/{len(person_lines)} 人在家）"
                    lines.append(f"\n【家庭成员状态】{summary}")
                    lines.extend(person_lines)
        except Exception:
            pass

        # Phase 13.5: 太阳位置（日出日落、仰角）
        try:
            sun_state = self.hass.states.get("sun.sun")
            if sun_state:
                _elev = sun_state.attributes.get("elevation", 0)
                _rising = sun_state.attributes.get("rising", True)
                _nr = sun_state.attributes.get("next_rising", "")
                _ns = sun_state.attributes.get("next_setting", "")
                if _elev < 0 and _rising:
                    _phase = "日出前（天未亮）"
                elif _elev >= 0 and _rising:
                    _phase = "白天（太阳上升中）"
                elif _elev >= 0 and not _rising:
                    _phase = "下午（太阳下降中）"
                else:
                    _phase = "夜晚（日落后）"
                lines.append(f"\n【太阳位置】{_phase}（仰角 {_elev:.1f}°，"
                             f"{'正在升起' if _rising else '正在下降'}）")
                _rise_str = str(_nr)[:16] if _nr else "未知"
                _set_str = str(_ns)[:16] if _ns else "未知"
                lines.append(f"  日出: {_rise_str}  日落: {_set_str}")
        except Exception:
            pass

        # Phase 13.5: 环境光照度（自动扫描 illuminance/lux 传感器）
        try:
            _lux_kw = ("illuminance", "lux", "光照", "照度")
            _lux_lines: list[str] = []
            for eid in self.hass.states.async_entity_ids("sensor"):
                if any(kw in eid.lower() for kw in _lux_kw):
                    _st = self.hass.states.get(eid)
                    if _st and _st.state not in ("unknown", "unavailable"):
                        _name = (_st.attributes or {}).get("friendly_name", eid)
                        _room = self.device_info.get(eid, {}).get("room", "")
                        _lux_lines.append(f"  - [{_room}] {_name}: {_st.state} lux")
            if _lux_lines:
                lines.append("\n【环境光照度】")
                lines.extend(_lux_lines[:10])
        except Exception:
            pass

        # 脚本/场景（上限 40 条）
        if self._ha_scripts:
            lines.append("\n【可用脚本】")
            for s in self._ha_scripts[:40]:
                lines.append(f"- {s['name']}({s['entity_id']})")
        if self._ha_scenes:
            lines.append("\n【可用场景】")
            for s in self._ha_scenes[:40]:
                lines.append(f"- {s['name']}({s['entity_id']})")

        return "\n".join(lines)

    # ── 视觉 LLM 调用（Phase 7E）────────────────────────────────────────────

    async def _call_vision_llm(self, img_b64: str, prompt: str) -> str | None:
        """调用视觉大模型分析图片，返回描述文本。

        支持两条路径：
          - local：Ollama 多模态 API（messages[].images 字段），如 qwen3-vl:8b
          - online：OpenAI 兼容多模态 API（content 数组格式），如 qwen-vl-max / qwen3.5-omni-flash

        :param img_b64: Base64 编码的 JPEG 图片
        :param prompt: 分析指令文本
        :return: 描述字符串，失败时返回 None
        """
        if not getattr(self, "_vision_enabled", False):
            return None

        vision_engine: str = getattr(self, "_vision_engine", "online")
        vision_model: str  = getattr(self, "_vision_model", "qwen-vl-max")

        try:
            async with aiohttp.ClientSession() as session:
                if vision_engine == "local":
                    # ── Ollama 多模态路径：images 字段放置 base64 ────────────
                    # Ollama /api/chat 格式：messages[].images = [base64_str]
                    ollama_url: str = getattr(self, "ollama_url", "http://127.0.0.1:11434")
                    payload = {
                        "model": vision_model,
                        "stream": False,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt,
                                "images": [img_b64],
                            }
                        ],
                    }
                    async with session.post(
                        f"{ollama_url}/api/chat",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            self._sys_log("WARN", f"[视觉] Ollama VL 返回 HTTP {resp.status}")
                            return None
                        res = await resp.json()
                        return (res.get("message", {}).get("content") or "").strip() or None

                else:
                    # ── 云端 OpenAI 兼容多模态路径 ───────────────────────────
                    # 支持 DashScope qwen-vl-max / qwen3.5-omni-flash 等
                    api_key: str = getattr(self, "_online_api_key", "")
                    if not api_key:
                        self._sys_log("WARN", "[视觉] 云端视觉分析未配置 API Key")
                        return None
                    base_url: str = getattr(self, "online_base_url", "")
                    headers = {"Authorization": f"Bearer {api_key}"}
                    payload = {
                        "model": vision_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{img_b64}"
                                        },
                                    },
                                    {"type": "text", "text": prompt},
                                ],
                            }
                        ],
                    }
                    api_url = f"{base_url}/chat/completions"
                    async with session.post(
                        api_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status >= 400:
                            _err = ""
                            try:
                                _err = await resp.text()
                            except Exception:
                                pass
                            self._sys_log("WARN", f"[视觉] 云端 VL API HTTP {resp.status} | {_err[:120]}")
                            return None
                        res = await resp.json()
                        if res.get("error"):
                            err = res["error"]
                            self._sys_log("WARN", f"[视觉] 云端 VL API 错误: {err.get('message', err)}")
                            return None
                        return (
                            res.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content") or ""
                        ).strip() or None

        except Exception as exc:
            self._sys_log("WARN", f"[视觉] VL 调用异常: {exc}")
            return None

    # ── AI API 调用 ───────────────────────────────────────────────────────────

    def _get_dynamic_prompt_budget(self, trigger: str, is_voice: bool = False) -> int:
        """基于运行上下文计算推理预算（默认保持兼容，逐步动态化）。"""
        base_budget = 10_000
        device_count = len(getattr(self, "device_info", {}) or {})
        if device_count >= 200:
            base_budget += 2_000
        elif device_count >= 120:
            base_budget += 1_000
        if is_voice:
            base_budget += 500
        if "[巡检]" in (trigger or ""):
            base_budget += 500
        return max(8_000, min(base_budget, 16_000))

    async def _call_ai_engine(self, context: str, trigger: str, is_voice: bool = False, one_off_prompt: str = "", bundle: dict | None = None) -> dict | None:
        """Call Ollama or online API; return parsed JSON decision.

        bundle: 若提供（降级路径传入的 InferenceBundle），直接读取预计算字段，
                跳过重复的 DB/HA 查询（history, rules, habits, MemoryStore 等）。
                bundle 为 None 时走完整独立推理路径（展厅直推/语音等场景）。
        """
        from .const import MODE_SHOWROOM, SHOWROOM_SCENES

        # ── 数据采集：Bundle 快读路径 vs 独立推理路径 ────────────────────────────
        if bundle:
            # 所有数据已由 ContextBuilder 预计算，零 DB/HA 异步调用
            # _anno_hour / safe_one_off 不在此路径读取：
            #   rules 已由 ContextBuilder 预注解（无需 anno_hour）
            #   scene 已由 ContextBuilder 预计算（无需 safe_one_off 推导）
            time_str             = bundle.get("time_str", "00:00")
            day_str              = bundle.get("day_str", "")
            is_showroom          = bundle.get("is_showroom", False)
            trigger_room         = bundle.get("trigger_room", "")
            scene                = bundle.get("scene_desc", "")
            history              = bundle.get("history", "")
            locked_rules         = bundle.get("locked_rules", "")
            locked_habits        = bundle.get("locked_habits", "")
            normal_rules         = bundle.get("normal_rules", "")
            normal_habits        = bundle.get("normal_habits", "")
            manual_actions_text  = bundle.get("manual_actions_text", "")
            realtime_habits      = bundle.get("realtime_habits", "")
            memory_narrative     = bundle.get("memory_narrative", "")
            memory_constraint    = bundle.get("memory_constraint", "")
            memory_behavior      = bundle.get("memory_behavior", "")
            memory_reflex        = bundle.get("memory_reflex", "")
            memory_episodic      = bundle.get("memory_episodic", "")
            rag_context          = bundle.get("rag_context", "")
            corrections_text     = bundle.get("corrections_text", "")
            baseline_hint        = bundle.get("baseline_hint", "")
            recent_overrides     = bundle.get("recent_overrides", "")
            reflexion_antipatterns = bundle.get("reflexion_antipatterns", "")
            active_scenes_hint   = bundle.get("ai_scenes_hint", "")
            occupancy_section    = bundle.get("occupancy_section", "")
            vision_context       = bundle.get("vision_context", "")
            tool_results         = bundle.get("tool_results", "")
            priority_section_b   = bundle.get("priority_section", "")
            tiered_prompt        = bundle.get("showroom_tiered_prompt", "")

            # P1 section（锁定铁律）
            p1_parts: list[str] = []
            if locked_rules:    p1_parts.append(f"锁定规则：\n{locked_rules}")
            if locked_habits:   p1_parts.append(f"锁定画像：\n{locked_habits}")
            if priority_section_b: p1_parts.append(priority_section_b)
            p1_section = ("\n【⚠️ 用户锁定铁律（P1 配置）】\n" + "\n".join(p1_parts)) if p1_parts else ""

            # P2 section（行为学习）— 直接组装预计算文本
            p2_parts: list[str] = []
            if manual_actions_text:     p2_parts.append(manual_actions_text)
            if realtime_habits:         p2_parts.append(f"实时习惯：\n{realtime_habits}")
            if rag_context:             p2_parts.append(rag_context)

            layered_memory_parts: list[str] = []
            if memory_constraint:
                layered_memory_parts.append(f"【Constraint 记忆层】\n{memory_constraint}")
            if memory_behavior:
                layered_memory_parts.append(f"【Behavior 记忆层】\n{memory_behavior}")
            if memory_reflex:
                layered_memory_parts.append(f"【Reflex 记忆层】\n{memory_reflex}")
            if memory_episodic:
                layered_memory_parts.append(f"【Episodic Runtime 记忆层】\n{memory_episodic}")
            if layered_memory_parts:
                p2_parts.append("\n\n".join(layered_memory_parts))
            elif memory_narrative:
                p2_parts.append(memory_narrative)
            else:
                if corrections_text:    p2_parts.append(corrections_text)
                if baseline_hint:       p2_parts.append(baseline_hint)
            if recent_overrides:        p2_parts.append(recent_overrides)
            if reflexion_antipatterns:  p2_parts.append(reflexion_antipatterns)
            if active_scenes_hint:      p2_parts.append(active_scenes_hint)
            p2_section = (
                tiered_prompt + ("\n【P2 行为学习】\n" + "\n".join(p2_parts) if p2_parts else "")
                if is_showroom
                else ("\n【P2 行为学习】\n" + "\n".join(p2_parts) if p2_parts else "")
            )

            # P3 section（普通规则）
            p3_parts: list[str] = []
            if normal_rules:  p3_parts.append(f"普通规则：\n{normal_rules}")
            if normal_habits: p3_parts.append(f"普通画像：\n{normal_habits}")
            p3_section = ("\n【P3 画像与规则】\n" + "\n".join(p3_parts)) if p3_parts else ""

            region_hint = f"⚠️ 本次触发区域：「{trigger_room}」，请优先操作该区域设备。\n" if trigger_room else ""

        else:
            # ── 独立推理路径（无 bundle：展厅直推 / 语音 / 旧调用路径）──────────
            now = datetime.now()
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

            # 区域隔离：先提取触发房间，避免 trigger_room 先用后定义
            trigger_room = _extract_trigger_room(trigger)

            history = await self._get_history_context(trigger_room=trigger_room)

            # 安全脱敏 (Mitigate Prompt Injection)
            if one_off_prompt:
                safe_one_off = re.sub(r"[{}[\]'\"\n\r【】『』「」]", "", one_off_prompt)
                safe_one_off = safe_one_off[:200].strip()
            else:
                safe_one_off = ""
            if safe_one_off:
                scene = f"[展厅·一次性指令] {safe_one_off}"
            else:
                scene = self._detect_scene(trigger_room=trigger_room)

            is_showroom = self._mode == MODE_SHOWROOM
            if is_showroom:
                if self._showroom_scene and self._showroom_scene in SHOWROOM_SCENES:
                    time_str = self._effective_showroom_scenes[self._showroom_scene].get("virtual_time", "18:00")
                else:
                    time_str = "18:00"
            else:
                time_str = now.strftime("%H:%M")
            day_str = weekdays[now.weekday()]

            # M2: 规则时间注解与 AI 看到的 time_str 保持一致
            if is_showroom:
                try:
                    _anno_hour = int(time_str.split(":")[0])
                except (ValueError, IndexError):
                    _anno_hour = now.hour
            else:
                _anno_hour = now.hour
            locked_rules  = self._annotate_time(self._get_locked_rules_text(), _anno_hour)
            locked_habits = self._annotate_time(self._get_locked_habits_text(), _anno_hour)
            normal_rules  = self._annotate_time(self._get_normal_rules_text(), _anno_hour)
            normal_habits = self._annotate_time(self._get_normal_habits_text(), _anno_hour)

            region_hint = f"⚠️ 本次触发区域：「{trigger_room}」，请优先操作该区域设备。\n" if trigger_room else ""

            # P1 铁律
            p1_parts = []
            if locked_rules:  p1_parts.append(f"锁定规则：\n{locked_rules}")
            if locked_habits: p1_parts.append(f"锁定画像：\n{locked_habits}")
            priority_section = self._build_priority_prompt_section()
            if priority_section: p1_parts.append(priority_section)
            p1_section = ("\n【⚠️ 用户锁定铁律（P1 配置）】\n" + "\n".join(p1_parts)) if p1_parts else ""

            # P2 行为学习
            now_ts = _time.time()
            p2_parts = []
            with self._user_manual_actions_lock:
                _manual_actions_snapshot = dict(self._user_manual_actions)
            if _manual_actions_snapshot:
                m_lines = []
                for e, v in _manual_actions_snapshot.items():
                    age_s = now_ts - v["time"]
                    if age_s > self._USER_MANUAL_WINDOW:
                        continue
                    age_m = int(age_s / 60)
                    if age_s <= 300:
                        hint = "禁止反向"
                    elif age_s <= 900:
                        hint = "建议保持当前状态"
                    else:
                        hint = "仅供参考"
                    m_lines.append(f"- {self.get_device_name(e)}({e}): {age_m}min前手动操作（{hint}）")
                if m_lines:
                    p2_parts.append(
                        "【近期手动操作】（注意：'禁止反向'仅指禁止将该设备恢复到操作前的状态；"
                        "对其他设备或对同设备执行相同方向的操作不受此限制）\n"
                        + "\n".join(m_lines)
                    )

            _occ_map_for_prompt = self._get_room_occupancy_map() if hasattr(self, "_get_room_occupancy_map") else {}
            _room_presence_for_prompt = "any"
            if trigger_room and trigger_room in _occ_map_for_prompt:
                _sensors = _occ_map_for_prompt[trigger_room]
                if any(s == "on" for _, s in _sensors):
                    _room_presence_for_prompt = "occupied"
                elif all(s == "off" for _, s in _sensors):
                    _room_presence_for_prompt = "empty"

            realtime_habits = await self._get_realtime_habits(focus_room=trigger_room)
            if realtime_habits: p2_parts.append(f"实时习惯：\n{realtime_habits}")

            # ── RAG 条件性检索（Phase RAG）────────────────────────────────────
            if trigger_room and hasattr(self, "_db"):
                try:
                    from .rag_retriever import RAGRetriever
                    _rag_trigger_type = _detect_cache_trigger_type(trigger)
                    _rag = RAGRetriever(
                        db_query_func=self._db.query,
                        device_info=self.device_info,
                        get_device_name_func=getattr(self, "get_device_name", None),
                    )
                    _rag_context = await self.hass.async_add_executor_job(
                        _rag.retrieve,
                        trigger_room,
                        _rag_trigger_type,
                        now.hour,
                        now.weekday(),
                        now.weekday() >= 5,
                        _room_presence_for_prompt if _room_presence_for_prompt != "any" else "",
                    )
                    if _rag_context:
                        p2_parts.append(_rag_context)
                except Exception as _rag_exc:
                    _LOGGER.debug("[RAG] 独立推理路径 RAG 检索失败（忽略）: %s", _rag_exc)

            _room_context_injected = False
            if trigger_room and hasattr(self, "_db"):
                try:
                    from .memory_store import MemoryStore
                    _ms_trigger_type = _detect_cache_trigger_type(trigger)
                    _ms = MemoryStore(
                        db_query_func=self._db.query,
                        device_info=self.device_info,
                        get_device_name_func=getattr(self, "get_device_name", None),
                    )
                    _room_context = await self.hass.async_add_executor_job(
                        _ms.get_room_context,
                        trigger_room,
                        _ms_trigger_type,
                        now.hour,
                        _room_presence_for_prompt if _room_presence_for_prompt != "any" else "",
                    )
                    if _room_context:
                        p2_parts.append(_room_context)
                        _room_context_injected = True
                except Exception as _ms_exc:
                    _LOGGER.debug("[MemoryStore] 房间记忆生成失败（忽略）: %s", _ms_exc)

            if not _room_context_injected:
                try:
                    corrections_text = await self.hass.async_add_executor_job(
                        self._get_corrections_for_prompt, None,
                        trigger_room or None,
                        _room_presence_for_prompt if _room_presence_for_prompt != "any" else None,
                    )
                    if corrections_text: p2_parts.append(corrections_text)
                except Exception:
                    pass
                try:
                    baseline_hint = await self.hass.async_add_executor_job(
                        self._build_baseline_hint, trigger_room
                    )
                    if baseline_hint: p2_parts.append(baseline_hint)
                except Exception:
                    pass

            recent_overrides = await self._get_recent_overrides()
            if recent_overrides: p2_parts.append(recent_overrides)

            try:
                reflexion_antipatterns = self._get_reflexion_antipatterns_for_prompt()
                if reflexion_antipatterns: p2_parts.append(reflexion_antipatterns)
            except AttributeError:
                pass

            active_scenes_hint = self._get_active_ai_scenes_hint()
            if active_scenes_hint: p2_parts.append(active_scenes_hint)

            if is_showroom:
                tiered_prompt = await self._build_showroom_tiered_prompt()
                p2_section = tiered_prompt + (f"\n【P2 行为学习】\n" + "\n".join(p2_parts) if p2_parts else "")
            else:
                p2_section = (f"\n【P2 行为学习】\n" + "\n".join(p2_parts) if p2_parts else "")

            p3_parts = []
            if normal_rules:  p3_parts.append(f"普通规则：\n{normal_rules}")
            if normal_habits: p3_parts.append(f"普通画像：\n{normal_habits}")
            p3_section = (f"\n【P3 画像与规则】\n" + "\n".join(p3_parts)) if p3_parts else ""

            occupancy_section = self._build_occupancy_section()
            vision_context = (
                self._build_vision_context()
                if (getattr(self, "_frigate_enabled", False) or getattr(self, "_vision_enabled", False))
                else ""
            )
            tool_results = await self._detect_and_run_tools(trigger)

        # ── 1. System Prompt（静态，KV Cache 常驻） ─────────────────────────────
        sys_prompt = self._build_system_prompt(is_showroom)

        # API Key 有效性检查（仅 online 引擎时校验）
        if self.engine == "online" and not self._online_api_key:
            self._sys_log("ERROR", "[推理] 云端引擎未配置 API Key，无法调用，请前往集成设置填写 API Key")
            return None

        # 展厅模式/区域 提示
        if is_showroom:
            if "[展厅] 自定义场景:" in trigger:
                _cmd_text = trigger.split("[展厅] 自定义场景:")[-1].strip()
                # 操作员直接指令优先级高于 P1-P4 所有配置规则（包括用户锁定规则）
                # 仅 P0 安全红线（烟雾报警、燃气、门锁等）不可违反
                # 判断是否为"全局关闭"类指令（关所有灯/除展厅外关所有灯）
                _is_global_off = any(
                    kw in _cmd_text for kw in ("所有灯", "全部灯", "所有的灯", "全部的灯")
                ) and any(kw in _cmd_text for kw in ("关", "关闭", "熄"))
                _global_off_hint = (
                    "\n🔴【全局关灯指令】必须枚举并关闭所有灯光设备（light domain），包括：\n"
                    "  - 最近几分钟内刚被打开的灯（不受30分钟不反向规则限制）\n"
                    "  - 展厅/办公室/餐厅/客厅等所有区域的灯\n"
                    "  - P1《不反向操作》规则对本指令无效，必须覆盖所有 light 实体\n"
                ) if _is_global_off else ""
                mode_hint = (
                    f"【⚡ 操作员直接指令 — 最高优先级】\n"
                    f"指令内容：「{_cmd_text}」\n"
                    "⚠️ 此指令优先级高于 P1-P4 所有规则，包括用户设置的锁定规则（如《无人关灯》《营业时间规则》等）。\n"
                    "请立即执行该指令，confidence 填 90 以上。\n"
                    "不得以《无人在场》《规则冲突》为由返回空 actions 或低置信度。\n"
                    f"唯一不可违反的是 P0 安全红线（烟雾报警、燃气探测器、门锁等）。{_global_off_hint}"
                )
            else:
                from .const import format_biz_time
                biz_s = format_biz_time(self.showroom_biz_start_min)
                biz_e = format_biz_time(self.showroom_biz_end_min)
                mode_hint = (
                    f"【展厅模式】营业时间 {biz_s}-{biz_e}\n"
                    "区域规则（严格执行）：\n"
                    "· 展示区（产品陈列）：营业时间内无论有无顾客，灯光保持开启以展示效果\n"
                    "· 体验区（客厅/餐厅等）：有顾客时开灯/调场景；顾客离开后 <=2 分钟必须关灯节能，"
                    "  即使仍在营业时间内也必须执行关灯，顾客已离开则无需维持展示效果\n"
                    "· 办公区：仅员工使用，无员工时关灯，不受营业时间规则影响\n"
                    "!! 不能因营业时间或展厅模式而忽视体验区/办公区的无人关灯逻辑"
                )
        else:
            mode_hint = region_hint

        # 语音指令特殊提示
        voice_hint = (
            "\n⚡【语音指令 — 用户直接命令】请立即执行，reply 字段作为语音回答。"
            "此指令优先级高于 P1-P4 所有规则（包括锁定规则），不得以规则冲突或无人在场为由拒绝执行。\n"
        ) if is_voice else ""

        # Phase 13.5: 季节月份感知
        _month = datetime.now().month
        _season_map = {12: "冬", 1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春",
                       6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋", 11: "秋"}
        _season = _season_map.get(_month, "")

        # ── Prompt Token 预算硬保护（组装后强校验 + 分段逐步裁剪）───────────────
        # 优先级：联网信息 → 历史记录 → 环境状态 → 视觉感知 → 在场状态 → P3 → P2（P1 不裁剪）
        # 要求：组装后必须落入预算，不满足则按优先级逐段裁剪并每轮重估。
        prompt_budget = self._get_dynamic_prompt_budget(trigger, is_voice=is_voice)

        stable_header = "".join([
            f"当前时间: {time_str} ({day_str}), {_month}月({_season}季), 场景: {scene}\n",
            f"触发事件: {trigger}\n",
            f"{voice_hint}",
            f"{mode_hint}\n",
        ])

        sections = [
            {
                "name": "occupancy_section",
                "text": occupancy_section,
                "priority": 4,
                "trim_step": 0.18,
                "min_ratio": 0.25,
                "hard_min_chars": 80,
            },
            {
                "name": "vision_context",
                "text": vision_context,
                "priority": 3,
                "trim_step": 0.20,
                "min_ratio": 0.20,
                "hard_min_chars": 60,
            },
            {
                "name": "context_section",
                "text": f"【环境状态】\n{context}\n",
                "priority": 2,
                "trim_step": 0.15,
                "min_ratio": 0.28,
                "hard_min_chars": 160,
            },
            {
                "name": "history_section",
                "text": f"【历史记录】\n{history}\n",
                "priority": 1,
                "trim_step": 0.15,
                "min_ratio": 0.30,
                "hard_min_chars": 120,
            },
            {
                "name": "tool_results",
                "text": tool_results or "",
                "priority": 0,
                "trim_step": 0.25,
                "min_ratio": 0.0,
                "hard_min_chars": 0,
            },
            {
                "name": "p3_section",
                "text": p3_section,
                "priority": 5,
                "trim_step": 0.20,
                "min_ratio": 0.15,
                "hard_min_chars": 120,
            },
            {
                "name": "p2_section",
                "text": p2_section,
                "priority": 6,
                "trim_step": 0.10,
                "min_ratio": 0.55,
                "hard_min_chars": 400,
            },
            {
                "name": "p1_section",
                "text": p1_section,
                "priority": 99,
                "trim_step": 0.0,
                "min_ratio": 1.0,
                "hard_min_chars": len(p1_section),
            },
        ]

        raw_user_prompt = stable_header + "".join((s.get("text") or "") for s in sorted(sections, key=lambda x: x.get("priority", 100))) + "\n"
        raw_tokens = _estimate_prompt_tokens(raw_user_prompt)

        trimmed_sections, _up_tokens, trim_logs = _enforce_token_budget_hard(
            sections=sections,
            total_budget=prompt_budget,
            estimate_fn=lambda _merged: _estimate_prompt_tokens(stable_header + _merged + "\n"),
        )

        ordered_names = [s["name"] for s in sorted(sections, key=lambda x: x.get("priority", 100))]
        user_prompt = stable_header + "".join(trimmed_sections.get(n, "") for n in ordered_names) + "\n"

        # 兜底：若仍超预算（通常意味着 P1 自身过大），强制压缩可裁剪段并保留 P1
        if _up_tokens > prompt_budget:
            emergency_sections = [
                {
                    "name": n,
                    "text": trimmed_sections.get(n, ""),
                    "priority": i,
                    "trim_step": 0.35,
                    "min_ratio": 0.0,
                    "hard_min_chars": 0,
                }
                for i, n in enumerate(ordered_names)
                if n != "p1_section"
            ]
            emergency_trimmed, _up_tokens, emergency_logs = _enforce_token_budget_hard(
                sections=emergency_sections,
                total_budget=prompt_budget,
                estimate_fn=lambda _merged: _estimate_prompt_tokens(stable_header + _merged + trimmed_sections.get("p1_section", "") + "\n"),
            )
            for n in emergency_trimmed:
                trimmed_sections[n] = emergency_trimmed[n]
            user_prompt = stable_header + "".join(trimmed_sections.get(n, "") for n in ordered_names) + "\n"
            trim_logs.extend([f"emergency::{x}" for x in emergency_logs])

        _up_tokens = _estimate_prompt_tokens(user_prompt)

        # 最终硬保护：若仍超预算，按最小幅度裁剪 P1（仅极端场景）直至落入预算
        if _up_tokens > prompt_budget:
            p1_curr = trimmed_sections.get("p1_section", "")
            while _up_tokens > prompt_budget and p1_curr:
                prev_len = len(p1_curr)
                next_len = max(256, prev_len - max(120, int(prev_len * 0.12)))
                next_p1 = _clip_with_tail_notice(p1_curr, next_len, "p1_section")
                if next_p1 == p1_curr:
                    break
                before_tokens = _up_tokens
                p1_curr = next_p1
                trimmed_sections["p1_section"] = p1_curr
                user_prompt = stable_header + "".join(trimmed_sections.get(n, "") for n in ordered_names) + "\n"
                _up_tokens = _estimate_prompt_tokens(user_prompt)
                trim_logs.append(
                    f"p1_section(last_resort): {before_tokens}->{_up_tokens} tok, chars {prev_len}->{len(p1_curr)}"
                )

        if trim_logs:
            self._sys_log(
                "WARN",
                f"[PromptBudget] 裁剪触发 | before≈{raw_tokens}tok after≈{_up_tokens}tok budget={prompt_budget} | "
                + " | ".join(trim_logs[:8]),
            )
            if len(trim_logs) > 8:
                _LOGGER.info("[PromptBudget] 裁剪日志省略 %d 条", len(trim_logs) - 8)

        if _up_tokens > prompt_budget:
            self._sys_log(
                "ERROR",
                f"[PromptBudget] 硬保护失败（已尝试所有段落）: ~{_up_tokens}tok > {prompt_budget}tok（focus_room={trigger_room if 'trigger_room' in dir() else 'N/A'}）",
            )

        self._sys_log("INFO", f"[Prompt] P1={bool(p1_parts)} P2={bool(p2_parts)} ~{_up_tokens}tok | 触发: {trigger[:50]}")

        # Phase 9.3: Structured Output JSON Schema（供 Ollama format 字段使用）
        from .schemas import DECISION_JSON_SCHEMA, validate_decision

        async def _do_call(engine_override: str | None = None) -> dict | None:
            """内部 API 调用，支持云端降级（Phase 9.1 统一 + P1.3 Structured Output）。"""
            _engine = engine_override or self.engine
            try:
                async with aiohttp.ClientSession() as session:
                    if _engine == "local":
                        # Phase 9.3: Ollama 传入 format 字段实现 Structured Output
                        payload = {
                            "model": self.ollama_model, "think": False, "stream": False,
                            "format": DECISION_JSON_SCHEMA,
                            "options": {"num_predict": 1500, "temperature": 0.1},
                            "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
                        }
                        async with session.post(f"{self.ollama_url}/api/chat", json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                            res = await resp.json()
                            raw = res.get("message", {}).get("content", "")
                    else:
                        if not self._online_api_key:
                            return None
                        headers = {"Authorization": f"Bearer {self._online_api_key}"}
                        base_url = self.online_base_url or ""
                        # 仅当 base_url 精确包含官方域名时才走 Anthropic 原生 API
                        # 避免第三方代理（如 openrouter.ai）使用 claude 模型名时被误判
                        _is_anthropic = "api.anthropic.com" in base_url
                        # Qwen3/Qwen3.5 系列模型默认启用 chain-of-thought 思考模式，
                        # 会先生成大量 <think>...</think> 内容再输出 JSON，严重增加响应时间。
                        # 智能家居控制场景无需深度推理，强制关闭思考模式以提升速度。
                        _model_name = (self.online_model or "").lower()
                        _base_url_lower = (self.online_base_url or "").lower()
                        # Qwen3 专属特性（json_schema / enable_thinking=false）
                        # 仅在 DashScope 官方端点启用；第三方代理不一定支持这两个参数
                        _is_dashscope = (
                            "dashscope" in _base_url_lower
                            or "aliyuncs" in _base_url_lower
                        )
                        _is_qwen3 = "qwen3" in _model_name and _is_dashscope

                        if _is_anthropic:
                            # Anthropic Claude: 显式 cache_control 标记 System Prompt 为可缓存
                            # 需要 anthropic-beta: prompt-caching-2024-07-31 头
                            headers["anthropic-beta"] = "prompt-caching-2024-07-31"
                            headers["anthropic-version"] = "2023-06-01"
                            system_msg = [{"type": "text", "text": sys_prompt, "cache_control": {"type": "ephemeral"}}]
                            payload = {
                                "model": self.online_model,
                                "max_tokens": 1500,
                                "system": system_msg,
                                "messages": [{"role": "user", "content": user_prompt}],
                            }
                        else:
                            # OpenAI 兼容接口（DeepSeek / 通义千问 / MiniMax 等）
                            # DeepSeek 对 >64 token 的 System Prompt 自动开启 KV Cache，无需额外参数
                            #
                            # Qwen3/3.5：DashScope 支持 json_schema 结构化输出（比 json_object 更强）
                            # json_schema 在 API 层强制字段结构，不依赖 prompt 指令遵从；
                            # strict=false 允许 params 含 additionalProperties（transition/color_temp_kelvin 等自由参数）
                            _response_format: dict
                            if _is_qwen3:
                                _response_format = {
                                    "type": "json_schema",
                                    "json_schema": {
                                        "name": "smart_agent_decision",
                                        "strict": False,
                                        "schema": DECISION_JSON_SCHEMA,
                                    },
                                }
                            else:
                                # 其他 OpenAI 兼容提供商（DeepSeek / MiniMax 等）
                                # 仅使用 json_object 保证兼容性（各厂 json_schema 实现差异较大）
                                _response_format = {"type": "json_object"}
                            payload = {
                                "model": self.online_model,
                                "messages": [
                                    {"role": "system", "content": sys_prompt},
                                    {"role": "user", "content": user_prompt},
                                ],
                                "response_format": _response_format,
                            }
                            # Qwen3/Qwen3.5 系列：关闭思考模式，减少响应时间
                            # 参考 DashScope 文档：enable_thinking=false 跳过 CoT 步骤
                            if _is_qwen3:
                                payload["enable_thinking"] = False
                        if _is_anthropic:
                            api_url = f"{self.online_base_url}/messages"
                        else:
                            api_url = f"{self.online_base_url}/chat/completions"
                        # 超时 90s：Qwen3.5-Flash 处理 10K+ token prompt 可能需 30-50s，
                        # Self-Rationalization Guard 会触发二次调用，60s 不足导致 TimeoutError
                        async with session.post(api_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                            # H1: 检查 HTTP 状态码，防止 4xx/5xx 错误被静默吞掉
                            if resp.status >= 400:
                                _err_body = ""
                                try:
                                    _err_body = await resp.text()
                                except Exception:
                                    pass
                                _err_hint = "（API Key 无效或已过期）" if resp.status == 401 else \
                                            "（触发限速，请稍后重试）" if resp.status == 429 else \
                                            "（请求格式错误，请检查模型名称和参数）" if resp.status == 400 else ""
                                self._sys_log("ERROR",
                                    f"[推理] {'Anthropic' if _is_anthropic else 'OpenAI'} API HTTP {resp.status}{_err_hint} | {self._redact_sensitive(_err_body[:200])}")
                                return None
                            res = await resp.json()
                            if _is_anthropic:
                                # 先检查 Anthropic 错误响应，防止错误被静默吞掉
                                if res.get("error"):
                                    err = res["error"]
                                    self._sys_log("ERROR",
                                        f"[推理] Anthropic API 错误: [{err.get('type')}] {err.get('message')}")
                                    return None
                                # Anthropic 响应格式：{"content": [{"type": "text", "text": "..."}]}
                                raw = (res.get("content") or [{}])[0].get("text", "")
                            else:
                                # OpenAI 兼容：检查 error 字段（如 rate_limit / invalid_request）
                                if res.get("error"):
                                    err = res["error"]
                                    self._sys_log("ERROR",
                                        f"[推理] OpenAI API 错误: [{err.get('type', 'unknown')}] {err.get('message', err)}")
                                    return None
                                raw = res.get("choices", [{}])[0].get("message", {}).get("content", "")

                    raw_clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                    # Phase 9.3: 先尝试直接 JSON 解析（Structured Output 通常是完整 JSON）
                    try:
                        parsed = json.loads(raw_clean)
                    except (json.JSONDecodeError, ValueError):
                        parsed = self._extract_json(raw_clean) or self._extract_json(raw)
                    return validate_decision(parsed, sys_log_func=getattr(self, "_sys_log", None))
            except Exception as e:
                # asyncio.TimeoutError 在 Python 3.11+ str() 为空字符串，需要特殊处理
                import asyncio as _asyncio
                _err_type = type(e).__name__
                _err_msg = str(e) or f"<{_err_type}>"
                if isinstance(e, (_asyncio.TimeoutError, TimeoutError)):
                    _err_msg = f"请求超时（>90s）— 检查网络或减少 Prompt 长度"
                _err_msg = self._redact_sensitive(_err_msg)
                self._sys_log("WARN" if engine_override else "ERROR",
                              f"[推理] {_engine} 调用失败 [{_err_type}]: {_err_msg}")
                # 可重试错误（网络/超时）re-raise，外层重试循环捕获
                if isinstance(e, (_asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
                    raise
                return None

        # 主调用（含重试 + 指数退避）
        import asyncio as _aio
        _MAX_RETRIES = 2
        out = None
        for _attempt in range(_MAX_RETRIES + 1):
            _retryable_error = False
            try:
                out = await _do_call()
            except (TimeoutError, ConnectionError, OSError):
                out = None
                _retryable_error = True
            if out is not None:
                break
            # 仅对可重试异常进行退避；正常 None（如 4xx/校验失败）不重试
            if not _retryable_error:
                break
            if _attempt < _MAX_RETRIES:
                _delay = 1.0 * (2 ** _attempt)  # 1s, 2s
                self._sys_log("WARN", f"[推理] 第 {_attempt + 1} 次调用失败（可重试异常），{_delay:.0f}s 后重试...")
                await _aio.sleep(_delay)
            else:
                break

        # 云端降级：本地引擎失败且已配置在线 API 时自动降级
        if out is None and self.engine == "local" and getattr(self, "_cloud_fallback", False) and self._online_api_key:
            self._sys_log("WARN", "[推理] 本地引擎无响应，尝试云端降级...")
            out = await _do_call("online")
            if out:
                self._sys_log("INFO", "[推理] 云端降级成功")

        if out:
            _conf = out.get('confidence', 0)
            _acts = out.get('actions', [])
            _reply_hint = ""
            # 置信度低或无动作时，附带 AI 的 reply 说明，方便排查
            if _conf < 60 or not _acts:
                _ai_reply = (out.get('reply') or out.get('speak') or "").strip()
                if _ai_reply:
                    _reply_hint = f" | AI说明: {_ai_reply[:80]}"
            self._sys_log("INFO", f"AI 推理成功 ← 置信度={_conf} 场景={out.get('scene')} 动作={len(_acts)}{_reply_hint}")

            # Phase 11.6: Self-Rationalization Guard（自我合理化防护）
            # 检测 AI 用"高置信度"掩盖"不作为"的死亡螺旋行为。
            # 若 confidence >= 60 但 actions 为空，且本次触发不是明确的"无需操作"场景，
            # 用追加 challenge context 的方式重试一次，要求 AI 审视自己的判断。
            if _conf >= 60 and not _acts and not is_voice:
                _scene_str = (out.get('scene') or "").lower()
                _trigger_type = _detect_cache_trigger_type(trigger)
                _no_action_ok = any(kw in _scene_str for kw in (
                    "无需", "已是", "状态正常", "保持现状", "不需要", "正常", "维持",
                    "灯已关", "设备已关", "所有设备已关",
                    # 「有人」场景：保持照明是合理的无操作，不应触发对抗重试
                    "有人保持", "保持照明", "保持灯光", "保持当前",
                    # 用户主动锁定保护期，不应强制操作
                    "用户锁定", "物理锁定", "物理操作保护", "保护期", "受保护",
                    # 展厅特有：展示区设备维持现状
                    "展厅维持", "展示设备", "营业时间",
                    # 展厅非营业时间 + 设备已被保护/已关灯的正常无操作场景（Phase 11.7）
                    "设备锁定", "锁定保护", "锁定状态",
                    "保持节能", "节能状态", "节能关灯",
                    "手动关灯", "已手动关", "用户手动",
                    "尊重用户", "尊重操作",
                    "灯光已关", "体验区灯光已关", "体验区无人",
                    "客厅体验区", "确认无人后",
                    "无人且灯", "灯均已关",
                    # 展厅无人巡检、核心展示灯维持开启（Phase 11.8 补充）
                    "核心展示灯", "展示灯开启", "核心展示",
                    "展示区灯光", "保持展示区", "展示区亮灯",
                    "保持灯光开启", "维持灯光", "灯光开启",
                    "营业时段", "营业巡检", "展厅营业",
                    # 体验区人员离开后保持常亮的展示策略（Phase 11.9 补充）
                    "体验区人员", "保持常亮", "展示灯光常亮", "常亮",
                    "营业展示", "保持营业展示", "展厅巡检",
                    "灯光常亮", "保持展示", "展示保持",
                ))
                # 离开类触发且模型已给出明确节能/无人语义时，允许无动作
                if _trigger_type == "departure" and any(kw in _scene_str for kw in (
                    "无人", "离开", "已离开", "节能", "无需关灯", "已关闭", "已关",
                )):
                    _no_action_ok = True

                if not _no_action_ok:
                    _retry_key = f"{_trigger_type}|{trigger[:120]}"
                    _retry_now = _time.time()
                    _retry_last = getattr(self, "_rational_guard_last_retry", {}).get(_retry_key, 0)
                    _retry_cooldown = 90
                    if _retry_now - _retry_last < _retry_cooldown:
                        self._sys_log(
                            "INFO",
                            f"[自我合理化防护] 同类触发 {_retry_cooldown}s 内已重试过，"
                            f"本次跳过对抗重试（scene={out.get('scene', '')}）",
                        )
                        return out

                    self._rational_guard_last_retry[_retry_key] = _retry_now
                    self._sys_log("WARN",
                        f"[自我合理化防护] 置信度={_conf} 但 actions=[]，"
                        f"场景描述未明确说明无需操作（{out.get('scene', '')}），"
                        f"触发对抗性重试..."
                    )
                    # 构造对抗性 challenge：把第一次结果反馈给 AI，要求其审视判断
                    _challenge_context = (
                        f"\n\n[⚠️ 系统审查 — 对抗性验证]\n"
                        f"你上一次的输出：confidence={_conf}, actions=[], scene=\"{out.get('scene', '')}\"\n"
                        f"但系统检测到当前环境可能需要操作（如：无人区域灯光仍开启、设备状态与场景不匹配等）。\n"
                        f"请重新审视你的判断：\n"
                        f"1. 如果确实无需操作，请在 scene 字段写明具体原因（如'客厅无人且灯已关闭'）\n"
                        f"2. 如果存在应该关灯/调暗/关闭的设备，请在 actions 中列出具体动作\n"
                        f"3. 不要因为修正历史中有'不要关灯'的记录就放弃关灯——请核查该修正是否在当前场景下适用"
                    )
                    # 保存原始 user_prompt，追加 challenge 后重试
                    _orig_user_prompt = user_prompt
                    user_prompt = _orig_user_prompt + _challenge_context
                    _retry_out = await _do_call()
                    user_prompt = _orig_user_prompt  # 恢复原始 prompt

                    if _retry_out and _retry_out.get('actions'):
                        self._sys_log("INFO",
                            f"[自我合理化防护] 对抗重试后 AI 给出了 {len(_retry_out['actions'])} 个动作，"
                            f"采用重试结果"
                        )
                        out = _retry_out
                    elif _retry_out:
                        self._sys_log("INFO",
                            f"[自我合理化防护] 对抗重试后 AI 仍无动作，"
                            f"场景={_retry_out.get('scene', '')}，接受本次判断"
                        )
                        out = _retry_out
        return out

    def _build_system_prompt(self, is_showroom: bool) -> str:
        """
        构建 System Prompt（Phase 9.2: Prefix Caching 优化版）。

        目标 > 1024 token，包含全部静态规则和 JSON Schema，
        使 KV Cache 在支持的供应商（Anthropic/DeepSeek/Ollama）生效。
        动态内容（时间、状态、用户习惯）保留在 User Prompt。
        """
        role = "展厅智能助手" if is_showroom else "智能家居私人管家"
        identity = (
            f"你是专业的{role}，基于 Home Assistant 平台运行。"
            f"你的任务是：根据传感器事件、实时设备状态和用户习惯，做出精准、安全的智能家居控制决策。\n"
            f"你的名字叫 SmartAgent，由开源社区开发。\n"
        )

        # ── P0/P1 安全红线（前置！优先级最高，必须在输出格式之前声明）────────
        # 研究表明 LLM 对 System Prompt 早期内容权重更高；安全规则必须先于格式指令出现
        safety_first = """
【🛑 P0 安全红线（代码级强制，绝对不可违反）】
- 有人在场时，严禁关闭：烟雾报警器、燃气探测器、门锁、摄像头、安防设备
- 严禁执行任何可能危及生命安全的操作
- 严禁操作不在设备清单中的设备（防止幻觉捏造 entity_id）
- 有人传感器检测到"有人"时，严禁关闭该区域灯光
- 深夜(0-6时)有人活动，灯光不超过 20%，不可主动开强光
- 用户刚手动操作某设备 5 分钟内，禁止 AI 反向操作
"""

        # ── 完整 JSON 输出格式 Schema ─────────────────────────────────────
        output_schema = """
【📋 输出格式（严格遵守，输出 ONLY 一个合法 JSON）】
字段说明：confidence 为 0-100 整数，不确定时填50以下，确定时填80以上。
{
  "intent":           "意图标识，如 arrival_lighting/departure_off/scene_switch/climate_adjust/no_action",
  "intent_label":     "意图中文标签，如 '晚间回家开灯' / '离开关灯' / '睡前调暗'",
  "scene":            "当前场景的简短中文描述（10-30字）",
  "confidence":       75,
  "scene_candidate":  "优先推荐的 HA 场景 entity_id（如 scene.living_room_evening），无匹配填空字符串",
  "param_adjustments": {"brightness_pct": 70, "color_temp_kelvin": 3500},
  "need_confirm":     false,
  "actions": [
    {
      "domain":         "light|switch|climate|cover|fan|script|scene|media_player|vacuum",
      "service":        "turn_on|turn_off|set_temperature|set_hvac_mode|open_cover|...",
      "entity_id":      "完整 HA entity_id，如 light.living_room_main",
      "params":         {"brightness_pct": 75, "color_temp_kelvin": 4000, "transition": 3},
      "reason":         "执行原因（中文，用于日志和用户通知）",
      "delay_seconds":  0,
      "is_global":      false
    }
  ],
  "reply":  "语音指令时的口语化回复，非语音场景填空字符串",
  "speak":  "TTS播报内容，不需要播报时填空字符串"
}

【scene_candidate 填写指引】
- User Prompt 的【可用场景】中若有名称含触发房间或意图关键词的场景 → 填入其 entity_id
- 填写 scene_candidate 后，actions 只需填空数组 []（系统会直接调用场景，无需重复列出设备）
- param_adjustments：如场景亮度偏高/偏低，可在此微调（系统在场景后 500ms 应用），不需要调整填 {}
- need_confirm：置信度 < 55 时设为 true，让用户先确认再执行

⚠️ 格式铁律：
1. 降低亮度必须用 light.turn_on + params:{brightness_pct:X}，严禁用 turn_off 来"调暗"灯光
2. domain 和 entity_id 必须精确匹配，不得捏造不存在的 entity_id
3. 无需任何操作时 actions 填 []，confidence 填实际判断的置信度
4. 不得在 JSON 外输出任何其他文字、注释、markdown 代码块
5. 调节灯光色温必须用 color_temp_kelvin（单位：K），禁止使用 color_temp（mireds 单位已废弃）
   - 暖白光: color_temp_kelvin=2700, 中性白: color_temp_kelvin=4000, 冷白光: color_temp_kelvin=6000
   - 可同时指定亮度和色温: {"brightness_pct": 80, "color_temp_kelvin": 4000, "transition": 3}
6. 灯光调节【必须】使用 transition 平滑过渡（单位：秒），避免瞬间跳变刺激眼睛：
   - 日常开关灯：transition=2~3（快速自然）
   - 氛围调整（色温/亮度微调）：transition=5~10（柔和过渡）
   - 睡前调暗 / 早晨唤醒：transition=30~60（缓慢渐变，不惊扰）
   - 示例：{"brightness_pct": 40, "color_temp_kelvin": 2700, "transition": 30}
7. is_global 字段：正常情况填 false；当动作为跨区联动（A区触发→B区设备）时必须填 true，
   否则系统安全层会拦截该跨区动作
"""

        # ── P0-P4 优先级体系（完整版） ────────────────────────────────────
        priority_framework = """
【🎯 决策优先级体系（必须遵守，高优先级约束不可被低优先级覆盖）】

P0【安全红线 - 代码级强制执行，AI不可违反】
  - 有人在场时，严禁关闭：烟雾报警、燃气探测器、门锁、摄像头、安防设备
  - 严禁执行任何可能危及生命安全的操作
  - 严禁操作不在 device_info 中的设备（防止幻觉）

P1【铁律 - AI 必须遵守，即使用户规则或场景提示与此矛盾】
  - 有人传感器检测到"有人"时，严禁关闭该区域灯光
  - 深夜(0-6时)有人活动，灯光调至 20% 以下（防止刺眼），不可主动开强光
  - 用户刚手动操作某设备，5分钟内禁止 AI 反向操作（尊重用户意志）；5-15分钟内建议保持；超过15分钟可根据场景判断
  - 【区域隔离 AI-03】触发传感器所在区域 ≠ 设备所在区域时，禁止跨区操作
    - 例外：全局命令（"关所有灯"）、温度类设备（空调可全局联动）

P2【学习画像 - 用户历史习惯数据，优先参考】
  - 行为模式数据库中有 ≥55% 置信度的历史数据时，遵循用户习惯
  - 用户修正记录（Override）：AI 被用户推翻过的决策，下次必须避免重犯
  - 近期手动操作的设备，20分钟内不要反向操作

P3【普通规则与画像 - 用户自定义偏好，AI 参考执行】
  - 用户在配置界面设置的规则（非锁定）和行为画像
  - 时段适用性：规则带有时间条件时，只在对应时段生效

P4【AI 推理 - 上述都没有约束时，AI 用智能判断】
  - 根据场景、时间、季节、历史模式做合理推断
  - 不确定时宁可不动（confidence < 60），提示用户而非贸然操作
"""

        # ── 区域隔离规则（完整说明） ──────────────────────────────────────
        isolation_rules = """
【🚫 区域隔离规则（AI-03）】
- 传感器触发事件中会包含触发区域，例如：[客厅] 存在传感器: off→on
- 原则：只操作触发区域内的设备。不得因为"顺便"而操作其他区域
- 例外情况（允许跨区操作）：
  ① 用户明确的语音/文字全局指令（"关所有灯"/"睡眠模式"）
  ② 空调/新风：温度联动可跨区（厨房温度高 → 客厅空调辅助）
  ③ 安防设备：门锁/摄像头是全局设备，不受区域限制
  ④ 场景脚本：HA 场景本身会定义多区域操作，执行时视为全局
  ⑤ 用户规则中明确描述跨区联动（如"展厅有人时开启客厅灯带"）
- 违反此规则的后果：造成用户惊吓（在别的房间莫名其妙开了灯）

【🔗 跨区联动动作标记（is_global 字段）】
- 当用户规则明确描述 A 区域状态触发 B 区域设备时，属于合法跨区联动
- 此类 action 必须在 JSON 中添加 "is_global": true 字段，系统才会放行
- 示例规则："展厅有人时开启客厅灯带，无人时关闭"
  正确 action 格式：
  {
    "domain": "light", "service": "turn_on",
    "entity_id": "light.ke_ting_bei_jing_1",
    "is_global": true,
    "reason": "展厅有人，根据联动规则开启客厅背景灯带"
  }
- 未添加 is_global 的跨区动作将被系统安全层拦截
"""

        # ── 展厅模式附加规则（v4.11.0：三区分治）──────────────────────────
        showroom_extra = ""
        if is_showroom:
            # 动态生成区域角色说明（从 coordinator 读取 zone map）
            _zone_role_hint = self._build_zone_role_hint()
            showroom_extra = f"""
【🏪 展厅模式附加规则（仅在展厅模式下生效）】

本展厅采用三区分治架构，每个区域有独立的控制策略，严格按区域角色执行：

{_zone_role_hint}

【展示区（Display Zone）灯光分层规则】
- 灯光分三层（User Prompt 中会标注哪些灯属于哪层）：
  ① 核心层(Core)：绝对不能关，即使无人也要亮着；有人时亮度不得低于 30%
  ② 展示层(Display)：无人时调暗至 10%（节能待机）；有人时恢复 90%；禁止彻底关闭
  ③ 辅助层(Auxiliary)：无人时可完全关闭；有人时按需开启
- 营业时间内有人：积极展示，turn_on 默认 90% 亮度
- 营业时间内无人：Core 维持最低 30%，Display 降至 10%，Auxiliary 可关
- 非营业时间有人（员工加班/顺路取物等）：仅开启必要照明，禁止主动开展示灯
- 非营业时间无人：完全节能，AI 可关闭所有灯光
- 操作员可通过一次性指令覆盖所有展厅规则（强制执行）

【体验区（Experience Zone）规则 — 与家庭模式相同】
- 有访客进入 → 积极开灯演示智能家居，亮度按房间类型推荐值
- ⚠️ 无人离开 → 必须关灯节能（等同家庭模式"无人关灯"）
- 禁止因"展厅营业时间"而在体验区无人时保持灯光开启
- 每次推理须核查该区域传感器状态：确认有人才开灯，确认无人即关灯

【工作区（Work Zone）规则 — 完全家庭模式】
- 完全独立于展厅营业时间，不受任何展厅规则约束
- 按普通家庭逻辑运行：有人开灯，无人关灯，服从用户习惯和修正记录
- 展厅营业/非营业状态对工作区无任何影响
"""

        # ── 行为准则 ─────────────────────────────────────────────────────
        behavior_rules = """
【⚖️ 行为准则】
1. 推理透明：reason 字段必须清晰说明为什么执行此动作
2. 安全第一：有疑问时选择不动作（confidence < 55 则 actions 填 []）
3. 节能意识：无人区域默认倾向关闭不必要设备
4. 尊重用户：用户刚操作过的设备视为"用户意图"，短期内不要反向
5. 防止幻觉：entity_id 必须来自 System Prompt 中的【合法设备清单】，不得自行捏造或拼接
6. 不重复执行：若设备已经处于目标状态（灯已开且亮度匹配），跳过该动作
7. 置信度诚实：使用场景清晰则填 80-95，有歧义则填 50-70，完全不确定填 <50

【🔒 设备管辖模式（重要，请严格遵守）】
User Prompt 的设备列表中，部分设备标注了管辖模式标签：
- [HA优先⚠️]：该设备由 Home Assistant 自动化管控，**AI 不得输出控制该设备的动作**
  * 即使用户指令涉及该设备，也应使用其他可控设备实现等效效果，或在 reason 中说明
  * 可以在场景（scene/script）层面间接影响它（场景自带的 entity 由 HA 统一执行）
- [AI全权]：该设备由 AI 完全管控，可以直接控制
- 无标签（默认）：共享模式，AI 可直接控制，系统会自动尝试路由到关联场景/脚本

【🎬 HA 场景/脚本优先调用原则（重要）】
当 User Prompt 中【可用脚本】或【可用场景】列表里存在与当前情境匹配的场景时：
1. 优先调用该场景/脚本（domain=scene 或 script, service=turn_on）而非逐个控制设备
2. 一个场景动作等于多设备协同（灯光+窗帘+空调），比逐个控制更精准、更符合用户预期
3. 场景匹配优先级（从高到低）：
   ① 名称含触发房间名的场景（如 scene.cha_shi_hui_ke → 适用"茶室"触发）
   ② 名称含当前时段关键词的场景（如 scene.ye_jian_xiu_xi → 适用深夜触发）
   ③ 名称含动作意图关键词的场景（如 script.kai_hui_mo_shi → 适用"会议"指令）
4. 若无适合场景/脚本 → 再逐个控制设备
⚠️ 调用场景时仍须遵守 P0/P1 安全规则；置信度按场景匹配程度填写（高匹配 85+，模糊匹配 70+）
"""

        # ── 家庭模式设备联动指南（仅非展厅模式注入，避免增加展厅 System Prompt token）──
        home_device_guide = ""
        if not is_showroom:
            home_device_guide = """
【🏠 家庭模式设备联动指南（家庭专用，展厅模式不适用）】

▶ 窗帘（cover 实体）
  服务：open_cover（全开）/ close_cover（全关）/ set_cover_position（设位置，position=0-100）
  联动时机：
  - 早晨（6-9时）有人：先 set_cover_position=30（缓和唤醒），3分钟后可全开
  - 强光下午（12-16时，西向房间）：set_cover_position=50 遮阳
  - 傍晚日落后：close_cover，保护隐私
  - 影院模式（media_player 进入 playing 状态）：close_cover + 灯光调至20%暖光
  - 离家/长时间无人：close_cover（隐私+节能）
  ⚠️ 不得在用户睡眠中打开窗帘（卧室有人且深夜0-6时）

▶ 空调（climate 实体）
  ⚠️ 控制空调必须发送两个独立 action（两种服务不可合并）：
    action 1: {"domain":"climate","service":"set_hvac_mode","entity_id":"...","params":{"hvac_mode":"cool"}}
    action 2: {"domain":"climate","service":"set_temperature","entity_id":"...","params":{"temperature":26}}
  hvac_mode 取值：cool（制冷）/ heat（制热）/ fan_only（送风）/ dry（除湿）/ off（关机）
  建议温度：夏季制冷 26°C；冬季制热 22°C；睡眠模式夏季 27°C/冬季 20°C
  设备状态中会显示当前 hvac_mode，若已处于目标模式则只发 set_temperature 一个动作
  - 有人且温度不舒适时开启（夏>28°C 或 冬<18°C 为触发阈值，User Prompt 中有当前温度）
  - 无人超过 30 分钟：调至节能模式（28°C/25°C）或 fan_only
  - 厨房温度高时可联动客厅/餐厅空调辅助（此为跨区联动，需加 is_global=true）

▶ 地暖（floor_heat，通常为 switch 或 climate 实体）
  - 冬季早晨（6-8时）或傍晚（17-20时）有人：turn_on，可使用 delay_seconds=0
  - 地暖升温慢（约30分钟），建议在有人前 15 分钟提前开启（通过 delay_seconds=-900 或巡检时预判）
  - 深夜0-5时 / 离家状态：turn_off 节能
  - 注意：地暖与空调制热不要同时大功率运行（能耗过高）

▶ 电视/媒体播放器（media_player 实体）
  服务：media_player.turn_on / turn_off / media_play / media_pause / volume_set
  ⚠️ 不主动开关电视，电视由用户控制；AI 负责联动环境：
  - 电视/媒体进入 playing 状态 → 联动：灯光调至影院模式（20%亮度+2700K）+ 关窗帘
  - 电视暂停/停止 → 灯光恢复（60-80%亮度+4000K）
  - 不得在用户观影时主动增亮或开强光

▶ 人数情境感知（Frigate 摄像头 / HA person 实体）
  User Prompt 中会提供：【视觉感知】各房间人数 + 【家庭成员状态】谁在家
  利用人数做情境判断：
  - 1人（仅主人）→ 个人偏好模式：安静、低亮度、暖色调，参考用户习惯基线
  - 2人以上（有访客）→ 社交/会客模式：亮度+10-20%，色温中性（4000K），可开背景音乐脚本
  - 例：茶室仅主人 → 60%+3000K；茶室有访客 → 70%+3500K
  - 例：客厅全家 → 优先调用 scene.ke_ting_ju_jia（如存在），否则 80%+4000K
  - 家庭成员全部不在家（HA person 全部 not_home）→ 视为离家，可执行节能/安防联动
"""

        # ── 房间场景照明情景参考（静态提示，帮助 AI 做出符合场景的色温亮度决策）──
        lighting_context_hint = """
【💡 房间场景照明参考（建议，AI 可结合实际情况调整）】
| 场景       | 建议亮度 | 建议色温  | 建议过渡 | 说明                     |
|------------|----------|-----------|----------|--------------------------|
| 茶室/茶区  | 60%      | 3000K 暖白 | 3s      | 温馨放松，促进交流        |
| 餐厅       | 70%      | 3000K 暖白 | 3s      | 促进食欲，温馨就餐        |
| 卧室       | 40%      | 2700K 极暖 | 8s      | 助眠，避免刺激            |
| 书房/学习  | 100%     | 6000K 冷白 | 2s      | 提升专注力                |
| 办公       | 100%     | 5500K 中冷 | 2s      | 高效工作                  |
| 客厅（日常）| 80%     | 4000K 中性 | 3s      | 日常活动舒适              |
| 客厅（影院）| 20%     | 2700K 极暖 | 10s     | 营造观影氛围              |
| 厨房       | 100%     | 5000K 中冷 | 2s      | 操作安全明亮              |
| 卫浴       | 80%      | 4500K 中性 | 2s      | 梳妆/清洁适用             |
| 玄关       | 80%      | 4000K 中性 | 2s      | 欢迎归家                  |
| 走廊       | 70%      | 4000K 中性 | 2s      | 通道导引                  |

⚙️ 调光格式：{"brightness_pct": 60, "color_temp_kelvin": 3000, "transition": 3}
⚙️ 色温范围：2700K(极暖橙)~3000K(暖白)~4000K(中性白)~5000K(冷白)~6500K(冷光)
⚙️ 过渡时长：transition 单位为秒，值越大灯光变化越柔和

【🌅 昼夜节律提示】
系统已集成昼夜节律引擎，快脑路径会自动使用节律曲线的亮度和色温。
当你（慢脑）做决策时，请参考以下原则：
- 早晨（日出前后）：偏暖低亮度，渐进提亮，避免强光惊醒（transition=10~30）
- 白天：根据房间功能取最大亮度和中偏冷色温（transition=2~3）
- 傍晚-晚间：逐步降低亮度和色温，向暖白过渡（transition=5~10）
- 睡前：极暖低亮度，用 transition=30~60 缓慢过渡，暗示该休息了
- 深夜：若有人活动，仅用极低亮度（<20%）极暖光（2200K），transition=10 不打扰睡眠
- 有客人时：比独处时亮度+10~20%，色温偏中性（4000K）
- 看电影时：20% + 2700K，transition=10
"""

        # ── 设备名称对照表（静态部分，防止 AI 捏造 entity_id）────────────────
        # Phase 9.2: 将已注册设备列表移入 System Prompt，User Prompt 只含实时状态值
        # 注意：device_info 变动（新增/删除设备）时 System Prompt 会改变，KV Cache 自动失效后重建
        device_table = self._build_device_name_table()

        # Phase 9.4 (Reflexion) 注意：反面教材为动态内容（每周更新），
        # 已移至 User Prompt 注入，此处 System Prompt 保持纯静态以保证 KV Cache 稳定。
        full_prompt = (
            identity
            + safety_first          # P0/P1 安全红线前置（优先于格式指令）
            + output_schema
            + priority_framework
            + isolation_rules
            + showroom_extra
            + home_device_guide
            + behavior_rules
            + lighting_context_hint
            + device_table
        )
        # L1: 分别统计中文字符（÷1.5）和非中文字符（÷4），精度优于统一 ÷3
        _cn_chars = sum(1 for c in full_prompt if "\u4e00" <= c <= "\u9fff")
        _en_chars = len(full_prompt) - _cn_chars
        _estimated_tokens = int(_cn_chars / 1.5 + _en_chars / 4)
        if _estimated_tokens < 1024:
            _LOGGER.debug(
                "[PrefixCache] ⚠️ System Prompt 约 %d token，建议 >1024 以激活 KV Cache",
                _estimated_tokens,
            )
        else:
            _LOGGER.debug("[PrefixCache] ✅ System Prompt 约 %d token，KV Cache 可生效", _estimated_tokens)
        return full_prompt

    def _build_device_name_table(self) -> str:
        """
        构建设备名称对照表，纳入 System Prompt 静态部分（Phase 9.2 Prefix Caching）。

        目的：
          1. 让 AI 知道所有合法 entity_id 及其中文名，防止幻觉捏造
          2. 将此静态信息移出 User Prompt，缩短每次动态上下文的长度
          3. 配合 KV Cache，第一次发送后 System Prompt 常驻 GPU 显存，后续请求复用

        Returns:
            格式化的设备名对照字符串，或空字符串（无设备时）
        """
        if not self.device_info:
            return ""

        # 保护上限：设备数超过 150 时优先保留可控域，防止 System Prompt 超 token 限制
        # 大型商业场景（200+ 设备）全量输出可能超 4096 token 导致 API 400 错误
        CONTROLLABLE_DOMAINS = (
            "light", "switch", "climate", "cover",
            "fan", "media_player", "vacuum", "script", "scene",
        )
        MAX_DEVICES = 150
        all_items = sorted(self.device_info.items())
        if len(all_items) > MAX_DEVICES:
            controllable = [(e, i) for e, i in all_items if e.split(".")[0] in CONTROLLABLE_DOMAINS]
            others = [(e, i) for e, i in all_items if e.split(".")[0] not in CONTROLLABLE_DOMAINS]
            all_items = (controllable + others)[:MAX_DEVICES]
            _LOGGER.warning(
                "[PrefixCache] 设备数 %d 超过上限 %d，System Prompt 仅保留前 %d 个（可控域优先）",
                len(self.device_info), MAX_DEVICES, MAX_DEVICES,
            )

        lines = ["\n【📋 合法设备清单（entity_id ↔ 中文名，仅可操作此列表中的设备）】"]
        by_room: dict[str, list[str]] = {}
        for eid, info in all_items:
            room = info.get("room", "未分配区域") or "未分配区域"
            name = info.get("name", eid)
            by_room.setdefault(room, []).append(f"  {eid} → {name}")
        for room, entries in sorted(by_room.items()):
            lines.append(f"【{room}】")
            lines.extend(entries)
        lines.append("（操作时必须使用完整 entity_id，如 light.living_room_main，不得自行拼接或缩写）")
        return "\n".join(lines) + "\n"

    async def _build_showroom_tiered_prompt(self) -> str:
        """构建展厅分层保护 Prompt。"""
        tiered_lines = {"core": [], "display": [], "auxiliary": []}
        _showroom_area = self.showroom_area_name
        for eid, info in self.device_info.items():
            if not eid.startswith("light."):
                continue
            _room = info.get("room", "")
            # 完全基于 device_info 中来自 HA Area Registry 的 room 字段，不依赖实体 ID 拼音
            if _showroom_area and _room == _showroom_area and _room not in self.showroom_excluded_subareas:
                # v2：优先使用基线分数判断层级，与 actions.py 保持一致
                tier = await self.hass.async_add_executor_job(self._get_showroom_light_tier_v2, eid)
                tiered_lines[tier].append(f"{info.get('name', eid)}({eid})")
        
        from .const import SHOWROOM_DISPLAY_DIM_PCT, SHOWROOM_OCCUPIED_PCT, SHOWROOM_CORE_MIN_PCT
        res = "\n【智能 P1：展厅灯光分层保护（基线学习驱动）】\n"
        if tiered_lines["core"]:
            res += (f"  🟢 核心层 (Core) — 营业时间严禁关闭，有人亮度≥{SHOWROOM_CORE_MIN_PCT}%: "
                    f"{', '.join(tiered_lines['core'])}\n")
        if tiered_lines["display"]:
            res += (f"  🟡 展示层 (Display) — 无人→{SHOWROOM_DISPLAY_DIM_PCT}%节能待机，有人→{SHOWROOM_OCCUPIED_PCT}%: "
                    f"{', '.join(tiered_lines['display'])}\n")
        if tiered_lines["auxiliary"]:
            res += (f"  🔴 辅助层 (Auxiliary) — 无人可完全关闭，有人按需开启: "
                    f"{', '.join(tiered_lines['auxiliary'])}\n")
        if not any(tiered_lines.values()):
            res += "  （基线数据收集中，所有灯暂按 Core 层保护）\n"
        return res

    def _extract_json(self, text: str) -> dict | None:
        """从文本中提取第一个完整的 JSON 对象。

        处理两种常见格式：
          1. Markdown 代码围栏（```json\\n{...}\\n```）——部分云端模型默认带围栏
          2. 裸 JSON（直接 {…}）—— Ollama structured output 和标准 OpenAI
        """
        if not text:
            return None
        # 先尝试剥离 Markdown 围栏（```json ... ``` 或 ``` ... ```）
        _fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if _fence:
            try:
                return json.loads(_fence.group(1))
            except json.JSONDecodeError:
                pass
        # 按括号范围兜底：找第一个 { 和最后一个 }
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start: end + 1])
            except json.JSONDecodeError:
                pass
        return None

    async def _notify_rejected_actions(self, rejected: list[dict], trigger: str) -> None:
        """
        当用户主动指令被 IntentVerifier 拒绝时，通过 HA 持久通知告知用户原因。

        只在有被拒绝的动作时才发送，避免打扰用户（传感器自动触发被拒不通知）。

        Args:
            rejected: 被拒绝的动作列表（含 reject_reason 字段）
            trigger:  触发描述（用于通知标题）
        """
        if not rejected:
            return
        try:
            # 最多展示 3 条原因，避免通知过长
            reason_lines: list[str] = []
            for act in rejected[:3]:
                reason = act.get("reject_reason", "原因未知")
                eid = act.get("entity_id", "")
                dev_name = (self.device_info.get(eid) or {}).get("name", eid)
                reason_lines.append(f"• {dev_name}：{reason}")

            suffix = f"（共 {len(rejected)} 条被拦截）" if len(rejected) > 3 else ""
            body = (
                f"以下操作被安全规则拦截{suffix}：\n\n"
                + "\n".join(reason_lines)
                + "\n\n**提示：** 若需强制执行，可在规则页面添加跨区豁免说明，"
                "或直接在 HA 面板手动操作设备。"
            )
            # 兼容不同 HA 版本的持久通知 API
            try:
                from homeassistant.components.persistent_notification import (
                    async_create as _pn_create,
                )
                _pn_create(
                    self.hass,
                    message=body,
                    title="SmartAgent 操作提示",
                    notification_id="smart_agent_action_rejected",
                )
            except Exception:
                await self.hass.services.async_call(
                    "persistent_notification", "create",
                    {"message": body, "title": "SmartAgent 操作提示",
                     "notification_id": "smart_agent_action_rejected"},
                    blocking=False,
                )
            self._sys_log("INFO", f"[拒绝通知] 已推送用户通知（{len(rejected)} 条被拒）")
        except Exception as exc:
            _LOGGER.warning("[notify_rejected] 推送通知失败: %s", exc)

    # ── 推理主流程 ────────────────────────────────────────────────────────────

    @staticmethod
    def _detect_cmd_source(trigger: str, one_off_prompt: str = "") -> str:
        """
        根据触发描述判断指令来源优先级。

        Returns:
            CMD_SOURCE_USER_EXPLICIT: 用户面板/语音/展厅一次性指令
            CMD_SOURCE_SCHEDULE     : 巡检/定时触发
            CMD_SOURCE_SENSOR       : 传感器自动触发（默认）
        """
        from .intent_verifier import (
            CMD_SOURCE_USER_EXPLICIT,
            CMD_SOURCE_SCHEDULE,
            CMD_SOURCE_SENSOR,
        )
        # 展厅一次性指令 / 语音指令 → 用户主动
        if one_off_prompt or "[展厅] 自定义场景:" in trigger:
            return CMD_SOURCE_USER_EXPLICIT
        # 用户界面直接操作（来源标记为"用户"）
        if "[用户]" in trigger:
            return CMD_SOURCE_USER_EXPLICIT
        # 巡检/定时任务
        if "[巡检]" in trigger or "[定时]" in trigger:
            return CMD_SOURCE_SCHEDULE
        return CMD_SOURCE_SENSOR

    async def _run_inference(self, trigger: str, one_off_prompt: str = "") -> None:
        """Full inference pipeline: fast-path check → AI call → action execution.

        并发策略（Per-room Lock）：
          - 从 trigger 文本提取触发房间名，获取该房间专属的 asyncio.Lock
          - 不同房间的 LLM 推理可真正并发（asyncio I/O 等待时交出事件循环控制权）
          - 同一房间内仍串行，防止重复触发产生动作冲突
          - 无法提取房间名时降级使用全局 _inference_lock（巡检/定时/位置变化等场景）
        """
        # 从 trigger 文本提取房间名（统一复用 context_builder 提取逻辑）
        _trigger_room = _extract_trigger_room(trigger)

        # 选择锁：有房间用 per-room 锁，否则用全局锁兜底
        lock = (
            self._get_room_lock(_trigger_room)
            if _trigger_room
            else self._inference_lock
        )

        if lock.locked():
            _LOGGER.debug(
                "[Inference] %s 推理进行中，跳过重复触发: %s",
                _trigger_room or "全局",
                trigger[:60],
            )
            return
        async with lock:
            await self._run_inference_inner(trigger, one_off_prompt)

    async def _run_inference_inner(self, trigger: str, one_off_prompt: str = "") -> None:
        """实际推理执行体，由 _run_inference 在锁内调用。"""
        from .const import MODE_SHOWROOM, TTS_LEVEL_ACTIONS
        import re as _re_trig
        _trigger_room_log = _extract_trigger_room(trigger)
        _is_global_log = bool(
            ("所有" in trigger or "全部" in trigger)
            or (one_off_prompt and ("所有" in one_off_prompt or "全部" in one_off_prompt))
        )
        _LOGGER.info(
            "[Trigger] room=%s source=%s global=%s",
            _trigger_room_log or "unknown",
            self._detect_cmd_source(trigger, one_off_prompt),
            _is_global_log,
        )
        await self._async_update_status("推理中", "⏳ 触发处理中")

        trigger_room = _trigger_room_log

        _is_global = bool(("所有" in trigger or "全部" in trigger) or (one_off_prompt and ("所有" in one_off_prompt or "全部" in one_off_prompt)))

        # 检测指令来源（用于 IntentVerifier 豁免逻辑）
        _cmd_source = self._detect_cmd_source(trigger, one_off_prompt)

        if "[展厅] 自定义场景:" in trigger or one_off_prompt:
            self._last_showroom_cmd_time = _time.time()

        # H2: 特征快照在 LLM 调用前采集，确保反映触发时刻的环境状态
        # M3: 修正正则末尾多余的 ]?（原 r"[（(](\w+\.\w+)[）)]]?" 末尾多一个 ]）
        _trigger_entity = ""
        _m_eid = _re_trig.search(r"[（(](\w+\.\w+)[）)]", trigger)
        if _m_eid:
            _trigger_entity = _m_eid.group(1)
        _feat_snap: dict | None = None
        try:
            from .feature_encoder import FeatureEncoder as _FE
            # 从 HA 状态机获取触发实体当前状态（比 LLM 调用后更接近触发时刻）
            _trig_state_obj = self.hass.states.get(_trigger_entity) if _trigger_entity else None
            _trig_new_state = _trig_state_obj.state if _trig_state_obj else ""
            _feat_snap = _FE(self.hass, self.device_info).encode(
                _trigger_entity, _trig_new_state, ""
            )
        except Exception:
            _feat_snap = None

        try:
            # ── Add-on 委托推理（v4.10.10：LLM 核心剥离 + 内部认证）──────────
            # 若 smartagent-addon 容器在线，则将完整 InferenceBundle 发给 Add-on，
            # 由受 Cython 保护的 inference_engine 执行 Prompt 构建 + LLM 调用。
            # Add-on 不可用（未启动/超时/503/401）时自动降级到本地推理（_call_ai_engine）。
            # _bundle 在两条路径间共享：Add-on 路径构建后若失败，降级路径直接复用，
            # 避免 ContextBuilder（含 DB 查询 + MemoryStore）被重复执行。
            decision: dict | None = None
            context: str = ""          # 供 _record_training_sample 使用
            _bundle: dict | None = None
            _addon_client = getattr(self, "_addon_client", None)
            if _addon_client is not None:
                try:
                    if await _addon_client.is_available():
                        from .context_builder import ContextBuilder
                        _bundle = await ContextBuilder(self).build(
                            trigger, one_off_prompt, is_voice=False
                        )
                        # 保留 context_text 供训练数据记录
                        context = _bundle.get("context_text", "")
                        decision = await _addon_client.infer(_bundle)
                        if decision:
                            self._sys_log("INFO", "[推理] Add-on 推理成功，使用受保护引擎")
                        else:
                            self._sys_log("INFO", "[推理] Add-on 返回空（503/超时/认证失败），降级到本地推理")
                    else:
                        self._sys_log("INFO", "[推理] Add-on 未在线，使用本地推理")
                except Exception as _addon_exc:
                    _LOGGER.info("[推理] Add-on 路径异常，降级到本地推理: %s", _addon_exc)
                    decision = None

            # ── 本地推理（Add-on 不可用时的降级路径）──────────────────────
            # 优先复用已构建的 _bundle（Add-on 超时时 bundle 已有，无需重建）；
            # 若 Add-on 根本未部署，重新通过 ContextBuilder 构建以保持数据采集逻辑一致性：
            # 两条路径均经过 ContextBuilder（SYS-02 死区、Phase 8E 折叠、MemoryStore 等）。
            if decision is None:
                if _bundle is None:
                    from .context_builder import ContextBuilder
                    _bundle = await ContextBuilder(self).build(
                        trigger, one_off_prompt, is_voice=False
                    )
                context = _bundle.get("context_text", "")
                decision = await self._call_ai_engine(
                    context, trigger, one_off_prompt=one_off_prompt, bundle=_bundle
                )

            if not decision:
                await self._async_update_status("运行中", "AI 引擎无响应")
                return

            confidence = decision.get("confidence", 0)
            actions = [a for a in decision.get("actions", []) if isinstance(a, dict)]
            scene = decision.get("scene", "未知场景")
            speak = decision.get("speak", "")
            reply = decision.get("reply", "")

            # ── 5B-2: 意图层新字段处理 ──────────────────────────────────────
            _intent       = (decision.get("intent") or "").strip()
            _intent_label = (decision.get("intent_label") or "").strip()
            _scene_cand   = (decision.get("scene_candidate") or "").strip()
            _param_adj    = decision.get("param_adjustments") or {}
            _need_confirm = bool(decision.get("need_confirm", False))

            # scene_candidate 路由：若 AI 推荐了场景且该场景存在于 HA，优先调用
            if _scene_cand and self.hass.states.get(_scene_cand) is not None:
                _sc_action = {
                    "domain": "scene",
                    "service": "turn_on",
                    "entity_id": _scene_cand,
                    "params": {},
                    "reason": f"AI场景: {_intent_label or _intent or _scene_cand}",
                    "delay_seconds": 0,
                }
                # 参数微调：500ms 后对触发房间灯光应用 param_adjustments
                _adj_actions: list[dict] = []
                if _param_adj and trigger_room:
                    _room_light_ids = [
                        eid for eid, info in self.device_info.items()
                        if info.get("room") == trigger_room and eid.startswith("light.")
                    ]
                    # 若 LLM 未指定 transition，补默认 2s 平滑过渡，避免亮度跳变
                    _adj_params = dict(_param_adj)
                    if "transition" not in _adj_params:
                        _adj_params["transition"] = 2
                    for _leid in _room_light_ids[:6]:
                        _adj_actions.append({
                            "domain": "light",
                            "service": "turn_on",
                            "entity_id": _leid,
                            "params": _adj_params,
                            "reason": f"场景后微调: {_intent_label or _intent}",
                            "delay_seconds": 0.5,
                        })
                actions = [_sc_action] + _adj_actions
                self._sys_log(
                    "INFO",
                    f"[5B-2] intent={_intent} → scene_candidate={_scene_cand}"
                    + (f"，微调 {len(_adj_actions)} 盏灯" if _adj_actions else ""),
                )
            elif _scene_cand:
                self._sys_log(
                    "INFO",
                    f"[5B-2] scene_candidate={_scene_cand} 在 HA 中不存在，使用 fallback actions",
                )

            # need_confirm：置信度偏低，推送确认事件让用户决策后再执行
            if _need_confirm and actions:
                self.hass.bus.async_fire(
                    "smart_agent_confirm_required",
                    {
                        "scene": scene,
                        "intent": _intent,
                        "intent_label": _intent_label,
                        "confidence": confidence,
                        "action_count": len(actions),
                        "actions": [a.get("reason", a.get("entity_id", "?")) for a in actions[:6]],
                        "trigger": trigger[:120],
                        "reply": "",
                        "txn_id": None,
                    },
                )
                self._sys_log(
                    "INFO",
                    f"[5B-2 Confirm] need_confirm=true，等待用户确认: "
                    f"{scene}（置信度 {confidence}，{len(actions)} 个动作）",
                )
                await self._async_update_status(scene, f"⏸ 等待用户确认（{confidence}%）")
                return

            # 记录推理事件（供历史上下文、修正学习使用）
            self.hass.async_add_executor_job(
                self._record_event, "AI_Inference",
                f"[置信度:{confidence}] {scene[:80]}",
                "", "", "ai",
            )

            # Phase 9.9: 模型训练自标注数据收集（特征快照已在 LLM 调用前采集）
            self.hass.async_add_executor_job(
                self._record_training_sample, trigger, context, decision, _feat_snap
            )

            # 计入每日推理次数（License 限额管理）
            self.increment_daily_count()

            # 存储上次推理结果（用于重复推理抑制）
            self._last_inference_result = decision

            if not actions:
                # AI 主动返回空动作 - 记录 AI 给出的说明（reply / scene）
                _ai_reason = (reply or speak or "").strip()
                if _ai_reason:
                    self._sys_log("INFO", f"[推理] AI 无动作说明(置信度={confidence}): {_ai_reason[:120]}")
                else:
                    self._sys_log("INFO", f"[推理] AI 判断无需动作 置信度={confidence}，未给出说明")
                await self._async_update_status(scene, "无需动作")
                return

            # Phase 9.5 (P2.2): 双阶段意图验证管道（含 cmd_source 豁免逻辑）
            try:
                from .intent_verifier import IntentVerifier, CMD_SOURCE_USER_EXPLICIT
                _occ_map = self._get_room_occupancy_map() if hasattr(self, "_get_room_occupancy_map") else {}
                # M2 修正：注入 sys_log_func，使慢脑路径的拒绝记录也显示在面板
                _verifier = IntentVerifier(
                    self.hass, self.device_info, _occ_map,
                    sys_log_func=getattr(self, "_sys_log", None),
                    suppress_check_func=getattr(self, "_should_suppress_action", None),
                )
                _verifier._locked_people_rules = (
                    self._build_locked_people_rules()
                    if hasattr(self, "_build_locked_people_rules")
                    else []
                )
                actions, _rejected = _verifier.verify(
                    actions,
                    trigger_room,
                    is_global_cmd=_is_global,
                    cmd_source=_cmd_source,
                )
                if _rejected:
                    # 直接在此处记录详细拒绝原因，避免依赖 IntentVerifier 内部 sys_log 注入
                    _rej_detail = ", ".join(
                        "{eid}({reason})".format(
                            eid=a.get("entity_id", "?"),
                            reason=a.get("reject_reason", ""),
                        )
                        for a in _rejected
                    )
                    self._sys_log(
                        "INFO",
                        f"[意图验证] 拒绝 {len(_rejected)} 个不合规动作: [{_rej_detail}]",
                    )
                    # 用户主动指令被拒时，推送 HA 通知告知原因（非静默失败）
                    if _cmd_source == CMD_SOURCE_USER_EXPLICIT:
                        await self._notify_rejected_actions(_rejected, trigger)
            except Exception as _ve:
                # fail-closed 原则：验证器自身异常时拒绝所有动作，不放行
                _LOGGER.error("[IntentVerifier] 验证异常（fail-closed）: %s", _ve)
                self._sys_log("ERROR", f"[意图验证] 验证器异常，已拒绝全部动作: {_ve}")
                _rejected = [dict(a, reject_reason=f"验证器异常: {_ve}") for a in actions]
                actions = []

            if not actions:
                # 将首条拒绝原因写入状态栏，方便用户无需查日志即可看到原因
                if _rejected:
                    _first_reason = _rejected[0].get("reject_reason", "")
                    _first_eid = _rejected[0].get("entity_id", "")
                    _dev_name = (self.device_info.get(_first_eid) or {}).get("name", _first_eid)
                    _status_hint = f"({_dev_name}: {_first_reason})" if _first_reason else ""
                    await self._async_update_status(scene, f"意图验证后无有效动作 {_status_hint}".strip())
                else:
                    await self._async_update_status(scene, "意图验证后无有效动作")
                return

            # Phase 1 (DecisionCache): 触发类型预判（仅 arrival 类型写缓存）
            # 注意：实际写缓存在 confidence >= auto_th 且成功执行后进行，
            # 避免将"仅通知、未执行"的决策写入缓存（防止绕过渐进式自治机制）
            _cache_trigger_type = _detect_cache_trigger_type(trigger)

            auto_th = self._SHOWROOM_CONFIDENCE_AUTO if self._mode == MODE_SHOWROOM else self.confidence_auto
            notify_th = self._SHOWROOM_CONFIDENCE_NOTIFY if self._mode == MODE_SHOWROOM else self.confidence_notify

            # ── 全局关灯兜底：补全 AI 漏掉的 light 实体 ────────────────────────
            # 当 _is_global=True 且 AI 生成了 turn_off 动作时，
            # 检查 device_info 中所有 light 域设备，将 AI 遗漏的自动补入，
            # 防止 AI 因"刚操作过"等内部推理跳过某些设备。
            _has_global_off = _is_global and any(
                a.get("domain") == "light" and a.get("service") == "turn_off"
                for a in actions if isinstance(a, dict)
            )
            if _has_global_off:
                _covered = {a.get("entity_id") for a in actions if isinstance(a, dict)}
                # 如果指令包含"除展厅外"，则展厅灯不补入（AI 应当已排除展厅）
                _exclude_showroom = any(kw in trigger for kw in ("除展厅", "展厅外", "非展厅"))
                _supplemented = []
                for eid, info in self.device_info.items():
                    if not eid.startswith("light."):
                        continue
                    if eid in _covered:
                        continue
                    # 跳过当前已关闭的设备（避免无效调用）
                    _state = self.hass.states.get(eid)
                    if _state and _state.state == "off":
                        continue
                    # 排除展厅灯（若"除展厅外"指令）
                    if _exclude_showroom:
                        _dev_room = (info or {}).get("room", "")
                        if _dev_room and ("展厅" in _dev_room or "showroom" in _dev_room.lower()):
                            continue
                    _supplemented.append({
                        "domain": "light",
                        "service": "turn_off",
                        "entity_id": eid,
                        "params": {},
                        "reason": "全局关灯补全（AI未枚举）",
                        "delay_seconds": 0,
                    })
                if _supplemented:
                    self._sys_log("INFO",
                        f"[全局关灯补全] AI 漏掉 {len(_supplemented)} 盏灯，已自动补入: "
                        f"{[a['entity_id'] for a in _supplemented[:5]]}"
                        f"{'...' if len(_supplemented) > 5 else ''}"
                    )
                    actions = actions + _supplemented
                    # 补全动作必须再走一次统一验证链，避免绕过 IntentVerifier
                    try:
                        actions, _supp_rejected = _verifier.verify(
                            actions,
                            trigger_room,
                            is_global_cmd=_is_global,
                            cmd_source=_cmd_source,
                        )
                        if _supp_rejected:
                            _supp_detail = ", ".join(
                                "{eid}({reason})".format(
                                    eid=a.get("entity_id", "?"),
                                    reason=a.get("reject_reason", ""),
                                )
                                for a in _supp_rejected
                            )
                            self._sys_log(
                                "INFO",
                                f"[全局关灯补全-二次验证] 拒绝 {len(_supp_rejected)} 个动作: [{_supp_detail}]",
                            )
                    except Exception as _supp_ve:
                        _LOGGER.error("[IntentVerifier] 全局补全二次验证异常（fail-closed）: %s", _supp_ve)
                        self._sys_log("ERROR", f"[全局关灯补全-二次验证] 验证异常，已拒绝全部动作: {_supp_ve}")
                        actions = []

            # 动作上限放宽 (P0)
            _MAX_ACTIONS = (len(self.device_info) + 20) if _is_global else 50
            if len(actions) > _MAX_ACTIONS:
                self._sys_log("WARN", f"[截断] 动作数 {len(actions)} > {_MAX_ACTIONS}")
                actions = actions[:_MAX_ACTIONS]

            if confidence >= auto_th:
                # ── 模式 1: 完全自治 (Confidence >= auto_th) ──
                # 信任 AI 决策，直接执行所有动作
                _patrol_cmd_time = _time.time()  # ReAct-Lite: 记录命令下发时刻
                executed = await self._execute_actions(
                    actions, trigger_summary=trigger, scene_desc=scene,
                    confidence=confidence, trigger_room=trigger_room, is_global_cmd=_is_global,
                    cmd_source=_cmd_source,
                )
                # ReAct-Lite (9.10): 确认执行后才保存待验证动作（只记录 turn_on/turn_off）
                # 置于 executed > 0 判断后，防止低置信度未执行时误存数据产生虚假验证
                if executed > 0 and "[巡检]" in trigger:
                    self._last_executed_actions_for_verify = [
                        a for a in actions
                        if "turn_on" in a.get("service", "") or "turn_off" in a.get("service", "")
                    ]
                    self._patrol_cmd_time = _patrol_cmd_time
                if executed > 0:
                    # Phase 1 (DecisionCache): 仅在成功自动执行后写缓存
                    # 确保缓存存储的是「真正被执行了」的决策，防止绕过渐进式自治机制
                    # Phase 1+（v4.10.4）: 扩展至 departure，arrival + departure 均缓存
                    if (
                        _cache_trigger_type in ("arrival", "departure")
                        and trigger_room
                        and hasattr(self, "_write_decision_cache")
                    ):
                        from datetime import datetime as _dt_cache
                        _now_cache = _dt_cache.now()
                        self.hass.async_add_executor_job(
                            self._write_decision_cache,
                            trigger_room,
                            _now_cache.hour,
                            _now_cache.weekday(),
                            _cache_trigger_type,
                            actions,
                            confidence,
                            scene,
                            _intent,         # 5B-3: 意图标识
                            _scene_cand,     # 5B-3: 场景候选
                        )
                    if speak:
                        await self._speak_tts(speak)
                    # TTS 动作摘要（level=2 时播报）
                    action_summary = "、".join(
                        self.get_device_name(a.get("entity_id", "")) for a in actions[:3] if a.get("entity_id")
                    )
                    if action_summary:
                        await self._tts_speak(f"已执行：{action_summary}", min_level=TTS_LEVEL_ACTIONS)
                await self._async_update_status(scene, f"已执行 {executed} 个动作")

            elif confidence >= notify_th:
                # ── 模式 2: 渐进式自治 (Confidence 60-90) ──
                # 核心哲学：先做安全的，存疑的询问用户
                safe, high, critical = _verifier.split_actions_by_safety(actions)
                
                # 1. 执行安全可逆项（灯光、窗帘等）
                executed_safe = 0
                if safe:
                    executed_safe = await self._execute_actions(
                        safe, trigger_summary=trigger, scene_desc=scene,
                        confidence=confidence, trigger_room=trigger_room, is_global_cmd=_is_global,
                        cmd_source=_cmd_source,
                    )
                
                # 2. 对高成本项（空调、安防）进行通报/询问
                pending_actions = high + critical
                pending_names = [self.get_device_name(a.get("entity_id", "")) for a in pending_actions]
                
                if pending_names:
                    # 构造询问文本
                    _safe_count = len(safe) if executed_safe > 0 else 0
                    prefix = f"已为您处理了{_safe_count}项基础操作。" if _safe_count > 0 else ""
                    ask_msg = f"{prefix}AI 建议执行{'、'.join(pending_names[:2])}，由于置信度不足，已为您暂缓。您需要执行吗？"
                    
                    # 同时发送 TTS 询问和 HA 通知
                    await self._speak_tts(ask_msg)
                    self._notify_dedup(ask_msg, "🤖 SmartAgent 存疑询问")
                    
                    self._sys_log("INFO", f"[渐进式自治] 执行{len(safe)}个安全项，拦截{len(pending_actions)}个存疑项")
                    await self._async_update_status(scene, f"执行基础操作，待确认存疑项")
                else:
                    # 只有安全项时，即使置信度稍低也直接执行（反正可逆）
                    if safe:
                        await self._execute_actions(
                            safe, trigger_summary=trigger, scene_desc=scene,
                            confidence=confidence, trigger_room=trigger_room, is_global_cmd=_is_global,
                            cmd_source=_cmd_source,
                        )
                        await self._async_update_status(scene, f"低风险操作已自动执行")

            else:
                self._sys_log("INFO", f"置信度不足: {confidence}")
                await self._async_update_status(scene, "置信度不足，仅供参考")

        except Exception as e:
            self._sys_log("ERROR", f"推理异常: {e}")
            # L3: 打印完整 traceback，方便生产环境调试罕见 bug
            _LOGGER.exception("[_run_inference] 未预期异常: %s", e)
        finally:
            self._batch_trigger_controllable.clear()

    async def _speak_tts(self, text: str) -> None:
        """播报 AI speak 字段内容。"""
        if not text:
            return
        self._notify_dedup(text, "🎙️ AI 播报")
        from .const import TTS_LEVEL_SPEAK_ONLY
        await self._tts_speak(text, min_level=TTS_LEVEL_SPEAK_ONLY)

    async def _run_voice_inference(self, text: str, source: str = "touch") -> dict:
        """执行语音指令推理流。"""
        from .intent_verifier import IntentVerifier, CMD_SOURCE_USER_EXPLICIT
        trigger = f"[语音·{source}] 用户说：{text}"
        await self._async_update_status("正在听", f"🎙️ {text}")

        # Add-on 委托推理（语音路径）
        decision = None
        context: str = ""          # 供 _record_training_sample 使用（Add-on 成功时也需有值）
        _voice_bundle: dict | None = None
        _addon_client = getattr(self, "_addon_client", None)
        if _addon_client is not None:
            try:
                if await _addon_client.is_available():
                    from .context_builder import ContextBuilder
                    _voice_bundle = await ContextBuilder(self).build(trigger, "", is_voice=True)
                    context = _voice_bundle.get("context_text", "")
                    decision = await _addon_client.infer(_voice_bundle)
            except Exception as _ae:
                _LOGGER.debug("[VoiceInference] Add-on 失败，降级到本地: %s", _ae)

        if decision is None:
            # 优先复用已构建的 bundle；若 Add-on 未部署则重新构建
            if _voice_bundle is None:
                from .context_builder import ContextBuilder
                _voice_bundle = await ContextBuilder(self).build(trigger, "", is_voice=True)
            context = _voice_bundle.get("context_text", "")
            decision = await self._call_ai_engine(
                context, trigger, is_voice=True, bundle=_voice_bundle
            )
        if not decision: return {"status": "error"}

        actions = decision.get("actions", [])
        scene = decision.get("scene", "语音指令")
        reply = decision.get("reply", "")
        # H3: 使用 LLM 实际返回的置信度，而非硬编码 95
        confidence = decision.get("confidence", 85)
        self._voice_reply = reply

        # H3: 语音指令也记录训练样本，让 ML 模型学习用户的语音意图
        self.hass.async_add_executor_job(
            self._record_training_sample, trigger, context, decision, None
        )

        # 5B-2: 语音路径同样支持 scene_candidate 路由（语音指令也能调用 HA 场景）
        _v_intent       = (decision.get("intent") or "").strip()
        _v_intent_label = (decision.get("intent_label") or "").strip()
        _v_scene_cand   = (decision.get("scene_candidate") or "").strip()
        _v_param_adj    = decision.get("param_adjustments") or {}
        if _v_scene_cand and self.hass.states.get(_v_scene_cand) is not None:
            _v_sc_action = {
                "domain": "scene",
                "service": "turn_on",
                "entity_id": _v_scene_cand,
                "params": {},
                "reason": f"语音·场景: {_v_intent_label or _v_intent or _v_scene_cand}",
                "delay_seconds": 0,
            }
            _v_adj: list[dict] = []
            if _v_param_adj:
                _v_adj_params = dict(_v_param_adj)
                if "transition" not in _v_adj_params:
                    _v_adj_params["transition"] = 2
                _v_trigger_room = _extract_trigger_room(trigger)
                for _ve in [
                    eid for eid, info in self.device_info.items()
                    if info.get("room") == _v_trigger_room and eid.startswith("light.")
                ][:6]:
                    _v_adj.append({
                        "domain": "light", "service": "turn_on", "entity_id": _ve,
                        "params": _v_adj_params,
                        "reason": f"语音·场景后微调: {_v_intent_label or _v_intent}",
                        "delay_seconds": 0.5,
                    })
            actions = [_v_sc_action] + _v_adj
            self._sys_log(
                "INFO",
                f"[5B-2 Voice] scene_candidate={_v_scene_cand} intent={_v_intent}",
            )
        elif _v_scene_cand:
            self._sys_log(
                "INFO",
                f"[5B-2 Voice] scene_candidate={_v_scene_cand} 不存在，使用 fallback",
            )

        # 1. 意图验证 (语音指令使用 USER_EXPLICIT 来源)
        # M3: 根据 LLM 决策中是否有 is_global 字段判断是否跨区，而非无条件设 True
        _occ_map = self._get_room_occupancy_map() if hasattr(self, "_get_room_occupancy_map") else {}
        # M2 修正：注入 sys_log_func
        _verifier = IntentVerifier(
            self.hass, self.device_info, _occ_map,
            sys_log_func=getattr(self, "_sys_log", None),
            suppress_check_func=getattr(self, "_should_suppress_action", None),
        )
        _has_global_action = any(a.get("is_global") for a in actions if isinstance(a, dict))
        _is_global = _has_global_action or any(
            kw in text for kw in ("所有", "全部", "全屋", "整个", "所有房间")
        )
        actions, _rejected = _verifier.verify(
            actions, cmd_source=CMD_SOURCE_USER_EXPLICIT, is_global_cmd=_is_global
        )

        # 2. 如果动作被拒绝，将原因加入回复中（语音主动告知）
        if _rejected:
            reject_reasons = "、".join(set(a.get("reject_reason", "安全拦截") for a in _rejected))
            reply = f"{reply}。抱歉，有 {len(_rejected)} 项操作被拦截：{reject_reasons}"
            self._voice_reply = reply

        # 5B-2: need_confirm 检查同样作用于语音路径
        _need_confirm = bool(decision.get("need_confirm", False))
        if _need_confirm and actions:
            _txn_id = f"voice_{int(__import__('time').time())}"
            self.hass.bus.async_fire(
                "smart_agent_confirm_required",
                {
                    "txn_id": _txn_id,
                    "trigger": trigger[:120],
                    "scene": scene,
                    "intent": _v_intent,
                    "intent_label": _v_intent_label,
                    "confidence": confidence,
                    "action_count": len(actions),
                    "actions": [a.get("reason", a.get("entity_id", "?")) for a in actions[:6]],
                    "reply": reply,
                },
            )
            self._sys_log(
                "INFO",
                f"[5B-2 Voice-Confirm] need_confirm=true，等待用户确认: "
                f"confidence={confidence}, actions={len(actions)}",
            )
            # TTS 告知用户需要确认，而非播放原始 reply（原 reply 可能描述已完成的动作）
            _pending_reply = "操作需要确认，请在面板点击确认后执行"
            self._voice_reply = _pending_reply
            await self._speak_tts(_pending_reply)
        elif actions:
            await self._execute_actions(
                actions, trigger_summary=trigger, scene_desc=scene,
                confidence=confidence, is_global_cmd=_is_global,
                cmd_source=CMD_SOURCE_USER_EXPLICIT,
            )
            if reply: await self._speak_tts(reply)
        elif reply:
            await self._speak_tts(reply)

        return {"status": "done", "reply": self._voice_reply if _need_confirm else reply}
