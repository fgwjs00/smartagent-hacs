"""SmartAgent text entities: status, last_action, CRUD input fields."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENTITY_DEV_DESC,
    ENTITY_DEV_ENTITY,
    ENTITY_HABIT_INPUT,
    ENTITY_LAST_ACTION,
    ENTITY_RULE_INPUT,
    ENTITY_STATUS,
)
from .coordinator import SmartAgentCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SmartAgentCoordinator = hass.data[DOMAIN][entry.entry_id]
    unique = entry.entry_id
    async_add_entities([
        SmartAgentText(coordinator, unique, ENTITY_STATUS, "AI 当前状态", 255, coordinator.status_text, True),
        SmartAgentText(coordinator, unique, ENTITY_LAST_ACTION, "AI 决策细节", 255, coordinator.last_action_text, True),
        SmartAgentText(coordinator, unique, ENTITY_DEV_ENTITY, "设备实体ID", 255, "", False),
        SmartAgentText(coordinator, unique, ENTITY_DEV_DESC, "设备描述（名称|区域|类型|操作）", 255, "", False),
        SmartAgentText(coordinator, unique, ENTITY_HABIT_INPUT, "画像内容", 255, "", False),
        SmartAgentText(coordinator, unique, ENTITY_RULE_INPUT, "规则内容", 255, "", False),
    ])


class SmartAgentText(CoordinatorEntity, TextEntity):
    _attr_has_entity_name = False
    _attr_native_max = 255

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str, key: str, name: str, max_len: int, initial: str, read_only: bool) -> None:
        super().__init__(coordinator)
        self.entity_id = f"text.smart_agent_{key}"
        self._attr_unique_id = f"{unique_id}_{key}"
        self._attr_suggested_object_id = f"smart_agent_{key}"
        self._attr_name = name
        self._attr_native_value = initial
        self._attr_native_max = max_len
        self._key = key
        self._read_only = read_only

    @property
    def native_value(self) -> str:
        max_len = self._attr_native_max or 255
        if self._key == ENTITY_STATUS:
            return (self.coordinator.status_text or "")[:max_len]
        if self._key == ENTITY_LAST_ACTION:
            return (self.coordinator.last_action_text or "")[:max_len]
        return (self._attr_native_value or "")[:max_len]

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._key in (ENTITY_STATUS, ENTITY_LAST_ACTION):
            self.async_write_ha_state()

    async def async_set_value(self, value: str) -> None:
        if self._read_only:
            return
        self._attr_native_value = value[: (self._attr_native_max or 255)]
        self.async_write_ha_state()
