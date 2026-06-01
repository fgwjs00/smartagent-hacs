"""
FrigateConfigManager — Frigate NVR 配置文件管理器。

负责：
  - 动态查找 Frigate 配置路径（每台设备 addon hash 不同）
  - 读写 frigate.yml / config.yaml
  - 生成标准摄像头配置块
  - 通过 HA Supervisor API 重启 Frigate Add-on
  - 通过 Frigate HTTP API 读取摄像头列表（跨容器，无需文件系统权限）

架构说明：
    SmartAgent 面板 → FrigateConfigManager → frigate.yml（直接写文件）
                                           → Supervisor API（重启 Add-on）
                                           → Frigate HTTP API（读取配置，主路径）
    摄像头→房间绑定存储在 SmartAgent DB（frigate_cameras 表），
    AI 推理时查 DB 获取触发房间，无需依赖 HA camera.* 实体。

注意：SmartAgent 运行在 HA Core 容器内，该容器不挂载 /addon_configs/，
      因此读取摄像头列表优先通过 Frigate HTTP API 实现，文件系统搜索仅作降级兜底。
"""
from __future__ import annotations

import glob
import hashlib
import logging
import os
import re
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)

# Frigate 配置文件的可能路径（按优先级排序，支持通配）
_CONFIG_SEARCH_PATTERNS = [
    "/addon_configs/*frigate*/config.yaml",
    "/addon_configs/*frigate*/config.yml",
    "/config/frigate/config.yaml",
    "/config/frigate/config.yml",
    "/config/frigate.yaml",
    "/config/frigate.yml",
]
_ADDON_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def find_frigate_config_path() -> Optional[str]:
    """
    动态查找 Frigate 配置文件路径。

    每台 HA OS 设备的 addon hash 不同（如 ccab4aaf_frigate），
    使用 glob 通配匹配避免硬编码路径。

    Returns:
        找到的配置文件完整路径，未找到返回 None。
    """
    for pattern in _CONFIG_SEARCH_PATTERNS:
        matches = glob.glob(pattern)
        if matches:
            _LOGGER.debug("[FrigateConfig] 找到配置文件: %s", matches[0])
            return matches[0]
    # 预期行为：HA Core 容器不挂载 /addon_configs/，摄像头信息通过 Frigate HTTP API 获取
    _LOGGER.info(
        "[FrigateConfig] 文件系统未找到 Frigate 配置（正常，HA Core 容器不挂载 addon 目录），"
        "将通过 Frigate HTTP API 读取摄像头列表。已搜索: %s",
        _CONFIG_SEARCH_PATTERNS,
    )
    return None


def extract_addon_slug(config_path: str) -> Optional[str]:
    """
    从配置文件路径中提取 Frigate Add-on slug。

    例如 /addon_configs/ccab4aaf_frigate/config.yaml → ccab4aaf_frigate

    Args:
        config_path: 配置文件完整路径

    Returns:
        Add-on slug 字符串，无法提取时返回 None。
    """
    normalized = str(config_path or "").strip().replace("\\", "/")
    if not normalized:
        return None
    parts = [part for part in normalized.split("/") if part]
    try:
        addon_configs_idx = parts.index("addon_configs")
    except ValueError:
        return None
    if addon_configs_idx + 2 >= len(parts):
        return None
    slug = parts[addon_configs_idx + 1]
    if not _ADDON_SLUG_RE.fullmatch(slug):
        return None
    return slug


def generate_camera_id(friendly_name: str) -> str:
    """
    根据摄像头友好名称生成唯一 ID（cam_xxxxxxxx 格式）。

    使用 MD5 前 8 位，与 Frigate 内置命名风格一致。

    Args:
        friendly_name: 摄像头中文或英文名称

    Returns:
        形如 cam_d5fe7a4f 的摄像头 ID。
    """
    h = hashlib.md5(friendly_name.encode("utf-8")).hexdigest()[:8]
    return f"cam_{h}"


def read_frigate_config(path: str) -> dict:
    """
    读取并解析 Frigate YAML 配置文件。

    Args:
        path: 配置文件路径

    Returns:
        解析后的配置字典，失败时返回空字典。
    """
    try:
        import yaml  # noqa: PLC0415
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config if isinstance(config, dict) else {}
    except FileNotFoundError:
        _LOGGER.warning("[FrigateConfig] 配置文件不存在: %s", path)
        return {}
    except Exception as exc:
        _LOGGER.error("[FrigateConfig] 读取配置失败: %s", exc)
        return {}


