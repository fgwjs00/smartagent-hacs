"""Scene deduplication; authorization and effects belong to execution preflight.

A scene name or its guessed room cannot describe the actions inside it. Keep
opaque scene/script calls on the normal service/registry/authorization path.
"""

from __future__ import annotations
import time
from typing import Any
from .action_execution_context import ActionCall, ActionGuardOutcome


def _scene_cooldown_guard(host: Any, call: ActionCall) -> ActionGuardOutcome | None:
    now = time.time()
    last = host._scene_last_exec.get(call.entity_id, 0)
    if now - last < host._SCENE_COOLDOWN:
        remain = int(host._SCENE_COOLDOWN - (now - last))
        host._sys_log(
            "INFO",
            f"[场景冷却] {call.entity_id} 距上次执行 {int(now - last)}s < {host._SCENE_COOLDOWN}s，跳过（{remain}s 后可再执行）",
        )
        return ActionGuardOutcome(
            {
                "entity_id": call.entity_id,
                "service": call.service,
                "status": "skip",
                "msg": "scene_cooldown",
            }
        )
    return None


def evaluate_scene_guards(host: Any, call: ActionCall) -> ActionGuardOutcome | None:
    if call.domain in ("script", "scene"):
        outcome = _scene_cooldown_guard(host, call)
        if outcome is not None:
            return outcome
        host._sys_log(
            "INFO",
            f"[动作] 场景/脚本通过前置守卫，转交统一保护链: {call.domain}.{call.service}({call.entity_id})",
        )
    return None
