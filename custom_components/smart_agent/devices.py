"""
DevicesMixin — 设备管理层。
负责：设备发现与批量导入、CRUD、区域管理、管辖域配置、
      习惯/规则的 CRUD、行为规律删除。
"""
from __future__ import annotations

import logging
import threading
import json as _json

from .action_mapping import entities_to_actions, normalize_raw_actions
from typing import Any
from .const import (
    DEVICE_CAP_KEY_CAN_BLOCK_TURN_OFF,
    DEVICE_CAP_KEY_CAN_CONFIRM_LEAVE,
    DEVICE_CAP_KEY_CAN_LOCALIZE_ZONE,
    DEVICE_CAP_KEY_CAN_TRIGGER_ENTER,
    DEVICE_CAP_KEY_COVERAGE_SPACES,
    DEVICE_CAP_KEY_ENERGY_LEVEL,
    DEVICE_CAP_KEY_RISK_LEVEL,
    DEVICE_CAP_KEY_SHARED_FIXTURE,
    DEVICE_CAP_KEY_SLEEP_SAFE,
)

from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

_LOGGER = logging.getLogger(__name__)

# 用于设备自动发现时的域名标签与说明
DOMAIN_LABELS = {
    "light": ("灯", "turn_on/turn_off，支持 brightness_pct(0-100)"),
    "switch": ("开关", "turn_on/turn_off"),
    "binary_sensor": ("传感器", "只读，on=触发 off=正常"),
    "sensor": ("传感器", "只读，数值类"),
    "climate": ("空调", "turn_on/turn_off/set_temperature/set_hvac_mode"),
    "cover": ("窗帘", "open_cover/close_cover/set_cover_position(0-100)"),
    "media_player": ("媒体", "turn_on/turn_off/volume_set/media_pause"),
    "device_tracker": ("位置", "home=在家 not_home=不在家"),
    "fan": ("风扇", "turn_on/turn_off/set_percentage"),
}

_ROLLBACK_OFF_STATES = {"", "off", "unavailable", "unknown", "none"}


def _find_ha_area_by_id_or_name(area_reg: Any, target: str) -> Any | None:
    target_norm = str(target or "").strip()
    if not target_norm:
        return None
    getter = getattr(area_reg, "async_get_area", None)
    if callable(getter):
        try:
            area = getter(target_norm)
            if area is not None:
                return area
        except Exception:
            pass

    raw_areas = getattr(area_reg, "areas", None)
    values = getattr(raw_areas, "values", None)
    try:
        area_items = values() if callable(values) else ()
    except Exception:
        area_items = ()
    folded = target_norm.casefold()
    for area in area_items:
        area_id = str(getattr(area, "id", "") or getattr(area, "area_id", "") or "").strip()
        name = str(getattr(area, "name", "") or "").strip()
        if target_norm in {area_id, name} or folded in {area_id.casefold(), name.casefold()}:
            return area
    return None


def _rollback_service_for_snapshot_state(domain: str, state: Any) -> str:
    state_norm = str(state or "").strip().lower()
    if domain == "cover":
        return "open_cover" if state_norm == "open" else "close_cover"
    if domain == "climate":
        return "turn_off" if state_norm in _ROLLBACK_OFF_STATES else "turn_on"
    return "turn_on" if state_norm in {"on", "open"} else "turn_off"


