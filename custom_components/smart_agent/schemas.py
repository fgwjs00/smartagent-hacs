"""
SmartAgent 标准化输出 Schema 定义 (Phase 9.3 - P1.3)。

包含：
  - Pydantic 模型（DecisionResponse / ActionItem）用于验证 LLM 输出
  - JSON Schema（供 Ollama format 字段使用的严格模式）
  - 公共验证函数 validate_decision()
"""
from __future__ import annotations

import copy
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# domain 白名单（与 DECISION_JSON_SCHEMA enum 同源，模块级避免每次调用重建）
_VALID_DOMAINS: frozenset[str] = frozenset({
    "light", "switch", "climate", "cover", "fan",
    "script", "scene", "media_player", "vacuum",
    "input_boolean", "input_number", "input_select",
    "water_heater", "humidifier", "number", "select", "button",
})

# intent 已知值域（软验证：未知值只记录 DEBUG，不拒绝，允许扩展）
_KNOWN_INTENTS: frozenset[str] = frozenset({
    "arrival_lighting", "departure_off", "scene_switch",
    "climate_adjust", "no_action", "scene_route", "micro_adjust", "",
})

# ── JSON Schema（传给 Ollama format 字段） ─────────────────────────────────────

#: Ollama /api/chat 的 format 字段：严格定义 LLM 输出的 JSON 结构。
DECISION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "scene": {
            "type": "string",
            "description": "当前场景的简短中文描述，例如 '客厅有人进入，自动开灯'",
        },
        "confidence": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "本次决策的置信度 0-100，不确定时填 50 以下",
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "enum": [
                            "light", "switch", "climate", "cover", "fan",
                            "script", "scene", "media_player", "vacuum",
                            "input_boolean", "input_number",
                        ],
                    },
                    "service": {
                        "type": "string",
                        "description": (
                            "HA 服务名，如 turn_on / turn_off / set_temperature。"
                            "注意：调节亮度必须用 light.turn_on + params.brightness_pct，"
                            "严禁用 turn_off 来降低亮度。"
                        ),
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "完整 HA entity_id，例如 light.living_room_main",
                    },
                    "params": {
                        "type": "object",
                        "description": (
                            "服务参数。灯光调光使用 {brightness_pct: 0-100}；"
                            "色温使用 {color_temp_kelvin: 2700-6500}；"
                            "渐变过渡使用 {transition: 秒数}（如 transition:5 表示5秒平滑过渡）；"
                            "空调设温使用 {temperature: 20-30, hvac_mode: 'cool'/'heat'}。"
                        ),
                        "additionalProperties": True,
                    },
                    "reason": {
                        "type": "string",
                        "description": "执行此动作的原因，用于日志和用户通知",
                    },
                    "delay_seconds": {
                        "type": "number",
                        "minimum": 0,
                        "description": "延迟执行秒数，通常为 0",
                    },
                    "is_global": {
                        "type": "boolean",
                        "description": (
                            "跨区联动标记。正常情况填 false；"
                            "当动作设备所在区域与触发传感器区域不同（合法跨区联动）时填 true，"
                            "否则系统安全层会拦截该动作。"
                        ),
                    },
                },
                "required": ["domain", "service", "entity_id"],
            },
            "description": "要执行的动作列表，无需动作时填空数组 []",
        },
        # ── 5B-1: 意图层新增字段 ──────────────────────────────────────────
        "intent": {
            "type": "string",
            "description": (
                "AI 对本次意图的分类标识，如 'arrival_lighting' / 'departure_off' / "
                "'scene_switch' / 'climate_adjust' / 'no_action'。"
                "便于 DecisionCache 按意图匹配缓存。"
            ),
        },
        "intent_label": {
            "type": "string",
            "description": "意图的中文标签，如 '晚间回家开灯' / '离开关灯' / '睡前调暗'",
        },
        "scene_candidate": {
            "type": "string",
            "description": (
                "推荐优先调用的 HA 场景 entity_id（如 scene.bedroom_evening）。"
                "系统将直接调用该场景，比逐设备控制更精准。"
                "User Prompt 中【可用场景】存在匹配时请务必填写；无匹配时填空字符串。"
            ),
        },
        "param_adjustments": {
            "type": "object",
            "description": (
                "在 scene_candidate 执行后，对触发房间灯光的微调参数，"
                "如 {brightness_pct: 70, color_temp_kelvin: 3500}。"
                "无需微调或无 scene_candidate 时填 {}。"
            ),
            "additionalProperties": True,
        },
        "need_confirm": {
            "type": "boolean",
            "description": (
                "true 表示 AI 不确定，请求用户在面板确认后再执行；"
                "false（默认）表示直接自动执行。"
                "置信度 < 55 时建议设为 true。"
            ),
        },
        "reply": {
            "type": "string",
            "description": "语音指令时的口语化回复，非语音场景可填空字符串",
        },
        "speak": {
            "type": "string",
            "description": "TTS 播报内容，无需播报时填空字符串",
        },
    },
    "required": ["scene", "confidence", "actions"],
    "additionalProperties": False,
}

# ── 验证函数 ───────────────────────────────────────────────────────────────────

