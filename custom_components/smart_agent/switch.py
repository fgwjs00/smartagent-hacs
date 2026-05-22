"""SmartAgent switches: AI 托管总开关 + 传感器静默 + 静默学习 + 习惯主动询问."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_AI_ENABLED,
    CONF_SENSORS_MUTED,
    CONF_LEARNING_MODE,
    CONF_HABIT_PROACTIVE,
    CONF_FRIGATE_ENABLED,
    CONF_VISION_ENABLED,
    DOMAIN,
    ENTITY_PAUSED,
    ENTITY_SENSOR_MUTE,
    ENTITY_LEARNING_MODE,
    ENTITY_HABIT_PROACTIVE,
    ENTITY_FRIGATE,
    ENTITY_VISION,
)
from .coordinator import SmartAgentCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SmartAgentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SmartAgentPausedSwitch(coordinator, entry.entry_id),
        SmartAgentSensorMuteSwitch(coordinator, entry.entry_id),
        SmartAgentLearningModeSwitch(coordinator, entry.entry_id),
        SmartAgentHabitProactiveSwitch(coordinator, entry.entry_id),
        SmartAgentFrigateSwitch(coordinator, entry.entry_id),
        SmartAgentVisionSwitch(coordinator, entry.entry_id),
    ])


class SmartAgentPausedSwitch(CoordinatorEntity, SwitchEntity):
    """Switch: on = AI enabled, off = paused."""

    _attr_has_entity_name = False
    _attr_name = "AI 智能托管总开关"
    _attr_icon = "mdi:auto-fix"
    _attr_is_on = True

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"switch.smart_agent_{ENTITY_PAUSED}"
        self._attr_unique_id = f"{unique_id}_{ENTITY_PAUSED}"
        self._attr_suggested_object_id = "smart_agent_paused"
        self._attr_is_on = coordinator._enabled

    @callback
    def _handle_coordinator_update(self) -> None:
        pass

    def _persist(self, value: bool) -> None:
        """持久化到 config entry（必须在事件循环中调用）。"""
        self.coordinator._skip_next_reload = True
        opts = dict(self.coordinator._entry.options or {})
        opts[CONF_AI_ENABLED] = value
        self.hass.config_entries.async_update_entry(self.coordinator._entry, options=opts)

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator._enabled = True
        self._attr_is_on = True
        self._persist(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator._enabled = False
        self._attr_is_on = False
        self._persist(False)
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self.coordinator._enabled


class SmartAgentSensorMuteSwitch(CoordinatorEntity, SwitchEntity):
    """Switch: on = 传感器静默（不处理传感器事件）, off = 正常监听."""

    _attr_has_entity_name = False
    _attr_name = "传感器静默开关"
    _attr_icon = "mdi:motion-sensor-off"
    _attr_is_on = False

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"switch.smart_agent_{ENTITY_SENSOR_MUTE}"
        self._attr_unique_id = f"{unique_id}_{ENTITY_SENSOR_MUTE}"
        self._attr_suggested_object_id = f"smart_agent_{ENTITY_SENSOR_MUTE}"
        self._attr_is_on = coordinator._sensors_muted

    @callback
    def _handle_coordinator_update(self) -> None:
        pass

    def _persist(self, value: bool) -> None:
        """持久化到 config entry（必须在事件循环中调用）。"""
        self.coordinator._skip_next_reload = True
        opts = dict(self.coordinator._entry.options or {})
        opts[CONF_SENSORS_MUTED] = value
        self.hass.config_entries.async_update_entry(self.coordinator._entry, options=opts)

    async def async_turn_on(self, **kwargs) -> None:
        """开启传感器静默：所有 binary_sensor / sensor 事件不触发推理."""
        self.coordinator._sensors_muted = True
        self._attr_is_on = True
        self._persist(True)
        self.coordinator._sys_log("INFO", "传感器静默已开启：传感器事件将不触发 AI 推理")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """关闭传感器静默：恢复正常监听."""
        self.coordinator._sensors_muted = False
        self._attr_is_on = False
        self._persist(False)
        self.coordinator._sys_log("INFO", "传感器静默已关闭：恢复正常传感器监听")
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self.coordinator._sensors_muted


class SmartAgentLearningModeSwitch(CoordinatorEntity, SwitchEntity):
    """Switch: on = 静默学习（仅记录事件不执行），off = 正常推理与执行。"""

    _attr_has_entity_name = False
    _attr_name = "静默学习模式"
    _attr_icon = "mdi:school-outline"
    _attr_is_on = False

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"switch.smart_agent_{ENTITY_LEARNING_MODE}"
        self._attr_unique_id = f"{unique_id}_{ENTITY_LEARNING_MODE}"
        self._attr_suggested_object_id = f"smart_agent_{ENTITY_LEARNING_MODE}"
        self._attr_is_on = coordinator._learning_mode

    @callback
    def _handle_coordinator_update(self) -> None:
        pass

    def _persist(self, value: bool) -> None:
        """持久化到 config entry（必须在事件循环中调用）。"""
        self.coordinator._skip_next_reload = True
        opts = dict(self.coordinator._entry.options or {})
        opts[CONF_LEARNING_MODE] = value
        self.hass.config_entries.async_update_entry(self.coordinator._entry, options=opts)

    async def _push_to_addon(self, field: str, value: bool) -> bool:
        """把单个布尔字段反写到 add-on /settings/system；失败时返回 False。"""
        addon_client = getattr(self.coordinator, "_addon_client", None)
        if addon_client is None:
            return False
        try:
            result = await addon_client.post_system_settings({field: value})
        except Exception as exc:
            self.coordinator._sys_log("WARNING", f"[AddonSettings] {field} 写入 add-on 失败: {exc}")
            return False
        if isinstance(result, dict) and int(result.get("status_code") or 200) >= 400:
            self.coordinator._sys_log(
                "WARNING",
                f"[AddonSettings] {field} 写入 add-on 状态码异常: {result.get('status_code')}",
            )
            return False
        return True

    async def async_turn_on(self, **kwargs) -> None:
        # add-on first：先反写 add-on，让真源更新；HA 内存随后翻转
        await self._push_to_addon("learning_mode", True)
        self.coordinator._learning_mode = True
        self._attr_is_on = True
        self._persist(True)
        self.coordinator._sys_log("INFO", "静默学习模式已开启：仅记录设备事件，不执行推理与动作")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._push_to_addon("learning_mode", False)
        self.coordinator._learning_mode = False
        self._attr_is_on = False
        self._persist(False)
        self.coordinator._sys_log("INFO", "静默学习模式已关闭：恢复正常推理与执行")
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self.coordinator._learning_mode


class SmartAgentHabitProactiveSwitch(CoordinatorEntity, SwitchEntity):
    """Switch: on = 根据行为习惯主动询问是否执行，off = 不主动询问。"""

    _attr_has_entity_name = False
    _attr_name = "习惯主动询问"
    _attr_icon = "mdi:head-heart-outline"
    _attr_is_on = False

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"switch.smart_agent_{ENTITY_HABIT_PROACTIVE}"
        self._attr_unique_id = f"{unique_id}_{ENTITY_HABIT_PROACTIVE}"
        self._attr_suggested_object_id = f"smart_agent_{ENTITY_HABIT_PROACTIVE}"
        self._attr_is_on = coordinator._habit_proactive

    @callback
    def _handle_coordinator_update(self) -> None:
        pass

    def _persist(self, value: bool) -> None:
        """持久化到 config entry（必须在事件循环中调用）。"""
        self.coordinator._skip_next_reload = True
        opts = dict(self.coordinator._entry.options or {})
        opts[CONF_HABIT_PROACTIVE] = value
        self.hass.config_entries.async_update_entry(self.coordinator._entry, options=opts)

    async def _push_to_addon(self, field: str, value: bool) -> bool:
        addon_client = getattr(self.coordinator, "_addon_client", None)
        if addon_client is None:
            return False
        try:
            result = await addon_client.post_system_settings({field: value})
        except Exception as exc:
            self.coordinator._sys_log("WARNING", f"[AddonSettings] {field} 写入 add-on 失败: {exc}")
            return False
        if isinstance(result, dict) and int(result.get("status_code") or 200) >= 400:
            self.coordinator._sys_log(
                "WARNING",
                f"[AddonSettings] {field} 写入 add-on 状态码异常: {result.get('status_code')}",
            )
            return False
        return True

    async def async_turn_on(self, **kwargs) -> None:
        await self._push_to_addon("habit_proactive", True)
        self.coordinator._habit_proactive = True
        self._attr_is_on = True
        self._persist(True)
        self.coordinator._sys_log("INFO", "习惯主动询问已开启：将根据历史行为在合适时间询问是否执行")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._push_to_addon("habit_proactive", False)
        self.coordinator._habit_proactive = False
        self._attr_is_on = False
        self._persist(False)
        self.coordinator._sys_log("INFO", "习惯主动询问已关闭")
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self.coordinator._habit_proactive


class SmartAgentFrigateSwitch(CoordinatorEntity, SwitchEntity):
    """Switch: on = 启用 Frigate NVR 视觉感知集成，off = 不使用 Frigate（默认）。"""

    _attr_has_entity_name = False
    _attr_name = "Frigate NVR 视觉感知"
    _attr_icon = "mdi:cctv"
    _attr_is_on = False

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"switch.smart_agent_{ENTITY_FRIGATE}"
        self._attr_unique_id = f"{unique_id}_{ENTITY_FRIGATE}"
        self._attr_suggested_object_id = f"smart_agent_{ENTITY_FRIGATE}"
        self._attr_is_on = coordinator._frigate_enabled

    @callback
    def _handle_coordinator_update(self) -> None:
        pass

    def _persist(self, value: bool) -> None:
        """持久化到 config entry（必须在事件循环中调用）。"""
        self.coordinator._skip_next_reload = True
        opts = dict(self.coordinator._entry.options or {})
        opts[CONF_FRIGATE_ENABLED] = value
        self.hass.config_entries.async_update_entry(self.coordinator._entry, options=opts)

    async def _push_to_addon(self, field: str, value: bool) -> bool:
        addon_client = getattr(self.coordinator, "_addon_client", None)
        if addon_client is None:
            return False
        try:
            result = await addon_client.post_system_settings({field: value})
        except Exception as exc:
            self.coordinator._sys_log("WARNING", f"[AddonSettings] {field} 写入 add-on 失败: {exc}")
            return False
        if isinstance(result, dict) and int(result.get("status_code") or 200) >= 400:
            self.coordinator._sys_log(
                "WARNING",
                f"[AddonSettings] {field} 写入 add-on 状态码异常: {result.get('status_code')}",
            )
            return False
        return True

    async def async_turn_on(self, **kwargs) -> None:
        await self._push_to_addon("frigate_enabled", True)
        self.coordinator._frigate_enabled = True
        self._attr_is_on = True
        self._persist(True)
        self.coordinator._sys_log(
            "INFO",
            "Frigate NVR 视觉感知已启用：将读取 person_count 传感器并注入 AI 决策上下文"
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._push_to_addon("frigate_enabled", False)
        self.coordinator._frigate_enabled = False
        self._attr_is_on = False
        self._persist(False)
        self.coordinator._sys_log("INFO", "Frigate NVR 视觉感知已关闭")
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self.coordinator._frigate_enabled


class SmartAgentVisionSwitch(CoordinatorEntity, SwitchEntity):
    """Switch: on = 启用 LLMVision 视觉增强分析, off = 禁用（默认）。"""

    _attr_has_entity_name = False
    _attr_name = "LLMVision 视觉增强开关"
    _attr_icon = "mdi:eye-check-outline"
    _attr_is_on = False

    def __init__(self, coordinator: SmartAgentCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self.entity_id = f"switch.smart_agent_{ENTITY_VISION}"
        self._attr_unique_id = f"{unique_id}_{ENTITY_VISION}"
        self._attr_suggested_object_id = f"smart_agent_{ENTITY_VISION}"
        self._attr_is_on = coordinator._vision_enabled

    @callback
    def _handle_coordinator_update(self) -> None:
        pass

    def _persist(self, value: bool) -> None:
        """持久化到 config entry。"""
        self.coordinator._skip_next_reload = True
        opts = dict(self.coordinator._entry.options or {})
        opts[CONF_VISION_ENABLED] = value
        self.hass.config_entries.async_update_entry(self.coordinator._entry, options=opts)

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator._vision_enabled = True
        self._attr_is_on = True
        self._persist(True)
        self.coordinator._sys_log("INFO", "LLMVision 视觉增强已启用：将对关键事件进行多模态分析")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator._vision_enabled = False
        self._attr_is_on = False
        self._persist(False)
        self.coordinator._sys_log("INFO", "LLMVision 视觉增强已关闭")
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self.coordinator._vision_enabled
