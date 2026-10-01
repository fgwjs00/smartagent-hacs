"""Explicit availability for the optional HA-local scene projection."""
from __future__ import annotations
from typing import Any


class SceneProjectionUnavailable(RuntimeError):
    def __init__(self, cause: BaseException | None = None) -> None:
        self.error_id = str(getattr(cause, "error_id", "ha_scene_projection"))
        super().__init__(f"ai_scene_projection_unavailable: error_id={self.error_id}")


def refresh_ai_scene_projection(owner: Any) -> None:
    try:
        rows = owner._query_ai_scenes()
    except Exception as exc:
        owner._ai_scenes_read_error = exc
        raise
    owner._ai_scenes_cache = rows
    owner._ai_scenes_read_error = None


def ai_scene_projection_context(owner: Any) -> dict[str, Any]:
    error = getattr(owner, "_ai_scenes_read_error", None)
    rows = getattr(owner, "_ai_scenes_cache", [])
    if error is not None or not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return {"available": False, "error": "ai_scene_projection_unavailable",
                "error_id": str(getattr(error, "error_id", "ha_scene_projection")), "scenes": []}
    return {"available": True, "scenes": [dict(row) for row in rows]}


def require_ai_scene_projection(owner: Any) -> list[dict]:
    projection = ai_scene_projection_context(owner)
    if not projection["available"]:
        cause = getattr(owner, "_ai_scenes_read_error", None)
        raise SceneProjectionUnavailable(cause) from cause
    return projection["scenes"]
