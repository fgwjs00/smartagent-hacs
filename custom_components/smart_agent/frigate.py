"""
FrigateMixin — Frigate NVR 深度集成层。
负责：MQTT 事件订阅、区域感知、事件去重去抖、快照缓存。

架构：
    Frigate → MQTT (frigate/events) → FrigateMixin → 结构化事件 → 推理队列
    同时保留 HA Entity 通道（_state_changed 中的传感器去抖），兼容无 MQTT 场景。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import base64
import aiohttp
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol

from homeassistant.core import callback

try:
    from core.vision import FrigateProvider as CoreFrigateProvider
except Exception:  # pragma: no cover - add-on Core is optional inside HA runtime
    CoreFrigateProvider = None  # type: ignore[assignment]

_LOGGER = logging.getLogger(__name__)

# Frigate MQTT 事件去抖参数
_MQTT_DEBOUNCE_NEW = 3        # new 事件后等待 N 秒再触发推理（等待 zone 数据填充）
_MQTT_DEBOUNCE_UPDATE = 8     # update 事件冷却（同一 event_id 内的后续更新）
_MQTT_DEBOUNCE_END = 2        # end 事件延迟（确认人员确实离开）
_MQTT_EVENT_CACHE_SIZE = 50   # 最近 N 个事件缓存
_MQTT_ZONE_COOLDOWN = 30      # 同一 zone 的触发冷却（秒）
_CRITICAL_FRIGATE_EVENT_TTL = 300  # 关键门禁视觉事件最长保留时间（秒）

# 行为识别参数（Phase 7G）
_ACTIVITY_ANALYSIS_COOLDOWN = 300   # 同一摄像头行为分析冷却时间（秒）—— 5 分钟
_ACTIVITY_STALE_TIMEOUT = 600       # 行为标签过期时间（秒）—— 10 分钟内视为有效
_ACTIVITY_LABELS = [
    "看电视", "阅读", "用电脑/手机", "休息/躺下", "用餐", "做饭",
    "健身/运动", "站立活动", "交谈", "儿童玩耍", "无人",
]


@dataclass(frozen=True)
class VisionEventSnapshot:
    """迁移期统一视觉事件快照。"""

    provider: str
    camera_id: str
    event_id: str
    event_type: str
    label: str
    sub_label: str | None
    score: float
    entered_zones: list[str]
    current_zones: list[str]
    has_snapshot: bool
    thumbnail: str
    timestamp: float


class VisionProvider(Protocol):
    """最小视觉 Provider 接口（Wave 1B）。"""

    def parse_event_payload(self, payload: dict[str, Any]) -> VisionEventSnapshot | None:
        ...

    def get_trigger_room(self, camera_id: str, zone_id: str | None = None) -> str:
        ...


class FrigateVisionProvider:
    """Frigate 适配器：把 Frigate 事件映射到统一 VisionProvider 接口。"""

    provider_name = "frigate"

    def __init__(self, owner: "FrigateMixin") -> None:
        self._owner = owner

    def parse_event_payload(self, payload: dict[str, Any]) -> VisionEventSnapshot | None:
        if CoreFrigateProvider is not None:
            frame = CoreFrigateProvider().normalize_event(payload)
            metadata = frame.metadata if isinstance(frame.metadata, dict) else {}
            label = str(metadata.get("label") or "")
            if label != "person":
                return None
            return VisionEventSnapshot(
                provider=self.provider_name,
                camera_id=frame.camera_id or "unknown",
                event_id=str(metadata.get("event_id") or ""),
                event_type=str(metadata.get("event_type") or ""),
                label=label,
                sub_label=metadata.get("sub_label"),
                score=float(metadata.get("top_score") or 0),
                entered_zones=[str(item) for item in metadata.get("entered_zones", []) if isinstance(item, str)],
                current_zones=[str(item) for item in metadata.get("current_zones", []) if isinstance(item, str)],
                has_snapshot=bool(metadata.get("has_snapshot", False)),
                thumbnail=str(metadata.get("thumbnail") or ""),
                timestamp=time.time(),
            )

        after = payload.get("after") or {}
        if not isinstance(after, dict):
            return None
        label = after.get("label", "")
        if label != "person":
            return None
        event_id = after.get("id", "")
        camera = after.get("camera", "unknown")
        entered_zones = [z.lower() for z in after.get("entered_zones", []) if isinstance(z, str)]
        current_zones = [z.lower() for z in after.get("current_zones", []) if isinstance(z, str)]
        return VisionEventSnapshot(
            provider=self.provider_name,
            camera_id=camera,
            event_id=event_id,
            event_type=payload.get("type", ""),
            label=label,
            sub_label=after.get("sub_label"),
            score=after.get("top_score", 0),
            entered_zones=entered_zones,
            current_zones=current_zones,
            has_snapshot=after.get("has_snapshot", False),
            thumbnail=after.get("thumbnail", ""),
            timestamp=time.time(),
        )

    def get_trigger_room(self, camera_id: str, zone_id: str | None = None) -> str:
        if zone_id:
            room = self._owner._get_frigate_zone_room(camera_id, zone_id)
            if room:
                return room
        return self._owner._get_frigate_camera_room(camera_id)


class FrigateMixin:
    """Mixin: Frigate NVR 深度集成 — MQTT 事件驱动 + 区域感知。"""

    def _init_frigate_mqtt(self) -> None:
        """初始化 Frigate MQTT 相关状态。在 coordinator.__init__ 中调用。"""
        self._frigate_mqtt_unsub: Any = None
        self._frigate_events_cache: OrderedDict[str, dict] = OrderedDict()
        self._frigate_zone_last_trigger: dict[str, float] = {}
        self._frigate_mqtt_debounce_timers: dict[str, Any] = {}
        self._frigate_zone_occupancy: dict[str, dict[str, int]] = {}
        self._frigate_event_counted_zones: dict[str, set[str]] = {}
        self._frigate_visual_descriptions: OrderedDict[str, str] = OrderedDict()  # event_id -> description（临时，仅供触发文本拼接）
        self._vision_provider: VisionProvider = FrigateVisionProvider(self)
        # Phase 7G：行为识别 — 每个摄像头维护最新行为标签（持续有效，不依赖具体事件 ID）
        self._frigate_camera_activity: dict[str, dict] = {}      # camera_id -> {label, desc, ts}
        self._frigate_activity_last_analyzed: dict[str, float] = {}  # camera_id -> 上次分析时间戳

    @staticmethod
    def _frigate_event_zone_key(camera: str, event_id: str) -> str:
        return f"{camera}:{event_id}" if event_id else ""

    def _remember_frigate_visual_description(self, event_id: str, description: str) -> None:
        """Store one-shot visual text for the MQTT trigger and bound the cache."""
        if not event_id or not description:
            return
        cache = self._frigate_visual_descriptions
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict(cache)
            self._frigate_visual_descriptions = cache
        cache[event_id] = description
        cache.move_to_end(event_id)
        while len(cache) > _MQTT_EVENT_CACHE_SIZE:
            cache.popitem(last=False)

    def _pop_frigate_visual_description(self, event_id: str) -> str:
        if not event_id:
            return ""
        return self._frigate_visual_descriptions.pop(event_id, "")

    def _discard_frigate_visual_description(self, event_id: str) -> None:
        if event_id:
            self._frigate_visual_descriptions.pop(event_id, None)

    def _observe_frigate_task_failure(self, task: Any, *, context: str) -> None:
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            self._sys_log("WARN", f"[Frigate] {context} task cancelled: task_cancelled")
            return
        except Exception as err:
            self._sys_log("WARN", f"[Frigate] {context} task failed: {err}")
            return
        if exc is None:
            if hasattr(task, "cancelled") and task.cancelled():
                self._sys_log("WARN", f"[Frigate] {context} task cancelled: task_cancelled")
            return
        self._sys_log("WARN", f"[Frigate] {context} task failed: {exc}")

    def _spawn_frigate_task(self, coro: Any, *, context: str) -> Any | None:
        try:
            task = self.hass.async_create_task(coro)
        except Exception as exc:
            close = getattr(coro, "close", None)
            if callable(close):
                close()
            _LOGGER.warning(
                "[Frigate] %s task create failed | exception_type=%s: %s",
                context,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            self._sys_log(
                "WARN",
                f"[Frigate] {context} task create failed: task_create_failed "
                f"exception_type={type(exc).__name__}: {exc}",
            )
            return None
        add_done_callback = getattr(task, "add_done_callback", None)
        if callable(add_done_callback):
            add_done_callback(
                lambda done_task: self._observe_frigate_task_failure(
                    done_task,
                    context=context,
                )
            )
        return task

    def _expire_critical_frigate_event(self, now: float | None = None, *, notify: bool = True) -> bool:
        event = getattr(self, "_critical_frigate_event", None)
        if not event:
            return False
        if now is None:
            now = time.time()
        try:
            event_time = float(event.get("time") or 0)
        except Exception:
            event_time = 0
        if event_time and now - event_time <= _CRITICAL_FRIGATE_EVENT_TTL:
            return False
        self._critical_frigate_event = None
        if notify:
            try:
                self.async_set_updated_data({})
            except Exception:
                pass
        return True

    def get_critical_frigate_event(self) -> dict | None:
        """Return the current critical event after enforcing TTL expiry."""
        self._expire_critical_frigate_event(notify=False)
        return getattr(self, "_critical_frigate_event", None)

    async def _async_get_frigate_snapshot_base64(self, event_id: str) -> str | None:
        """Fetch snapshot from Frigate and convert to base64."""
        # 注意：这里假设 Frigate 在本地，可以通过 HA 的内部代理或直接访问
        # 推荐使用 HA 内部 URL，如果 HA 安装了 Frigate 集成，通常有内部 API
        url = f"http://127.0.0.1:5000/api/events/{event_id}/snapshot.jpg"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return base64.b64encode(data).decode("utf-8")
                    else:
                        self._sys_log("WARN", f"[Frigate] 无法获取快照 {event_id}: HTTP {resp.status}")
        except Exception as e:
            _LOGGER.debug("Fetch snapshot failed: %s", e)
        return None

    async def _async_get_frigate_latest_frame_base64(self, camera_id: str) -> str | None:
        """从 Frigate 获取指定摄像头的当前最新帧（不需要事件 ID）。

        使用 Frigate REST API: GET /api/{camera_name}/latest.jpg
        若 camera_id 不是合法摄像头名（如 zone 名），接口返回 404，静默跳过。
        """
        url = f"http://127.0.0.1:5000/api/{camera_id}/latest.jpg"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return base64.b64encode(data).decode("utf-8")
                    _LOGGER.debug("[Frigate] latest.jpg HTTP %s for camera=%s", resp.status, camera_id)
        except Exception as exc:
            _LOGGER.debug("[Frigate] 获取最新帧失败 camera=%s: %s", camera_id, exc)
        return None

    async def _async_do_activity_analysis(
        self,
        camera: str,
        img_b64: str,
        trigger_source: str,
        event_id: str | None = None,
    ) -> None:
        """公共行为分析核心逻辑：调用视觉 LLM、解析结果、存储到 per-camera 字典。

        Args:
            camera: 摄像头 entity ID 或 camera_id。
            img_b64: base64 编码的图像数据。
            trigger_source: 触发来源描述（如"Frigate事件"/"存在传感器"），用于日志区分。
            event_id: 若由 Frigate 事件触发，提供 event_id 以写入兼容路径；否则为 None。
        """
        camera_name = self._get_frigate_camera_name(camera)
        labels_str = "、".join(_ACTIVITY_LABELS)

        prompt = (
            f"你是智能家居行为分析助手，分析「{camera_name}」摄像头画面中人物的当前行为。\n\n"
            f"从以下选项中选择最匹配的活动标签：{labels_str}\n\n"
            "严格按照以下格式输出（不要输出其他任何内容）：\n"
            "活动标签：[选项]\n"
            "简要描述：[不超过15字]\n\n"
            "注意：若画面无人请填写「无人」；若选项不完全匹配，选最接近的一个。"
        )

        raw = await self._call_vision_llm(img_b64, prompt)
        if not raw:
            return

        label_m = re.search(r"活动标签[：:]\s*(.+)", raw)
        desc_m  = re.search(r"简要描述[：:]\s*(.+)", raw)
        label = label_m.group(1).strip() if label_m else ""
        desc  = desc_m.group(1).strip()  if desc_m  else raw[:30].strip()

        valid_label = next(
            (lb for lb in _ACTIVITY_LABELS if lb in label or label in lb), label or "未知"
        )

        self._frigate_camera_activity[camera] = {
            "label": valid_label,
            "desc": desc,
            "ts": time.time(),
        }

        if event_id:
            trigger_text = f"{valid_label} — {desc}" if desc else valid_label
            self._remember_frigate_visual_description(event_id, f"【行为识别】{trigger_text}")

        self._sys_log("INFO",
            f"[行为识别/{trigger_source}] camera={camera} 识别结果：{valid_label}（{desc}）"
        )

    async def _async_analyze_visual_event(self, event_id: str, camera: str) -> None:
        """Phase 7G 行为识别：通过 Frigate 事件快照触发视觉大模型行为分析。

        输出结构化的行为标签（如"阅读"、"看电视"），存储在 _frigate_camera_activity[camera] 中，
        供 AI 决策上下文持续使用（不依赖单个事件 ID，有效期 10 分钟）。
        """
        if not getattr(self, "_vision_enabled", False):
            return

        img_b64 = await self._async_get_frigate_snapshot_base64(event_id)
        if not img_b64:
            return

        await self._async_do_activity_analysis(camera, img_b64, "Frigate事件", event_id)

    async def _async_analyze_on_presence(self, sensor_eid: str) -> None:
        """Phase 7G 备用路径：存在传感器确认有人时主动拉取摄像头当前帧进行行为分析。

        当 Frigate 未检测到人（MQTT 事件静默）但存在传感器报告有人时，
        主动通过 Frigate REST API 获取最新帧并分析行为，确保行为分析不依赖 Frigate 人检结果。

        仅对触发传感器所关联的摄像头执行分析，避免因单一房间有人而拉取所有摄像头帧。
        """
        if not getattr(self, "_vision_enabled", False) or not getattr(self, "_frigate_enabled", False):
            return

        # 从触发传感器推导关联摄像头：
        # 优先按命名约定（binary_sensor.{camera}_person_occupancy → camera_id = {camera}）
        camera_candidates: list[str] = []

        # 尝试命名约定推导
        _bare = sensor_eid.replace("binary_sensor.", "")
        if "_person_occupancy" in _bare:
            camera_candidates.append(_bare.replace("_person_occupancy", ""))

        # 若推导失败，尝试从 device_info 获取传感器所在房间，再找同房间的摄像头
        if not camera_candidates:
            sensor_room = ""
            if hasattr(self, "device_info"):
                sensor_room = (self.device_info.get(sensor_eid) or {}).get("room", "")
            if sensor_room:
                for eid in list(self.hass.states.async_entity_ids("binary_sensor")):
                    if "person_occupancy" not in eid:
                        continue
                    cam_room = (self.device_info.get(eid) or {}).get("room", "")
                    if cam_room == sensor_room:
                        _cid = eid.replace("binary_sensor.", "").replace("_person_occupancy", "")
                        camera_candidates.append(_cid)

        if not camera_candidates:
            _LOGGER.debug("[Frigate] 无法从 %s 推导关联摄像头，跳过在场视觉分析", sensor_eid)
            return

        now = time.time()
        for camera_id in camera_candidates:
            last_analyzed = self._frigate_activity_last_analyzed.get(camera_id, 0)
            if now - last_analyzed < _ACTIVITY_ANALYSIS_COOLDOWN:
                continue

            img_b64 = await self._async_get_frigate_latest_frame_base64(camera_id)
            if not img_b64:
                continue

            self._frigate_activity_last_analyzed[camera_id] = now
            await self._async_do_activity_analysis(camera_id, img_b64, f"存在传感器({sensor_eid})")

    async def _async_start_frigate_mqtt(self) -> None:
        """订阅 Frigate MQTT events topic。在 async_start_listeners 中调用。"""
        if not getattr(self, "_frigate_enabled", False):
            return
        if self._frigate_mqtt_unsub:
            return

        try:
            from homeassistant.components.mqtt import async_subscribe
        except ImportError:
            self._sys_log("WARN", "[Frigate] MQTT 集成未安装，Frigate MQTT 深度集成不可用，将使用 HA Entity 通道")
            return

        mqtt_available = self.hass.services.has_service("mqtt", "publish")
        if not mqtt_available:
            self._sys_log("WARN", "[Frigate] MQTT 服务未就绪，Frigate MQTT 深度集成不可用")
            return

        try:
            self._frigate_mqtt_unsub = await async_subscribe(
                self.hass, "frigate/events", self._on_frigate_mqtt_event
            )
            self._sys_log("INFO", "[Frigate] MQTT 事件订阅成功 → frigate/events")
        except Exception as exc:
            self._sys_log("WARN", f"[Frigate] MQTT 订阅失败: {exc}，将使用 HA Entity 通道")
            return

        # v4.11.1：启动时扫描 HA 实体注册表，检测 Frigate 僵尸 person_occupancy 实体
        # v4.11.2：同时从 Frigate HTTP API 恢复当前活跃事件的 zone 人数，
        #          防止 HA 重启后 _frigate_zone_occupancy 从 0 开始导致感知数据断层。
        await self._async_check_frigate_zombie_entities()
        await self._async_recover_frigate_occupancy()

    async def _async_stop_frigate_mqtt(self) -> None:
        """取消 Frigate MQTT 订阅。"""
        if self._frigate_mqtt_unsub:
            try:
                self._frigate_mqtt_unsub()
            except Exception:
                pass
            self._frigate_mqtt_unsub = None
        for cancel in self._frigate_mqtt_debounce_timers.values():
            try:
                cancel()
            except Exception:
                pass
        self._frigate_mqtt_debounce_timers.clear()

    @callback
    def _on_frigate_mqtt_event(self, msg) -> None:
        """
        处理 Frigate MQTT 事件消息。

        Frigate 事件格式:
        {
            "type": "new" | "update" | "end",
            "before": { ... },
            "after": {
                "id": "1234567890.123456-abcdef",
                "camera": "chashi",
                "label": "person",
                "sub_label": null,
                "top_score": 0.85,
                "entered_zones": ["tea_room"],
                "current_zones": ["tea_room"],
                "has_snapshot": true,
                "has_clip": false,
                "thumbnail": "/api/frigate/thumbnail/...",
                ...
            }
        }
        """
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, AttributeError):
            return

        snap = self._vision_provider.parse_event_payload(payload)
        if not snap:
            return

        event_type = snap.event_type
        event_id = snap.event_id
        camera = snap.camera_id
        label = snap.label
        sub_label = snap.sub_label
        top_score = snap.score
        entered_zones = snap.entered_zones
        current_zones = snap.current_zones
        has_snapshot = snap.has_snapshot
        now = time.time()
        self._expire_critical_frigate_event(now)

        # 缓存事件（限制大小，FIFO 淘汰）
        self._frigate_events_cache[event_id] = {
            "type": event_type,
            "camera": camera,
            "label": label,
            "sub_label": sub_label,
            "score": top_score,
            "entered_zones": entered_zones,
            "current_zones": current_zones,
            "has_snapshot": has_snapshot,
            "time": now,
            "thumbnail": snap.thumbnail,
        }
        if len(self._frigate_events_cache) > _MQTT_EVENT_CACHE_SIZE:
            self._frigate_events_cache.popitem(last=False)

        # 更新 zone 占用统计（按 event_id 记住实际计入的 zone，避免 end 误扣其他追踪目标）
        occ_zones = entered_zones if event_type == "end" else current_zones
        presence_zones = self._update_zone_occupancy(camera, event_type, occ_zones, event_id)
        self._frigate_events_cache[event_id]["presence_zones"] = presence_zones
        self._record_frigate_observation(snap, zone_ids=presence_zones)

        # ── 关键视觉事件识别 (Critical Event Recognition) ──
        is_critical = False
        # 条件：门禁类摄像头 + 检测到人 + 置信度 > 0.7
        door_keywords = ("door", "entrance", "gate", "门口", "门", "玄关")
        if any(kw in camera.lower() for kw in door_keywords) and label == "person" and top_score > 0.7:
            if event_type in ("new", "update"):
                is_critical = True
        
        if is_critical:
            self._critical_frigate_event = {
                "id": event_id,
                "camera": camera,
                "camera_name": self._get_frigate_camera_name(camera),
                "snapshot": f"/api/frigate/notifications/{event_id}/snapshot.jpg",
                "time": now,
                "label": label,
                "sub_label": sub_label,
                "score": top_score,
            }
            # 视觉分析现在统一在 "new" 事件段处理（Phase 7G），此处不再单独触发
            # 广播状态变更
            self.async_set_updated_data({})
        elif event_type == "end" and self._critical_frigate_event and self._critical_frigate_event["id"] == event_id:
            # 事件结束，清除关键事件
            self._critical_frigate_event = None
            self.async_set_updated_data({})
        # ──────────────────────────────────────────────────

        if event_type == "new":
            # 新检测事件 — 延迟 N 秒触发（等待 zone 数据填充稳定）
            zones_str = ", ".join(entered_zones) if entered_zones else "无区域"
            self._sys_log("INFO",
                f"[Frigate/MQTT] 新检测: camera={camera} label={label}"
                f" score={top_score:.2f} zones=[{zones_str}] event={event_id[:12]}")

            # Phase 7G 行为识别：所有摄像头检测到人时触发，按冷却时间限流
            vision_delay = _MQTT_DEBOUNCE_NEW
            if getattr(self, "_vision_enabled", False) and label == "person":
                last_analyzed = self._frigate_activity_last_analyzed.get(camera, 0)
                if now - last_analyzed >= _ACTIVITY_ANALYSIS_COOLDOWN:
                    self._frigate_activity_last_analyzed[camera] = now
                    # 非门禁摄像头：立即分析（无需等待），不阻塞推理调度
                    self._spawn_frigate_task(
                        self._async_analyze_visual_event(event_id, camera),
                        context="Frigate visual analysis",
                    )
                    if is_critical:
                        # 门禁摄像头：增加延迟让视觉分析有时间完成，供触发文本拼接
                        vision_delay = 8

            self._schedule_frigate_inference(
                event_id, camera, entered_zones, current_zones,
                label, sub_label, top_score, "new", vision_delay
            )

        elif event_type == "update":
            # 检测更新 — 仅在 zone 变化时触发
            before = payload.get("before", {})
            old_zones = set(before.get("current_zones", []))
            new_zones = set(current_zones)
            if new_zones != old_zones and new_zones:
                added_zones = new_zones - old_zones
                if added_zones:
                    self._sys_log("INFO",
                        f"[Frigate/MQTT] 区域变化: camera={camera}"
                        f" 进入新区域={added_zones} event={event_id[:12]}")
                    self._schedule_frigate_inference(
                        event_id, camera, list(added_zones), list(new_zones),
                        label, sub_label, top_score, "zone_enter", _MQTT_DEBOUNCE_UPDATE
                    )

        elif event_type == "end":
            # 人员离开 — 延迟确认后触发
            self._sys_log("INFO",
                f"[Frigate/MQTT] 检测结束: camera={camera} event={event_id[:12]}")
            self._schedule_frigate_inference(
                event_id, camera, entered_zones, [],
                label, sub_label, top_score, "end", _MQTT_DEBOUNCE_END
            )

    def _record_frigate_observation(
        self,
        snapshot: VisionEventSnapshot,
        *,
        zone_ids: list[str] | None = None,
    ) -> None:
        """Persist a redacted, structured Frigate observation through the add-on bridge."""
        record_event = getattr(self, "_record_event", None)
        if not callable(record_event):
            return
        if zone_ids is None:
            zone_ids = list(
                snapshot.entered_zones
                if snapshot.event_type == "end"
                else (snapshot.current_zones or snapshot.entered_zones)
            )
        context = self._frigate_presence_context(
            snapshot.camera_id,
            zone_ids,
            snapshot.label,
            snapshot.event_type,
        )
        metadata = {
            "provider": snapshot.provider,
            "event_id": snapshot.event_id,
            "event_type": snapshot.event_type,
            "camera_id": snapshot.camera_id,
            "label": snapshot.label,
            "confidence": max(0.0, min(float(snapshot.score or 0.0), 1.0)),
            "has_snapshot": bool(snapshot.has_snapshot),
            **context,
        }
        try:
            record_event(
                "vision_observation",
                f"Frigate {snapshot.event_type}: {snapshot.camera_id}",
                entity_id=f"camera.{snapshot.camera_id}",
                new_state=str(context["state"]),
                source="frigate_mqtt",
                confidence=int(round(metadata["confidence"] * 100)),
                metadata=metadata,
            )
        except Exception as exc:
            _LOGGER.warning(
                "[Frigate] structured observation enqueue failed: %s",
                exc.__class__.__name__,
                exc_info=True,
            )

    def _frigate_presence_context(
        self,
        camera_id: str,
        zone_ids: list[str],
        label: str,
        event_type: str,
    ) -> dict[str, Any]:
        normalized_zones = list(dict.fromkeys(str(item) for item in zone_ids if str(item)))
        space_ids: list[str] = []
        for zone_id in normalized_zones:
            room = str(self._vision_provider.get_trigger_room(camera_id, zone_id) or "").strip()
            if room and room not in space_ids:
                space_ids.append(room)
        if not space_ids:
            room = str(self._vision_provider.get_trigger_room(camera_id) or "").strip()
            if room:
                space_ids.append(room)

        is_person = str(label or "").strip().lower() == "person"
        all_zone_counts = getattr(self, "_frigate_zone_occupancy", {})
        zone_counts = all_zone_counts.get(camera_id, {})
        event_zone_sets = [
            (event_key.split(":", 1)[0], zones)
            for event_key, zones in getattr(self, "_frigate_event_counted_zones", {}).items()
            if ":" in event_key
        ]
        if space_ids and event_zone_sets:
            people_count = sum(
                1
                for event_camera, event_zones in event_zone_sets
                if any(
                    str(
                        self._vision_provider.get_trigger_room(
                            event_camera, zone_id or None
                        )
                        or ""
                    ).strip()
                    in space_ids
                    for zone_id in event_zones
                )
            )
        elif space_ids:
            people_count = sum(
                max(0, int(count or 0))
                for observed_camera, observed_zones in all_zone_counts.items()
                for zone_id, count in observed_zones.items()
                if str(
                    self._vision_provider.get_trigger_room(observed_camera, zone_id or None)
                    or ""
                ).strip()
                in space_ids
            )
        else:
            people_count = sum(
                max(0, int(zone_counts.get(zone_id, 0) or 0))
                for zone_id in normalized_zones
            )
        if not is_person:
            state = "observed_non_person"
            people_count = 0
        elif not space_ids:
            state = "observed_unlocalized"
        elif event_type == "end" and not normalized_zones:
            state = "observed_end_unconfirmed"
        elif event_type == "end":
            state = "occupied" if people_count > 0 else "vacant"
        else:
            people_count = max(1, people_count)
            state = "occupied"
        occupied = state == "occupied"
        return {
            "state": state,
            "zone_ids": normalized_zones,
            "space_ids": space_ids,
            "occupied": occupied,
            "people_count": people_count,
        }

    def _update_zone_occupancy(
        self, camera: str, event_type: str, zones: list[str], event_id: str
    ) -> list[str]:
        """
        维护每个 zone 的实时占用状态（camera → zone → person count）。

        Args:
            zones: new/update 事件传 current_zones，end 事件传 entered_zones（离开的区域）。
        """
        cam_zones = self._frigate_zone_occupancy.setdefault(camera, {})
        if not hasattr(self, "_frigate_event_counted_zones"):
            self._frigate_event_counted_zones = {}
        normalized_zones = list(dict.fromkeys(str(zone) for zone in zones if zone))
        target_zones = set(normalized_zones) or {""}
        event_key = self._frigate_event_zone_key(camera, event_id)
        previous_zones = (
            set(self._frigate_event_counted_zones.get(event_key, set()))
            if event_key else set()
        )

        changed_zones: set[str] = set()
        event_zones = set(target_zones)

        if event_type == "end":
            zones_to_decrement = previous_zones
            for zone in zones_to_decrement:
                cam_zones[zone] = max(0, cam_zones.get(zone, 0) - 1)
            if event_key:
                self._frigate_event_counted_zones.pop(event_key, None)
            changed_zones = zones_to_decrement
            event_zones = set(zones_to_decrement)
        elif event_type in ("new", "update"):
            if event_key:
                zones_to_decrement = previous_zones - target_zones
                zones_to_increment = target_zones - previous_zones
                for zone in zones_to_decrement:
                    cam_zones[zone] = max(0, cam_zones.get(zone, 0) - 1)
                for zone in zones_to_increment:
                    cam_zones[zone] = cam_zones.get(zone, 0) + 1
                if target_zones:
                    self._frigate_event_counted_zones[event_key] = target_zones
                else:
                    self._frigate_event_counted_zones.pop(event_key, None)
                changed_zones = zones_to_decrement | zones_to_increment | target_zones
            elif event_type == "new":
                for zone in target_zones:
                    cam_zones[zone] = cam_zones.get(zone, 0) + 1
                changed_zones = target_zones

        # 更新后打印各区域当前人数，方便日志追踪
        if changed_zones and hasattr(self, "_sys_log"):
            cam_name = self._get_frigate_camera_name(camera)
            zone_counts = ", ".join(
                f"{self._get_frigate_zone_name(camera, z)}={cam_zones.get(z, 0)}人"
                for z in sorted(changed_zones)
            )
            total = sum(cam_zones.values())
            self._sys_log(
                "INFO",
                f"[Frigate/人数] {cam_name} 区域人数更新({event_type}): {zone_counts}  ·  摄像头合计={total}人",
            )
        return sorted(event_zones)

    def _schedule_frigate_inference(
        self, event_id: str, camera: str,
        entered_zones: list[str], current_zones: list[str],
        label: str, sub_label: str | None, score: float,
        event_type: str, delay: float
    ) -> None:
        """去抖调度 Frigate 触发的 AI 推理。"""
        from homeassistant.helpers.event import async_call_later
        from homeassistant.core import callback as _ha_callback

        # 同一 event_id 的重复触发取消旧计时器
        old_cancel = self._frigate_mqtt_debounce_timers.pop(event_id, None)
        if old_cancel:
            try:
                old_cancel()
            except Exception:
                pass

        # zone 冷却检查
        now = time.time()
        zones_key = f"{camera}:{','.join(sorted(entered_zones))}" if entered_zones else f"{camera}:no_zone"
        last_trigger = self._frigate_zone_last_trigger.get(zones_key, 0)
        if (now - last_trigger) < _MQTT_ZONE_COOLDOWN and event_type != "end":
            self._sys_log("INFO",
                f"[Frigate/MQTT] zone 冷却中({int(now - last_trigger)}s < {_MQTT_ZONE_COOLDOWN}s)，跳过: {zones_key}")
            self._discard_frigate_visual_description(event_id)
            return

        @_ha_callback
        def _fire_inference(_now) -> None:
            """
            在事件循环线程中执行推理调度。

            必须用 @callback 标记，否则 HA 会将其扔到 executor 线程池，
            导致在无事件循环的线程中调用 async_call_later 报 'no running event loop'。
            """
            self._frigate_mqtt_debounce_timers.pop(event_id, None)
            self._frigate_zone_last_trigger[zones_key] = time.time()

            # 获取当前缓存中的最新事件数据（可能已被 update 更新）
            cached = self._frigate_events_cache.get(event_id, {})
            final_zones = cached.get("current_zones", current_zones)
            final_entered = cached.get("entered_zones", entered_zones)
            presence_zones = cached.get("presence_zones")
            if not isinstance(presence_zones, list):
                presence_zones = list(final_entered if event_type == "end" else (final_zones or final_entered))

            # 构建结构化触发文本
            trigger = self._build_frigate_trigger(
                camera, final_entered, final_zones,
                label, sub_label, score, event_type,
                event_id=event_id
            )
            presence_context = self._frigate_presence_context(
                camera,
                presence_zones,
                label,
                event_type,
            )

            entity_id = f"camera.{camera}"
            try:
                self._schedule_inference(
                    entity_id,
                    trigger,
                    new_state=str(presence_context["state"]),
                    source_trace_context={
                        "provider": "frigate",
                        "event_id": event_id,
                        "event_type": event_type,
                        "camera_id": camera,
                        "label": label,
                        "confidence": max(0.0, min(float(score or 0.0), 1.0)),
                        **presence_context,
                    },
                )
            except Exception as exc:
                self._sys_log("ERROR", f"[Frigate/MQTT] 调度推理失败: {exc}")

        handle = async_call_later(self.hass, delay, _fire_inference)
        self._frigate_mqtt_debounce_timers[event_id] = handle

    def _build_frigate_trigger(
        self, camera: str, entered_zones: list[str], current_zones: list[str],
        label: str, sub_label: str | None, score: float, event_type: str,
        event_id: str = ""
    ) -> str:
        """
        构建 Frigate MQTT 触发的结构化触发文本。

        优先使用 DB 中绑定的房间名作为 [区域] 前缀，
        推理层（_call_ai_engine）会自动提取 [区域] 实现精确区域隔离。
        """
        camera_name = self._get_frigate_camera_name(camera)

        # 精确房间：优先从 entered_zones 的第一个 zone 查房间绑定
        # 一台摄像头可同时覆盖多个房间，需按实际触发的 zone 确定房间
        trigger_zone = (entered_zones or current_zones or [None])[0]
        if trigger_zone:
            trigger_room = self._get_frigate_zone_room(camera, trigger_zone)
        else:
            trigger_room = self._get_frigate_camera_room(camera)
        room_prefix = f"[{trigger_room}] " if trigger_room else ""
        desc = self._pop_frigate_visual_description(event_id)

        if event_type == "end":
            zone_names_end = [self._get_frigate_zone_name(camera, z) for z in entered_zones] if entered_zones else []
            zone_text = f"离开区域=[{', '.join(zone_names_end)}]" if zone_names_end else ""
            return (
                f"{room_prefix}[视觉检测] {camera_name} 人员离开"
                f"（camera.{camera}）{zone_text}"
            )

        person_desc = f"{label}"
        if sub_label:
            person_desc = f"{label}:{sub_label}"

        zone_text = ""
        if entered_zones:
            zone_names = [self._get_frigate_zone_name(camera, z) for z in entered_zones]
            zone_text = f" 进入区域=[{', '.join(zone_names)}]"
        elif current_zones:
            zone_names = [self._get_frigate_zone_name(camera, z) for z in current_zones]
            zone_text = f" 在区域=[{', '.join(zone_names)}]"

        # 附加 zone 占用统计
        occupancy_parts = []
        cam_zones = self._frigate_zone_occupancy.get(camera, {})
        for zone, count in cam_zones.items():
            if count > 0:
                zone_name = self._get_frigate_zone_name(camera, zone)
                occupancy_parts.append(f"{zone_name}:{count}人")
        occupancy_text = f" 区域人数=[{', '.join(occupancy_parts)}]" if occupancy_parts else ""

        # 附加视觉增强描述（Phase 7E）
        visual_desc = ""
        if desc:
            visual_desc = f"【视觉分析】：{desc}"

        return (
            f"{room_prefix}[视觉检测] {camera_name} 检测到{person_desc}"
            f"（camera.{camera}）置信度={score:.0%}{zone_text}{occupancy_text}\n{visual_desc}"
        )

    def _get_frigate_camera_name(self, camera_id: str) -> str:
        """
        获取 Frigate 摄像头的友好名称。

        查询优先级：
        1. SmartAgent DB frigate_cameras 表（camera → friendly_name）
        2. HA camera.* 实体 friendly_name
        3. 原始 camera_id 作为兜底
        """
        # 优先查 DB（适配摄像头未接入 HA 的场景）
        if hasattr(self, "_db"):
            try:
                rows = self._db.query(
                    "SELECT friendly_name FROM frigate_cameras WHERE camera_id=? AND enabled=1",
                    (camera_id,),
                )
                if rows and rows[0]["friendly_name"]:
                    return rows[0]["friendly_name"]
            except Exception:
                pass
        # 回退：HA 实体
        state = self.hass.states.get(f"camera.{camera_id}")
        if state:
            return state.attributes.get("friendly_name", camera_id)
        return camera_id

    def _get_frigate_camera_room(self, camera_id: str) -> str:
        """
        获取 Frigate 摄像头对应的 SmartAgent 房间名。

        查询 DB 中 frigate_cameras.room 字段，
        供 AI 推理直接使用正确的触发房间（无需解析 HA 实体区域）。

        Args:
            camera_id: Frigate 摄像头 ID（如 cam_d5fe7a4f）

        Returns:
            房间名字符串，未配置时返回空字符串。
        """
        if hasattr(self, "_db"):
            try:
                rows = self._db.query(
                    "SELECT room FROM frigate_cameras WHERE camera_id=? AND enabled=1",
                    (camera_id,),
                )
                if rows and rows[0]["room"]:
                    return rows[0]["room"]
            except Exception:
                pass
        return ""

    def _get_frigate_zone_name(self, camera_id: str, zone_id: str) -> str:
        """
        获取 Frigate zone 的友好名称。

        优先查 DB frigate_zones.friendly_name，
        回退到 zone_id 的 snake_case → Title Case 转换。

        Args:
            camera_id: 摄像头 ID
            zone_id: Frigate zone ID（snake_case）

        Returns:
            友好名称字符串。
        """
        if hasattr(self, "_db"):
            try:
                rows = self._db.query(
                    "SELECT friendly_name FROM frigate_zones WHERE camera_id=? AND zone_id=?",
                    (camera_id, zone_id),
                )
                if rows and rows[0]["friendly_name"]:
                    return rows[0]["friendly_name"]
            except Exception:
                pass
        return zone_id.replace("_", " ").title()

    def _get_frigate_zone_room(self, camera_id: str, zone_id: str) -> str:
        """
        获取 Frigate zone 对应的 SmartAgent 房间名（zone 级精确绑定）。

        一台摄像头可覆盖多个房间，需按具体 zone 查房间，
        而非使用摄像头级别的粗粒度绑定。

        查找优先级：
          1. frigate_zones 表（zone 级绑定）
          2. frigate_cameras 表（摄像头级兜底）

        Args:
            camera_id: 摄像头 ID
            zone_id: Frigate zone ID

        Returns:
            房间名字符串，未配置时返回空字符串。
        """
        if hasattr(self, "_db"):
            try:
                # 1. 优先查 zone 级绑定
                rows = self._db.query(
                    "SELECT room FROM frigate_zones WHERE camera_id=? AND zone_id=? AND room!=''",
                    (camera_id, zone_id),
                )
                if rows and rows[0]["room"]:
                    return rows[0]["room"]
                # 2. 降级到摄像头级绑定
                rows = self._db.query(
                    "SELECT room FROM frigate_cameras WHERE camera_id=? AND enabled=1 AND room!=''",
                    (camera_id,),
                )
                if rows and rows[0]["room"]:
                    return rows[0]["room"]
            except Exception:
                pass
        return ""

    def get_frigate_zone_summary(self) -> str:
        """
        获取 Frigate 各区域的实时人员占用摘要（供 AI prompt 使用）。

        Returns:
            格式化的区域占用摘要字符串，无数据时返回空字符串。
        """
        if not self._frigate_zone_occupancy:
            return ""

        parts = []
        for camera, zones in self._frigate_zone_occupancy.items():
            camera_name = self._get_frigate_camera_name(camera)
            active_zones = {z: c for z, c in zones.items() if c > 0}
            if active_zones:
                zone_strs = [f"{self._get_frigate_zone_name(camera, z)}={c}人" for z, c in active_zones.items()]
                parts.append(f"  - {camera_name}: {', '.join(zone_strs)}")
            else:
                parts.append(f"  - {camera_name}: 无人")

        if not parts:
            return ""

        return "【Frigate 视觉区域占用】\n" + "\n".join(parts)

    def _restore_frigate_occupancy_snapshot(
        self, active_events: list[dict[str, Any]]
    ) -> dict[str, dict[str, int]]:
        """Restore zone totals and per-event ownership from active Frigate events."""
        recovered: dict[str, dict[str, int]] = {}
        recovered_event_zones: dict[str, set[str]] = {}
        for event in active_events:
            if not isinstance(event, dict) or event.get("label") != "person":
                continue
            camera = str(event.get("camera") or "").strip()
            event_id = str(event.get("id") or "").strip()
            current_zones = {
                str(zone).strip().lower()
                for zone in (event.get("zones") or [])
                if str(zone or "").strip()
            }
            if not camera:
                continue
            camera_counts = recovered.setdefault(camera, {})
            if current_zones:
                for zone in current_zones:
                    camera_counts[zone] = camera_counts.get(zone, 0) + 1
                event_key = self._frigate_event_zone_key(camera, event_id)
                if event_key:
                    recovered_event_zones[event_key] = current_zones
            else:
                camera_counts[""] = camera_counts.get("", 0) + 1
                event_key = self._frigate_event_zone_key(camera, event_id)
                if event_key:
                    recovered_event_zones[event_key] = {""}

        for camera, zones in recovered.items():
            camera_counts = self._frigate_zone_occupancy.setdefault(camera, {})
            for zone, count in zones.items():
                if camera_counts.get(zone, 0) == 0:
                    camera_counts[zone] = count
        for event_key, zones in recovered_event_zones.items():
            self._frigate_event_counted_zones.setdefault(event_key, zones)
        return recovered

    async def _async_recover_frigate_occupancy(self) -> None:
        """
        从 Frigate HTTP API 恢复当前活跃事件的 zone 人数统计。

        问题背景：
          SmartAgent 使用 MQTT 事件来维护 _frigate_zone_occupancy（zone → 人数）。
          HA 或 SmartAgent 重启后，该字典从 0 开始。如果此时有人已经在检测 zone 内，
          Frigate 只会发送 "update" 事件（而非 "new"），导致人数永远无法从 0 递增，
          使得 AI 看到的 Frigate 视觉感知数据恒为空，影响展厅/客厅的精准人数判断。

        恢复策略：
          调用 Frigate API GET /api/events?has_ended=0 获取当前所有未结束的活跃追踪事件，
          统计各摄像头各 zone 的人数，初始化 _frigate_zone_occupancy。

        v4.11.2
        """
        import aiohttp

        try:
            from .frigate_config import get_cameras_from_frigate_api

            # 先获取 Frigate base URL（复用已有的 API 发现逻辑）
            _, base_url = await get_cameras_from_frigate_api()
            if not base_url:
                _LOGGER.debug("[Frigate] 占用恢复跳过：Frigate API 不可达")
                return

            active_events: list[dict] = []
            async with aiohttp.ClientSession() as _sess:
                async with _sess.get(
                    f"{base_url}/api/events",
                    params={"has_ended": "0", "include_thumbnails": "0", "limit": "200"},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status == 200:
                        active_events = await resp.json(content_type=None)
                    else:
                        _LOGGER.debug("[Frigate] 占用恢复: API 返回 %d", resp.status)
                        return

            if not active_events:
                _LOGGER.debug("[Frigate] 占用恢复: 无活跃事件，zone 人数维持 0")
                return

            recovered = self._restore_frigate_occupancy_snapshot(active_events)

            if not recovered:
                return

            # 日志汇报
            summary_parts = []
            for camera, zones in recovered.items():
                cam_name = self._get_frigate_camera_name(camera)
                zone_strs = [
                    f"{self._get_frigate_zone_name(camera, z) if z else '整体'}={c}人"
                    for z, c in zones.items() if c > 0
                ]
                if zone_strs:
                    summary_parts.append(f"{cam_name}: {', '.join(zone_strs)}")

            total_persons = sum(c for zones in recovered.values() for c in zones.values())
            self._sys_log(
                "INFO",
                f"[Frigate] 启动占用恢复：发现 {total_persons} 个活跃追踪目标"
                + (f" — {'; '.join(summary_parts)}" if summary_parts else ""),
            )

        except Exception as exc:
            _LOGGER.debug("[Frigate] 占用恢复跳过: %s", exc)

    def get_recent_frigate_events(self, limit: int = 5) -> list[dict]:
        """获取最近 N 个 Frigate 事件（供前端面板使用）。"""
        events = list(self._frigate_events_cache.values())
        events.sort(key=lambda e: e.get("time", 0), reverse=True)
        return events[:limit]

    async def _async_check_frigate_zombie_entities(self) -> None:
        """
        扫描 HA 状态机，检测 Frigate 僵尸 person_occupancy 实体。

        触发时机：Frigate MQTT 订阅成功后（系统启动阶段）。
        僵尸实体：HA 实体注册表中存在 binary_sensor.*_person_occupancy，
                  但 Frigate 配置文件（通过 HTTP API 获取）和 SmartAgent DB 中均无对应 zone，
                  说明该 zone 已被彻底删除，导致：
                    1. HA 周期性输出 "Forced update failed" 错误日志
                    2. MQTT 区域人数统计持续为 0，AI 决策缺失视觉感知数据

        判断优先级：
          1. Frigate HTTP API config（最权威：反映 Frigate 当前实际配置）
          2. SmartAgent DB frigate_zones（已绑定房间的 zone 记录）
          → 任意一处存在该 zone 名则认为合法，不标记为僵尸

        v4.11.2: 修复 v4.11.1 假阳性 bug——DB 为空时（用户未绑定 zone）会误报所有 person_occupancy 实体
        """
        try:
            from .frigate_config import get_cameras_from_frigate_api

            # ── 1. 从 Frigate HTTP API 获取实际 zones（最权威来源）──────────────
            frigate_zones_from_api: set[str] = set()
            try:
                yml_cameras, _ = await get_cameras_from_frigate_api()
                for cam in yml_cameras:
                    for zone in cam.get("zones", []):
                        frigate_zones_from_api.add(str(zone.get("zone_id", "")).lower())
                        frigate_zones_from_api.add(str(cam.get("camera_id", "")).lower())
            except Exception as _api_exc:
                _LOGGER.debug("[Frigate] 僵尸检测: API 查询失败，仅使用 DB: %s", _api_exc)

            # ── 2. 从 SmartAgent DB 收集已绑定的 zone/camera 名称 ──────────────
            db_zones: set[str] = set()
            if hasattr(self, "_db"):
                for _r in (self._db.query("SELECT zone_id FROM frigate_zones") or []):
                    db_zones.add(str(_r.get("zone_id", "")).lower())
                for _r in (self._db.query("SELECT camera_id FROM frigate_cameras") or []):
                    db_zones.add(str(_r.get("camera_id", "")).lower())

            known_zones = frigate_zones_from_api | db_zones

            # ── 3. 若两个来源均为空，说明 Frigate 不可达且 DB 未配置，跳过检测 ──
            if not known_zones:
                _LOGGER.debug(
                    "[Frigate] 僵尸实体检测跳过：Frigate API 不可达且 DB 无 zone 记录"
                    "（可能 Frigate 尚未配置或刚重启）"
                )
                return

            # ── 4. 扫描 HA 状态机 ─────────────────────────────────────────────
            zombie: list[str] = []
            _suffix = "_person_occupancy"
            for _state in self.hass.states.async_all():
                _eid = _state.entity_id
                if "person_occupancy" not in _eid.lower():
                    continue
                _local = _eid.lower().split(".")[-1]
                if not _local.endswith(_suffix):
                    continue
                _zone_cand = _local[: -len(_suffix)]
                if _zone_cand not in known_zones:
                    zombie.append(_eid)

            if zombie:
                self._sys_log(
                    "WARN",
                    "[Frigate] 检测到僵尸 person_occupancy 实体（zone 已从 Frigate 配置中删除，但实体仍在 HA 注册表）：\n"
                    + "\n".join(f"  ⛔ {e}" for e in zombie)
                    + "\n修复方法 A（推荐）：在 Frigate config.yml 中重新添加对应 zone，重启 Frigate。"
                    + "\n修复方法 B（快速）：HA → 设置 → 设备和服务 → 实体 → 搜索上述实体 → 禁用/删除 → 重启 HA。",
                )
            else:
                _LOGGER.debug("[Frigate] 未发现僵尸 person_occupancy 实体")
        except Exception as exc:
            _LOGGER.debug("[Frigate] 僵尸实体检测跳过: %s", exc)
