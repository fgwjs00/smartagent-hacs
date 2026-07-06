"""
PresenceFusion — 存在传感器融合域引擎 (Phase 12.0)

Boundary: legacy compatibility only. This module is not a canonical decision fact source.
Canonical presence decisions are owned by addon_presence_engine.

解决「一镜多区 + 大开间 + 多传感器」场景下的误判问题：
  - Frigate zone 子区无人 ≠ 整个开间无人
  - 存在传感器只覆盖一侧，另一侧 zone 还有人
  - 「无人离开」需要整个融合域全部满足条件才成立

设计目标（通用性优先）：
  - 不写死任何房间名；规则全部通过配置实例化
  - 同一套引擎适配家庭/展厅/办公等所有场景
  - 融合域独立于展厅模式，家庭模式同样可使用

配置格式（JSON 数组，存为字符串，与 showroom_zone_map 风格一致）：
  [
    {
      "scope_id":        "open_plan_living",          // 唯一标识（英文）
      "name":            "客餐厅开间",                // 显示名称（日志可见）
      "strategy":        "occupied_or",               // occupied_or | vacant_and
      "rooms":           ["客厅", "餐厅"],            // 此域覆盖的 HA 房间名列表
      "members":         [                             // 参与融合的传感器 entity_id 列表
                           "binary_sensor.linp_cn_xxx_occupancy",
                           "binary_sensor.chazhuo_person_occupancy",
                           "binary_sensor.shafa_person_occupancy"
                         ],
      "vacant_hold_secs": 60                          // 默认 60，全员无人持续多少秒才算真正离开
    }
  ]

strategy 说明：
  occupied_or  (默认) — 任一成员为「有人」 → 域 = 有人。
                        适合开间/大厅/共享空间。
  vacant_and          — 全部成员「无人」持续 vacant_hold_secs → 域 = 无人。
                        单个子区无人不影响整体判断，需所有成员都安静才关灯。

主要用途：
  1. 监听器状态变化链路 → 形成离开/无人证据，交由 add-on PresenceEngine 与 Guard 校验
  2. 保护层占用判断 → 优先使用域状态而非单个传感器，避免子区无人误关共享设备
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PresenceMemberPolicy:
    """融合域成员能力配置。"""

    entity_id: str
    can_enter_trigger: bool = True
    can_leave_evidence: bool = True
    priority: int = 100
    confidence: float = 1.0

_LOGGER = logging.getLogger(__name__)

STRATEGY_OR  = "occupied_or"    # 任一有人即有人（默认）
STRATEGY_AND = "vacant_and"     # 全员无人才算无人


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_members(members_raw: Any) -> tuple[list[str], dict[str, PresenceMemberPolicy]]:
    members: list[str] = []
    member_policies: dict[str, PresenceMemberPolicy] = {}
    if not isinstance(members_raw, list):
        return members, member_policies

    for m in members_raw:
        if isinstance(m, str):
            eid = m.strip()
            if not eid:
                continue
            members.append(eid)
            member_policies[eid] = PresenceMemberPolicy(entity_id=eid)
            continue
        if isinstance(m, dict):
            eid = str(m.get("entity_id", "")).strip()
            if not eid:
                continue
            members.append(eid)
            member_policies[eid] = PresenceMemberPolicy(
                entity_id=eid,
                can_enter_trigger=bool(m.get("can_enter_trigger", True)),
                can_leave_evidence=bool(m.get("can_leave_evidence", True)),
                priority=_safe_int(m.get("priority", 100), 100),
                confidence=_safe_float(m.get("confidence", 1.0), 1.0),
            )
    return members, member_policies


@dataclass
class PresenceFusionScope:
    """单个融合域的数据模型。"""

    scope_id: str
    """唯一标识符（英文 slug，如 open_plan_living）"""

    name: str = ""
    """人类可读名称，用于日志显示"""

    strategy: str = STRATEGY_OR
    """融合策略：occupied_or | vacant_and"""

    rooms: list[str] = field(default_factory=list)
    """此域覆盖的 HA 房间名列表（对应 device_info 里的 room 字段）"""

    members: list[str] = field(default_factory=list)
    """兼容旧配置：成员实体列表（默认 enter/leave 都可用）"""

    member_policies: dict[str, PresenceMemberPolicy] = field(default_factory=dict)
    """成员能力策略：entity_id -> PresenceMemberPolicy"""

    enter_hold_secs: int = 0
    """进入迟滞：域从 off→on 后需持续多久才确认有人（秒）"""

    vacant_hold_secs: int = 60
    """离开迟滞：域从 on→off 后需持续多久才确认无人（秒）"""

    @property
    def display_name(self) -> str:
        return self.name or self.scope_id


class PresenceFusionRegistry:
    """
    融合域注册表。

    从配置字符串（JSON）解析域列表，提供：
      - 按实体查域 (get_scope_for_entity)
      - 按房间查域 (get_scope_for_room)
      - 实时评估域状态 (evaluate_scope) → "on" | "off" | "unknown"
    """

    def __init__(self, hass: Any, scopes_json: str) -> None:
        self.hass = hass
        self._scopes: list[PresenceFusionScope] = []
        # 反向索引：entity_id → scope
        self._entity_to_scope: dict[str, PresenceFusionScope] = {}
        # 反向索引：room_name → scope
        self._room_to_scope: dict[str, PresenceFusionScope] = {}

        # 迟滞计时器：scope_id -> 首次满足候选条件的时间戳
        self._scope_enter_candidate_since: dict[str, float | None] = {}
        self._scope_vacant_candidate_since: dict[str, float | None] = {}
        # 已确认状态缓存：scope_id -> "on"|"off"|"unknown"
        self._scope_confirmed_state: dict[str, str] = {}
        self._load(scopes_json)

    # ── 公开接口 ───────────────────────────────────────────────────────────────

    @property
    def scopes(self) -> list[PresenceFusionScope]:
        return self._scopes

    @property
    def has_scopes(self) -> bool:
        return bool(self._scopes)

    def get_scope_for_entity(self, entity_id: str) -> PresenceFusionScope | None:
        """返回指定传感器所属的融合域，不在任何域中则返回 None。"""
        return self._entity_to_scope.get(entity_id)

    def get_scope_for_room(self, room: str) -> PresenceFusionScope | None:
        """返回覆盖指定房间的融合域，未覆盖则返回 None。"""
        return self._room_to_scope.get(room)

    def evaluate_scope(self, scope: PresenceFusionScope) -> str:
        """实时评估融合域状态（含进入/离开迟滞）。"""
        states = self._collect_member_states(scope)
        if not states:
            self._scope_confirmed_state[scope.scope_id] = "unknown"
            return "unknown"

        raw_state = self._compute_raw_state(scope, states)
        return self._apply_hysteresis(scope, raw_state)

    def can_trigger_enter(self, scope: PresenceFusionScope, entity_id: str) -> bool:
        """检查指定成员是否允许触发 enter（开灯触发）。"""
        pol = scope.member_policies.get(entity_id)
        return True if pol is None else bool(pol.can_enter_trigger)

    def can_provide_leave_evidence(self, scope: PresenceFusionScope, entity_id: str) -> bool:
        """检查指定成员是否参与 leave 证据聚合。"""
        pol = scope.member_policies.get(entity_id)
        return True if pol is None else bool(pol.can_leave_evidence)

    def _collect_member_states(self, scope: PresenceFusionScope) -> list[tuple[str, str]]:
        """收集成员状态列表: [(entity_id, state), ...]。"""
        items: list[tuple[str, str]] = []
        for eid in scope.members:
            state_obj = self.hass.states.get(eid)
            items.append((eid, state_obj.state if state_obj else "unknown"))
        return items

    def _compute_raw_state(self, scope: PresenceFusionScope, states: list[tuple[str, str]]) -> str:
        """计算未迟滞前的融合状态。"""
        if scope.strategy == STRATEGY_OR:
            if any(s == "on" for _, s in states):
                return "on"
            if any(s == "off" for _, s in states):
                return "off"
            return "unknown"

        leave_states = [
            s for eid, s in states
            if self.can_provide_leave_evidence(scope, eid)
        ]
        if not leave_states:
            leave_states = [s for _, s in states]

        if any(s == "on" for _, s in states):
            return "on"
        if all(s == "off" for s in leave_states):
            return "off"
        return "unknown"

    def _apply_hysteresis(self, scope: PresenceFusionScope, raw_state: str) -> str:
        """应用 enter/leave 迟滞，返回最终确认状态。"""
        sid = scope.scope_id
        now = time.time()
        confirmed = self._scope_confirmed_state.get(sid, "unknown")

        if raw_state == "unknown":
            self._scope_enter_candidate_since[sid] = None
            self._scope_vacant_candidate_since[sid] = None
            self._scope_confirmed_state[sid] = "unknown"
            return "unknown"

        if raw_state == "on":
            self._scope_vacant_candidate_since[sid] = None
            if confirmed == "on":
                self._scope_enter_candidate_since[sid] = None
                return "on"
            hold = max(0, int(scope.enter_hold_secs))
            if hold == 0:
                self._scope_enter_candidate_since[sid] = None
                self._scope_confirmed_state[sid] = "on"
                return "on"
            since = self._scope_enter_candidate_since.get(sid)
            if since is None:
                self._scope_enter_candidate_since[sid] = now
                return confirmed
            if now - since >= hold:
                self._scope_enter_candidate_since[sid] = None
                self._scope_confirmed_state[sid] = "on"
                return "on"
            return confirmed

        self._scope_enter_candidate_since[sid] = None
        if confirmed == "off":
            self._scope_vacant_candidate_since[sid] = None
            return "off"
        hold = max(0, int(scope.vacant_hold_secs))
        if hold == 0:
            self._scope_vacant_candidate_since[sid] = None
            self._scope_confirmed_state[sid] = "off"
            return "off"
        since = self._scope_vacant_candidate_since.get(sid)
        if since is None:
            self._scope_vacant_candidate_since[sid] = now
            return confirmed if confirmed != "unknown" else "on"
        if now - since >= hold:
            self._scope_vacant_candidate_since[sid] = None
            self._scope_confirmed_state[sid] = "off"
            return "off"
        return confirmed if confirmed != "unknown" else "on"

    def evaluate_room(self, room: str) -> str | None:
        """
        评估指定房间的融合状态。

        Returns:
            "on" / "off" / "unknown"  — 该房间属于某个融合域时
            None                       — 该房间不在任何融合域中（调用方使用原始传感器逻辑）
        """
        scope = self.get_scope_for_room(room)
        if scope is None:
            return None
        return self.evaluate_scope(scope)

    def get_summary(self) -> list[dict]:
        """供诊断日志/MCP 工具使用的状态摘要。"""
        result = []
        for scope in self._scopes:
            result.append({
                "scope_id": scope.scope_id,
                "name": scope.display_name,
                "strategy": scope.strategy,
                "rooms": scope.rooms,
                "members": [
                    {
                        "entity_id": eid,
                        "can_enter_trigger": (pol.can_enter_trigger if pol else True),
                        "can_leave_evidence": (pol.can_leave_evidence if pol else True),
                        "priority": (pol.priority if pol else 100),
                        "confidence": (pol.confidence if pol else 1.0),
                    }
                    for eid in scope.members
                    for pol in [scope.member_policies.get(eid)]
                ],
                "state": self.evaluate_scope(scope),
            })
        return result

    def build_presence_snapshot_for_entity(
        self,
        entity_id: str,
        *,
        blocked_actions: list[str] | None = None,
        reasons: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """构建指定成员实体的统一 Presence Snapshot。"""
        scope = self.get_scope_for_entity(entity_id)
        if scope is None:
            return None
        return self.build_presence_snapshot_for_scope(
            scope,
            trigger_entity_id=entity_id,
            blocked_actions=blocked_actions,
            reasons=reasons,
        )

    def build_presence_snapshot_for_scope(
        self,
        scope: PresenceFusionScope,
        *,
        trigger_entity_id: str | None = None,
        blocked_actions: list[str] | None = None,
        reasons: list[str] | None = None,
    ) -> dict[str, Any]:
        """构建融合域的统一 Presence Snapshot。"""
        states = self._collect_member_states(scope)
        confirmed_state = self.evaluate_scope(scope)

        member_state_map = {eid: s for eid, s in states}
        on_members = [eid for eid, s in states if s == "on"]
        off_members = [eid for eid, s in states if s == "off"]
        unknown_members = [eid for eid, s in states if s not in ("on", "off")]

        weighted_total = 0.0
        weighted_on = 0.0
        for eid, s in states:
            pol = scope.member_policies.get(eid)
            weight = float(pol.confidence if pol else 1.0)
            if weight <= 0:
                weight = 0.1
            weighted_total += weight
            if s == "on":
                weighted_on += weight

        if confirmed_state == "on":
            confidence = 1.0 if weighted_total <= 0 else max(0.6, min(1.0, weighted_on / weighted_total))
        elif confirmed_state == "off":
            confidence = 0.0
        else:
            confidence = 0.3 if unknown_members else 0.0

        final_reasons = list(reasons or [])
        final_reasons.append(f"scope={scope.scope_id}")
        final_reasons.append(f"strategy={scope.strategy}")
        if on_members:
            final_reasons.append("on_members=" + ",".join(on_members[:6]))
        if off_members:
            final_reasons.append("off_members=" + ",".join(off_members[:6]))
        if unknown_members:
            final_reasons.append("unknown_members=" + ",".join(unknown_members[:6]))

        enter_qualified = bool(
            trigger_entity_id
            and member_state_map.get(trigger_entity_id) == "on"
            and self.can_trigger_enter(scope, trigger_entity_id)
        )
        if enter_qualified and scope.strategy == STRATEGY_AND and trigger_entity_id:
            enter_members = [
                mid for mid in scope.members if self.can_trigger_enter(scope, mid)
            ]
            if len(enter_members) >= 2:
                peer_active = any(
                    mid != trigger_entity_id and member_state_map.get(mid) == "on"
                    for mid in enter_members
                )
                if not peer_active:
                    enter_qualified = False
                    final_reasons.append("vacant_and_single_source_enter_blocked")
        leave_qualified = bool(
            trigger_entity_id
            and member_state_map.get(trigger_entity_id) == "off"
            and self.can_provide_leave_evidence(scope, trigger_entity_id)
            and confirmed_state == "off"
        )

        return {
            "state": confirmed_state,
            "confidence": round(max(0.0, min(confidence, 1.0)), 3),
            "reasons": final_reasons,
            "enter_qualified": enter_qualified,
            "leave_qualified": leave_qualified,
            "localized_spaces": list(scope.rooms),
            "blocked_actions": list(blocked_actions or []),
        }

    # ── 内部方法 ───────────────────────────────────────────────────────────────

    def _load(self, scopes_json: str) -> None:
        """解析 JSON 配置并建立反向索引。解析失败时记录警告并使用空列表。"""
        if not scopes_json or not scopes_json.strip():
            return

        try:
            raw_list = json.loads(scopes_json)
        except (json.JSONDecodeError, TypeError) as exc:
            _LOGGER.warning("[FusionRegistry] 配置 JSON 解析失败，融合功能已禁用: %s", exc)
            return

        if not isinstance(raw_list, list):
            _LOGGER.warning("[FusionRegistry] 配置应为 JSON 数组，实际类型=%s，融合功能已禁用", type(raw_list).__name__)
            return

        for item in raw_list:
            if not isinstance(item, dict):
                continue
            scope_id = item.get("scope_id", "").strip()
            if not scope_id:
                _LOGGER.warning("[FusionRegistry] 跳过缺少 scope_id 的条目: %s", item)
                continue

            strategy = item.get("strategy", STRATEGY_OR)
            if strategy not in (STRATEGY_OR, STRATEGY_AND):
                _LOGGER.warning("[FusionRegistry] scope_id=%s 未知策略 %s，降级为 occupied_or", scope_id, strategy)
                strategy = STRATEGY_OR

            members, member_policies = _parse_members(item.get("members", []))

            scope = PresenceFusionScope(
                scope_id=scope_id,
                name=item.get("name", scope_id),
                strategy=strategy,
                rooms=list(item.get("rooms", [])),
                members=members,
                member_policies=member_policies,
                enter_hold_secs=max(0, _safe_int(item.get("enter_hold_secs", 0), 0)),
                vacant_hold_secs=max(0, _safe_int(item.get("vacant_hold_secs", 60), 60)),
            )
            self._scopes.append(scope)

            for eid in scope.members:
                if eid in self._entity_to_scope:
                    _LOGGER.warning(
                        "[FusionRegistry] 实体 %s 被多个域引用（%s 和 %s），以首次注册为准",
                        eid, self._entity_to_scope[eid].scope_id, scope_id,
                    )
                else:
                    self._entity_to_scope[eid] = scope

            for room in scope.rooms:
                if room in self._room_to_scope:
                    _LOGGER.warning(
                        "[FusionRegistry] 房间 %s 被多个域覆盖（%s 和 %s），以首次注册为准",
                        room, self._room_to_scope[room].scope_id, scope_id,
                    )
                else:
                    self._room_to_scope[room] = scope

        if self._scopes:
            _LOGGER.info(
                "[FusionRegistry] 已加载 %d 个融合域: %s",
                len(self._scopes),
                ", ".join(f"{s.scope_id}({s.strategy})" for s in self._scopes),
            )


def parse_fusion_config(scopes_json: str) -> list[PresenceFusionScope]:
    """
    工具函数：解析融合域配置字符串，返回域列表。

    供 config_flow 校验和展示使用（不需要 hass）。
    """
    if not scopes_json or not scopes_json.strip():
        return []
    try:
        raw_list = json.loads(scopes_json)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(raw_list, list):
        return []
    scopes = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        scope_id = item.get("scope_id", "").strip()
        if not scope_id:
            continue
        members, member_policies = _parse_members(item.get("members", []))

        scopes.append(PresenceFusionScope(
            scope_id=scope_id,
            name=item.get("name", scope_id),
            strategy=item.get("strategy", STRATEGY_OR),
            rooms=list(item.get("rooms", [])),
            members=members,
            member_policies=member_policies,
            enter_hold_secs=max(0, _safe_int(item.get("enter_hold_secs", 0), 0)),
            vacant_hold_secs=max(0, _safe_int(item.get("vacant_hold_secs", 60), 60)),
        ))
    return scopes
