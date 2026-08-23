"""Server-owned HA config update service handler."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

_LOGGER = logging.getLogger(__name__)


async def apply_config_update_service(
    hass: Any,
    entry: Any,
    coordinator: Any,
    call: Any,
    *,
    check_admin: Callable[[Any], Awaitable[bool]],
    coerce_file_log_level: Callable[[Any], int],
) -> None:
    """前端设置面板保存通用配置，持久化到 config entry options。"""
    if not await check_admin(call):
        return
    from .const import (
        CONF_TTS_SERVICE, CONF_TTS_TARGET, CONF_TTS_LEVEL,
        CONF_ENGINE, CONF_OLLAMA_URL, CONF_OLLAMA_MODEL,
        CONF_ONLINE_API_KEY, CONF_ONLINE_BASE_URL, CONF_ONLINE_MODEL,
        CONF_CONFIDENCE_AUTO, CONF_CONFIDENCE_NOTIFY, CONF_COOLDOWN,
        CONF_SHOWROOM_BIZ_START, CONF_SHOWROOM_BIZ_END,
        CONF_SHOWROOM_AREA_NAME, CONF_SHOWROOM_EXCLUDED_SUBAREAS,
        CONF_SHOWROOM_ZONE_MAP,
        CONF_FRIGATE_ENABLED, CONF_QWEATHER_API_KEY, CONF_SEARXNG_URL,
        CONF_CLOUD_FALLBACK, CONF_VISION_ENABLED, CONF_VISION_ENGINE,
        CONF_VISION_MODEL,
        CONF_BRAND_NAME, CONF_BRAND_PRIMARY_COLOR, CONF_BRAND_LOGO_URL, CONF_DEPLOY_NAME,
        CONF_LICENSE_KEY, CONF_LOG_RETENTION, CONF_FILE_LOG_LEVEL,
        CONF_CLEANUP_LEGACY_PAIR_TOKENS,
        CONF_PRESENCE_FUSION,
        CONF_CIRCADIAN_ENABLED, CONF_CIRCADIAN_WAKE_TIME,
        CONF_CIRCADIAN_SLEEP_TIME, CONF_CIRCADIAN_MAX_BRIGHTNESS,
        CONF_CIRCADIAN_AUTO_ADJUST,
    )
    opts = dict(entry.options or {})

    # 定义所有可能的配置键及其转换函数
    conf_map = {
        "tts_service": (CONF_TTS_SERVICE, str),
        "tts_target": (CONF_TTS_TARGET, str),
        "tts_level": (CONF_TTS_LEVEL, int),
        "engine": (CONF_ENGINE, str),
        "ollama_url": (CONF_OLLAMA_URL, str),
        "ollama_model": (CONF_OLLAMA_MODEL, str),
        "online_api_key": (CONF_ONLINE_API_KEY, str),
        "online_base_url": (CONF_ONLINE_BASE_URL, str),
        "online_model": (CONF_ONLINE_MODEL, str),
        "confidence_auto": (CONF_CONFIDENCE_AUTO, int),
        "confidence_notify": (CONF_CONFIDENCE_NOTIFY, int),
        "cooldown": (CONF_COOLDOWN, int),
        "showroom_biz_start": (CONF_SHOWROOM_BIZ_START, int),
        "showroom_biz_end": (CONF_SHOWROOM_BIZ_END, int),
        "showroom_area_name": (CONF_SHOWROOM_AREA_NAME, str),
        "showroom_excluded_subareas": (CONF_SHOWROOM_EXCLUDED_SUBAREAS, str),
        "showroom_zone_map": (CONF_SHOWROOM_ZONE_MAP, str),
        "frigate_enabled": (CONF_FRIGATE_ENABLED, bool),
        "qweather_api_key": (CONF_QWEATHER_API_KEY, str),
        "searxng_url": (CONF_SEARXNG_URL, str),
        "cloud_fallback": (CONF_CLOUD_FALLBACK, bool),
        "vision_enabled": (CONF_VISION_ENABLED, bool),
        "vision_engine": (CONF_VISION_ENGINE, str),
        "vision_model": (CONF_VISION_MODEL, str),
        "license_key": (CONF_LICENSE_KEY, str),
        "log_retention_days": (CONF_LOG_RETENTION, int),
        "file_log_level": (CONF_FILE_LOG_LEVEL, str),
        "cleanup_legacy_pair_tokens": (CONF_CLEANUP_LEGACY_PAIR_TOKENS, bool),
        "mcp_enabled": ("mcp_enabled", bool),
        # 品牌化/白标
        "brand_name": (CONF_BRAND_NAME, str),
        "brand_primary_color": (CONF_BRAND_PRIMARY_COLOR, str),
        "brand_logo_url": (CONF_BRAND_LOGO_URL, str),
        "deploy_name": (CONF_DEPLOY_NAME, str),
        # 存在传感器融合域（Phase 12.0）
        "presence_fusion": (CONF_PRESENCE_FUSION, str),
        # 昼夜节律引擎（Phase 13）
        "circadian_enabled": (CONF_CIRCADIAN_ENABLED, bool),
        "circadian_wake_time": (CONF_CIRCADIAN_WAKE_TIME, str),
        "circadian_sleep_time": (CONF_CIRCADIAN_SLEEP_TIME, str),
        "circadian_max_brightness": (CONF_CIRCADIAN_MAX_BRIGHTNESS, int),
        "circadian_auto_adjust": (CONF_CIRCADIAN_AUTO_ADJUST, bool),
    }

    import re as _re
    import json as _json
    # HH:MM 严格校验：小时 00-23，分钟 00-59
    _TIME_RE = _re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
    _TIME_KEYS = {"circadian_wake_time", "circadian_sleep_time"}
    # 需要合法 JSON 数组或对象的字段，写入前校验
    _JSON_ARRAY_KEYS = {"presence_fusion"}
    _JSON_OBJ_KEYS   = {"showroom_zone_map"}

    any_changed = False
    for key, (conf_key, transform) in conf_map.items():
        if key in call.data:
            val = call.data[key]
            if transform == int:
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    continue
            elif transform == bool:
                # bool("false") == True，需要专门处理字符串布尔值
                if isinstance(val, str):
                    val = val.strip().lower() not in ("false", "0", "no", "off", "")
                else:
                    val = bool(val)
            elif key in _TIME_KEYS:
                # HH:MM 严格格式校验，范围外值（如 99:99）跳过
                if not _TIME_RE.match(str(val)):
                    _LOGGER.warning(
                        "[Config] %s 格式错误（应为 HH:MM，小时00-23分钟00-59）: %s，已忽略",
                        key, val
                    )
                    continue
            elif key in _JSON_ARRAY_KEYS:
                # P2修复：写入前验证为合法 JSON 数组，防止无效值存入配置导致运行时崩溃
                if val and isinstance(val, str):
                    try:
                        _parsed = _json.loads(val)
                        if not isinstance(_parsed, list):
                            raise ValueError("非数组")
                    except (ValueError, TypeError) as _je:
                        _LOGGER.warning("[Config] %s 不是合法 JSON 数组: %s，已忽略", key, _je)
                        continue
            elif key in _JSON_OBJ_KEYS:
                # P2修复：写入前验证为合法 JSON 对象
                if val and isinstance(val, str):
                    try:
                        _parsed = _json.loads(val)
                        if not isinstance(_parsed, dict):
                            raise ValueError("非对象")
                    except (ValueError, TypeError) as _je:
                        _LOGGER.warning("[Config] %s 不是合法 JSON 对象: %s，已忽略", key, _je)
                        continue

            if opts.get(conf_key) != val:
                # 密码型字段保护：前端回显使用掩码（如 **** / sk-xx****yy），
                # 空值或掩码值不应覆盖已保存的真实密钥。
                if conf_key in (CONF_ONLINE_API_KEY, CONF_QWEATHER_API_KEY, CONF_LICENSE_KEY):
                    if not str(val or "").strip() or "****" in str(val):
                        continue
                opts[conf_key] = val
                # 同步更新 coordinator 内存中的值（JSON 字段保持运行态结构类型）
                sync_val = val
                if key == "file_log_level":
                    sync_val = coerce_file_log_level(val)
                    coordinator._file_log_level_name = logging.getLevelName(sync_val)
                    coordinator._file_logger.setLevel(sync_val)
                if key in _JSON_OBJ_KEYS and isinstance(val, str):
                    try:
                        _obj = _json.loads(val) if val else {}
                        sync_val = _obj if isinstance(_obj, dict) else {}
                    except (ValueError, TypeError):
                        sync_val = {}
                attr_name = f"_{key}" if hasattr(coordinator, f"_{key}") else key
                if hasattr(coordinator, attr_name):
                    setattr(coordinator, attr_name, sync_val)
                elif hasattr(coordinator, key):
                    setattr(coordinator, key, sync_val)
                any_changed = True

    if any_changed:
        # Phase 13: 热更新昼夜节律引擎配置
        _ce = getattr(coordinator, "_circadian_engine", None)
        if _ce is not None:
            _ce.update_config(
                wake_time=opts.get(CONF_CIRCADIAN_WAKE_TIME),
                sleep_time=opts.get(CONF_CIRCADIAN_SLEEP_TIME),
                max_brightness=opts.get(CONF_CIRCADIAN_MAX_BRIGHTNESS),
                enabled=opts.get(CONF_CIRCADIAN_ENABLED),
            )
            coordinator._circadian_auto_adjust = opts.get(CONF_CIRCADIAN_AUTO_ADJUST, False)

        coordinator._skip_next_reload = True
        hass.config_entries.async_update_entry(entry, options=opts)
        coordinator.async_set_updated_data(coordinator.get_config_attributes())
        coordinator._sys_log("INFO", "[配置] 系统参数已更新")

__all__ = ["apply_config_update_service"]
