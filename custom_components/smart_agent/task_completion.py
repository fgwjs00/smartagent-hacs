"""Read completed HA task outcomes and report safe, correlated diagnostics."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TaskCompletion:
    cancelled: bool = False
    error: BaseException | None = None
    phase: str = "result"


def read_task_completion(task: Any) -> TaskCompletion:
    try:
        if hasattr(task, "cancelled") and task.cancelled():
            return TaskCompletion(cancelled=True)
        error = task.exception()
    except asyncio.CancelledError:
        return TaskCompletion(cancelled=True)
    except Exception as exc:
        return TaskCompletion(error=exc, phase="read_result")
    return TaskCompletion(error=error)


def report_task_completion(
    task: Any, completion: TaskCompletion, *, logger: logging.Logger, operation: str,
    system_log: Callable[..., None] | None = None, system_level: str = "WARN",
) -> str:
    code = "task_cancelled" if completion.cancelled else "background_task_failed"
    state = "cancelled" if completion.cancelled else "failed"
    if completion.phase == "create":
        code, state = "task_create_failed", "create failed"
    elif completion.phase == "observe":
        code, state = "task_observer_failed", "observer failed"
    exception_type = "CancelledError" if completion.cancelled else type(completion.error).__name__
    message = (f"{operation} task {state}: {code} operation={operation} task_id={id(task):x} "
               f"phase={completion.phase} exception_type={exception_type}")
    logger.warning(message)
    if callable(system_log):
        try:
            system_log(system_level, message)
        except Exception as exc:
            logger.warning("task_log_failed operation=%s task_id=%x phase=system_log exception_type=%s",
                           operation, id(task), type(exc).__name__)
    return message


def create_ha_task(
    factory: Callable[[Any], Any], coro: Any, *, logger: logging.Logger, operation: str,
    system_log: Callable[..., None] | None = None, system_level: str = "WARN",
) -> Any:
    """Close rejected coroutine objects even on cancellation, then propagate."""
    try:
        return factory(coro)
    except BaseException:
        try:
            close = getattr(coro, "close", None)
            if callable(close):
                close()
        except Exception as exc:
            report_task_completion(coro, TaskCompletion(error=exc, phase="close_coroutine"),
                                   logger=logger, operation=operation,
                                   system_log=system_log, system_level=system_level)
        raise


def observe_ha_task(
    task: Any, callback: Callable[[Any], None], *, logger: logging.Logger, operation: str,
    system_log: Callable[..., None] | None = None,
) -> Any:
    """Report observer failure without cancelling or retrying an admitted task."""
    try:
        task.add_done_callback(callback)
    except Exception as exc:
        report_task_completion(task, TaskCompletion(error=exc, phase="observe"),
                               logger=logger, operation=operation, system_log=system_log)
    return task
