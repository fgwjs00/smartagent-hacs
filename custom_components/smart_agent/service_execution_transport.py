"""Existing canonical call and legacy parameter fallback with explicit context."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any
from .service_execution_context import ServiceCallContext
from .action_execution_diagnostics import action_failure_details
from .service_execution_errors import (
    ServiceErrorRecorder,
    is_param_rejection,
)


@dataclass(frozen=True, slots=True)
class ServiceEnvelopeTransport:
    host: Any
    context: ServiceCallContext
    errors: ServiceErrorRecorder
    missing_service_error: type[Exception]
    color_param_keys: Any

    async def _call(self, data: dict[str, Any]) -> dict[str, Any]:
        host, context = self.host, self.context
        batch, call = context.batch, context.call
        correlations = getattr(host, "_active_service_correlation_ids", None)
        if not isinstance(correlations, dict):
            correlations = {}
            host._active_service_correlation_ids = correlations
        task = asyncio.current_task()
        previous = correlations.get(task)
        if batch.correlation_id:
            correlations[task] = batch.correlation_id
        try:
            active_kwargs = (
                {
                    "world_snapshot_id": batch.world_snapshot_id,
                    "active_space_id": batch.active_space_id,
                    "decision_time": batch.decision_time,
                    "target_space_id": context.target_space_id,
                    "cmd_source": batch.cmd_source,
                    "require_world_snapshot_guard": True,
                    "decision_contract_lineage": batch.decision_contract_lineage,
                    "user_intent_authority": batch.user_intent_authority,
                }
                if batch.require_world_snapshot_guard
                else {}
            )
            return await host._execute_enveloped_service(
                call.domain,
                call.service,
                call.entity_id,
                data,
                call.reason,
                batch.transaction_id,
                context.action_seq,
                **active_kwargs,
            )
        finally:
            if previous:
                correlations[task] = previous
            else:
                correlations.pop(task, None)

    def _initial_failure(self, error: Exception) -> bool:
        return self.errors.after_exception(error, self.context.batch, operation="service_call")

    async def _bare_retry(self) -> dict[str, Any] | bool:
        try:
            return await self._call({})
        except self.missing_service_error:
            raise
        except Exception as error:
            return self.errors.after_exception(
                error, self.context.batch, operation="service_bare_retry", overwrite_stale=True,
            )

    async def _retry_without_color(self, data: dict[str, Any]) -> dict[str, Any] | bool:
        try:
            return await self._call(data)
        except self.missing_service_error:
            raise
        except Exception as error:
            if not is_param_rejection(error):
                return self.errors.after_exception(
                    error, self.context.batch, operation="service_color_retry", overwrite_stale=True,
                )
            action_failure_details(
                self.context.batch, self.context.action_seq, error, operation="service_color_param_rejected",
            )
            self.host._sys_log(
                "WARN", f"[动作] {self.context.call.entity_id} 亮度参数也失败，去除全部扩展参数重试"
            )
            return await self._bare_retry()

    async def _legacy_fallback(self, data: dict[str, Any], error: Exception) -> dict[str, Any] | bool:
        keys = list(data)
        color_keys = [key for key in keys if key in self.color_param_keys]
        non_color = {key: value for key, value in data.items() if key not in self.color_param_keys}
        entity_id = self.context.call.entity_id
        action_failure_details(
            self.context.batch, self.context.action_seq, error, operation="service_params_rejected",
        )
        if color_keys and non_color:
            self.host._sys_log(
                "WARN", f"[动作] {entity_id} 不支持色温参数，保留亮度重试"
            )
            return await self._retry_without_color(non_color)
        self.host._sys_log("WARN", f"[动作] {entity_id} 不支持扩展参数，去除后重试")
        return await self._bare_retry()

    async def execute(self, data: dict[str, Any]) -> dict[str, Any] | bool:
        try:
            return await self._call(data)
        except Exception as error:
            # Canonical admission covers exact parameters. Never strip or retry them.
            if self.context.batch.require_world_snapshot_guard:
                return self._initial_failure(error)
            if list(data) and is_param_rejection(str(error).lower()):
                return await self._legacy_fallback(data, error)
            return self._initial_failure(error)
