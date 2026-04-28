"""SmartAgent number entities: confidence thresholds."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CONFIDENCE_AUTO,
    CONF_CONFIDENCE_NOTIFY,
    DOMAIN,
    ENTITY_CONFIDENCE_AUTO,
    ENTITY_CONFIDENCE_NOTIFY,
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
        SmartAgentNumber(coordinator, unique, ENTITY_CONFIDENCE_AUTO, "AI 自动执行置信度", 50, 100, 90, "mdi:gauge"),
        SmartAgentNumber(coordinator, unique, ENTITY_CONFIDENCE_NOTIFY, "AI 通知推送置信度", 30, 100, 60, "mdi:bell-badge"),
    ])


class SmartAgentNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = False
    _attr_native_min_value = 50
    _attr_native_max_value = 100
    _attr_native_step = 5.0
    _attr_mode = "slider"

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str, key: str, name: str, min_v: float, max_v: float, initial: float, icon: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"number.smart_agent_{key}"
        self._attr_unique_id = f"{unique_id}_{key}"
        self._attr_suggested_object_id = f"smart_agent_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._key = key
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_value = float(coordinator.confidence_auto if key == ENTITY_CONFIDENCE_AUTO else coordinator.confidence_notify)

    @property
    def native_value(self) -> float:
        if self._key == ENTITY_CONFIDENCE_AUTO:
            return float(self.coordinator.confidence_auto)
        return float(self.coordinator.confidence_notify)

    async def async_set_native_value(self, value: float) -> None:
        v = int(value)
        if self._key == ENTITY_CONFIDENCE_AUTO:
            self.coordinator.confidence_auto = v
        else:
            self.coordinator.confidence_notify = v
        self.async_write_ha_state()
        self.coordinator._skip_next_reload = True
        opts = dict(self.coordinator._entry.options or {})
        opts[CONF_CONFIDENCE_AUTO] = self.coordinator.confidence_auto
        opts[CONF_CONFIDENCE_NOTIFY] = self.coordinator.confidence_notify
        self.hass.config_entries.async_update_entry(self.coordinator._entry, options=opts)
