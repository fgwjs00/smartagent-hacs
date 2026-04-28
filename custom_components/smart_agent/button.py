"""SmartAgent button entities: discover, CRUD, lock."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENTITY_DEV_ADD,
    ENTITY_DEV_DELETE,
    ENTITY_DISCOVER,
    ENTITY_HABIT_ADD,
    ENTITY_HABIT_CANCEL,
    ENTITY_HABIT_CONFIRM,
    ENTITY_HABIT_DELETE,
    ENTITY_HABIT_LOCK,
    ENTITY_RULE_ADD,
    ENTITY_RULE_DELETE,
    ENTITY_RULE_LOCK,
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
        SmartAgentButton(coordinator, unique, ENTITY_DISCOVER, "发现未配置设备", "mdi:magnify-scan", "discover"),
        SmartAgentButton(coordinator, unique, ENTITY_DEV_ADD, "添加/更新设备", "mdi:plus-circle", "dev_add"),
        SmartAgentButton(coordinator, unique, ENTITY_DEV_DELETE, "删除设备", "mdi:delete", "dev_delete"),
        SmartAgentButton(coordinator, unique, ENTITY_HABIT_ADD, "添加/更新画像", "mdi:plus-circle", "habit_add"),
        SmartAgentButton(coordinator, unique, ENTITY_HABIT_DELETE, "删除画像", "mdi:delete", "habit_delete"),
        SmartAgentButton(coordinator, unique, ENTITY_HABIT_LOCK, "锁定/解锁画像", "mdi:lock-outline", "habit_lock"),
        SmartAgentButton(coordinator, unique, ENTITY_RULE_ADD, "添加/更新规则", "mdi:plus-circle", "rule_add"),
        SmartAgentButton(coordinator, unique, ENTITY_RULE_DELETE, "删除规则", "mdi:delete", "rule_delete"),
        SmartAgentButton(coordinator, unique, ENTITY_RULE_LOCK, "锁定/解锁规则", "mdi:shield-lock", "rule_lock"),
        SmartAgentButton(coordinator, unique, ENTITY_HABIT_CONFIRM, "确认执行习惯建议", "mdi:check-circle", "confirm_habit"),
        SmartAgentButton(coordinator, unique, ENTITY_HABIT_CANCEL, "取消习惯建议", "mdi:close-circle", "cancel_habit"),
    ])


class SmartAgentButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str, key: str, name: str, icon: str, action: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"button.smart_agent_{key}"
        self._attr_unique_id = f"{unique_id}_{key}"
        self._attr_suggested_object_id = f"smart_agent_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._action = action

    async def async_press(self) -> None:
        reg = er.async_get(self.hass)
        uid = self.coordinator._entry.entry_id
        dev_entity_id = reg.async_get_entity_id("text", DOMAIN, f"{uid}_dev_entity") or f"text.smart_agent_{uid}_dev_entity"
        dev_desc_id = reg.async_get_entity_id("text", DOMAIN, f"{uid}_dev_desc") or f"text.smart_agent_{uid}_dev_desc"
        habit_input_id = reg.async_get_entity_id("text", DOMAIN, f"{uid}_habit_input") or f"text.smart_agent_{uid}_habit_input"
        rule_input_id = reg.async_get_entity_id("text", DOMAIN, f"{uid}_rule_input") or f"text.smart_agent_{uid}_rule_input"
        dev_select_id = reg.async_get_entity_id("select", DOMAIN, f"{uid}_dev_select") or f"select.smart_agent_{uid}_dev_select"
        habit_select_id = reg.async_get_entity_id("select", DOMAIN, f"{uid}_habit_select") or f"select.smart_agent_{uid}_habit_select"
        rule_select_id = reg.async_get_entity_id("select", DOMAIN, f"{uid}_rule_select") or f"select.smart_agent_{uid}_rule_select"

        def _state(eid: str) -> str:
            s = self.hass.states.get(eid)
            return (s.state or "").strip() if s else ""

        if self._action == "discover":
            await self.coordinator._async_discover_devices()
        elif self._action == "dev_add":
            await self.coordinator.async_dev_add(_state(dev_entity_id), _state(dev_desc_id))
        elif self._action == "dev_delete":
            await self.coordinator.async_dev_delete(_state(dev_select_id))
        elif self._action == "habit_add":
            await self.coordinator.async_habit_add(_state(habit_input_id), _state(habit_select_id))
        elif self._action == "habit_delete":
            await self.coordinator.async_habit_delete(_state(habit_select_id))
        elif self._action == "habit_lock":
            await self.coordinator.async_habit_lock(_state(habit_select_id))
        elif self._action == "rule_add":
            await self.coordinator.async_rule_add(_state(rule_input_id), _state(rule_select_id))
        elif self._action == "rule_delete":
            await self.coordinator.async_rule_delete(_state(rule_select_id))
        elif self._action == "rule_lock":
            await self.coordinator.async_rule_lock(_state(rule_select_id))
        elif self._action == "confirm_habit":
            await self.coordinator.async_confirm_habit()
        elif self._action == "cancel_habit":
            await self.coordinator.async_cancel_habit()
