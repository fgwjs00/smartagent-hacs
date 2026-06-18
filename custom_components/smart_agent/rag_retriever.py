"""
RAGRetriever — 条件性 RAG 检索器（Phase RAG）。

纯 SQLite 实现，无外部依赖。当 FastBrain 低置信度或返回 None 时，
为 LLM 推理提供结构化历史上下文，让 AI 不再"失忆"。

四维检索：
  1. 历史 LLM 决策（decision_cache）
  2. 用户修正历史（corrections）
  3. 行为模式匹配（behavior_patterns）
  4. 行为戒律（correction_lessons）

设计为无状态轻量对象，所有方法均为同步（在 executor 中执行）。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from .const import (
    RAG_MAX_TOKENS,
    RAG_SIMILAR_HOUR_RANGE,
    RAG_CORRECTIONS_LOOKBACK_DAYS,
    RAG_MIN_CORRECTION_COUNT,
    RAG_BEHAVIOR_MIN_CONFIDENCE,
)

_LOGGER = logging.getLogger(__name__)

_WEEKDAY_NAMES = {
    0: "周一", 1: "周二", 2: "周三", 3: "周四",
    4: "周五", 5: "周六", 6: "周日",
}


class RAGRetriever:
    """条件性 RAG 检索器 — 纯 SQLite 实现，无外部依赖。"""

    def __init__(
        self,
        db_query_func: Callable[..., list[dict]],
        device_info: dict[str, dict],
        get_device_name_func: Callable[[str], str] | None = None,
    ) -> None:
        self._query = db_query_func
        self._device_info = device_info
        self._name = get_device_name_func or (lambda eid: eid)

    def retrieve(
        self,
        room: str,
        trigger_type: str,
        hour: int,
        weekday: int,
        is_weekend: bool,
        presence: str = "",
        max_tokens: int = RAG_MAX_TOKENS,
    ) -> str:
        """主入口：检索并组装 RAG 上下文，控制在 max_tokens 预算内。

        :param room: 触发房间
        :param trigger_type: 'arrival' | 'departure' | 'other'
        :param hour: 当前小时 0-23
        :param weekday: Python weekday 0=Mon..6=Sun
        :param is_weekend: 是否周末
        :param presence: 'occupied' | 'empty' | ''
        :param max_tokens: Token 预算上限
        :return: 格式化的 RAG 上下文字符串，空字符串表示无有效检索结果
        """
        if not room:
            return ""

        sections: list[str] = []

        # 维度 1: 历史 LLM 决策（~150 token）
        decisions = self._retrieve_decisions(room, trigger_type, hour, weekday, is_weekend)
        if decisions:
            sections.append(decisions)

        # 维度 2: 用户修正历史（~120 token）
        corrections = self._retrieve_corrections(room, presence)
        if corrections:
            sections.append(corrections)

        # 维度 3: 行为模式（~100 token）
        patterns = self._retrieve_patterns(room, hour, weekday)
        if patterns:
            sections.append(patterns)

        # 维度 4: 行为戒律（~130 token）
        lessons = self._retrieve_lessons(room, presence)
        if lessons:
            sections.append(lessons)

        if not sections:
            return ""

        result = "【RAG 历史参考（相似场景检索）】\n" + "\n".join(sections)

        # 粗略 Token 预算控制（1 中文字 ≈ 1.5 token）
        estimated_tokens = int(len(result) * 1.5)
        if estimated_tokens > max_tokens:
            # 按比例截断
            max_chars = int(max_tokens / 1.5)
            result = result[:max_chars] + "…"

        return result

    def _retrieve_decisions(
        self, room: str, trigger_type: str, hour: int, weekday: int, is_weekend: bool,
    ) -> str:
        """维度 1: 从 decision_cache 检索相似场景的历史 LLM 决策。"""
        try:
            h_lo = max(0, hour - RAG_SIMILAR_HOUR_RANGE)
            h_hi = min(23, hour + RAG_SIMILAR_HOUR_RANGE)
            # 同类日：工作日匹配工作日(1-5)，周末匹配周末(0,6)
            sqlite_wd = (weekday + 1) % 7  # Python→SQLite weekday
            if is_weekend:
                wd_clause = "weekday IN (0, 6)"
            else:
                wd_clause = "weekday BETWEEN 1 AND 5"

            rows = self._query(
                f"SELECT hour_bucket, weekday, actions_json, confidence, scene, hit_count "
                f"FROM decision_cache "
                f"WHERE trigger_room = ? AND hour_bucket BETWEEN ? AND ? "
                f"AND trigger_type = ? AND {wd_clause} "
                f"ORDER BY hit_count DESC, confidence DESC LIMIT 3",
                (room, h_lo, h_hi, trigger_type),
            )
            if not rows:
                return ""

            lines: list[str] = []
            for r in rows:
                wd_name = _WEEKDAY_NAMES.get(
                    (r.get("weekday", 0) - 1) % 7 if r.get("weekday") is not None else weekday,
                    "?"
                )
                h = r.get("hour_bucket", hour)
                hits = r.get("hit_count", 0)
                conf = r.get("confidence", 0)
                # 解析 actions 摘要
                actions_summary = self._summarize_actions(r.get("actions_json", ""))
                if actions_summary:
                    lines.append(
                        f"▸ 历史决策：{wd_name}{h}时 {room}→{actions_summary}"
                        f"(命中{hits}次,置信度{conf}%)"
                    )
            return "\n".join(lines)
        except Exception as exc:
            _LOGGER.debug("[RAG] 历史决策检索失败: %s", exc)
            return ""

    def _retrieve_corrections(self, room: str, presence: str) -> str:
        """维度 2: 从 corrections 检索该房间的高频用户修正。"""
        try:
            rows = self._query(
                "SELECT entity_id, ai_service, user_state, correction_count, presence_context "
                "FROM corrections "
                "WHERE room = ? AND correction_count >= ? "
                "AND time >= datetime('now', ? || ' days') "
                "ORDER BY correction_count DESC LIMIT 5",
                (room, RAG_MIN_CORRECTION_COUNT, f"-{RAG_CORRECTIONS_LOOKBACK_DAYS}"),
            )
            if not rows:
                return ""

            lines: list[str] = []
            for r in rows:
                name = self._name(r["entity_id"])
                svc = r.get("ai_service", "?")
                user_st = r.get("user_state", "?")
                cnt = r.get("correction_count", 0)
                pres = r.get("presence_context", "any")
                pres_tag = {"occupied": "有人时", "empty": "无人时"}.get(pres, "")
                lines.append(
                    f"▸ 用户修正：{name} AI→{svc} 用户→{user_st}"
                    f"(累计{cnt}次{','+pres_tag if pres_tag else ''})"
                )
            return "\n".join(lines)
        except Exception as exc:
            _LOGGER.debug("[RAG] 修正历史检索失败: %s", exc)
            return ""

    def _retrieve_patterns(self, room: str, hour: int, weekday: int) -> str:
        """维度 3: 从 behavior_patterns 检索当前时段的行为模式。"""
        try:
            sqlite_wd = str((weekday + 1) % 7)
            rows = self._query(
                "SELECT bp.entity_id, bp.expected_state, bp.dim_key, bp.expected_value, bp.season, "
                "bp.hour_start, bp.hour_end, bp.confidence, bp.hit_count, bp.source, bp.source_type "
                "FROM behavior_patterns bp "
                "INNER JOIN devices d ON bp.entity_id = d.entity_id "
                "WHERE d.area = ? "
                "AND bp.hour_start <= ? AND bp.hour_end >= ? "
                "AND bp.weekday_mask LIKE ? "
                "AND bp.confidence >= ? "
                "AND (COALESCE(bp.source, '') != 'silent_learning' OR COALESCE(bp.hit_count, 0) >= 3) "
                "ORDER BY bp.confidence DESC, bp.hit_count DESC LIMIT 5",
                (room, hour, hour, f"%{sqlite_wd}%", RAG_BEHAVIOR_MIN_CONFIDENCE),
            )
            if not rows:
                return ""

            lines: list[str] = []
            for r in rows:
                name = self._name(r["entity_id"])
                dim_key = str(r.get("dim_key") or "power").strip().lower() or "power"
                expected_value = str(r.get("expected_value") or r.get("expected_state") or "?")
                state = expected_value if dim_key == "power" else f"{dim_key}={expected_value}"
                h_s = r.get("hour_start", 0)
                h_e = r.get("hour_end", 23)
                conf = r.get("confidence", 0)
                lines.append(
                    f"▸ 行为模式：{h_s}-{h_e}时 {name} {state} 概率{conf}%"
                )
            return "\n".join(lines)
        except Exception as exc:
            _LOGGER.debug("[RAG] 行为模式检索失败: %s", exc)
            return ""

    def _retrieve_lessons(self, room: str, presence: str) -> str:
        """维度 4: 从 correction_lessons 检索行为戒律。"""
        try:
            rows = self._query(
                "SELECT lesson_text, correction_count, confidence "
                "FROM correction_lessons "
                "WHERE room = ? AND is_conflicted = 0 "
                "AND (presence_context = ? OR presence_context = 'any') "
                "ORDER BY correction_count DESC LIMIT 5",
                (room, presence or "any"),
            )
            if not rows:
                return ""

            lines: list[str] = []
            for r in rows:
                text = r.get("lesson_text", "").strip()
                if text:
                    lines.append(f"▸ 行为戒律：{text}")
            return "\n".join(lines)
        except Exception as exc:
            _LOGGER.debug("[RAG] 行为戒律检索失败: %s", exc)
            return ""

    def _summarize_actions(self, actions_json: str) -> str:
        """将 actions_json 字符串解析为简短摘要。"""
        if not actions_json:
            return ""
        try:
            actions = json.loads(actions_json)
            if not isinstance(actions, list):
                return ""
            parts: list[str] = []
            for a in actions[:3]:  # 最多展示 3 个动作
                eid = a.get("entity_id", "")
                svc = a.get("service", "")
                name = self._name(eid) if eid else "?"
                if svc == "turn_on":
                    parts.append(f"开{name}")
                elif svc == "turn_off":
                    parts.append(f"关{name}")
                else:
                    parts.append(f"{svc} {name}")
            return "+".join(parts)
        except (json.JSONDecodeError, TypeError):
            return ""