class DevicesMixin:
    """Mixin: 设备管理 — 发现/CRUD/区域/管辖域/习惯/规则。"""

    # ── 工具方法 ──────────────────────────────────────────────────────────────

    def _ha_db_now_text(self) -> str:
        """Delegate HA-local DB timestamp generation for standalone mixin use."""
        from .database import DatabaseMixin

        return DatabaseMixin._ha_db_now_text(self)

    def get_device_name(self, entity_id: str) -> str:
        """Return device friendly name with room prefix if available, fallback to entity_id."""
        info = self.device_info.get(entity_id, {})
        name = info.get("name", entity_id)
        room = info.get("room", "")
        return f"[{room}] {name}" if room else name

    def get_dev_options(self) -> list[str]:
        if not self.device_info:
            return ["(无设备)"]
        return [f"{eid} | {info['name']}" for eid, info in sorted(self.device_info.items())]

    def get_habit_options(self) -> list[str]:
        if not self._habits:
            return ["(无)"]
        return [self._habit_display(c, lk)[:255] for c, lk in self._habits[:100]]

    def get_rule_options(self) -> list[str]:
        if not self._rules:
            return ["(无)"]
        return [self._rule_display(c, lk)[:255] for c, lk in self._rules[:100]]

    def _get_entity_registry_metadata(self, entity_id: str) -> dict[str, str]:
        """Return stable HA registry identifiers for a managed entity."""
        eid = str(entity_id or "").strip()
        if not eid:
            return {}
        try:
            ent_reg = er.async_get(self.hass)
            entry = ent_reg.async_get(eid)
        except Exception as exc:
            _LOGGER.debug("[Devices] entity registry metadata unavailable for %s: %s", eid, exc)
            return {}
        if not entry:
            return {}
        return {
            "ha_unique_id": str(getattr(entry, "unique_id", "") or ""),
            "ha_device_id": str(getattr(entry, "device_id", "") or ""),
        }

    def _get_entity_area(self, entity_id: str) -> str:
        """Look up the area name for an entity via HA's entity/device/area registries."""
        try:
            ent_reg = er.async_get(self.hass)
            entry = ent_reg.async_get(entity_id)
            if not entry:
                return ""
            area_id = entry.area_id
            if not area_id and entry.device_id:
                dev_reg = dr.async_get(self.hass)
                device = dev_reg.async_get(entry.device_id)
                if device:
                    area_id = device.area_id
            if area_id:
                area_reg = ar.async_get(self.hass)
                area = area_reg.async_get_area(area_id)
                if area:
                    return area.name
        except Exception:
            pass
        return ""

    def get_device_capability(self, entity_id: str) -> dict[str, Any]:
        """返回单设备能力快照（Wave 6 只读语义，默认值保持保守）。"""
        info = dict(self.device_info.get(entity_id, {}) or {})
        room = (info.get("room") or "").strip()
        space_id = (info.get("space_id") or room).strip()

        raw_spaces = info.get(DEVICE_CAP_KEY_COVERAGE_SPACES)
        coverage_spaces: list[str] = []
        if isinstance(raw_spaces, (list, tuple, set)):
            for item in raw_spaces:
                s = str(item).strip()
                if s and s not in coverage_spaces:
                    coverage_spaces.append(s)
        elif space_id:
            coverage_spaces = [space_id]

        explicit_truthy = {True, 1, "1", "true", "yes", "on", "explicit"}
        explicit_falsey = {False, 0, "0", "false", "no", "off"}

        def _explicit_bool(value: Any) -> bool | None:
            if isinstance(value, bool):
                return value
            if isinstance(value, int) and value in (0, 1):
                return bool(value)
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in explicit_truthy:
                    return True
                if normalized in explicit_falsey:
                    return False
            return None

        raw_shared = info.get(DEVICE_CAP_KEY_SHARED_FIXTURE)
        shared_fixture = _explicit_bool(raw_shared) is True

        disturbance_level = str(info.get("disturbance_level") or "").lower()
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        sensor_type = str(info.get("sensor_type") or "").lower()

        sleep_safe = _explicit_bool(info.get(DEVICE_CAP_KEY_SLEEP_SAFE))

        raw_risk_level = str(info.get(DEVICE_CAP_KEY_RISK_LEVEL) or "").strip().lower()
        risk_level = raw_risk_level if raw_risk_level in {"safe", "low", "medium", "high", "critical"} else None

        raw_energy_level = str(info.get(DEVICE_CAP_KEY_ENERGY_LEVEL) or "").lower()
        if raw_energy_level in {"low", "medium", "high"}:
            energy_level = raw_energy_level
        elif domain in {"climate", "cover", "media_player"}:
            energy_level = "high"
        elif domain in {"fan", "light", "switch"}:
            energy_level = "medium"
        else:
            energy_level = "low"

        raw_can_trigger_enter = info.get(DEVICE_CAP_KEY_CAN_TRIGGER_ENTER)
        if isinstance(raw_can_trigger_enter, bool):
            can_trigger_enter = raw_can_trigger_enter
        else:
            can_trigger_enter = sensor_type in {"pir", "mmwave", "frigate"}

        raw_can_confirm_leave = info.get(DEVICE_CAP_KEY_CAN_CONFIRM_LEAVE)
        if isinstance(raw_can_confirm_leave, bool):
            can_confirm_leave = raw_can_confirm_leave
        else:
            can_confirm_leave = sensor_type in {"mmwave", "frigate"}

        can_block_turn_off = _explicit_bool(info.get(DEVICE_CAP_KEY_CAN_BLOCK_TURN_OFF))

        raw_can_localize_zone = info.get(DEVICE_CAP_KEY_CAN_LOCALIZE_ZONE)
        if isinstance(raw_can_localize_zone, bool):
            can_localize_zone = raw_can_localize_zone
        else:
            can_localize_zone = sensor_type in {"frigate", "mmwave"}

        domain_capabilities = {
            "light": "lighting",
            "switch": "switch",
            "button": "scene",
            "input_button": "scene",
            "scene": "scene",
            "script": "scene",
            "binary_sensor": "sensor",
            "sensor": "sensor",
            "climate": "climate",
            "cover": "cover",
            "fan": "fan",
            "media_player": "media",
            "alarm_control_panel": "security",
            "lock": "security",
            "camera": "security",
            "vacuum": "vacuum",
            "humidifier": "appliance",
            "water_heater": "appliance",
        }
        supported_capabilities = set(domain_capabilities.values()) | {"unknown"}
        type_capability = str(info.get("type") or "").strip().lower()
        if type_capability not in supported_capabilities:
            type_capability = ""
        raw_roles = info.get("roles") or info.get("role") or info.get("fixture_roles")
        roles: list[str] = []
        if isinstance(raw_roles, str):
            roles = [raw_roles] if raw_roles else []
        elif isinstance(raw_roles, (list, tuple, set)):
            roles = [str(item).strip() for item in raw_roles if str(item).strip()]
        if shared_fixture and "shared" not in roles:
            roles.append("shared")
        raw_services = info.get("supported_services") or info.get("ops")
        if isinstance(raw_services, str):
            supported_services = [raw_services] if raw_services else []
        elif isinstance(raw_services, (list, tuple, set)):
            supported_services = [str(item).strip() for item in raw_services if str(item).strip()]
        else:
            supported_services = []
        capability_name = str(
            info.get("capability")
            or info.get("device_class")
            or type_capability
            or domain_capabilities.get(domain)
            or domain
            or "unknown"
        ).strip().lower()

        capability = {
            "entity_id": entity_id,
            "domain": domain,
            "capability": capability_name,
            "room": room,
            "space_id": space_id,
            "control_mode": info.get("control_mode", "shared"),
            "sensor_type": info.get("sensor_type", ""),
            "role": info.get("role", ""),
            "roles": roles,
            "supported_services": supported_services,
            "control_zone": info.get("control_zone", space_id),
            "disturbance_level": info.get("disturbance_level", ""),
            DEVICE_CAP_KEY_COVERAGE_SPACES: coverage_spaces,
            "coverage_space_ids": list(coverage_spaces),
            DEVICE_CAP_KEY_SHARED_FIXTURE: bool(shared_fixture),
            "shared_space_ids": list(coverage_spaces) if shared_fixture else [],
            DEVICE_CAP_KEY_ENERGY_LEVEL: energy_level,
            DEVICE_CAP_KEY_CAN_TRIGGER_ENTER: bool(can_trigger_enter),
            DEVICE_CAP_KEY_CAN_CONFIRM_LEAVE: bool(can_confirm_leave),
            DEVICE_CAP_KEY_CAN_LOCALIZE_ZONE: bool(can_localize_zone),
        }
        if sleep_safe is not None:
            capability[DEVICE_CAP_KEY_SLEEP_SAFE] = bool(sleep_safe)
        if risk_level is not None:
            capability[DEVICE_CAP_KEY_RISK_LEVEL] = risk_level
        if can_block_turn_off is not None:
            capability[DEVICE_CAP_KEY_CAN_BLOCK_TURN_OFF] = bool(can_block_turn_off)
        return capability

    def get_device_capability_snapshot(self) -> dict[str, dict[str, Any]]:
        """返回当前所有托管设备的能力快照（仅内存态）。"""
        return {
            eid: self.get_device_capability(eid)
            for eid in self.device_info.keys()
        }

    # ── 设备自动发现 ──────────────────────────────────────────────────────────

    @staticmethod
    def _is_frigate_control_entity(eid: str) -> bool:
        """
        精确判断是否为 Frigate 摄像头控制实体（switch/select），应跳过 AI 托管。

        Frigate 摄像头控制实体命名规律固定为：
          {domain}.cam_{8位hash}_{suffix}
        例如：switch.cam_d5fe7a4f_detect、switch.cam_d5fe7a4f_motion

        普通人体传感器（如 binary_sensor.office_motion）不应被过滤，
        因此不能用简单的 `_motion in eid` 子串匹配。
        """
        from .const import FRIGATE_CAM_ID_PREFIX, FRIGATE_CONTROL_SUFFIXES
        # object_id 是点后的部分（如 cam_d5fe7a4f_detect）
        object_id = eid.split(".", 1)[-1] if "." in eid else eid
        if not object_id.startswith(FRIGATE_CAM_ID_PREFIX):
            return False
        return any(object_id.endswith(suffix) for suffix in FRIGATE_CONTROL_SUFFIXES)

    async def _async_discover_devices(self) -> list[dict]:
        """Scan HA states to build a candidate device list (for batch-add UI)."""
        from .const import SKIP_KEYWORDS, SKIP_NAME_KEYWORDS, TARGET_DOMAINS
        candidates = []
        for domain in TARGET_DOMAINS:
            for state in self.hass.states.async_all(domain):
                eid = state.entity_id
                if eid in self.device_info:
                    continue
                if any(kw in eid for kw in SKIP_KEYWORDS):
                    continue
                if self._is_frigate_control_entity(eid):
                    continue
                name = state.attributes.get("friendly_name", "")
                if not name or any(kw in name for kw in SKIP_NAME_KEYWORDS):
                    continue
                domain_label, ops = DOMAIN_LABELS.get(domain, (domain, ""))
                area_name = self._get_entity_area(eid) or "未知区域"
                candidates.append({
                    "entity_id": eid, "name": name, "domain": domain,
                    "domain_label": domain_label, "area": area_name, "ops": ops,
                })
        self._sys_log("INFO", f"[发现] 扫描到 {len(candidates)} 个候选设备（未录入）")
        self.async_set_updated_data({})
        return candidates

    async def async_batch_add_devices(self, selected_ids: list[str]) -> int:
        """Add multiple devices from the discovery results to device_info and DB."""
        from .const import SKIP_KEYWORDS, SKIP_NAME_KEYWORDS, TARGET_DOMAINS
        count = 0
        now = self._ha_db_now_text()
        for domain in TARGET_DOMAINS:
            for state in self.hass.states.async_all(domain):
                eid = state.entity_id
                if eid not in selected_ids:
                    continue
                if eid in self.device_info:
                    continue
                if any(kw in eid for kw in SKIP_KEYWORDS):
                    continue
                if self._is_frigate_control_entity(eid):
                    continue
                name = state.attributes.get("friendly_name", "")
                if not name or any(kw in name for kw in SKIP_NAME_KEYWORDS):
                    continue
                label, ops = DOMAIN_LABELS.get(domain, (domain, ""))
                area_name = self._get_entity_area(eid) or "待填写区域"
                
                # 推断传感器类型 (PIR/mmWave)
                s_type = ""
                if domain == "binary_sensor":
                    eid_low = eid.lower()
                    name_low = name.lower()
                    if any(kw in eid_low or kw in name_low for kw in ("pir", "motion", "移动", "红外")):
                        s_type = "pir"
                    elif any(kw in eid_low or kw in name_low for kw in ("radar", "mmwave", "雷达", "presence", "存在")):
                        s_type = "mmwave"

                registry_meta = self._get_entity_registry_metadata(eid)
                info = {
                    "name": name,
                    "room": area_name,
                    "type": label,
                    "ops": ops,
                    "control_mode": "shared",
                    "sensor_type": s_type,
                    **registry_meta,
                }
                _ok = await self._async_db_exec(
                    "INSERT OR IGNORE INTO devices (entity_id, name, area, type, ops, control_mode, sensor_type, ha_unique_id, ha_device_id, created, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        eid,
                        name,
                        area_name,
                        label,
                        ops,
                        "shared",
                        s_type,
                        registry_meta.get("ha_unique_id", ""),
                        registry_meta.get("ha_device_id", ""),
                        now,
                        now,
                    ),
                )
                if not _ok:
                    self._sys_log("WARN", f"[批量添加] 写入失败，跳过设备: {eid}")
                    continue
                self.device_info[eid] = info
                count += 1
        if count:
            self._refresh_listeners()
            self._sys_log("INFO", f"[批量添加] 成功添加 {count} 个设备")
            self.async_set_updated_data({})
        return count

    # ── 设备 CRUD（服务调用入口）─────────────────────────────────────────────

    async def async_svc_add_device(self, entity_id: str, description: str) -> None:
        """Service handler: add/update single device (pipe-separated description string)."""
        await self.async_dev_add(entity_id, description)

    async def async_svc_delete_device(self, entity_id: str) -> None:
        """Service handler: delete device by entity_id."""
        if entity_id in self.device_info:
            name = self.device_info[entity_id]["name"]
            _ok = await self._async_db_exec("DELETE FROM devices WHERE entity_id=?", (entity_id,))
            if not _ok:
                self._sys_log("WARN", f"[设备删除] 写入失败，未删除: {entity_id}")
                return
            del self.device_info[entity_id]
            self._refresh_listeners()
            self._sys_log("INFO", f"设备已删除: {name} ({entity_id})")
            await self._async_update_status("设备管理", f"删除设备: {name}")
            self.async_set_updated_data({})

    async def async_svc_update_device(self, entity_id: str, name: str = "", room: str = "",
                                      dev_type: str = "", ops: str = "", sensor_type: str = "",
                                      capability: str = "") -> None:
        """Service handler: update device fields."""
        if entity_id not in self.device_info:
            return
        current = self.device_info[entity_id]
        info = dict(current)
        if name:
            info["name"] = name
        if room:
            info["room"] = room
        if dev_type:
            info["type"] = dev_type
        if ops:
            info["ops"] = ops
        if sensor_type:
            info["sensor_type"] = sensor_type
        normalized_capability = str(capability or "").strip().lower()
        if normalized_capability:
            info["capability"] = normalized_capability
            info["type"] = normalized_capability

        now = self._ha_db_now_text()
        _ok = await self._async_db_exec(
            "UPDATE devices SET name=?, area=?, type=?, ops=?, sensor_type=?, updated=? WHERE entity_id=?",
            (info["name"], info["room"], info["type"], info["ops"], info.get("sensor_type", ""), now, entity_id),
        )
        if not _ok:
            self._sys_log("WARN", f"[设备更新] 写入失败，未更新内存态: {entity_id}")
            return
        self.device_info[entity_id] = info
        if room:
            try:
                sync_result = await self.async_sync_device_room_to_ha(entity_id, info["room"])
                if isinstance(sync_result, dict) and sync_result.get("ok") is False:
                    self._sys_log(
                        "WARN",
                        f"[设备更新] 同步 HA 区域未完成: {entity_id}: "
                        f"{sync_result.get('error') or sync_result.get('reason') or sync_result}",
                    )
            except Exception as exc:
                self._sys_log("WARN", f"[设备更新] 同步 HA 区域失败: {entity_id}: {exc}")
        self.async_set_updated_data({})

    async def async_dev_add(self, entity_id: str, desc: str) -> None:
        """Add or update device from UI. Format: name|room|type|ops|sensor_type"""
        if not entity_id or not desc:
            return
        parts = [p.strip() for p in desc.split("|")]
        existing = self.device_info.get(entity_id, {}) or {}
        existing_mode = existing.get("control_mode", "shared")
        registry_meta = {
            "ha_unique_id": existing.get("ha_unique_id", ""),
            "ha_device_id": existing.get("ha_device_id", ""),
            **self._get_entity_registry_metadata(entity_id),
        }
        info = {
            "name": parts[0] if parts else entity_id,
            "room": parts[1] if len(parts) > 1 else "未知区域",
            "type": parts[2] if len(parts) > 2 else "",
            "ops": parts[3] if len(parts) > 3 else "",
            "sensor_type": parts[4] if len(parts) > 4 else "",
            "control_mode": existing_mode,
            **registry_meta,
        }
        now = self._ha_db_now_text()
        _ok = await self._async_db_exec(
            "INSERT INTO devices (entity_id, name, area, type, ops, control_mode, sensor_type, ha_unique_id, ha_device_id, created, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(entity_id) DO UPDATE SET name=excluded.name, area=excluded.area, type=excluded.type, ops=excluded.ops, sensor_type=excluded.sensor_type, ha_unique_id=excluded.ha_unique_id, ha_device_id=excluded.ha_device_id, updated=excluded.updated",
            (
                entity_id,
                info["name"],
                info["room"],
                info["type"],
                info["ops"],
                info["control_mode"],
                info["sensor_type"],
                info.get("ha_unique_id", ""),
                info.get("ha_device_id", ""),
                now,
                now,
            ),
        )
        if not _ok:
            self._sys_log("WARN", f"[设备新增] 写入失败，未更新内存态: {entity_id}")
            return
        self.device_info[entity_id] = info
        self._refresh_listeners()
        self.async_set_updated_data({})

    async def async_dev_delete(self, selected: str) -> None:
        if not selected or selected == "(无设备)":
            return
        eid = selected.split("|")[0].strip()
        if eid in self.device_info:
            name = self.device_info[eid]["name"]
            _ok = await self._async_db_exec("DELETE FROM devices WHERE entity_id=?", (eid,))
            if not _ok:
                self._sys_log("WARN", f"[设备删除] 写入失败，未删除: {eid}")
                return
            del self.device_info[eid]
            await self._async_update_status("设备管理", f"删除设备: {name}")
        self.async_set_updated_data({})

    async def async_refresh_device_areas(self) -> int:
        """仅刷新仍处于「待填写区域」的设备区域信息（通过 HA 注册表查找）。"""
        updated = 0
        now = self._ha_db_now_text()
        for eid, info in self.device_info.items():
            if info.get("room") and info["room"] != "待填写区域":
                continue
            area = self._get_entity_area(eid)
            if area:
                _ok = await self._async_db_exec(
                    "UPDATE devices SET area=?, updated=? WHERE entity_id=?", (area, now, eid)
                )
                if not _ok:
                    self._sys_log("WARN", f"[设备] 区域刷新写入失败: {eid}")
                    continue
                info["room"] = area
                updated += 1
        if updated > 0:
            self.async_set_updated_data({})
            self._sys_log("INFO", f"[设备] 区域信息刷新完成: 更新了 {updated} 个设备的区域")
        return updated

    async def async_sync_rooms_to_ha(self) -> dict:
        """将 SmartAgent 的房间信息同步回 Home Assistant 的 Area Registry。"""
        from homeassistant.helpers import area_registry as ar, entity_registry as er
        area_reg = ar.async_get(self.hass)
        entity_reg = er.async_get(self.hass)

        results = {"created_areas": 0, "updated_entities": 0, "errors": 0}
        area_cache = {} # name -> area_id

        # 1. 预加载现有区域
        for entry in area_reg.areas.values():
            area_cache[entry.name] = entry.id

        # 2. 遍历设备进行同步
        for eid, info in self.device_info.items():
            room = info.get("room")
            if not room or room in ("待填写区域", "未知区域"):
                continue

            # 获取或创建区域
            area_id = area_cache.get(room)
            if not area_id:
                try:
                    area = area_reg.async_get_or_create(room)
                    area_id = area.id
                    area_cache[room] = area_id
                    results["created_areas"] += 1
                except Exception as e:
                    self._sys_log("ERROR", f"[同步] 创建区域 {room} 失败: {e}")
                    results["errors"] += 1
                    continue

            # 更新实体区域
            try:
                entry = entity_reg.async_get(eid)
                if entry and entry.area_id != area_id:
                    entity_reg.async_update_entity(eid, area_id=area_id)
                    results["updated_entities"] += 1
            except Exception as e:
                self._sys_log("ERROR", f"[同步] 更新实体 {eid} 区域失败: {e}")
                results["errors"] += 1

        self._sys_log("INFO", f"[同步] 房间同步到 HA 完成: 新建区域 {results['created_areas']}，更新实体 {results['updated_entities']}，错误 {results['errors']}")
        self.async_set_updated_data({})
        return results

    async def async_sync_device_room_to_ha(self, entity_id: str, room: str) -> dict:
        """Mirror one SmartAgent room assignment into HA's Area Registry."""
        eid = str(entity_id or "").strip()
        target_room = str(room or "").strip()
        result = {
            "ok": True,
            "entity_id": eid,
            "room": target_room,
            "created_areas": 0,
            "updated_entities": 0,
            "errors": 0,
            "source": "ha_area_registry_mirror",
        }
        if not eid:
            result.update({"ok": False, "error": "entity_id_required", "errors": 1})
            return result
        if not target_room or target_room in ("待填写区域", "未知区域", "未分配"):
            result.update({"skipped": True, "reason": "room_not_provided"})
            return result

        area_reg = ar.async_get(self.hass)
        entity_reg = er.async_get(self.hass)
        area = _find_ha_area_by_id_or_name(area_reg, target_room)
        if area is None:
            result.update({"ok": False, "error": "area_not_found", "error_type": "not_found", "errors": 1})
            return result

        area_id = str(getattr(area, "id", "") or getattr(area, "area_id", "") or "").strip()
        area_name = str(getattr(area, "name", "") or target_room).strip()
        result["area_id"] = area_id
        result["area_name"] = area_name
        try:
            entry = entity_reg.async_get(eid)
            if entry is None:
                result.update({"ok": False, "error": "entity_not_found", "errors": 1})
                return result
            if entry.area_id != area_id:
                entity_reg.async_update_entity(eid, area_id=area_id)
                result["updated_entities"] = 1
        except Exception as exc:
            self._sys_log("ERROR", f"[同步] 更新设备 {eid} 区域失败: {exc}")
            result.update({"ok": False, "error": "entity_area_update_failed", "errors": 1})
            return result

        info = self.device_info.get(eid)
        if isinstance(info, dict):
            info["room"] = target_room
            self.async_set_updated_data({})
        return result

    async def async_sync_device_identity_to_ha(
        self,
        entity_id: str,
        name: str,
        new_entity_id: str = "",
    ) -> dict:
        """Mirror a display name and an optional explicit entity-id rename into HA."""
        eid = str(entity_id or "").strip()
        target_name = str(name or "").strip()
        target_entity_id = str(new_entity_id or "").strip() or eid
        result = {
            "ok": True,
            "old_entity_id": eid,
            "entity_id": target_entity_id or eid,
            "new_entity_id": target_entity_id or eid,
            "name": target_name,
            "renamed": False,
            "errors": 0,
            "source": "ha_entity_registry_mirror",
        }
        if not eid:
            result.update({"ok": False, "error": "entity_id_required", "error_type": "bad_request", "status": 400, "errors": 1})
            return result
        if not target_name and target_entity_id == eid:
            result.update({"skipped": True, "reason": "identity_not_provided", "entity_id": eid, "new_entity_id": eid})
            return result
        if not target_entity_id:
            result.update({"ok": False, "error": "target_entity_id_required", "error_type": "bad_request", "status": 400, "errors": 1})
            return result

        entity_reg = er.async_get(self.hass)
        entry = entity_reg.async_get(eid)
        if entry is None:
            result.update({"ok": False, "error": "entity_not_found", "error_type": "not_found", "status": 404, "errors": 1})
            return result
        target_info = self.device_info.get(target_entity_id) if target_entity_id != eid else None
        if target_entity_id != eid and (
            entity_reg.async_get(target_entity_id) is not None or isinstance(target_info, dict)
        ):
            result.update(
                {
                    "ok": False,
                    "error": "entity_id_conflict",
                    "error_type": "conflict",
                    "status": 409,
                    "target_entity_id": target_entity_id,
                    "entity_id": eid,
                    "new_entity_id": target_entity_id,
                    "errors": 1,
                }
            )
            return result

        try:
            update_kwargs: dict[str, Any] = {}
            if target_name:
                update_kwargs["name"] = target_name
            if target_entity_id != eid:
                update_kwargs["new_entity_id"] = target_entity_id
            entity_reg.async_update_entity(eid, **update_kwargs)
        except ValueError as exc:
            result.update(
                {
                    "ok": False,
                    "error": "entity_id_conflict",
                    "error_type": "conflict",
                    "status": 409,
                    "details": str(exc),
                    "target_entity_id": target_entity_id,
                    "errors": 1,
                }
            )
            return result
        except Exception as exc:
            self._sys_log("ERROR", f"[EntityRegistry] rename {eid} -> {target_entity_id} failed: {exc}")
            result.update({"ok": False, "error": "entity_registry_update_failed", "error_type": "internal_error", "status": 500, "errors": 1})
            return result

        info = self.device_info.pop(eid, None) if target_entity_id != eid else self.device_info.get(eid)
        registry_meta = self._get_entity_registry_metadata(target_entity_id)
        if isinstance(info, dict):
            if target_name:
                info["name"] = target_name
            info["entity_id"] = target_entity_id
            info.update(registry_meta)
            self.device_info[target_entity_id] = info
        renamed = target_entity_id != eid
        result.update({"entity_id": target_entity_id, "new_entity_id": target_entity_id, "renamed": renamed})
        self.async_set_updated_data({})
        if renamed:
            self._refresh_listeners()
        return result

    async def async_sync_device_patch_to_ha(self, entity_id: str, patch: dict[str, Any]) -> dict:
        """Mirror a SmartAgent device PATCH into HA registries."""
        eid = str(entity_id or "").strip()
        body = dict(patch) if isinstance(patch, dict) else {}
        name = str(body.get("name") or body.get("friendly_name") or "").strip()
        requested_entity_id = str(body.get("new_entity_id") or body.get("target_entity_id") or "").strip()
        room = str(body.get("room") or body.get("area") or body.get("space") or "").strip()
        capability_name = str(body.get("capability") or body.get("device_class") or "").strip().lower()
        result: dict[str, Any] = {
            "ok": True,
            "old_entity_id": eid,
            "entity_id": eid,
            "new_entity_id": eid,
            "source": "ha_entity_registry_mirror",
        }

        async def _apply_local_capability(active_entity_id: str) -> None:
            if not capability_name:
                return
            now = self._ha_db_now_text()
            info = dict(self.device_info.get(active_entity_id, {}) or {})
            if info:
                info["capability"] = capability_name
                info["type"] = capability_name
                self.device_info[active_entity_id] = info
            _ok = await self._async_db_exec(
                "UPDATE devices SET type=?, updated=? WHERE entity_id=?",
                (capability_name, now, active_entity_id),
            )
            if not _ok:
                self._sys_log("WARN", f"[设备能力] 写入失败，未更新: {active_entity_id}")
                result.setdefault("warnings", []).append("capability_persist_failed")
            result["capability"] = capability_name

        if not name and not requested_entity_id and not room:
            await _apply_local_capability(eid)
            result.update({"skipped": True, "reason": "patch_has_no_ha_registry_fields"})
            return result

        active_entity_id = requested_entity_id or eid
        entity_reg = er.async_get(self.hass)
        entry = entity_reg.async_get(eid)
        if entry is None:
            result.update(
                {
                    "ok": False,
                    "error": "entity_not_found",
                    "error_type": "not_found",
                    "status": 404,
                    "errors": 1,
                }
            )
            return result

        if active_entity_id != eid:
            target_info = self.device_info.get(active_entity_id)
            if entity_reg.async_get(active_entity_id) is not None or isinstance(target_info, dict):
                result.update(
                    {
                        "ok": False,
                        "error": "entity_id_conflict",
                        "error_type": "conflict",
                        "status": 409,
                        "target_entity_id": active_entity_id,
                        "errors": 1,
                    }
                )
                return result

        area = None
        area_id = ""
        area_name = ""
        if room:
            area = _find_ha_area_by_id_or_name(ar.async_get(self.hass), room)
            if area is None:
                result.update(
                    {
                        "ok": False,
                        "error": "area_not_found",
                        "error_type": "not_found",
                        "status": 404,
                        "errors": 1,
                    }
                )
                return result
            area_id = str(getattr(area, "id", "") or getattr(area, "area_id", "") or "").strip()
            area_name = str(getattr(area, "name", "") or room).strip()

        update_kwargs: dict[str, Any] = {}
        if name:
            update_kwargs["name"] = name
        if active_entity_id != eid:
            update_kwargs["new_entity_id"] = active_entity_id
        if area is not None:
            update_kwargs["area_id"] = area_id

        old_area_id = str(getattr(entry, "area_id", "") or "").strip()
        try:
            if update_kwargs:
                entity_reg.async_update_entity(eid, **update_kwargs)
        except ValueError as exc:
            result.update(
                {
                    "ok": False,
                    "error": "entity_id_conflict",
                    "error_type": "conflict",
                    "status": 409,
                    "details": str(exc),
                    "target_entity_id": active_entity_id,
                    "errors": 1,
                }
            )
            return result
        except Exception as exc:
            self._sys_log("ERROR", f"[EntityRegistry] patch {eid} failed: {exc}")
            result.update(
                {
                    "ok": False,
                    "error": "entity_registry_update_failed",
                    "error_type": "internal_error",
                    "status": 500,
                    "errors": 1,
                }
            )
            return result

        renamed = active_entity_id != eid
        info = self.device_info.pop(eid, None) if renamed else self.device_info.get(eid)
        if isinstance(info, dict):
            if name:
                info["name"] = name
            if room:
                info["room"] = room
            info["entity_id"] = active_entity_id
            info.update(self._get_entity_registry_metadata(active_entity_id))
            self.device_info[active_entity_id] = info

        if name or requested_entity_id:
            result["ha_entity_sync"] = {
                "ok": True,
                "old_entity_id": eid,
                "entity_id": active_entity_id,
                "new_entity_id": active_entity_id,
                "name": name,
                "renamed": renamed,
                "errors": 0,
                "source": "ha_entity_registry_mirror",
            }
        if room:
            result["ha_area_sync"] = {
                "ok": True,
                "entity_id": active_entity_id,
                "room": room,
                "area_id": area_id,
                "area_name": area_name,
                "created_areas": 0,
                "updated_entities": int(old_area_id != area_id),
                "errors": 0,
                "source": "ha_area_registry_mirror",
            }
            result["room"] = room

        result["entity_id"] = active_entity_id
        result["new_entity_id"] = active_entity_id
        self.async_set_updated_data({})
        if renamed:
            self._refresh_listeners()

        await _apply_local_capability(active_entity_id)
        return result

    # ── 设备管辖域 ────────────────────────────────────────────────────────────

    async def async_set_device_control_mode(self, entity_id: str, mode: str) -> None:
        """Service handler: set per-device control mode (ai / ha / shared)."""
        if mode not in self._VALID_CONTROL_MODES:
            self._sys_log("WARN", f"[管辖域] 无效模式 {mode!r}，仅接受 ai/ha/shared")
            return
        if entity_id not in self.device_info:
            self._sys_log("WARN", f"[管辖域] {entity_id} 不在已配置设备中")
            return
        now = self._ha_db_now_text()
        _ok = await self._async_db_exec(
            "UPDATE devices SET control_mode=?, updated=? WHERE entity_id=?",
            (mode, now, entity_id),
        )
        if not _ok:
            self._sys_log("WARN", f"[管辖域] 写入失败，未更新: {entity_id}")
            return
        self.device_info[entity_id]["control_mode"] = mode
        labels = {"ai": "AI 全权", "ha": "HA 优先", "shared": "共享"}
        self._sys_log("INFO", f"[管辖域] {self.get_device_name(entity_id)}({entity_id}) → {labels[mode]}")
        self.async_set_updated_data({})

    async def async_batch_set_control_mode(self, mode: str, room: str = "", dev_type: str = "") -> int:
        """批量设置管辖域：按房间和/或类型筛选设备，一次性修改 control_mode。"""
        if mode not in self._VALID_CONTROL_MODES:
            return 0
        labels = {"ai": "AI 全权", "ha": "HA 优先", "shared": "共享"}
        now = self._ha_db_now_text()
        count = 0
        for eid, info in self.device_info.items():
            if room and info.get("room", "") != room:
                continue
            if dev_type and info.get("type", "") != dev_type:
                continue
            if info.get("control_mode") == mode:
                continue
            _ok = await self._async_db_exec(
                "UPDATE devices SET control_mode=?, updated=? WHERE entity_id=?",
                (mode, now, eid),
            )
            if not _ok:
                self._sys_log("WARN", f"[管辖域] 批量写入失败，跳过设备: {eid}")
                continue
            info["control_mode"] = mode
            count += 1
        if count:
            filter_desc = []
            if room:
                filter_desc.append(f"房间={room}")
            if dev_type:
                filter_desc.append(f"类型={dev_type}")
            self._sys_log("INFO", f"[管辖域] 批量设置 {count} 台设备 → {labels[mode]}"
                          + (f"（{', '.join(filter_desc)}）" if filter_desc else "（全部设备）"))
            self.async_set_updated_data({})
        return count

    # ── 习惯 CRUD ─────────────────────────────────────────────────────────────

    async def async_svc_add_habit(self, content: str) -> None:
        now = self._ha_db_now_text()
        _ok = await self._async_db_exec("INSERT INTO habits (content, locked, created) VALUES (?,0,?)", (content, now))
        if not _ok:
            self._sys_log("WARN", "[习惯] 新增失败，未更新内存态")
            return
        self._habits.append((content, False))
        self.async_set_updated_data({})

    async def async_svc_delete_habit(self, content: str) -> None:
        idx = self._find_habit_idx(content)
        if idx < 0:
            return
        _, locked = self._habits[idx]
        if locked:
            return
        rows = await self._async_query("SELECT id FROM habits ORDER BY id LIMIT 1 OFFSET ?", (idx,))
        if not rows:
            self._sys_log("WARN", f"[habits] selected DB row missing; skip delete: idx={idx}")
            return
        if rows:
            _ok = await self._async_db_exec("DELETE FROM habits WHERE id=?", (rows[0]["id"],))
            if not _ok:
                self._sys_log("WARN", f"[习惯] 删除失败: idx={idx}")
                return
        del self._habits[idx]
        self.async_set_updated_data({})

    async def async_svc_toggle_habit_lock(self, content: str) -> None:
        idx = self._find_habit_idx(content)
        if idx < 0:
            return
        c, locked = self._habits[idx]
        new_locked = 0 if locked else 1
        rows = await self._async_query("SELECT id FROM habits ORDER BY id LIMIT 1 OFFSET ?", (idx,))
        if not rows:
            self._sys_log("WARN", f"[habits] selected DB row missing; skip lock toggle: idx={idx}")
            return
        if rows:
            _ok = await self._async_db_exec("UPDATE habits SET locked=? WHERE id=?", (new_locked, rows[0]["id"]))
            if not _ok:
                self._sys_log("WARN", f"[习惯] 锁定状态更新失败: idx={idx}")
                return
        self._habits[idx] = (c, bool(new_locked))
        self.async_set_updated_data({})

    async def async_habit_add(self, text: str, selected: str) -> None:
        if not text:
            return
        now = self._ha_db_now_text()
        idx = self._find_habit_idx(selected) if selected and selected != "(无)" else -1
        if idx >= 0:
            _, locked = self._habits[idx]
            if locked:
                await self._async_update_status("画像管理", "⛔ 锁定条目不可修改")
                return
            rows = await self._async_query("SELECT id FROM habits ORDER BY id LIMIT 1 OFFSET ?", (idx,))
            if not rows:
                self._sys_log("WARN", f"[habits] selected DB row missing; skip edit: idx={idx}")
                return
            if rows:
                _ok = await self._async_db_exec("UPDATE habits SET content=? WHERE id=?", (text, rows[0]["id"]))
                if not _ok:
                    self._sys_log("WARN", f"[习惯] 编辑失败: idx={idx}")
                    return
            self._habits[idx] = (text, False)
        else:
            _ok = await self._async_db_exec("INSERT INTO habits (content, locked, created) VALUES (?,0,?)", (text, now))
            if not _ok:
                self._sys_log("WARN", "[习惯] 新增失败，未更新内存态")
                return
            self._habits.append((text, False))
        self.async_set_updated_data({})

    async def async_habit_delete(self, selected: str) -> None:
        if not selected or selected == "(无)":
            return
        idx = self._find_habit_idx(selected)
        if idx < 0:
            return
        _, locked = self._habits[idx]
        if locked:
            await self._async_update_status("画像管理", "⛔ 锁定条目不可删除")
            return
        rows = await self._async_query("SELECT id FROM habits ORDER BY id LIMIT 1 OFFSET ?", (idx,))
        if not rows:
            self._sys_log("WARN", f"[habits] selected DB row missing; skip delete: idx={idx}")
            return
        if rows:
            _ok = await self._async_db_exec("DELETE FROM habits WHERE id=?", (rows[0]["id"],))
            if not _ok:
                self._sys_log("WARN", f"[习惯] 删除失败: idx={idx}")
                return
        del self._habits[idx]
        self.async_set_updated_data({})

    async def async_habit_lock(self, selected: str) -> None:
        if not selected or selected == "(无)":
            return
        idx = self._find_habit_idx(selected)
        if idx < 0:
            return
        content, locked = self._habits[idx]
        new_locked = 0 if locked else 1
        rows = await self._async_query("SELECT id FROM habits ORDER BY id LIMIT 1 OFFSET ?", (idx,))
        if not rows:
            self._sys_log("WARN", f"[habits] selected DB row missing; skip lock toggle: idx={idx}")
            return
        if rows:
            _ok = await self._async_db_exec("UPDATE habits SET locked=? WHERE id=?", (new_locked, rows[0]["id"]))
            if not _ok:
                self._sys_log("WARN", f"[习惯] 锁定状态更新失败: idx={idx}")
                return
        self._habits[idx] = (content, bool(new_locked))
        self.async_set_updated_data({})

    # ── 规则 CRUD ─────────────────────────────────────────────────────────────

    async def async_svc_add_rule(self, content: str) -> None:
        now = self._ha_db_now_text()
        _ok = await self._async_db_exec("INSERT INTO rules (content, locked, created) VALUES (?,0,?)", (content, now))
        if not _ok:
            self._sys_log("WARN", "[规则] 新增失败，未更新内存态")
            return
        self._rules.append((content, False))
        self.async_set_updated_data({})

    async def async_svc_delete_rule(self, content: str) -> None:
        idx = self._find_rule_idx(content)
        if idx < 0:
            return
        _, locked = self._rules[idx]
        if locked:
            return
        rows = await self._async_query("SELECT id FROM rules ORDER BY id LIMIT 1 OFFSET ?", (idx,))
        if not rows:
            self._sys_log("WARN", f"[rules] selected DB row missing; skip delete: idx={idx}")
            return
        if rows:
            _ok = await self._async_db_exec("DELETE FROM rules WHERE id=?", (rows[0]["id"],))
            if not _ok:
                self._sys_log("WARN", f"[规则] 删除失败: idx={idx}")
                return
        del self._rules[idx]
        self.async_set_updated_data({})

    async def async_svc_toggle_rule_lock(self, content: str) -> None:
        idx = self._find_rule_idx(content)
        if idx < 0:
            return
        c, locked = self._rules[idx]
        new_locked = 0 if locked else 1
        rows = await self._async_query("SELECT id FROM rules ORDER BY id LIMIT 1 OFFSET ?", (idx,))
        if not rows:
            self._sys_log("WARN", f"[rules] selected DB row missing; skip lock toggle: idx={idx}")
            return
        if rows:
            _ok = await self._async_db_exec("UPDATE rules SET locked=? WHERE id=?", (new_locked, rows[0]["id"]))
            if not _ok:
                self._sys_log("WARN", f"[规则] 锁定状态更新失败: idx={idx}")
                return
        self._rules[idx] = (c, bool(new_locked))
        self.async_set_updated_data({})

    async def async_rule_add(self, text: str, selected: str) -> None:
        if not text:
            return
        now = self._ha_db_now_text()
        idx = self._find_rule_idx(selected) if selected and selected != "(无)" else -1
        if idx >= 0:
            _, locked = self._rules[idx]
            if locked:
                await self._async_update_status("规则管理", "⛔ 铁律不可修改")
                return
            rows = await self._async_query("SELECT id FROM rules ORDER BY id LIMIT 1 OFFSET ?", (idx,))
            if not rows:
                self._sys_log("WARN", f"[rules] selected DB row missing; skip edit: idx={idx}")
                return
            if rows:
                _ok = await self._async_db_exec("UPDATE rules SET content=? WHERE id=?", (text, rows[0]["id"]))
                if not _ok:
                    self._sys_log("WARN", f"[规则] 编辑失败: idx={idx}")
                    return
            self._rules[idx] = (text, False)
        else:
            _ok = await self._async_db_exec("INSERT INTO rules (content, locked, created) VALUES (?,0,?)", (text, now))
            if not _ok:
                self._sys_log("WARN", "[规则] 新增失败，未更新内存态")
                return
            self._rules.append((text, False))
        self.async_set_updated_data({})

    async def async_rule_delete(self, selected: str) -> None:
        if not selected or selected == "(无)":
            return
        idx = self._find_rule_idx(selected)
        if idx < 0:
            return
        _, locked = self._rules[idx]
        if locked:
            await self._async_update_status("规则管理", "⛔ 铁律不可删除")
            return
        rows = await self._async_query("SELECT id FROM rules ORDER BY id LIMIT 1 OFFSET ?", (idx,))
        if not rows:
            self._sys_log("WARN", f"[rules] selected DB row missing; skip delete: idx={idx}")
            return
        if rows:
            _ok = await self._async_db_exec("DELETE FROM rules WHERE id=?", (rows[0]["id"],))
            if not _ok:
                self._sys_log("WARN", f"[规则] 删除失败: idx={idx}")
                return
        del self._rules[idx]
        self.async_set_updated_data({})

    async def async_rule_lock(self, selected: str) -> None:
        if not selected or selected == "(无)":
            return
        idx = self._find_rule_idx(selected)
        if idx < 0:
            return
        content, locked = self._rules[idx]
        new_locked = 0 if locked else 1
        rows = await self._async_query("SELECT id FROM rules ORDER BY id LIMIT 1 OFFSET ?", (idx,))
        if not rows:
            self._sys_log("WARN", f"[rules] selected DB row missing; skip lock toggle: idx={idx}")
            return
        if rows:
            _ok = await self._async_db_exec("UPDATE rules SET locked=? WHERE id=?", (new_locked, rows[0]["id"]))
            if not _ok:
                self._sys_log("WARN", f"[规则] 锁定状态更新失败: idx={idx}")
                return
        self._rules[idx] = (content, bool(new_locked))
        self.async_set_updated_data({})

    # ── 行为规律管理 ──────────────────────────────────────────────────────────

    async def async_delete_behavior_pattern(self, pattern_id: int) -> None:
        """Delete a single behavior pattern through the canonical add-on store."""
        try:
            addon_client = getattr(self, "_addon_client", None)
            if addon_client is None:
                self._sys_log("WARN", f"[行为习惯] Add-on 不可用，跳过删除: id={pattern_id}")
                return
            result = await addon_client.post_behavior_pattern_action(int(pattern_id), "delete")
            if not isinstance(result, dict):
                self._sys_log("WARN", f"[行为习惯] Add-on 无响应，删除失败: id={pattern_id}")
                return
            status = int(result.get("__status") or result.get("status_code") or 0)
            if status >= 400 or result.get("ok") is False:
                self._sys_log("WARN", f"[行为习惯] 删除失败: id={pattern_id}, result={result}")
                return
            self._sys_log("INFO", f"[行为习惯] 已删除习惯规律 id={pattern_id}")
            self.async_set_updated_data({})
        except Exception as e:
            _LOGGER.warning("[DevicesMixin] Delete pattern failed: %s", e)

    # ── Phase 4: AI 场景管理 ─────────────────────────────────────────────────

    def _refresh_ai_scenes_cache(self) -> None:
        """同步刷新 AI 场景内存缓存（在 executor 中调用）。"""
        self._ai_scenes_cache = self._query_ai_scenes()

    async def async_create_scene_from_text(
        self, text: str, auto_activate: bool = False
    ) -> dict:
        """一句话生成场景的主入口。

        流程：
        1. 调用 _parse_scene_from_text() 解析用户描述
        2. 验证 entity_id 存在于 device_info
        3. 生成唯一场景名（用户_ 前缀，避免与 AI_ 自动场景冲突）
        4. 调用 _upsert_ai_scene() 写入 DB（source='manual'）
        5. 若 auto_activate=True，直接调用 async_approve_ai_scene()
        6. 刷新 _ai_scenes_cache

        :return: {"success": True, "scene_id": int, "name": str, "status": str}
                 或 {"success": False, "error": str}
        """
        import json as _json

        if not text or not text.strip():
            return {"success": False, "error": "描述不能为空"}

        # Step 1: LLM 解析
        try:
            parsed = await self._parse_scene_from_text(text.strip())
        except Exception as e:
            self._sys_log("WARN", f"[场景创建] LLM 解析异常: {e}")
            return {"success": False, "error": f"AI 解析失败: {e}"}

        if not parsed:
            return {"success": False, "error": "AI 无法解析该描述，请尝试更具体的描述"}

        # Step 2: 生成唯一场景名（用户_ 前缀）
        base_name = f"用户_{text.strip()[:10]}"
        # 若名字已存在则加时间戳后缀
        existing_names = {s.get("name", "") for s in getattr(self, "_ai_scenes_cache", [])}
        scene_name = base_name
        if scene_name in existing_names:
            scene_name = f"{base_name}_{self._ha_local_now().strftime('%H%M')}"

        # Step 3: 构建 entities_json / actions_json
        entities_json = _json.dumps(parsed["entities"], ensure_ascii=False)
        actions_json = _json.dumps(parsed.get("actions") or [], ensure_ascii=False)

        # Step 4: 写入 DB
        ok = await self.hass.async_add_executor_job(
            self._upsert_ai_scene_manual,
            scene_name,
            parsed.get("description", text.strip()[:50]),
            entities_json,
            f"{parsed['hour_start']}-{parsed['hour_end']}时",
            parsed["hour_start"],
            parsed["hour_end"],
            parsed.get("weekday_mask", "0123456"),
            95,  # 用户手动创建默认高置信度
            actions_json,
        )
        if not ok:
            self._sys_log(
                "WARN",
                f"[场景创建] 写入 DB 失败: name={scene_name} trigger={parsed['hour_start']}-{parsed['hour_end']}时",
            )
            return {"success": False, "error": "保存失败：数据库写入失败"}

        # 刷新缓存，获取新场景 ID
        await self.hass.async_add_executor_job(self._refresh_ai_scenes_cache)
        scene_record = next(
            (s for s in self._ai_scenes_cache if s.get("name") == scene_name), None
        )
        scene_id = scene_record["id"] if scene_record else -1

        # Step 5: 若 auto_activate，直接激活
        status = "pending"
        if auto_activate and scene_id > 0:
            try:
                await self.async_approve_ai_scene(scene_id)
                status = "active"
            except Exception as e:
                self._sys_log("WARN", f"[场景创建] 自动激活失败: {e}")

        self._sys_log(
            "INFO",
            f"[场景创建] 场景「{scene_name}」创建成功 (id={scene_id}, status={status})",
        )
        return {"success": True, "scene_id": scene_id, "name": scene_name, "status": status}

    def _upsert_ai_scene_manual(
        self,
        name: str,
        description: str,
        entities_json: str,
        trigger_context: str,
        hour_start: int,
        hour_end: int,
        weekday_mask: str,
        confidence: int,
        actions_json: str = "[]",
    ) -> bool:
        """Delegate manual scene persistence to the DB bridge event owner."""
        from .database import DatabaseMixin

        return DatabaseMixin._upsert_ai_scene_manual(self,
            name,
            description,
            entities_json,
            trigger_context,
            hour_start,
            hour_end,
            weekday_mask,
            confidence,
            actions_json,
        )

    async def async_approve_ai_scene(self, scene_id: int) -> None:
        """用户确认候选场景 → 状态置为 active，写入 smart_agent_scenes.yaml 并调用 scene.reload。

        5C-2: 场景通过 YAML 文件持久化注册，重启 HA 后仍可通过 scene_candidate 引用。
        用户首次使用时只需在 configuration.yaml 中添加：
            scene: !include smart_agent_scenes.yaml
        之后批准的 AI 场景均自动生效，无需手动操作。
        """
        import json as _json
        from .const import AI_SCENE_STATUS_ACTIVE
        from .ha_adapter import async_create_scene, async_reload_scenes

        # 先刷新缓存读取 pending 记录（不提前设 active）
        await self.hass.async_add_executor_job(self._refresh_ai_scenes_cache)

        scene = next((s for s in self._ai_scenes_cache if s["id"] == scene_id), None)
        if not scene:
            self._sys_log("WARN", f"[AI场景] 批准后未找到场景记录 id={scene_id}")
            self.async_set_updated_data({})
            return

        # ── 5C-2: 写入 smart_agent_scenes.yaml（持久化）并调用 scene.reload ────
        ha_scene_id = f"ai_{scene_id}"
        ha_scene_eid = f"scene.{ha_scene_id}"
        _registered_ok = False
        try:
            entities_raw = _json.loads(scene.get("entities_json", "[]"))
            actions_raw = []
            try:
                actions_raw = _json.loads(scene.get("actions_json", "[]") or "[]")
            except Exception:
                actions_raw = []
            action_params_by_entity: dict[str, dict] = {}
            for act in actions_raw:
                if not isinstance(act, dict):
                    continue
                eid_act = act.get("entity_id", "")
                if not eid_act:
                    continue
                params_act = act.get("params") or {}
                if isinstance(params_act, dict) and params_act:
                    action_params_by_entity[eid_act] = params_act
            ha_entities: dict = {}
            for e in entities_raw:
                eid = e.get("entity_id", "")
                if not eid:
                    continue
                state = e.get("state", "on")
                entry: dict = {"state": state}
                merged = dict(e)
                merged.update(action_params_by_entity.get(eid, {}))
                if "brightness_pct" in merged:
                    entry["brightness"] = int(float(merged["brightness_pct"]) * 2.55)
                if "brightness" in merged:
                    entry["brightness"] = merged["brightness"]
                if "color_temp" in merged:
                    entry["color_temp"] = merged["color_temp"]
                if "color_temp_kelvin" in merged:
                    entry["color_temp_kelvin"] = merged["color_temp_kelvin"]
                if "temperature" in merged:
                    entry["temperature"] = merged["temperature"]
                ha_entities[eid] = entry

            # 写入 YAML（executor 中同步 I/O）
            yaml_ok = await self.hass.async_add_executor_job(
                self._write_scene_to_yaml, ha_scene_id, scene["name"], ha_entities
            )
            if yaml_ok:
                # 调用 scene.reload 令 HA 立即识别新场景
                await async_reload_scenes(self.hass)
                # 记录 ha_entity_id 到数据库
                _ha_entity_ok = await self.hass.async_add_executor_job(
                    self._update_ai_scene_ha_entity, scene_id, ha_scene_eid
                )
                if not _ha_entity_ok:
                    self._sys_log("WARN", f"[AI场景] ha_entity_id 持久化失败，状态保持 pending: id={scene_id}")
                else:
                    _registered_ok = True
                    self._sys_log(
                        "INFO",
                        f"[AI场景] 5C-2 已写入 YAML 并注册 {ha_scene_eid} "
                        f"（{len(ha_entities)} 个设备，场景名: {scene['name']}）",
                    )
            else:
                # YAML 写入失败时降级为 scene.create（易失但功能可用）
                await async_create_scene(self.hass, scene_id=ha_scene_id, entities=ha_entities)
                await self.hass.async_add_executor_job(
                    self._mark_ai_scene_ephemeral, scene_id
                )
                # 降级路径同样记录 ha_entity_id，FastBrain 才能复用此场景
                _ha_entity_ok = await self.hass.async_add_executor_job(
                    self._update_ai_scene_ha_entity, scene_id, ha_scene_eid
                )
                if not _ha_entity_ok:
                    self._sys_log("WARN", f"[AI场景] 降级路径 ha_entity_id 持久化失败，状态保持 pending: id={scene_id}")
                else:
                    _registered_ok = True
                    self._sys_log(
                        "WARN",
                        f"[AI场景] YAML 写入失败，降级使用 scene.create（重启后失效）: {ha_scene_eid}",
                    )
        except Exception as exc:
            self._sys_log("WARN", f"[AI场景] 场景注册失败，状态保持 pending: {exc}")

        _activated = False

        # 只有确认场景已在 HA 中可用，才将 DB 状态升为 active
        if _registered_ok:
            _status_ok = await self.hass.async_add_executor_job(
                self._update_ai_scene_status, scene_id, AI_SCENE_STATUS_ACTIVE
            )
            await self.hass.async_add_executor_job(self._refresh_ai_scenes_cache)
            _scene_after = next((s for s in self._ai_scenes_cache if s["id"] == scene_id), None)
            _activated = bool(_status_ok and _scene_after and _scene_after.get("status") == AI_SCENE_STATUS_ACTIVE)
            if not _activated:
                self._sys_log("WARN", f"[AI场景] 激活状态写入失败，保持 pending: id={scene_id}")

        # ── 刷新 HA 资源，使新场景进入 Action Router ──────────────────────────
        try:
            self._refresh_ha_resources()
        except Exception as exc:
            self._sys_log("WARN", f"[AI场景] 刷新 HA 资源失败: {exc}")

        if _activated:
            self._sys_log("INFO", f"[AI场景] 已激活场景: {scene['name']} (id={scene_id})")

            # ── Phase 7D: 同步导出为原生自动化逻辑 ────────────────────────────────
            await self._export_to_ha_automation(scene_id)
        else:
            self._sys_log("WARN", f"[AI场景] 未完成激活，跳过自动化导出: id={scene_id}")

        self.async_set_updated_data({})

    async def async_reject_ai_scene(self, scene_id: int) -> None:
        """用户拒绝候选场景 → 状态置为 rejected，并尝试删除对应 HA 场景实体。"""
        from .const import AI_SCENE_STATUS_REJECTED
        scene_name = next(
            (s["name"] for s in self._ai_scenes_cache if s["id"] == scene_id), str(scene_id)
        )
        _reject_ok = await self.hass.async_add_executor_job(
            self._update_ai_scene_status, scene_id, AI_SCENE_STATUS_REJECTED
        )
        if not _reject_ok:
            self._sys_log("WARN", f"[AI场景] 拒绝状态写入失败: id={scene_id}")
            return
        await self.hass.async_add_executor_job(self._refresh_ai_scenes_cache)
        _scene_after = next((s for s in self._ai_scenes_cache if s["id"] == scene_id), None)
        if not (_scene_after and _scene_after.get("status") == AI_SCENE_STATUS_REJECTED):
            self._sys_log("WARN", f"[AI场景] 拒绝状态缓存校验失败: id={scene_id}")
            return
        # 尝试删除已创建的 HA 场景实体（如有）
        await self._try_delete_ha_scene(scene_id)
        self._sys_log("INFO", f"[AI场景] 已拒绝场景: {scene_name} (id={scene_id})")
        self.async_set_updated_data({})

    async def async_archive_ai_scene(self, scene_id: int) -> None:
        """归档 AI 场景（archived 状态）：保留记录但标记为不可用，不再参与触发与学习。"""
        from .const import AI_SCENE_STATUS_ARCHIVED
        rows = await self.hass.async_add_executor_job(
            self._db.query, "SELECT status FROM ai_scenes WHERE id=?", (scene_id,)
        )
        if not rows:
            self._sys_log("WARN", f"[AI场景] 归档目标不存在: id={scene_id}")
            return
        archive_ok = await self.hass.async_add_executor_job(
            self._update_ai_scene_status, scene_id, AI_SCENE_STATUS_ARCHIVED
        )
        if not archive_ok:
            self._sys_log("WARN", f"[AI场景] 归档状态写入失败: id={scene_id}")
            return
        await self.hass.async_add_executor_job(self._refresh_ai_scenes_cache)
        self._sys_log("INFO", f"[AI场景] 已归档场景 id={scene_id}")
        self.async_set_updated_data({})

    async def async_delete_ai_scene(self, scene_id: int) -> None:
        """删除 AI 场景。

        - pending 状态（未确认候选）：标记为 rejected 而非物理删除，防止下次分析重新生成相同模式
        - active/rejected 状态：物理删除，同时清除对应 HA 场景实体
        """
        rows = await self.hass.async_add_executor_job(
            self._db.query, "SELECT status FROM ai_scenes WHERE id=?", (scene_id,)
        )
        current_status = rows[0]["status"] if rows else None

        if current_status == "pending":
            # pending 场景：标记 rejected，保留记录以防算法重新生成
            _reject_ok = await self.hass.async_add_executor_job(
                self._update_ai_scene_status, scene_id, "rejected"
            )
            if not _reject_ok:
                self._sys_log("WARN", f"[AI场景] 候选场景拒绝写入失败: id={scene_id}")
                return
            self._sys_log("INFO", f"[AI场景] 候选场景已拒绝并锁定（不再重新生成）id={scene_id}")
        else:
            # active / rejected 状态：物理删除
            _deleted = await self.hass.async_add_executor_job(self._delete_ai_scene_db, scene_id)
            if not _deleted:
                self._sys_log("WARN", f"[AI场景] 删除数据库记录失败，已中止后续清理: id={scene_id}")
                return
            await self._try_delete_ha_scene(scene_id)
            self._sys_log("INFO", f"[AI场景] 已删除场景 id={scene_id} (状态={current_status})")

        await self.hass.async_add_executor_job(self._refresh_ai_scenes_cache)
        self.async_set_updated_data({})

    # ── 5C-2: AI 场景 YAML 持久化 ────────────────────────────────────────────

    # 文件级写锁：防止并发 executor 任务同时写入同一 YAML 文件
    _scenes_yaml_lock: threading.Lock = threading.Lock()
    _automations_yaml_lock: threading.Lock = threading.Lock()

    def _write_scene_to_yaml(
        self, ha_scene_id: str, scene_name: str, ha_entities: dict
    ) -> bool:
        """将 AI 场景写入 smart_agent_scenes.yaml（同步，在 executor 中调用）。

        文件格式与 HA scenes.yaml 兼容。用户只需在 configuration.yaml 添加：
            scene: !include smart_agent_scenes.yaml

        采用 id 去重：同一场景重复批准只更新，不重复追加。
        返回 True 表示写入成功，返回 False 表示需要降级处理。
        """
        import os as _os
        import yaml as _yaml

        config_dir = self.hass.config.config_dir
        target_file = _os.path.join(config_dir, "smart_agent_scenes.yaml")

        def _build_entry() -> dict:
            entities_yaml: dict = {}
            for eid, attrs in ha_entities.items():
                entities_yaml[eid] = dict(attrs)
            return {
                "id": ha_scene_id,
                "name": scene_name,
                "entities": entities_yaml,
            }

        with self._scenes_yaml_lock:
            try:
                scenes: list = []
                if _os.path.exists(target_file):
                    try:
                        with open(target_file, encoding="utf-8") as _f:
                            existing = _yaml.safe_load(_f)
                        if isinstance(existing, list):
                            scenes = existing
                    except Exception:
                        scenes = []
                # 去重：移除相同 id 的旧记录
                scenes = [s for s in scenes if s.get("id") != ha_scene_id]
                scenes.append(_build_entry())
                with open(target_file, "w", encoding="utf-8") as _f:
                    _yaml.dump(
                        scenes, _f,
                        allow_unicode=True, sort_keys=False, default_flow_style=False
                    )
                return True
            except Exception as exc:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "[AI场景] smart_agent_scenes.yaml 写入失败: %s", exc
                )
                return False

    def _remove_scene_from_yaml(self, ha_scene_id: str) -> None:
        """从 smart_agent_scenes.yaml 中移除指定 id 的场景（同步，在 executor 中调用）。"""
        import os as _os
        import yaml as _yaml

        config_dir = self.hass.config.config_dir
        target_file = _os.path.join(config_dir, "smart_agent_scenes.yaml")
        if not _os.path.exists(target_file):
            return
        with self._scenes_yaml_lock:
            try:
                with open(target_file, encoding="utf-8") as _f:
                    existing = _yaml.safe_load(_f)
                if not isinstance(existing, list):
                    return
                updated = [s for s in existing if s.get("id") != ha_scene_id]
                if len(updated) == len(existing):
                    return  # 没有匹配项，无需写入
                with open(target_file, "w", encoding="utf-8") as _f:
                    _yaml.dump(
                        updated, _f,
                        allow_unicode=True, sort_keys=False, default_flow_style=False
                    )
            except Exception as exc:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "[AI场景] smart_agent_scenes.yaml 移除场景失败: %s", exc
                )

    # ── Phase 7D: 原生 YAML 自动化导出 ────────────────────────────────────────

    async def _export_to_ha_automation(self, scene_id: int) -> bool:
        """
        Phase 7D: 场景批准时自动将定时触发自动化写入配置目录。

        写入路径: <config_dir>/smart_agent_automations.yaml
        采用 alias 去重：同一场景反复批准只更新，不重复追加。
        写入后调用 automation.reload 令 HA 立即识别。

        用户只需第一次在 configuration.yaml 添加：
            automation: !include smart_agent_automations.yaml
        之后重启一次 HA，后续批准的场景均自动生效，无需手动操作。
        """
        import os as _os
        import yaml as _yaml
        from .ha_adapter import async_reload_automations

        yaml_str = self.get_scene_automation_yaml(scene_id)
        if yaml_str.startswith("# 错误") or yaml_str.startswith("# 生成"):
            self._sys_log("WARN", f"[Phase 7D] 生成 YAML 失败，跳过写入: {yaml_str[:80]}")
            return False

        try:
            new_automation = _yaml.safe_load(yaml_str)
            if isinstance(new_automation, list) and new_automation:
                new_automation = new_automation[0]
        except Exception as exc:
            self._sys_log("WARN", f"[Phase 7D] YAML 解析失败: {exc}")
            return False

        config_dir = self.hass.config.config_dir
        target_file = _os.path.join(config_dir, "smart_agent_automations.yaml")
        _lock = self._automations_yaml_lock

        def _write():
            with _lock:
                automations: list = []
                if _os.path.exists(target_file):
                    try:
                        with open(target_file, encoding="utf-8") as _f:
                            existing = _yaml.safe_load(_f)
                        if isinstance(existing, list):
                            automations = existing
                    except Exception:
                        automations = []
                alias = new_automation.get("alias", f"SmartAgent AI 场景 {scene_id}")
                automations = [a for a in automations if a.get("alias") != alias]
                automations.append(new_automation)
                with open(target_file, "w", encoding="utf-8") as _f:
                    _yaml.dump(automations, _f, allow_unicode=True,
                               sort_keys=False, default_flow_style=False)
                return len(automations)

        try:
            count = await self.hass.async_add_executor_job(_write)
            self._sys_log(
                "INFO",
                f"[Phase 7D] 已写入 smart_agent_automations.yaml"
                f"（场景 id={scene_id}，共 {count} 条定时自动化）"
            )
        except Exception as exc:
            self._sys_log("WARN", f"[Phase 7D] 写入自动化文件失败（不影响场景激活）: {exc}")
            return False

        # 调用 automation.reload（静默失败：用户可能尚未配置 !include）
        try:
            await async_reload_automations(self.hass)
        except Exception:
            pass

        return True

    def get_scene_automation_yaml(self, scene_id: int) -> str:
        """
        根据场景 ID 生成标准的 Home Assistant 自动化 YAML 字符串。
        """
        import json as _json
        import yaml as _yaml
        
        scene = next((s for s in self._ai_scenes_cache if s["id"] == scene_id), None)
        if not scene:
            return "# 错误：找不到场景记录"

        try:
            entities = _json.loads(scene.get("entities_json", "[]"))
            if not entities:
                return "# 错误：场景中没有设备动作"

            # 1. 构造 Actions
            actions = []
            for e in entities:
                eid = e.get("entity_id")
                if not eid or "." not in eid:
                    continue  # 跳过无效/缺失的 entity_id
                domain = eid.split(".")[0]
                state = e.get("state", "on")
                service = "turn_on" if state in ("on", "open", "playing") else "turn_off"

                data = {"entity_id": eid}
                if "brightness_pct" in e and service == "turn_on":
                    data["brightness_pct"] = int(float(e["brightness_pct"]))
                if "color_temp_kelvin" in e and service == "turn_on":
                    data["color_temp_kelvin"] = int(float(e["color_temp_kelvin"]))

                actions.append({
                    "service": f"{domain}.{service}",
                    "data": data
                })

            if not actions:
                return "# 错误：场景中所有设备的 entity_id 均无效"

            # 2. 构造 Trigger (定时触发)
            hour = scene.get("hour_start", 0)
            trigger = {
                "platform": "time",
                "at": f"{hour:02d}:00:00"
            }

            # 3. 构造 Condition (星期过滤)
            wd_mask = scene.get("weekday_mask", "0123456")
            conditions = []
            if wd_mask != "0123456":
                _WD_MAP = {"1": "mon", "2": "tue", "3": "wed", "4": "thu", "5": "fri", "6": "sat", "0": "sun"}
                wd_list = [_WD_MAP[c] for c in wd_mask if c in _WD_MAP]
                conditions.append({
                    "condition": "time",
                    "weekday": wd_list
                })

            # 4. 组装完整自动化结构
            automation_config = {
                "alias": f"SmartAgent: {scene['name']}",
                "description": f"由 SmartAgent AI 自动生成。原始置信度: {scene.get('confidence')}%",
                "trigger": [trigger],
                "condition": conditions,
                "action": actions,
                "mode": "single"
            }

            # 使用 yaml.dump 生成漂亮的字符串，禁用 flow style 保证可读性
            yaml_str = _yaml.dump([automation_config], allow_unicode=True, sort_keys=False, default_flow_style=False)
            return yaml_str

        except Exception as e:
            return f"# 生成 YAML 失败: {str(e)}"

    # ── Layer 2: 事务回滚 ──────────────────────────────────────────────────────

    async def async_rollback_transaction(self, txn_id: int) -> None:
        """Delegate rollback to the add-on canonical transaction source."""
        addon_client = getattr(self, "_addon_client", None)
        rollback = getattr(addon_client, "rollback_transaction", None)
        if not callable(rollback):
            self._sys_log("WARN", f"[Transaction] rollback unavailable: add-on client missing, id={txn_id}")
            return

        try:
            result = await rollback(int(txn_id))
        except Exception as exc:
            self._sys_log("WARN", f"[Transaction] add-on rollback failed id={txn_id}: {exc}")
            return

        if not isinstance(result, dict) or not result:
            self._sys_log("WARN", f"[Transaction] add-on rollback returned empty result id={txn_id}")
            return

        try:
            status = int(result.get("__status") or result.get("status") or 0)
        except (TypeError, ValueError):
            status = 0
        ok = bool(result.get("ok")) or (200 <= status < 300 and not result.get("error"))
        if not ok:
            error = (result.get("error") or result.get("error_type") or (f"http_{status}" if status else "unknown_error"))
            self._sys_log("WARN", f"[Transaction] add-on rollback failed id={txn_id}: {error}")
            return

        refresh = getattr(addon_client, "get_transactions", None)
        if callable(refresh):
            try:
                transactions = await refresh()
                if isinstance(transactions, list):
                    self._transactions_cache = transactions
                elif isinstance(transactions, dict):
                    for key in ("transactions", "items", "data"):
                        value = transactions.get(key)
                        if isinstance(value, list):
                            self._transactions_cache = [item for item in value if isinstance(item, dict)]
                            break
            except Exception as exc:
                self._sys_log("WARN", f"[Transaction] add-on transaction refresh failed after rollback id={txn_id}: {exc}")
        self.async_set_updated_data({})
        self._sys_log("INFO", f"[Transaction] rollback delegated to add-on id={txn_id}")
        return

    async def _try_delete_ha_scene(self, scene_id: int) -> None:
        """尝试删除对应的 HA 场景实体 scene.ai_<id>，同时从 YAML 文件中移除（静默失败）。"""
        from .ha_adapter import async_delete_scene, async_reload_scenes

        ha_scene_id = f"ai_{scene_id}"
        ha_scene_eid = f"scene.{ha_scene_id}"

        # 从 smart_agent_scenes.yaml 移除（5C-2 持久化）
        try:
            await self.hass.async_add_executor_job(
                self._remove_scene_from_yaml, ha_scene_id
            )
            # 调用 scene.reload 使 HA 识别场景已移除
            await async_reload_scenes(self.hass)
        except Exception as exc:
            self._sys_log("WARN", f"[AI场景] YAML 移除场景失败: {exc}")

        # 若场景实体仍存在（如通过 scene.create 创建），尝试删除
        if self.hass.states.get(ha_scene_eid) is None:
            return
        try:
            await async_delete_scene(self.hass, ha_scene_eid)
            self._sys_log("INFO", f"[AI场景] HA 场景实体已删除: {ha_scene_eid}")
        except Exception as exc:
            self._sys_log("WARN", f"[AI场景] 删除 HA 场景实体失败（不影响数据库操作）: {exc}")

    async def async_trigger_ai_scene(self, scene_id: int) -> None:
        """手动触发一个 active AI 场景：批量执行场景内所有设备动作。"""
        import json as _json
        from .const import AI_SCENE_STATUS_ACTIVE
        scene = next(
            (s for s in self._ai_scenes_cache
             if s["id"] == scene_id and s["status"] == AI_SCENE_STATUS_ACTIVE),
            None,
        )
        if not scene:
            self._sys_log("WARN", f"[AI场景] 手动触发失败：场景 id={scene_id} 不存在或未激活")
            return
        actions: list[dict] = []
        try:
            actions_raw = _json.loads(scene.get("actions_json", "[]") or "[]")
            actions = normalize_raw_actions(actions_raw, device_info=self.device_info)
        except Exception:
            actions = []

        if not actions:
            try:
                entities = _json.loads(scene["entities_json"])
            except Exception:
                self._sys_log("WARN", f"[AI场景] 场景 {scene['name']} entities_json 解析失败")
                return

            actions = entities_to_actions(
                entities,
                device_info=self.device_info,
                on_states=("on", "open", "heat", "cool", "auto"),
            )

        if actions:
            for a in actions:
                a["reason"] = f"手动触发AI场景: {scene['name']}"
            self._sys_log("INFO", f"[AI场景] 手动触发: {scene['name']} ({len(actions)} 个设备)")
            await self._execute_actions(actions, is_global_cmd=True)
