"""SmartAgent sensor entities: status and config."""
from __future__ import annotations

import json

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_CONFIG_SENSOR, ENTITY_STATUS
from .coordinator import SmartAgentCoordinator

# HA 16384 字节上限，留 2KB 安全余量
_ATTR_SIZE_LIMIT = 14000

# 超限时按优先级删减的字段（排前面的先删）
_STATUS_DROP_ORDER = [
    "sys_log",          # HTML 最大，最先删
    "terminal_log",     # 次大
    "action_history",   # 结构化列表
    "frigate_events",   # Frigate 事件
    "recent_ai_actions",# 纠错列表
    "last_correction",  # 单行文本
]

_CONFIG_DROP_ORDER = [
    # v4.8.25 架构升级：大列表已迁移到 WebSocket API，sensor 属性只保留小型统计值。
    # 以下字段为旧版遗留兼容项，或为未来可能重新写入的备用项，按体积优先丢弃顺序保留。
    "showroom_scenes",      # 展厅场景列表（轻量，但非必须）
    "priority_guards",      # 防护规则摘要
    "action_quality",       # 动作质量统计
]


def _trim_attrs(attrs: dict, drop_order: list[str]) -> dict:
    """Trim attribute dict to fit under HA 16KB limit, dropping least important fields first."""
    for field in drop_order:
        try:
            size = len(json.dumps(attrs, ensure_ascii=False, default=str).encode("utf-8"))
        except Exception:
            break
        if size <= _ATTR_SIZE_LIMIT:
            break
        if field in attrs:
            attrs.pop(field)
    return attrs


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartAgent sensors."""
    coordinator: SmartAgentCoordinator = hass.data[DOMAIN][entry.entry_id]
    unique = entry.entry_id

    async_add_entities([
        SmartAgentStatusSensor(coordinator, unique),
        SmartAgentConfigSensor(coordinator, unique),
    ])


class SmartAgentStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for current status and terminal log."""

    _attr_has_entity_name = False
    _attr_name = "AI 实时场景"
    _attr_icon = "mdi:robot"
    _attr_native_value = ""

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"sensor.smart_agent_{ENTITY_STATUS}"
        self._attr_unique_id = f"{unique_id}_{ENTITY_STATUS}"
        self._attr_suggested_object_id = "smart_agent_status"
        self._attr_native_value = coordinator.status_text
        self._attr_extra_state_attributes = _trim_attrs({
            "full_text": coordinator.status_text,
            "terminal_log": coordinator.terminal_log_html,
            "sys_log": getattr(coordinator, "sys_log_html_short", coordinator.sys_log_html),
            "action_history": getattr(coordinator, "_action_history_structured", [])[:10],
            "last_correction": getattr(coordinator, "last_correction_text", ""),
            "recent_ai_actions": [
                {"entity_id": k, "state": v.get("state"), "time": v.get("time"), "scene": (v.get("scene") or "")[:60]}
                for k, v in list(getattr(coordinator, "_last_ai_actions", {}).items())[:10]
            ],
            "critical_frigate_event": getattr(coordinator, "_critical_frigate_event", None),
            "frigate_events": getattr(coordinator, "get_recent_frigate_events", lambda: [])()[:5],
            "voice_status": getattr(coordinator, "_voice_status", "idle"),
            "last_stt": (getattr(coordinator, "_last_stt_text", "") or "")[:100],
        }, _STATUS_DROP_ORDER)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.coordinator.status_text[:30] if self.coordinator.status_text else ""
        self._attr_extra_state_attributes = _trim_attrs({
            "full_text": self.coordinator.status_text,
            "terminal_log": self.coordinator.terminal_log_html,
            "sys_log": getattr(self.coordinator, "sys_log_html_short", self.coordinator.sys_log_html),
            "action_history": getattr(self.coordinator, "_action_history_structured", [])[:10],
            "last_correction": getattr(self.coordinator, "last_correction_text", ""),
            "recent_ai_actions": [
                {"entity_id": k, "state": v.get("state"), "time": v.get("time"), "scene": (v.get("scene") or "")[:60]}
                for k, v in list(getattr(self.coordinator, "_last_ai_actions", {}).items())[:10]
            ],
            "critical_frigate_event": getattr(self.coordinator, "_critical_frigate_event", None),
            "frigate_events": getattr(self.coordinator, "get_recent_frigate_events", lambda: [])()[:5],
            "voice_status": getattr(self.coordinator, "_voice_status", "idle"),
            "last_stt": (getattr(self.coordinator, "_last_stt_text", "") or "")[:100],
        }, _STATUS_DROP_ORDER)
        self.async_write_ha_state()


class SmartAgentConfigSensor(CoordinatorEntity, SensorEntity):
    """Sensor for config overview (devices, habits, rules)."""

    _attr_has_entity_name = False
    _attr_name = "AI Agent 系统内核"
    _attr_icon = "mdi:cog-box"
    _attr_native_value = "运行中"

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"sensor.smart_agent_{ENTITY_CONFIG_SENSOR}"
        self._attr_unique_id = f"{unique_id}_{ENTITY_CONFIG_SENSOR}"
        self._attr_suggested_object_id = "smart_agent_config"
        attrs = coordinator.get_config_attributes()
        self._attr_extra_state_attributes = _trim_attrs(
            {**attrs, "friendly_name": "AI Agent 系统内核", "icon": "mdi:cog-box"},
            _CONFIG_DROP_ORDER,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_extra_state_attributes = _trim_attrs(
            {**self.coordinator.get_config_attributes(), "friendly_name": "AI Agent 系统内核", "icon": "mdi:cog-box"},
            _CONFIG_DROP_ORDER,
        )
        self.async_write_ha_state()