def write_frigate_config(path: str, config: dict) -> bool:
    """
    将配置字典写回 Frigate YAML 文件。

    自动创建父目录，写入前备份原文件到 .bak 后缀。

    Args:
        path: 目标文件路径
        config: 要写入的配置字典

    Returns:
        写入成功返回 True，失败返回 False。
    """
    try:
        import yaml  # noqa: PLC0415

        # 备份原文件
        if os.path.exists(path):
            bak_path = path + ".bak"
            try:
                import shutil
                shutil.copy2(path, bak_path)
            except Exception:
                pass

        # 确保父目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # 原子写：先写临时文件再 rename，避免 dump 中途失败截断/损坏原配置。
        # dump 失败时原文件保持不变（临时文件被清理）。
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    config, f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                )
            os.replace(tmp_path, path)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            raise
        _LOGGER.info("[FrigateConfig] 配置已写入: %s", path)
        return True
    except Exception as exc:
        _LOGGER.error("[FrigateConfig] 写入配置失败: %s", exc)
        return False


def build_camera_config(
    friendly_name: str,
    rtsp_url: str,
    min_score: float = 0.7,
    threshold: float = 0.85,
    fps: int = 5,
    width: int = 1920,
    height: int = 1080,
) -> dict:
    """
    构建标准的 Frigate 摄像头配置块。

    生成包含 ffmpeg/detect/objects 的完整配置，与现有展厅配置格式一致。

    Args:
        friendly_name: 摄像头中文友好名称（显示在 UI 中）
        rtsp_url: 摄像头 RTSP 地址
        min_score: 最低检测分数阈值（0.0-1.0）
        threshold: 目标追踪阈值（0.0-1.0）
        fps: 检测帧率
        width: 画面宽度（像素）
        height: 画面高度（像素）

    Returns:
        Frigate 格式的摄像头配置字典。
    """
    return {
        "enabled": True,
        "friendly_name": friendly_name,
        "ffmpeg": {
            "inputs": [
                {
                    "path": rtsp_url,
                    "roles": ["detect"],
                }
            ]
        },
        "detect": {
            "enabled": True,
            "width": width,
            "height": height,
            "fps": fps,
        },
        "objects": {
            "track": ["person"],
            "filters": {
                "person": {
                    "min_score": min_score,
                    "threshold": threshold,
                }
            },
        },
    }


def add_camera_to_config(
    config: dict,
    camera_id: str,
    camera_config: dict,
    rtsp_url: str,
) -> dict:
    """
    向 Frigate 配置中添加或更新摄像头。

    同时维护 go2rtc.streams 段（供 WebRTC 预览使用）。

    Args:
        config: 当前 Frigate 配置字典（会被就地修改）
        camera_id: 摄像头 ID（cam_xxxxxxxx）
        camera_config: build_camera_config() 返回的配置块
        rtsp_url: RTSP 地址（写入 go2rtc.streams）

    Returns:
        修改后的配置字典。
    """
    if "cameras" not in config:
        config["cameras"] = {}
    config["cameras"][camera_id] = camera_config

    # 同步更新 go2rtc.streams
    if "go2rtc" not in config:
        config["go2rtc"] = {}
    if "streams" not in config["go2rtc"]:
        config["go2rtc"]["streams"] = {}
    config["go2rtc"]["streams"][camera_id] = [rtsp_url]

    return config


def remove_camera_from_config(config: dict, camera_id: str) -> dict:
    """
    从 Frigate 配置中移除摄像头及其 go2rtc 流定义。

    Args:
        config: 当前 Frigate 配置字典（会被就地修改）
        camera_id: 要删除的摄像头 ID

    Returns:
        修改后的配置字典。
    """
    config.get("cameras", {}).pop(camera_id, None)
    config.get("go2rtc", {}).get("streams", {}).pop(camera_id, None)
    return config


def list_cameras_from_config(config: dict) -> list[dict]:
    """
    从 Frigate 配置中提取摄像头列表（供前端展示）。

    同时提取每台摄像头定义的 zones（zone_id + friendly_name），
    供前端展示 zone 级房间绑定 UI。

    Args:
        config: Frigate 配置字典

    Returns:
        摄像头信息列表，每项包含 camera_id / friendly_name / rtsp_url / zones。
    """
    cameras = []
    for cam_id, cam_cfg in config.get("cameras", {}).items():
        if not isinstance(cam_cfg, dict):
            continue
        rtsp = ""
        inputs = cam_cfg.get("ffmpeg", {}).get("inputs", [])
        if inputs and isinstance(inputs[0], dict):
            rtsp = inputs[0].get("path", "")

        # 提取 zones 定义（zone_id + friendly_name）
        zones = []
        for zone_id, zone_cfg in cam_cfg.get("zones", {}).items():
            if not isinstance(zone_cfg, dict):
                continue
            zones.append({
                "zone_id": zone_id,
                "friendly_name": zone_cfg.get("friendly_name", zone_id),
            })

        cameras.append({
            "camera_id": cam_id,
            "friendly_name": cam_cfg.get("friendly_name", cam_id),
            "rtsp_url": rtsp,
            "enabled": cam_cfg.get("enabled", True),
            "min_score": cam_cfg.get("objects", {}).get("filters", {}).get("person", {}).get("min_score", 0.7),
            "threshold": cam_cfg.get("objects", {}).get("filters", {}).get("person", {}).get("threshold", 0.85),
            "fps": cam_cfg.get("detect", {}).get("fps", 5),
            "zones": zones,
        })
    return cameras


