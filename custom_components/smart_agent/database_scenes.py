"""HA-local bridge helpers for AI scene projections."""
from __future__ import annotations

import logging

from .scene_attribution import ai_scene_space_attribution


_LOGGER = logging.getLogger(__name__)


class DatabaseSceneBridgeMixin:
    """Keep legacy HA scene projections behind the database bridge boundary."""

    def _query_ai_scenes(self, status: str | None = None) -> list[dict]:
        try:
            if status:
                return self._db.query(
                    "SELECT * FROM ai_scenes WHERE status=? ORDER BY confidence DESC, id DESC",
                    (status,),
                )
            return self._db.query("SELECT * FROM ai_scenes ORDER BY confidence DESC, id DESC")
        except Exception as exc:
            _LOGGER.warning("[AiScenes] query failed: %s", exc)
            return []

    def _upsert_ai_scene(
        self,
        name: str,
        description: str,
        entities_json: str,
        trigger_context: str,
        hour_start: int,
        hour_end: int,
        weekday_mask: str,
        confidence: int,
        hit_count: int,
        actions_json: str = "[]",
    ) -> None:
        now = self._ha_db_now_text()
        space_id, room, explain_bundle = ai_scene_space_attribution(
            entities_json,
            actions_json,
            getattr(self, "device_info", {}),
            source="ha_ai_scene_bridge",
        )
        payload = {
            "action": "upsert",
            "name": name,
            "description": description,
            "entities_json": entities_json,
            "actions_json": actions_json,
            "trigger_context": trigger_context,
            "hour_start": int(hour_start),
            "hour_end": int(hour_end),
            "weekday_mask": weekday_mask,
            "confidence": int(confidence),
            "hit_count": int(hit_count),
            "status": "pending",
            "source": "auto",
            "space_id": space_id,
            "room": room,
            "explain_bundle": explain_bundle,
            "created": now,
            "updated": now,
        }
        if not self._enqueue_bridge_event("ai_scene", payload, ts=now):
            _LOGGER.warning("[AiScenes] upsert enqueue failed: name=%s", name)

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
        now = self._ha_db_now_text()
        space_id, room, explain_bundle = ai_scene_space_attribution(
            entities_json,
            actions_json,
            getattr(self, "device_info", {}),
            source="ha_ai_scene_bridge",
        )
        payload = {
            "action": "upsert",
            "name": name,
            "description": description,
            "entities_json": entities_json,
            "actions_json": actions_json,
            "trigger_context": trigger_context,
            "hour_start": int(hour_start),
            "hour_end": int(hour_end),
            "weekday_mask": weekday_mask,
            "confidence": int(confidence),
            "hit_count": 0,
            "status": "pending",
            "source": "manual",
            "space_id": space_id,
            "room": room,
            "explain_bundle": explain_bundle,
            "created": now,
            "updated": now,
        }
        if not self._enqueue_bridge_event("ai_scene", payload, ts=now):
            _LOGGER.warning("[AiScenes] manual upsert enqueue failed: name=%s", name)
            return False
        return True

    def _update_ai_scene_status(self, scene_id: int, status: str) -> bool:
        now = self._ha_db_now_text()
        payload = {"action": "update_status", "id": int(scene_id), "status": status, "updated": now}
        if not self._enqueue_bridge_event("ai_scene", payload, ts=now):
            _LOGGER.warning("[AiScenes] status enqueue failed: id=%s", scene_id)
            return False
        return True

    def _update_ai_scene_ha_entity(self, scene_id: int, ha_entity_id: str) -> bool:
        now = self._ha_db_now_text()
        ok = self._db_exec(
            "UPDATE ai_scenes SET ha_entity_id=?, updated=? WHERE id=?",
            (ha_entity_id, now, scene_id),
        )
        if not ok:
            _LOGGER.warning("[AiScenes] HA entity update failed: id=%s", scene_id)
        return bool(ok)

    def _mark_ai_scene_ephemeral(self, scene_id: int) -> bool:
        now = self._ha_db_now_text()
        payload = {"action": "mark_ephemeral", "id": int(scene_id), "updated": now}
        if not self._enqueue_bridge_event("ai_scene", payload, ts=now):
            _LOGGER.warning("[AiScenes] ephemeral marker enqueue failed: id=%s", scene_id)
            return False
        return True

    def _delete_ai_scene_db(self, scene_id: int) -> bool:
        payload = {"action": "delete", "id": int(scene_id)}
        if not self._enqueue_bridge_event("ai_scene", payload):
            _LOGGER.warning("[AiScenes] delete enqueue failed: id=%s", scene_id)
            return False
        return True
