"""
MemoryStore — Phase 2 v2：统一记忆层（消灭碎片化学习，第二步）。

核心思想：AI 的唯一知识来源。
  - 整合所有数据源（corrections / device_baseline / arrival_baseline /
    behavior_patterns / reflexion_patterns / DecisionCache）
  - 为 AI 生成该房间的完整上下文叙事（自然语言）
  - 所有矛盾在这里如实呈现给 AI 让它权衡，而不是在 5 个不同模块里各自做判断

替代目标（渐进式）：
  - v1（v4.8.72）：作为 _call_ai_engine 的补充输入，与现有碎片化注入并存，
    新增「房间记忆」叙事段注入 P2 区，让 AI 获得更完整的房间历史上下文。
  - v2（v4.9.1，当前）：新增 get_room_context() 整合入口，包含：
      - 房间记忆叙事（narrative）
      - 设备使用基线摘要（baseline hint）
      - 修正感知（presence_context 感知）
    context_builder.py 可调用此单一入口替代分散的 _build_baseline_hint、
    _get_corrections_for_prompt 调用，减少 P2 Prompt 重复注入。
  - v3（后续）：完全替代所有碎片拼接逻辑，成为 AI 唯一知识来源。

架构参考：docs/HomeOS战略规划.md § 三、Phase 2 统一记忆层

重要：本模块所有方法均为同步（在 executor 中执行），禁止直接调用 asyncio / HA API。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)

# 到达基线最小样本数：低于此值的灯不进入叙事（数据不可靠）
_MIN_ARRIVAL_SAMPLES = 3
# 修正记录查询范围（天）：超出此范围的旧修正不注入（避免过时记录误导 AI）
_CORRECTIONS_LOOKBACK_DAYS = 90
# 矛盾检测时修正记录的最小次数：单次修正不视为明确意图
_CONFLICT_MIN_CORRECTIONS = 2


class MemoryStore:
    """AI 的统一记忆层 — 整合所有数据源，输出自然语言叙事给 LLM。

    设计为无状态轻量对象，每次推理调用时按需实例化，
    不缓存查询结果（数据库查询本身已由 DatabaseService WAL 缓存加速）。

    使用方式（在 executor 中调用）::

        ms = MemoryStore(
            db_query_func=self._db.query,
            device_info=self.device_info,
            get_device_name_func=self.get_device_name,
        )
        narrative = ms.get_room_narrative("客厅", "arrival", current_hour=20)
        # narrative 是自然语言字符串，可直接注入 AI Prompt
    """

    def __init__(
        self,
        db_query_func: Callable[..., list[dict]],
        device_info: dict[str, dict],
        get_device_name_func: Callable[[str], str] | None = None,
    ) -> None:
        """
        :param db_query_func:        DatabaseService.query 函数引用，在 executor 中同步调用
        :param device_info:          coordinator.device_info 设备信息字典
        :param get_device_name_func: 获取设备显示名称的函数（可选，默认使用 entity_id）
        """
        self._query = db_query_func
        self._device_info = device_info
        self._get_name: Callable[[str], str] = get_device_name_func or (lambda eid: eid)

    # ── 公共入口 ──────────────────────────────────────────────────────────────

    def get_room_narrative(
        self,
        room: str,
        trigger_type: str = "arrival",
        current_hour: int | None = None,
    ) -> str:
        """为 AI 生成该房间的完整上下文叙事。

        整合所有数据源，输出一段自然语言，例如：
          "进门时用户通常开 X、Y 灯（使用率 82%/76%）；
           用户 3 次关掉了 Z 灯，表明不希望 AI 开启；
           ⚡ 矛盾：Z 灯历史到达率 65%，但近期被纠正 3 次，请结合当前场景判断。"

        所有矛盾在这里被如实呈现给 AI 让它权衡，
        而不是在 5 个不同模块里各自做判断。

        :param room:         触发房间名称
        :param trigger_type: 触发类型（'arrival'/'departure'/'other'）
        :param current_hour: 当前小时（0-23），None 时使用系统时间
        :return: 自然语言叙事字符串，或空字符串（无记忆或查询失败时）
        """
        if not room:
            return ""
        if current_hour is None:
            current_hour = datetime.now().hour

        sections: list[str] = []

        # 1. 到达场景灯光习惯（arrival_baseline）
        if trigger_type == "arrival":
            arrival_text = self._build_arrival_narrative(room, current_hour)
            if arrival_text:
                sections.append(arrival_text)

        # 2. 用户修正记录（corrections）
        corrections_text = self._build_corrections_narrative(room)
        if corrections_text:
            sections.append(corrections_text)

        # 3. 矛盾检测：基线说开 vs 修正说不开，如实呈现给 AI
        if trigger_type == "arrival":
            conflict_text = self._detect_conflicts(room, current_hour)
            if conflict_text:
                sections.append(conflict_text)

        # 4. DecisionCache 命中统计（AI 历史决策在该房间的积累情况）
        cache_text = self._build_cache_narrative(room)
        if cache_text:
            sections.append(cache_text)

        if not sections:
            return ""

        return f"【{room} 房间历史记忆（供 AI 参考，遇矛盾时请综合判断）】\n" + "\n".join(sections)

    def get_room_context(
        self,
        room: str,
        trigger_type: str = "arrival",
        current_hour: int | None = None,
        current_presence: str = "",
    ) -> str:
        """Phase 2 v2 整合入口 — 一次调用获取房间所有历史上下文。

        整合 get_room_narrative() + _build_baseline_hint_sync() 为单一出口，
        供 context_builder.py 使用，减少 P2 Prompt 碎片注入与重复。

        与 get_room_narrative() 的区别：
          - 额外包含基线摘要（device_baseline / arrival_baseline）
          - 额外包含 Phase 3 Lite 行为戒律（correction_lessons 表，更高可读性）
          - lessons 存在时跳过原始 presence_corrections 注入，避免内容重叠
          - 提供更紧凑的格式，适合直接注入 P2 区

        :param room:             触发房间名称
        :param trigger_type:     触发类型（'arrival'/'departure'/'other'）
        :param current_hour:     当前小时（0-23），None 时使用系统时间
        :param current_presence: 当前在场状态（'occupied'/'empty'/''），用于过滤修正记录
        :return: 自然语言上下文字符串，或空字符串
        """
        if not room:
            return ""
        if current_hour is None:
            current_hour = datetime.now().hour

        parts: list[str] = []

        # 1. 房间历史记忆叙事（arrival/departure 偏好 + 矛盾检测 + 决策缓存统计）
        # 当 current_presence 已知时，用 presence 感知修正替代叙事中的全量修正段，
        # 避免「全量修正（无 presence 过滤）」与「presence 感知修正」两段内容重叠。
        if current_presence in ("occupied", "empty"):
            # 单独调用各子段，跳过全量 corrections（由 presence_corrections 代替）
            _arrival_text = ""
            _conflict_text = ""
            _cache_text = self._build_cache_narrative(room)
            if trigger_type == "arrival":
                _arrival_text = self._build_arrival_narrative(room, current_hour)
                _conflict_text = self._detect_conflicts(room, current_hour)

            _sub_sections: list[str] = []
            if _arrival_text:
                _sub_sections.append(_arrival_text)
            if _conflict_text:
                _sub_sections.append(_conflict_text)
            if _cache_text:
                _sub_sections.append(_cache_text)

            if _sub_sections:
                parts.append(
                    f"【{room} 房间历史记忆（供 AI 参考，遇矛盾时请综合判断）】\n"
                    + "\n".join(_sub_sections)
                )
        else:
            # current_presence 未知时：正常调用全量叙事（含全量修正）
            narrative = self.get_room_narrative(room, trigger_type, current_hour)
            if narrative:
                parts.append(narrative)

        # 2. 设备使用基线摘要（device_baseline，补充 arrival 以外的时段参考）
        baseline_hint = self._build_baseline_hint_sync(room, current_hour)
        if baseline_hint:
            parts.append(baseline_hint)

        # 3. 5D-1: 当前时段行为习惯（behavior_patterns — ML/LLM 行为学习结果）
        bp_text = self._build_behavior_patterns_narrative(room, current_hour)
        if bp_text:
            parts.append(bp_text)

        # 4. Phase 3 Lite / 5D-1：用户修正偏好参考（软化语气，供 AI 综合判断）
        # 优先注入 lessons（可读性更高）；lessons 存在时跳过原始 presence_corrections 注入。
        lessons_text = self._build_lessons_narrative(room, current_presence)
        if lessons_text:
            parts.append(lessons_text)
        elif current_presence in ("occupied", "empty"):
            # lessons 表尚未初始化（首日运行/新设备）时，回退到原始在场修正叙事
            presence_corrections = self._build_presence_corrections_narrative(
                room, current_presence
            )
            if presence_corrections:
                parts.append(presence_corrections)

        # 5. 5D-1: AI 反思记录（reflexion_patterns — AI 历史失败摘要）
        reflexion_text = self._build_reflexion_narrative(room)
        if reflexion_text:
            parts.append(reflexion_text)

        return "\n\n".join(parts)

    def _build_baseline_hint_sync(self, room: str, current_hour: int) -> str:
        """Phase 2 v2：同步版设备使用基线摘要，迁移自 InferenceMixin._build_baseline_hint。

        查询 device_baseline 表，汇总当前时段±1h 的设备历史使用率。
        过滤规则：
          - total_samples ≥ 5（至少 5 次记录，确保数据可靠性）
          - 使用率 ≥ 60%（习惯性开启）或 ≤ 30%（习惯性关闭）
          - 30%~60% 区间视为不确定，不注入（避免给 AI 无意义的模糊信号）

        :param room:         房间名
        :param current_hour: 当前小时（0-23）
        :return: 自然语言基线摘要，或空字符串
        """
        room_entities = [
            eid for eid, info in self._device_info.items()
            if info.get("room") == room and eid.split(".")[0] in (
                "light", "switch", "climate", "fan", "cover", "media_player"
            )
        ]
        if not room_entities:
            return ""

        buckets = [
            (current_hour - 1) % 24,
            current_hour,
            (current_hour + 1) % 24,
        ]
        placeholders_e = ",".join("?" * len(room_entities))
        placeholders_h = ",".join("?" * len(buckets))

        # 优先查询 v2 表（按小时分段，更精确）；若无数据则降级到 v1 全天汇总表。
        rows: list[dict] = []
        used_hourly = False
        try:
            rows = self._query(
                f"""
                SELECT entity_id,
                       AVG(usage_ratio)  AS avg_ratio,
                       SUM(sample_count) AS total_samples
                FROM device_baseline_hourly
                WHERE entity_id    IN ({placeholders_e})
                  AND hour_bucket  IN ({placeholders_h})
                GROUP BY entity_id
                HAVING SUM(sample_count) >= 5
                ORDER BY AVG(usage_ratio) DESC
                """,
                (*room_entities, *buckets),
            )
            used_hourly = bool(rows)
        except Exception as exc:
            _LOGGER.debug("[MemoryStore] device_baseline_hourly 查询失败 room=%s: %s", room, exc)

        # 降级：v1 全天汇总（on_ratio / total_samples）
        if not rows:
            try:
                rows = self._query(
                    f"""
                    SELECT entity_id,
                           on_ratio      AS avg_ratio,
                           total_samples
                    FROM device_baseline
                    WHERE entity_id IN ({placeholders_e})
                      AND total_samples >= 5
                    ORDER BY on_ratio DESC
                    """,
                    tuple(room_entities),
                )
                used_hourly = False
            except Exception as exc:
                _LOGGER.debug("[MemoryStore] device_baseline v1 查询失败 room=%s: %s", room, exc)
                return ""

        if not rows:
            return ""

        high_lines: list[str] = []
        low_lines: list[str] = []
        for r in rows:
            ratio = float(r["avg_ratio"] or 0)
            name = self._get_name(r["entity_id"])
            pct = round(ratio * 100)
            if ratio >= 0.6:
                high_lines.append(f"  - {name}：历史{'此时段 ' if used_hourly else ''}{pct}% 开启")
            elif ratio <= 0.3:
                low_lines.append(f"  - {name}：历史{'此时段 ' if used_hourly else ''}{pct}% 开启（通常关闭）")

        if not high_lines and not low_lines:
            return ""

        time_hint = "当前时段 ±1h" if used_hourly else "全天平均"
        lines = [f"  设备历史使用基线（{room}，{time_hint}）："]
        lines.extend(high_lines)
        lines.extend(low_lines)
        return "\n".join(lines)

    def _build_presence_corrections_narrative(
        self, room: str, current_presence: str
    ) -> str:
        """Phase 2 v2：在场感知修正记录叙事（基于 Phase 11.1 的 presence_context 列）。

        只返回与当前在场状态匹配的修正记录，避免「有人时修正」影响「无人时决策」。

        :param room:             房间名
        :param current_presence: 'occupied' 或 'empty'
        :return: 自然语言叙事，或空字符串
        """
        room_entities = [
            eid for eid, info in self._device_info.items()
            if info.get("room") == room
        ]
        if not room_entities:
            return ""

        placeholders = ",".join("?" * len(room_entities))
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            # 优先保留精确匹配 current_presence 的行（专属修正）
            # 对同一 entity_id + ai_service，用窗口函数取优先级最高的一行，
            # 确保 LIMIT 6 针对不同设备/动作，而非同设备的多个 presence_context 版本。
            # user_state 使用 MAX() 聚合：同一 entity+service 组内取出现次数最多/最新的状态值。
            # 严格而言应再 GROUP BY user_state，但会导致同设备多行；
            # 此处用 MAX() 保证 SELECT 的确定性（SQLite 不加聚合函数会随机取某行）。
            rows = self._query(
                f"""
                SELECT entity_id, ai_service,
                       MAX(user_state) AS user_state,
                       SUM(correction_count) AS total_count,
                       MAX(CASE WHEN presence_context = ? THEN 1 ELSE 0 END) AS is_presence_specific
                FROM corrections
                WHERE entity_id IN ({placeholders})
                  AND presence_context IN (?, 'any')
                  AND time >= ?
                GROUP BY entity_id, ai_service
                ORDER BY is_presence_specific DESC, total_count DESC
                LIMIT 6
                """,
                (current_presence, *room_entities, current_presence, cutoff),
            )
        except Exception as exc:
            _LOGGER.debug("[MemoryStore] presence corrections 查询失败 room=%s: %s", room, exc)
            return ""

        if not rows:
            return ""

        presence_label = "有人在场时" if current_presence == "occupied" else "无人时"
        lines = [f"  ⚠️ {presence_label}的修正记录（请重点参考）："]
        for r in rows:
            name = self._get_name(r["entity_id"])
            count = int(r["total_count"] or 1)
            ai_svc = r.get("ai_service") or ""
            user_st = r.get("user_state") or ""
            ctx_tag = "（该在场状态专属）" if r.get("is_presence_specific") else "（通用规则）"

            if "on" in ai_svc and ("off" in user_st or "turn_off" in user_st):
                action_desc = "AI 开灯 → 用户关掉"
            elif "off" in ai_svc and ("on" in user_st or "turn_on" in user_st):
                action_desc = "AI 关灯 → 用户开回"
            elif ai_svc:
                action_desc = f"AI {ai_svc} → 用户修正"
            else:
                action_desc = "用户修正了 AI 的操作"

            lines.append(f"    - {name}：{action_desc}（{count}次）{ctx_tag}")
        return "\n".join(lines)

    def _build_lessons_narrative(
        self, room: str, current_presence: str = ""
    ) -> str:
        """Phase 3 Lite / 5D-1：从 correction_lessons 表读取行为修正参考并注入 Prompt。

        5D-1 变更：将"请严格遵守"改为"供 AI 参考，请结合当前具体场景综合判断"，
        降低对 AI 决策的硬性约束。原则：矛盾信息如实呈现，让 AI 自己权衡，
        而非代码层面做判断。

        优先级排序：冲突戒律（警告类）> 高修正次数戒律 > 低修正次数戒律。
        当 presence 已知时：只取 presence_context 匹配当前状态或 'any' 的记录。

        :param room:             房间名
        :param current_presence: 'occupied'/'empty'/''（不限）
        :return: 自然语言参考段落，或空字符串
        """
        params: list = [room]
        presence_clause = ""
        if current_presence in ("occupied", "empty"):
            presence_clause = "AND (presence_context = ? OR presence_context = 'any')"
            params.append(current_presence)

        try:
            rows = self._query(
                f"""
                SELECT lesson_text, correction_count, is_conflicted
                FROM correction_lessons
                WHERE room = ? {presence_clause}
                ORDER BY is_conflicted DESC, correction_count DESC
                LIMIT 8
                """,
                tuple(params),
            )
        except Exception as exc:
            _LOGGER.debug("[MemoryStore] correction_lessons 查询失败 room=%s: %s", room, exc)
            return ""

        if not rows:
            return ""

        # 5D-1: 软化语气 — 从"请严格遵守"改为"供参考，请综合判断"
        lines = ["  [用户修正偏好参考 — 来自历史纠正，供 AI 参考，请结合当前具体场景综合判断]"]
        for r in rows:
            prefix = "⚠️" if r["is_conflicted"] else "→"
            lines.append(f"  {prefix} {r['lesson_text']}")
        return "\n".join(lines)

    def _build_behavior_patterns_narrative(
        self, room: str, current_hour: int
    ) -> str:
        """5D-1: 从 behavior_patterns 表读取当前时段的设备行为习惯叙事。

        behavior_patterns 记录每个设备在特定时段的预期状态（置信度 50-90），
        来源于本地 ML 训练或 LLM 行为学习（_async_llm_behavior_learn）。
        与 arrival_baseline 互补：后者只描述"进门时"，本方法描述"任意时段"习惯。

        :param room:         房间名
        :param current_hour: 当前小时（0-23）
        :return: 自然语言段落，或空字符串
        """
        # 获取该房间的设备列表
        room_entities = [
            eid for eid, info in self._device_info.items()
            if info.get("room") == room
        ]
        if not room_entities:
            return ""

        placeholders = ",".join("?" * len(room_entities))
        try:
            # 支持跨午夜时段：hour_end < hour_start 时用 OR 拆分
            # 例如 22:00-06:00 → (hour_start <= ? OR hour_end >= ?)
            rows = self._query(
                f"""
                SELECT entity_id, expected_state, hour_start, hour_end,
                       weekday_mask, confidence, hit_count
                FROM behavior_patterns
                WHERE entity_id IN ({placeholders})
                  AND confidence >= 60
                  AND (
                    (hour_start <= hour_end AND hour_start <= ? AND hour_end >= ?)
                    OR
                    (hour_start > hour_end AND (? >= hour_start OR ? <= hour_end))
                  )
                ORDER BY confidence DESC, hit_count DESC
                LIMIT 8
                """,
                (*room_entities, current_hour, current_hour, current_hour, current_hour),
            )
        except Exception as exc:
            _LOGGER.debug("[MemoryStore] behavior_patterns 查询失败 room=%s: %s", room, exc)
            return ""

        if not rows:
            return ""

        # P2 fix: 按当前星期过滤 — weekday_mask 使用 strftime %w 约定（0=周日，1=周一，…，6=周六）
        # 只展示与今日匹配的习惯，避免"工作日"习惯在周末误导 LLM
        today_wd = datetime.now().strftime("%w")  # "0"=Sun, "1"=Mon, ..., "6"=Sat
        filtered_rows = [
            r for r in rows
            if not r.get("weekday_mask") or today_wd in str(r["weekday_mask"])
        ]
        if not filtered_rows:
            return ""

        _wd_display = {
            "0123456": "每天",
            "12345": "工作日",
            "06": "周末",
            "6": "周六",
            "0": "周日",
        }
        lines: list[str] = [f"  {room} 当前时段行为习惯（来自统计/ML学习）："]
        for r in filtered_rows:
            name = self._get_name(r["entity_id"])
            state_cn = "开" if r["expected_state"] in ("on", "open") else "关"
            conf = int(r.get("confidence") or 65)
            hits = int(r.get("hit_count") or 0)
            mask = str(r.get("weekday_mask") or "0123456")
            wd_label = _wd_display.get(mask, f"星期{mask}")
            lines.append(
                f"    → {name}：{wd_label} {r['hour_start']:02d}-{r['hour_end']:02d}时"
                f" 通常{state_cn}（置信度 {conf}%{f'，命中{hits}次' if hits > 0 else ''}）"
            )
        return "\n".join(lines)

    def _build_reflexion_narrative(self, room: str) -> str:
        """5D-1: 从 reflexion_patterns 表读取 AI 反思记录叙事。

        reflexion_patterns 记录 AI 在某设备/服务/时段的历史失败摘要，
        是 AI 自我反思的结果，有助于避免重复犯同类错误。

        :param room: 房间名
        :return: 自然语言段落，或空字符串（无记录时）
        """
        room_entities = [
            eid for eid, info in self._device_info.items()
            if info.get("room") == room
        ]
        if not room_entities:
            return ""

        placeholders = ",".join("?" * len(room_entities))
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            rows = self._query(
                f"""
                SELECT entity_id, ai_service, failure_summary, correction_count
                FROM reflexion_patterns
                WHERE entity_id IN ({placeholders})
                  AND updated >= ?
                  AND correction_count >= 2
                ORDER BY correction_count DESC
                LIMIT 4
                """,
                (*room_entities, cutoff),
            )
        except Exception as exc:
            _LOGGER.debug("[MemoryStore] reflexion_patterns 查询失败 room=%s: %s", room, exc)
            return ""

        if not rows:
            return ""

        lines: list[str] = ["  AI 反思记录（近30天，供参考）："]
        for r in rows:
            name = self._get_name(r["entity_id"])
            summary = (r.get("failure_summary") or "").strip()
            count = int(r.get("correction_count") or 0)
            if summary:
                lines.append(f"    🔍 {name}：{summary}（纠正{count}次）")
        return "\n".join(lines) if len(lines) > 1 else ""

    # ── 私有构建方法（各数据源 → 自然语言段落）────────────────────────────────

    def _build_arrival_narrative(self, room: str, current_hour: int) -> str:
        """构建到达时灯光使用习惯叙事（来自 arrival_baseline）。

        :param room:         房间名
        :param current_hour: 当前小时（0-23），支持 ±1h 容差
        :return: 自然语言段落，或空字符串
        """
        buckets = [
            (current_hour - 1) % 24,
            current_hour,
            (current_hour + 1) % 24,
        ]
        placeholders = ",".join("?" * len(buckets))
        try:
            rows = self._query(
                f"""
                SELECT entity_id,
                       AVG(turn_on_ratio) AS ratio,
                       SUM(total_samples) AS samples
                FROM arrival_baseline
                WHERE room = ?
                  AND hour_bucket IN ({placeholders})
                GROUP BY entity_id
                HAVING SUM(total_samples) >= ?
                ORDER BY ratio DESC
                """,
                (room, *buckets, _MIN_ARRIVAL_SAMPLES),
            )
        except Exception as exc:
            _LOGGER.warning("[MemoryStore] arrival_baseline 查询失败 room=%s: %s", room, exc)
            return ""

        if not rows:
            return ""

        on_lines: list[str] = []
        off_lines: list[str] = []
        for r in rows:
            name = self._get_name(r["entity_id"])
            pct = round(r["ratio"] * 100)
            samples = int(r["samples"])
            if r["ratio"] >= 0.5:
                on_lines.append(f"    ✅ {name}：通常开灯（{pct}%，共{samples}次记录）")
            else:
                off_lines.append(f"    ❌ {name}：通常不开（{pct}%，共{samples}次记录）")

        parts: list[str] = ["  进门时灯光习惯（当前时段 ±1h 统计）："]
        parts.extend(on_lines)
        parts.extend(off_lines)
        return "\n".join(parts)

    def _build_corrections_narrative(self, room: str) -> str:
        """构建用户修正记录叙事（来自 corrections 表）。

        查该房间所有受管设备（灯光、开关、空调等）的修正，限制 90 天内的记录。

        :param room: 房间名
        :return: 自然语言段落，或空字符串
        """
        room_entities = [
            eid
            for eid, info in self._device_info.items()
            if info.get("room") == room
        ]
        if not room_entities:
            return ""

        cutoff = (datetime.now() - timedelta(days=_CORRECTIONS_LOOKBACK_DAYS)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        placeholders = ",".join("?" * len(room_entities))
        try:
            rows = self._query(
                f"""
                SELECT entity_id,
                       ai_service,
                       user_state,
                       SUM(correction_count) AS total_count,
                       MAX(time)             AS last_time
                FROM corrections
                WHERE entity_id IN ({placeholders})
                  AND time >= ?
                GROUP BY entity_id, ai_service
                ORDER BY total_count DESC
                LIMIT 8
                """,
                (*room_entities, cutoff),
            )
        except Exception as exc:
            _LOGGER.warning("[MemoryStore] corrections 查询失败 room=%s: %s", room, exc)
            return ""

        if not rows:
            return ""

        lines: list[str] = ["  用户修正记录（近90天，AI 应重点参考）："]
        for r in rows:
            name = self._get_name(r["entity_id"])
            ai_svc = r.get("ai_service") or ""
            user_st = r.get("user_state") or ""
            count = int(r["total_count"] or 1)

            # 根据 ai_service / user_state 字段生成人类可读描述
            if "on" in ai_svc and ("off" in user_st or "turn_off" in user_st):
                action_desc = "AI 开灯 → 用户关掉"
            elif "off" in ai_svc and ("on" in user_st or "turn_on" in user_st):
                action_desc = "AI 关灯 → 用户开回"
            elif ai_svc:
                action_desc = f"AI 执行 {ai_svc} → 用户修正"
            else:
                action_desc = "用户修正了 AI 的操作"

            lines.append(f"    ⚠️ {name}：{action_desc}（{count}次）")
        return "\n".join(lines)

    def _detect_conflicts(self, room: str, current_hour: int) -> str:
        """检测「到达基线高概率」与「用户修正多次」之间的矛盾。

        当某盏灯的到达使用率 ≥ 50% 但同时有近期修正记录时，
        这是矛盾信号，需要明确告知 AI 让它综合判断，而非机械执行历史习惯。

        :param room:         房间名
        :param current_hour: 当前小时（0-23）
        :return: 自然语言段落，或空字符串（无矛盾时）
        """
        buckets = [
            (current_hour - 1) % 24,
            current_hour,
            (current_hour + 1) % 24,
        ]
        placeholders = ",".join("?" * len(buckets))

        # 查询该房间到达率 ≥ 50% 的灯
        try:
            arrival_rows = self._query(
                f"""
                SELECT entity_id, AVG(turn_on_ratio) AS ratio
                FROM arrival_baseline
                WHERE room = ?
                  AND hour_bucket IN ({placeholders})
                GROUP BY entity_id
                HAVING SUM(total_samples) >= ? AND AVG(turn_on_ratio) >= 0.5
                """,
                (room, *buckets, _MIN_ARRIVAL_SAMPLES),
            )
        except Exception:
            return ""

        if not arrival_rows:
            return ""

        high_ratio_eids = {r["entity_id"] for r in arrival_rows}

        # 查询这些灯中有「AI 开灯后被用户纠正」记录的
        cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        placeholders2 = ",".join("?" * len(high_ratio_eids))
        try:
            conflict_rows = self._query(
                f"""
                SELECT entity_id, SUM(correction_count) AS total_corrections
                FROM corrections
                WHERE entity_id IN ({placeholders2})
                  AND (ai_service LIKE '%on%' OR ai_service = '')
                  AND time >= ?
                GROUP BY entity_id
                HAVING total_corrections >= ?
                """,
                (*high_ratio_eids, cutoff, _CONFLICT_MIN_CORRECTIONS),
            )
        except Exception:
            return ""

        if not conflict_rows:
            return ""

        lines: list[str] = [
            "  ⚡ 矛盾信号（以下设备数据存在冲突，请结合当前具体场景综合判断，不要机械执行）："
        ]
        ratio_map: dict[str, float] = {r["entity_id"]: r["ratio"] for r in arrival_rows}
        for r in conflict_rows:
            eid = r["entity_id"]
            name = self._get_name(eid)
            ratio_pct = round(ratio_map.get(eid, 0) * 100)
            corrections = int(r["total_corrections"])
            lines.append(
                f"    🔸 {name}：历史到达时 {ratio_pct}% 概率开灯，"
                f"但近60天被用户纠正 {corrections} 次。"
                f"请根据当前时间、是否有人、用户最近习惯来决策。"
            )
        return "\n".join(lines)

    def _build_cache_narrative(self, room: str) -> str:
        """构建 DecisionCache 历史统计叙事（AI 快路径积累情况）。

        当 DecisionCache 已建立时，说明 AI 在该房间有足够的历史决策经验，
        这些决策已被用户接受（否则会被纠正清除）。

        :param room: 房间名
        :return: 自然语言段落，或空字符串（缓存为空时）
        """
        try:
            rows = self._query(
                """
                SELECT trigger_type,
                       SUM(hit_count) AS hits,
                       MAX(last_hit)  AS last_used
                FROM decision_cache
                WHERE trigger_room = ?
                GROUP BY trigger_type
                """,
                (room,),
            )
        except Exception:
            return ""

        if not rows:
            return ""

        type_name_map = {"arrival": "到达", "departure": "离开", "other": "其他"}
        lines: list[str] = ["  AI 历史决策积累（快路径已建立，说明这些决策已被接受）："]
        for r in rows:
            type_label = type_name_map.get(r["trigger_type"], r["trigger_type"])
            hits = int(r.get("hits") or 0)
            last_used = r.get("last_used") or "无"
            if hits > 0:
                lines.append(
                    f"    📚 {type_label}场景：AI 决策已被复用 {hits} 次"
                    f"（最近：{last_used[:16] if last_used and last_used != '无' else '无'}）"
                )
        return "\n".join(lines) if len(lines) > 1 else ""
