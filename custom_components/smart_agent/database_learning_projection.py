"""HA-side causal projection helpers for add-on owned learning."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from .arrival_lighting_learning import (
    arrival_environment_bucket,
    arrival_lighting_entity_ids,
    classify_arrival_observation,
)

_LOGGER = logging.getLogger(__name__)


class DatabaseLearningProjectionMixin:
    """Maintain bounded execution receipts and emit auditable arrival samples."""

    _RECENT_AI_ACTION_RESULT_LIMIT = 512
    _RECENT_AI_ACTION_RETENTION_SECONDS = 120.0

    @staticmethod
    def _normalized_recent_ai_action_status(value: Any) -> str:
        status = str(value or "").strip().lower()
        if status in {"ok", "executed"}:
            return "executed"
        if status == "scheduled":
            return "scheduled"
        if status in {"skip", "skipped"}:
            return "skipped"
        if status in {"blocked_or_error", "failed", "error"}:
            return "failed"
        if status.startswith("blocked"):
            return "blocked"
        return status or "unknown"

    def _record_recent_ai_action_results(
        self,
        transaction_id: int | str,
        action_results: list[dict[str, Any]],
    ) -> None:
        """Maintain a bounded HA-side causal projection of execution receipts."""
        now_ts = time.time()
        normalized: list[dict[str, Any]] = []
        for item in action_results:
            if not isinstance(item, dict):
                continue
            entity_id = str(item.get("entity_id") or "").strip()
            if not entity_id:
                continue
            success_value = item.get("success")
            normalized.append(
                {
                    "entity_id": entity_id,
                    "domain": str(
                        item.get("domain")
                        or (entity_id.split(".", 1)[0] if "." in entity_id else "")
                    ),
                    "service": str(item.get("service") or ""),
                    "status": self._normalized_recent_ai_action_status(item.get("status")),
                    "verified": bool(item.get("verified", False)),
                    "success": bool(success_value) if success_value is not None else None,
                    "time": now_ts,
                    "transaction_id": str(transaction_id or item.get("transaction_id") or ""),
                    "action_seq": int(item.get("action_seq") or 0),
                }
            )
        if not normalized:
            return

        records = getattr(self, "_recent_ai_action_results", None)
        if not isinstance(records, list):
            records = []
            self._recent_ai_action_results = records
        lock = getattr(self, "_recent_ai_action_results_lock", None)

        def _update() -> None:
            cutoff = now_ts - self._RECENT_AI_ACTION_RETENTION_SECONDS
            records[:] = [
                dict(row)
                for row in records
                if isinstance(row, dict) and float(row.get("time") or 0) >= cutoff
            ]
            for row in normalized:
                key = (
                    row["transaction_id"],
                    row["action_seq"],
                    row["entity_id"],
                )
                existing_index = next(
                    (
                        index
                        for index, existing in enumerate(records)
                        if (
                            str(existing.get("transaction_id") or ""),
                            int(existing.get("action_seq") or 0),
                            str(existing.get("entity_id") or ""),
                        )
                        == key
                    ),
                    None,
                )
                if existing_index is not None:
                    row["time"] = float(records[existing_index].get("time") or now_ts)
                    records[existing_index] = row
                else:
                    records.append(row)
            if len(records) > self._RECENT_AI_ACTION_RESULT_LIMIT:
                records[:] = records[-self._RECENT_AI_ACTION_RESULT_LIMIT :]

        if lock is not None:
            with lock:
                _update()
        else:
            _update()

    def _recent_ai_action_entities(
        self,
        *,
        since: float,
        until: float,
        statuses: set[str] | frozenset[str] = frozenset({"executed"}),
    ) -> dict[str, list[dict[str, Any]]]:
        """Return recent SmartAgent receipts grouped by entity for causal checks."""
        try:
            start = float(since)
            end = float(until)
        except (TypeError, ValueError):
            return {}
        if end < start:
            return {}
        allowed = {
            self._normalized_recent_ai_action_status(status)
            for status in statuses
            if str(status or "").strip()
        }
        records = getattr(self, "_recent_ai_action_results", None)
        if not isinstance(records, list):
            return {}
        lock = getattr(self, "_recent_ai_action_results_lock", None)

        def _snapshot() -> list[dict[str, Any]]:
            return [dict(row) for row in records if isinstance(row, dict)]

        if lock is not None:
            with lock:
                rows = _snapshot()
        else:
            rows = _snapshot()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            try:
                row_time = float(row.get("time") or 0)
            except (TypeError, ValueError):
                continue
            status = self._normalized_recent_ai_action_status(row.get("status"))
            if not start <= row_time <= end or (allowed and status not in allowed):
                continue
            row["status"] = status
            entity_id = str(row.get("entity_id") or "").strip()
            if entity_id:
                grouped.setdefault(entity_id, []).append(row)
        for entity_rows in grouped.values():
            entity_rows.sort(key=lambda row: float(row.get("time") or 0))
        return grouped

    def _record_arrival_snapshot(
        self,
        room: str,
        presence_entity_id: str,
        light_states: dict[str, str | None] | None = None,
        *,
        pre_light_states: dict[str, str | None] | None = None,
        smartagent_actions: list[dict[str, Any]] | None = None,
        state_change_evidence: dict[str, dict[str, Any]] | None = None,
        sample_started_at: float | None = None,
        sample_ended_at: float | None = None,
        environment_context: dict[str, Any] | None = None,
        occupancy_cycle_id: str = "",
    ) -> None:
        """Forward auditable arrival lighting samples to add-on owned memory."""
        try:
            local_now = getattr(self, "_ha_local_now", None)
            now_value = local_now() if callable(local_now) else None
            if hasattr(now_value, "strftime"):
                now = now_value
            else:
                from homeassistant.util import dt as dt_util
                now = dt_util.now()
        except Exception:
            try:
                from homeassistant.util import dt as dt_util
                now = dt_util.now()
            except Exception:
                from datetime import timezone
                now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        month = now.month
        season = "spring" if month in {3, 4, 5} else "summer" if month in {6, 7, 8} else "autumn" if month in {9, 10, 11} else "winter"
        try:
            dark_lux_threshold = float(
                getattr(self, "_DAYLIGHT_GUARD_LUX_THRESHOLD", 80.0)
            )
        except (TypeError, ValueError):
            dark_lux_threshold = 80.0
        environment_bucket = arrival_environment_bucket(
            environment_context if isinstance(environment_context, dict) else {},
            dark_lux_threshold=dark_lux_threshold,
        )
        if light_states is None:
            device_info = (
                getattr(self, "device_info", {})
                if isinstance(getattr(self, "device_info", None), dict)
                else {}
            )
            states = getattr(getattr(self, "hass", None), "states", None)
            lighting_entity_ids = arrival_lighting_entity_ids(
                device_info,
                room,
                entity_states=states,
            )
            light_states = {
                entity_id: (
                    getattr(states.get(entity_id), "state", None)
                    if states is not None and hasattr(states, "get")
                    else None
                )
                for entity_id in lighting_entity_ids
            }

        pre_light_states = pre_light_states if isinstance(pre_light_states, dict) else {}
        raw_actions = smartagent_actions if isinstance(smartagent_actions, list) else []
        state_change_evidence = (
            state_change_evidence if isinstance(state_change_evidence, dict) else {}
        )

        def _action_in_sample_window(action: dict[str, Any]) -> bool:
            if sample_started_at is None or sample_ended_at is None:
                return True
            try:
                action_time = float(action.get("time"))
            except (TypeError, ValueError):
                return False
            return sample_started_at <= action_time <= sample_ended_at

        window_actions = [
            dict(action)
            for action in raw_actions
            if isinstance(action, dict) and _action_in_sample_window(action)
        ]

        def _is_executed_action(action: dict[str, Any]) -> bool:
            status = str(action.get("status") or "").strip().lower()
            if status in {"ok", "executed"}:
                return True
            if (
                status in {"blocked_or_error", "failed", "error", "scheduled", "skip", "skipped"}
                or status.startswith("blocked")
            ):
                return False
            # Legacy smartagent_actions rows did not persist a status. They remain
            # causal but unverified so they cannot contaminate positive learning.
            return True

        classifications: dict[str, dict[str, Any]] = {}
        for entity_id, state in light_states.items():
            if state is None:
                continue
            observed_state = str(state or "").strip().lower() or "unknown"
            causal_actions = [
                dict(action)
                for action in window_actions
                if str(action.get("entity_id") or "").strip() == entity_id
                and _is_executed_action(action)
            ]
            transaction_ids = list(
                dict.fromkeys(
                    str(action.get("transaction_id") or "").strip()
                    for action in causal_actions
                    if str(action.get("transaction_id") or "").strip()
                )
            )
            pre_state = str(pre_light_states.get(entity_id) or "unknown").strip().lower() or "unknown"
            pre_state_known = entity_id in pre_light_states and pre_state != "unknown"
            state_changed = pre_state_known and pre_state != observed_state
            change_evidence = state_change_evidence.get(entity_id)
            change_evidence = dict(change_evidence) if isinstance(change_evidence, dict) else {}
            evidence_space = str(
                change_evidence.get("space_id")
                or change_evidence.get("room")
                or ""
            ).strip()
            scope_matches = not evidence_space or evidence_space == room
            time_window_matches = not state_changed or bool(causal_actions)
            if state_changed and not causal_actions:
                try:
                    change_time = float(change_evidence.get("time"))
                except (TypeError, ValueError):
                    change_time = 0.0
                time_window_matches = (
                    sample_started_at is not None
                    and sample_ended_at is not None
                    and sample_started_at <= change_time <= sample_ended_at
                )

            classification = classify_arrival_observation(
                pre_state=pre_state,
                observed_state=observed_state,
                change_origin=str(change_evidence.get("origin") or ""),
                causal_ai_actions=causal_actions,
                trusted_automation_source=any(
                    change_evidence.get(key) is True
                    for key in (
                        "trusted_automation_source",
                        "owner_registered",
                    )
                ),
                scope_matches=scope_matches,
                time_window_matches=time_window_matches,
            )
            exclusion_reason = classification.exclusion_reason
            if causal_actions and not any(
                bool(action.get("verified", False)) for action in causal_actions
            ):
                exclusion_reason = "execution_status_unverified"

            classifications[entity_id] = {
                "observed_state": observed_state,
                "pre_state": pre_state,
                "baseline_eligible": classification.baseline_eligible,
                "observation_only": classification.observation_only,
                "evidence_kind": classification.evidence_kind,
                "evidence_weight": classification.evidence_weight,
                "exclusion_reason": exclusion_reason,
                "smartagent_actions": causal_actions,
                "source_transaction_ids": transaction_ids,
                "state_change_evidence": change_evidence,
            }

        included_entity_ids = [
            entity_id
            for entity_id, classification in classifications.items()
            if classification["baseline_eligible"]
        ]
        excluded_entity_ids = [
            entity_id
            for entity_id, classification in classifications.items()
            if not classification["baseline_eligible"]
        ]
        observation_only_entity_ids = [
            entity_id
            for entity_id, classification in classifications.items()
            if classification["observation_only"]
        ]
        source_transaction_ids = list(
            dict.fromkeys(
                transaction_id
                for classification in classifications.values()
                for transaction_id in classification["source_transaction_ids"]
            )
        )
        arrival_trace = {
            "included_entity_ids": included_entity_ids,
            "excluded_entity_ids": excluded_entity_ids,
            "observation_only_entity_ids": observation_only_entity_ids,
            "source_transaction_ids": source_transaction_ids,
            "exclusions": [
                {
                    "entity_id": entity_id,
                    "reason": classification["exclusion_reason"],
                    "transaction_ids": classification["source_transaction_ids"],
                }
                for entity_id, classification in classifications.items()
                if not classification["baseline_eligible"]
            ],
        }

        for entity_id, state in light_states.items():
            if state is None:
                continue
            classification = classifications[entity_id]
            observed_state = classification["observed_state"]
            entity_actions = classification["smartagent_actions"]
            linked_action = entity_actions[-1] if entity_actions else {}
            payload = {
                "action": "arrival_sample",
                "time": timestamp,
                "entity_id": entity_id,
                "room": room,
                "presence_entity_id": presence_entity_id,
                "occupancy_cycle_id": str(occupancy_cycle_id or "").strip(),
                "pre_state": classification["pre_state"],
                "observed_state": observed_state,
                "is_on": observed_state == "on",
                "baseline_eligible": classification["baseline_eligible"],
                "observation_only": classification["observation_only"],
                "environment_bucket": environment_bucket,
                "evidence_kind": classification["evidence_kind"],
                "evidence_weight": classification["evidence_weight"],
                "trust_state": (
                    "verified"
                    if classification["baseline_eligible"]
                    else "observation_only"
                ),
                "exclusion_reason": classification["exclusion_reason"],
                "smartagent_actions": entity_actions,
                "state_change_evidence": classification["state_change_evidence"],
                "source_transaction_ids": classification["source_transaction_ids"],
                "arrival_sample": arrival_trace,
                "sample_started_at": sample_started_at,
                "sample_ended_at": sample_ended_at,
                "hour_bucket": now.hour,
                "season": season,
                "origin": "presence_arrival_observation",
                "actor": presence_entity_id or "unknown",
                "decision_id": str(linked_action.get("decision_id") or "not_applicable"),
                "transaction_id": str(linked_action.get("transaction_id") or "not_applicable"),
                "world_snapshot_id": str(linked_action.get("world_snapshot_id") or "not_applicable"),
            }
            enqueue = getattr(self, "_enqueue_internal_event", None)
            if not callable(enqueue) or not enqueue("baseline", payload, ts=timestamp):
                _LOGGER.debug("[ArrivalBaseline] sample enqueue failed: %s", entity_id)
