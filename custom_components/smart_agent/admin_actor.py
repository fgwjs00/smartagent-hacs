"""Pure current-HA-user predicates for host authority boundaries.

This module deliberately does not implement delegation.  Callers may use the
user predicate for current user gestures and the admin predicate for registry
or configuration maintenance.  Automation/system contexts fail closed.
"""
from __future__ import annotations

import math
import time
from typing import Any


_ENTITY_CALL_CONTEXT_MAX_AGE_SECONDS = 5.0


def is_current_human_user(user: Any) -> bool:
    """Return whether *user* is a current active non-system HA user."""

    return bool(
        user is not None
        and getattr(user, "is_active", None) is True
        and getattr(user, "is_system_generated", None) is False
    )


def is_current_human_admin(user: Any) -> bool:
    """Return whether *user* is a current active non-system HA administrator."""

    return bool(
        is_current_human_user(user)
        and getattr(user, "is_admin", None) is True
    )


async def _current_human_user_for_entity_call(
    hass: Any,
    entity: Any,
    *,
    now: float | int | None = None,
) -> Any | None:
    """Resolve a fresh HA entity-service context to its current human user.

    Home Assistant sets ``entity._context`` immediately before invoking an
    entity service method.  The timestamp check prevents a direct/internal
    caller from reusing a previous user's context after that service
    call has completed.
    """

    current_time: float
    if now is None:
        current_time = time.time()
    elif type(now) in {int, float} and math.isfinite(float(now)):
        current_time = float(now)
    else:
        return None

    context_set = getattr(entity, "_context_set", None)
    if (
        type(context_set) not in {int, float}
        or not math.isfinite(float(context_set))
    ):
        return None
    context_age = current_time - float(context_set)
    if context_age < 0 or context_age > _ENTITY_CALL_CONTEXT_MAX_AGE_SECONDS:
        return None

    context = getattr(entity, "_context", None)
    user_id = getattr(context, "user_id", None)
    if (
        type(user_id) is not str
        or not user_id.strip()
        or user_id != user_id.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in user_id)
    ):
        return None

    try:
        auth = getattr(hass, "auth")
        user = await auth.async_get_user(user_id)
    except Exception:
        return None
    return user if is_current_human_user(user) else None


async def is_current_human_user_entity_call(
    hass: Any,
    entity: Any,
    *,
    now: float | int | None = None,
) -> bool:
    """Return whether this fresh entity-service call has a current HA user."""

    user = await _current_human_user_for_entity_call(hass, entity, now=now)
    return user is not None


async def is_current_human_admin_entity_call(
    hass: Any,
    entity: Any,
    *,
    now: float | int | None = None,
) -> bool:
    """Return whether this fresh entity-service call has a current HA admin."""

    user = await _current_human_user_for_entity_call(hass, entity, now=now)
    return is_current_human_admin(user)


async def current_human_admin_for_entity_call(
    hass: Any,
    entity: Any,
    *,
    now: float | int | None = None,
) -> Any | None:
    """Return the exact fresh current admin actor, or ``None`` fail closed."""

    user = await _current_human_user_for_entity_call(hass, entity, now=now)
    return user if is_current_human_admin(user) else None


__all__ = [
    "current_human_admin_for_entity_call",
    "is_current_human_admin",
    "is_current_human_admin_entity_call",
    "is_current_human_user",
    "is_current_human_user_entity_call",
]
