"""Queue the existing Presence candidate's due occurrence using HA timers."""
from __future__ import annotations

import copy
import time
from datetime import datetime
from typing import Any
from homeassistant.core import callback

VACANT_STATES = {"off", "closed", "not_home", "away", "idle", "clear", "empty", "vacant"}


def schedule_hold(owner: Any, entity_id: str, *, new_state: str,
                  presence: Any, reference: Any, schedule: Any) -> None:
    if str(new_state).lower() not in VACANT_STATES:
        owner._cancel_presence_temporal_recheck(entity_id)
        return
    if not isinstance(reference, dict):
        return
    reference = copy.deepcopy(reference)
    occurrence = reference.get("task_occurrence")
    if not isinstance(occurrence, dict):
        return
    try:
        due = datetime.fromisoformat(occurrence["scheduled_for_utc"].replace("Z", "+00:00")).timestamp()
    except (KeyError, TypeError, ValueError):
        return
    owner._cancel_presence_temporal_recheck(entity_id)
    timers = getattr(owner, "_presence_off_timers", None)
    if not isinstance(timers, dict):
        timers = owner._presence_off_timers = {}
    cancel = None

    @callback
    def recheck(_: datetime) -> None:
        nonlocal cancel
        if timers.get(entity_id) is not cancel:
            return
        if time.time() < due:
            cancel = schedule(owner.hass, due - time.time(), recheck)
            timers[entity_id] = cancel
            return
        timers.pop(entity_id, None)
        state = owner.hass.states.get(entity_id)
        if str(getattr(state, "state", "")).lower() not in VACANT_STATES:
            return
        owner._schedule_inference(
            "", "presence_hold_recheck", source_trace_context={
                "source": "presence_hold_recheck", "presence_hold_ref": reference,
            },
        )

    cancel = schedule(owner.hass, max(0.0, due - time.time()), recheck)
    timers[entity_id] = cancel
