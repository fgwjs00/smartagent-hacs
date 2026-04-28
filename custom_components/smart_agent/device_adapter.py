"""
DeviceAdapter — Phase A：设备抽象层（AI Core 可测试化）。

通过抽象接口隔离 AI Core 与 HA 具体 API，允许在无 HA 环境下进行单元测试。
当前唯一实现：HAAdapter（通过 hass.services.async_call）。

Phase A 目标：功能零变化，仅为可测试性。
Phase D 目标（6-12 月）：SmartAgent Hub 产品化时，可替换 HAAdapter 为其他实现。

战略规划参考：docs/HomeOS战略规划.md § 四、设备层策略
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceState:
    """设备状态快照。

    :param entity_id: 实体 ID
    :param state:     状态字符串（如 'on', 'off', '23.5'）
    :param attributes: 状态属性字典（亮度、色温、温度等）
    """

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)


class DeviceAdapter(ABC):
    """AI Core 通过此接口调用设备，不直接依赖 HA 具体 API。

    好处：AI Core 逻辑可在无 HA 环境下做单元测试。
    当前唯一实现：HAAdapter。

    SmartAgent Hub 阶段（Phase D）若需要支持多种底层协议，
    只需新增 DeviceAdapter 实现，AI Core 代码无需改动。
    """

    @abstractmethod
    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """调用设备服务。

        :param domain:    域名（如 'light', 'switch', 'climate'）
        :param service:   服务名（如 'turn_on', 'turn_off', 'set_temperature'）
        :param entity_id: 实体 ID
        :param params:    附加参数（如亮度、色温、目标温度）
        :return: 调用成功返回 True，失败返回 False
        """

    @abstractmethod
    async def get_state(self, entity_id: str) -> DeviceState | None:
        """获取单台设备的当前状态。

        :param entity_id: 实体 ID
        :return: DeviceState 快照，或 None（设备不存在）
        """

    @abstractmethod
    async def get_states_for_domain(self, domain: str) -> list[DeviceState]:
        """获取某个域的全部设备状态。

        :param domain: 域名（如 'light', 'binary_sensor'）
        :return: DeviceState 列表
        """


class HAAdapter(DeviceAdapter):
    """DeviceAdapter 的 HA 实现，通过 hass.services.async_call 控制设备。

    这是当前唯一的生产实现。所有设备控制最终都经过此类调用 HA 的服务总线。
    """

    def __init__(self, hass: "HomeAssistant") -> None:
        """
        :param hass: HomeAssistant 实例
        """
        self._hass = hass

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """通过 HA 服务总线控制设备。"""
        service_data: dict[str, Any] = {"entity_id": entity_id}
        if params:
            service_data.update(params)
        try:
            await self._hass.services.async_call(
                domain, service, service_data, blocking=True
            )
            return True
        except Exception as exc:
            _LOGGER.warning(
                "[HAAdapter] call_service 失败: %s.%s(%s): %s",
                domain,
                service,
                entity_id,
                exc,
            )
            return False

    async def get_state(self, entity_id: str) -> DeviceState | None:
        """获取 HA 中的设备状态。"""
        state = self._hass.states.get(entity_id)
        if state is None:
            return None
        return DeviceState(
            entity_id=entity_id,
            state=state.state,
            attributes=dict(state.attributes),
        )

    async def get_states_for_domain(self, domain: str) -> list[DeviceState]:
        """获取 HA 中某个域的全部设备状态。"""
        return [
            DeviceState(
                entity_id=s.entity_id,
                state=s.state,
                attributes=dict(s.attributes),
            )
            for s in self._hass.states.async_all(domain)
        ]
