"""SmartAgent select entities: engine, dev/habit/rule dropdowns."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_DEV_SELECT, ENTITY_ENGINE, ENTITY_HABIT_SELECT, ENTITY_RULE_SELECT
from .coordinator import SmartAgentCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SmartAgentCoordinator = hass.data[DOMAIN][entry.entry_id]
    unique = entry.entry_id
    async_add_entities([
        SmartAgentEngineSelect(coordinator, unique),
        SmartAgentDevSelect(coordinator, unique),
        SmartAgentHabitSelect(coordinator, unique),
        SmartAgentRuleSelect(coordinator, unique),
    ])


class _BaseSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str, key: str, name: str, icon: str, options: list[str]) -> None:
        super().__init__(coordinator)
        self.entity_id = f"select.smart_agent_{key}"
        self._attr_unique_id = f"{unique_id}_{key}"
        self._attr_suggested_object_id = f"smart_agent_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._key = key
        self._attr_options = options
        self._attr_current_option = options[0] if options else None


class SmartAgentEngineSelect(_BaseSelect):
    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        opts = ["本地 Ollama", "云端 API"]
        cur = "本地 Ollama" if coordinator.engine == "local" else "云端 API"
        super().__init__(coordinator, unique_id, ENTITY_ENGINE, "AI 推理引擎", "mdi:chip", opts)
        self._attr_current_option = cur

    @property
    def current_option(self) -> str | None:
        return "本地 Ollama" if self.coordinator.engine == "local" else "云端 API"

    async def async_select_option(self, option: str) -> None:
        self.coordinator.engine = "local" if option == "本地 Ollama" else "online"
        self.async_write_ha_state()


class SmartAgentDevSelect(_BaseSelect):
    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id, ENTITY_DEV_SELECT, "选择设备", "mdi:format-list-bulleted", coordinator.get_dev_options())

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_options = self.coordinator.get_dev_options()
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._attr_current_option or (self.coordinator.get_dev_options()[0] if self.coordinator.get_dev_options() else None)

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()


class SmartAgentHabitSelect(_BaseSelect):
    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id, ENTITY_HABIT_SELECT, "选择画像条目", "mdi:format-list-bulleted", coordinator.get_habit_options())

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_options = self.coordinator.get_habit_options()
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._attr_current_option or (self.coordinator.get_habit_options()[0] if self.coordinator.get_habit_options() else None)

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()


class SmartAgentRuleSelect(_BaseSelect):
    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id, ENTITY_RULE_SELECT, "选择规则条目", "mdi:format-list-bulleted", coordinator.get_rule_options())

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_options = self.coordinator.get_rule_options()
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        return self._attr_current_option or (self.coordinator.get_rule_options()[0] if self.coordinator.get_rule_options() else None)

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