async def get_cameras_from_frigate_api() -> tuple[list[dict], str]:
    """
    通过 Frigate HTTP API 获取摄像头列表，无需访问文件系统。

    HA Core 容器不挂载 /addon_configs/，因此通过以下优先级获取摄像头：
      1. Supervisor API 列出所有 Add-on → 找到 Frigate slug → 查询内网 IP
      2. 用 slug 构建 Docker 内网 hostname（ccab4aaf_frigate → ccab4aaf-frigate）
      3. 通用 hostname 兜底（http://frigate:5000）

    Returns:
        (cameras_list, api_base_url) 成功时返回摄像头列表及 API 地址，
        全部失败返回 ([], "")。
    """
    import aiohttp  # noqa: PLC0415

    token = os.environ.get("SUPERVISOR_TOKEN", "")
    candidate_urls: list[str] = []

    # ── 阶段 1：通过 Supervisor API 发现 Frigate slug 及内网 IP ──
    if token:
        try:
            async with aiohttp.ClientSession() as _sess:
                async with _sess.get(
                    "http://supervisor/addons",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for addon in data.get("data", {}).get("addons", []):
                            slug = addon.get("slug", "")
                            if "frigate" not in slug.lower():
                                continue
                            # 尝试从 info 端点获取内网 IP（最可靠）
                            try:
                                async with _sess.get(
                                    f"http://supervisor/addons/{slug}/info",
                                    headers={"Authorization": f"Bearer {token}"},
                                    timeout=aiohttp.ClientTimeout(total=5),
                                ) as info_resp:
                                    if info_resp.status == 200:
                                        info = await info_resp.json()
                                        ip = info.get("data", {}).get("ip_address", "")
                                        if ip and ip not in ("null", ""):
                                            candidate_urls.append(f"http://{ip}:5000")
                            except Exception:
                                pass
                            # slug 的两种 Docker hostname 形式
                            candidate_urls.append(f"http://{slug.replace('_', '-')}:5000")
                            candidate_urls.append(f"http://{slug}:5000")
        except Exception as exc:
            _LOGGER.debug("[FrigateConfig] Supervisor API 查询失败: %s", exc)

    # ── 阶段 2：通用兜底 hostname ──
    candidate_urls.append("http://frigate:5000")

    # ── 阶段 3：逐一尝试，取第一个成功的 ──
    for base_url in candidate_urls:
        try:
            async with aiohttp.ClientSession() as _sess:
                async with _sess.get(
                    f"{base_url}/api/config",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        # Frigate API 返回 JSON（不论 Content-Type）
                        config = await resp.json(content_type=None)
                        cameras = list_cameras_from_config(config)
                        _LOGGER.info(
                            "[FrigateConfig] Frigate API 获取摄像头成功: %d 台 ← %s",
                            len(cameras), base_url,
                        )
                        return cameras, base_url
        except Exception as exc:
            _LOGGER.debug("[FrigateConfig] %s 不可达: %s", base_url, exc)

    _LOGGER.warning("[FrigateConfig] Frigate API 所有候选地址均不可达，降级到文件系统读取")
    return [], ""


async def restart_frigate_addon(hass: Any, addon_slug: str) -> bool:
    """
    通过 HA Supervisor API 重启 Frigate Add-on。

    使用 SUPERVISOR_TOKEN 环境变量认证（HA OS 标准环境变量）。

    Args:
        hass: Home Assistant 实例
        addon_slug: Add-on slug（如 ccab4aaf_frigate）

    Returns:
        重启请求成功返回 True，失败返回 False。
    """
    # 方式一：通过 hassio 域服务（更可靠）
    try:
        if hass.services.has_service("hassio", "addon_restart"):
            from .ha_adapter import async_call_service

            await async_call_service(
                hass,
                "hassio", "addon_restart",
                {"addon": addon_slug},
                blocking=False,
            )
            _LOGGER.info("[FrigateConfig] 已通过 hassio 服务发送重启请求: %s", addon_slug)
            return True
    except Exception as exc:
        _LOGGER.debug("[FrigateConfig] hassio 服务重启失败: %s，尝试 Supervisor HTTP API", exc)

    # 方式二：直接调用 Supervisor REST API
    try:
        import aiohttp  # noqa: PLC0415
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            _LOGGER.warning("[FrigateConfig] SUPERVISOR_TOKEN 未设置，无法通过 API 重启")
            return False

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://supervisor/addons/{addon_slug}/restart",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    _LOGGER.info("[FrigateConfig] Supervisor API 重启成功: %s", addon_slug)
                    return True
                _LOGGER.warning("[FrigateConfig] Supervisor API 返回 %s", resp.status)
    except Exception as exc:
        _LOGGER.warning("[FrigateConfig] Supervisor API 重启失败: %s", exc)

    return False