def validate_decision(raw: dict | None, sys_log_func: Any = None) -> dict | None:
    """
    验证 LLM 返回的决策 JSON 是否符合规范。

    执行以下验证：
      1. 必填字段存在性检查
      2. confidence 范围检查（0-100）
      3. 每个 action 的必填字段检查
      4. domain 白名单检查
      5. 自动修正常见错误格式（宽容模式）

    Args:
        raw: LLM 返回的原始解析字典，None 则返回 None
        sys_log_func: 外部系统日志函数（注入自 coordinator._sys_log）

    Returns:
        验证通过的 dict，或 None（严重格式错误时）
    """
    if not isinstance(raw, dict):
        return None

    # 操作深拷贝，避免修改调用方传入的原始对象（防止副作用）
    raw = copy.deepcopy(raw)

    # 自动修正：scene 不存在时使用默认值
    if "scene" not in raw:
        raw["scene"] = "AI推理"

    # 自动修正：confidence 类型和范围
    try:
        conf = int(raw.get("confidence", 0))
        raw["confidence"] = max(0, min(100, conf))
    except (TypeError, ValueError):
        raw["confidence"] = 0

    # 自动修正：actions 不是列表时初始化为空列表
    if not isinstance(raw.get("actions"), list):
        raw["actions"] = []

    cleaned_actions: list[dict] = []
    for action in raw["actions"]:
        if not isinstance(action, dict):
            _LOGGER.debug("[Schema] 跳过非字典 action: %s", action)
            continue
        if not action.get("domain") or not action.get("service") or not action.get("entity_id"):
            _LOGGER.debug("[Schema] 跳过缺少必填字段的 action: %s", action)
            continue
        if action["domain"] not in _VALID_DOMAINS:
            _msg = f"[Schema] 未知 domain '{action['domain']}'，跳过动作: {action.get('entity_id')}"
            _LOGGER.warning(_msg)
            if sys_log_func:
                sys_log_func("WARN", _msg)
            continue
        # 确保 params 是字典
        if not isinstance(action.get("params"), dict):
            action["params"] = {}
        # 确保 delay_seconds 是数字
        try:
            action["delay_seconds"] = float(action.get("delay_seconds", 0))
        except (TypeError, ValueError):
            action["delay_seconds"] = 0.0
        # 钳位常用 params 字段，防止 AI 输出越界值直接打给 HA 报错
        _p = action["params"]
        if "brightness_pct" in _p:
            try:
                _p["brightness_pct"] = max(1, min(100, int(_p["brightness_pct"])))
            except (TypeError, ValueError):
                del _p["brightness_pct"]
        if "color_temp_kelvin" in _p:
            try:
                _p["color_temp_kelvin"] = max(2000, min(6500, int(_p["color_temp_kelvin"])))
            except (TypeError, ValueError):
                del _p["color_temp_kelvin"]
        if "transition" in _p:
            try:
                _tv = float(_p["transition"])
                _p["transition"] = max(0.0, min(300.0, _tv))
            except (TypeError, ValueError):
                del _p["transition"]
        # 确保 is_global 是布尔值（P1修复：bool("false")==True，需专门处理字符串）
        if "is_global" in action:
            _ig = action["is_global"]
            if isinstance(_ig, str):
                action["is_global"] = _ig.strip().lower() not in ("false", "0", "no", "off", "")
            else:
                action["is_global"] = bool(_ig)
        cleaned_actions.append(action)

    raw["actions"] = cleaned_actions

    # 确保 reply / speak 是字符串
    raw.setdefault("reply", "")
    raw.setdefault("speak", "")
    if not isinstance(raw["reply"], str):
        raw["reply"] = str(raw["reply"])
    if not isinstance(raw["speak"], str):
        raw["speak"] = str(raw["speak"])

    # ── 5B-1: 新字段验证与默认值 ──────────────────────────────────────────────
    # intent / intent_label — 字符串类型
    for _k in ("intent", "intent_label"):
        raw.setdefault(_k, "")
        if not isinstance(raw[_k], str):
            raw[_k] = str(raw[_k])

    # intent 软验证：未知值仅记录 DEBUG，不拒绝（允许 LLM 扩展意图类型）
    _intent_val = raw["intent"].strip().lower()
    if _intent_val and _intent_val not in _KNOWN_INTENTS:
        _LOGGER.debug("[Schema] 未知 intent 值 '%s'，已放行（扩展意图）", raw["intent"])

    # scene_candidate — entity_id 字符串，清理多余空白
    raw.setdefault("scene_candidate", "")
    if not isinstance(raw["scene_candidate"], str):
        raw["scene_candidate"] = ""
    else:
        raw["scene_candidate"] = raw["scene_candidate"].strip()

    # param_adjustments — 仅允许字典，其余类型重置为空
    if not isinstance(raw.get("param_adjustments"), dict):
        raw["param_adjustments"] = {}
    else:
        _p_adj = raw["param_adjustments"]
        # 钳位亮度和色温（与 actions 中的规则保持一致）
        if "brightness_pct" in _p_adj:
            try:
                _p_adj["brightness_pct"] = max(1, min(100, int(_p_adj["brightness_pct"])))
            except (TypeError, ValueError):
                del _p_adj["brightness_pct"]
        if "color_temp_kelvin" in _p_adj:
            try:
                _p_adj["color_temp_kelvin"] = max(2000, min(6500, int(_p_adj["color_temp_kelvin"])))
            except (TypeError, ValueError):
                del _p_adj["color_temp_kelvin"]
        if "transition" in _p_adj:
            try:
                _tv = float(_p_adj["transition"])
                _p_adj["transition"] = max(0.0, min(60.0, _tv))
            except (TypeError, ValueError):
                del _p_adj["transition"]

    # need_confirm — 布尔值，字符串 "false"/"0" 应视为 False
    _nc = raw.get("need_confirm", False)
    if isinstance(_nc, str):
        raw["need_confirm"] = _nc.strip().lower() not in ("false", "0", "no", "off", "")
    else:
        raw["need_confirm"] = bool(_nc)

    return raw
