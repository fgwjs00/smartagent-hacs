"""Translate native execution observations into the existing listener lineage.

These HA events contain bookkeeping only; they never call a device service.
HA assigns their authenticated sender context. Command receipts supply the
actual service context, including when a state event preceded the receipt.
"""
from __future__ import annotations

import time
from typing import Any

EVENT_NATIVE_EXECUTION = "smartagent_native_execution"


class NativeExecutionAttribution:
    def __init__(self, owner: Any) -> None:
        self.owner = owner
        self.users: set[str] = set()
        self.pending: dict[str, dict] = {}
        self.deferred: dict[str, list] = {}

    def _prune(self) -> None:
        now = time.monotonic()
        self.pending = {key: row for key, row in self.pending.items() if row["expires"] > now}
        for context_id, rows in list(self.deferred.items()):
            kept = [item for item in rows if item[0] > now]
            if kept:
                self.deferred[context_id] = kept
            else:
                self.deferred.pop(context_id, None)

    async def observe(self, event: Any) -> None:
        self._prune()
        data = event.data
        sender = str(getattr(getattr(event, "context", None), "user_id", None) or "")
        transaction_id = str(data.get("transaction_id") or "")
        if not sender or not transaction_id:
            return
        if data.get("phase") == "prepared":
            pending = self.pending[transaction_id] = {
                "sender": sender, "intent": data.get("execution_intent"),
                "prepared_at": time.time(),
                "source": data.get("source"),
                "expires": time.monotonic() + float(data.get("observation_seconds", 120)),
                "entities": {row["entity_id"] for row in data.get("commands", [])},
                "command_count": len(data.get("commands", [])), "received": set(),
                "commands": data.get("commands", []), "not_sent": set(),
                "lineage": data.get("lineage") or {},
            }
            # Register the pending sender before awaiting the HA user lookup;
            # a state event can otherwise outrun this bookkeeping event.
            user = await self.owner.hass.auth.async_get_user(sender)
            pending["system_user"] = getattr(user, "is_system_generated", None)
            if pending["system_user"] is True:
                self.users.add(sender)
            elif pending["system_user"] is False:
                self._flush_human_observations(sender)
            return
        pending = self.pending.get(transaction_id)
        if data.get("phase") != "receipt" or pending is None or pending["sender"] != sender:
            return
        cache = self.owner._prune_manual_service_contexts()
        manual = pending["intent"] == "user_explicit"
        for row in data.get("results", []):
            context = row.get("ha_context") or {}
            context_id = str(context.get("id") or "")
            if context_id or row.get("executed") is False:
                pending["received"].add(row.get("action_seq", 0))
            if row.get("executed") is False:
                pending["not_sent"].add(row.get("action_seq", 0))
                pending["entities"] = {item["entity_id"] for index, item in enumerate(pending["commands"])
                                       if index not in pending["not_sent"]}
            if not context_id:
                continue
            if cache.get(context_id, {}).get("transaction_id") == transaction_id:
                continue
            cache[context_id] = {
                "origin": "user_action" if manual else "smartagent",
                "actor": "smartagent:manual" if manual else "smartagent:execution",
                "context_id": context_id, "root_context_id": context_id,
                "transaction_id": transaction_id, "native_execution": True,
                "execution_transaction_id": transaction_id,
                "time": time.time(),
            }
            events = self.deferred.pop(context_id, [])
            for deferred_id, deferred_rows in list(self.deferred.items()):
                child_rows = [item for item in deferred_rows
                              if getattr(item[1].data.get("new_state").context, "parent_id", None) == context_id]
                if child_rows:
                    events.extend(child_rows)
                    remaining = [item for item in deferred_rows if item not in child_rows]
                    if remaining:
                        self.deferred[deferred_id] = remaining
                    else:
                        self.deferred.pop(deferred_id, None)
            if manual:
                # Replay only exactly correlated state events. A poll with no
                # context is never promoted to a user gesture by timing alone.
                for _, state_event, observed_at in events:
                    self._record_manual_observation(state_event, observed_at, params=row.get("data") or {})
            elif row.get("verified") is True and row.get("state_attribution") == "smartagent_context":
                # Keep existing correction attribution, without promoting a
                # reported setpoint to an environmental/learning success.
                lineage = pending["lineage"]
                parent_id = lineage.get("decision_transaction_id") or lineage.get("parent_transaction_id") or transaction_id
                self.owner._last_ai_actions[row["entity_id"]] = {
                    **lineage,
                    "state": (row.get("reported_state") or {}).get("state", ""),
                    "time": time.time(), "service": f"{row['domain']}.{row['service']}",
                    "origin": "smartagent", "actor": "smartagent:execution",
                    "transaction_id": parent_id, "execution_transaction_id": transaction_id,
                    "decision_id": lineage.get("decision_id") or parent_id,
                    "context_id": context_id,
                }
                cycle = str(lineage.get("occupancy_cycle_id") or "")
                current = getattr(self.owner, "_device_priority_map", {}).get(row["entity_id"], {})
                newer_manual = (current.get("priority") == 1
                                and float(current.get("time", 0)) >= pending["prepared_at"])
                if cycle and not newer_manual and pending["source"] != "smartagent_active_ai":
                    from .const import SOURCE_AI_INFER
                    # Native fast-path execution no longer returns through the
                    # old HACS writer. Preserve its occupancy-cycle lineage for
                    # later patrol/departure arbitration, never as a user sample.
                    self.owner._record_device_operation(
                        row["entity_id"], SOURCE_AI_INFER,
                        (row.get("reported_state") or {}).get("state", ""),
                        row.get("data") or {}, occupancy_cycle_id=cycle,
                    )
        # Keep unresolved, contextless updates as observations for the bounded
        # period; ending the HTTP request is not proof a slow device has stopped.
        pending["completed"] = len(pending["received"]) == pending["command_count"]
        if pending.get("system_user") is False:
            self._flush_human_observations(sender)

    def _flush_human_observations(self, sender: str) -> None:
        if not any(
            row["sender"] == sender and not row.get("completed") for row in self.pending.values()
        ):
            # Development may use a human's HA token. Other contexts from that
            # same person remain their real dashboard/physical service actions.
            for context_id, rows in list(self.deferred.items()):
                if all(self._sender_of(row[1].data["new_state"]) == sender for row in rows):
                    self.deferred.pop(context_id, None)
                    for _, state_event, observed_at in rows:
                        self._record_manual_observation(state_event, observed_at)

    def _sender_of(self, state: Any) -> str:
        context = getattr(state, "context", None)
        user_id = str(getattr(context, "user_id", None) or "")
        if user_id:
            return user_id
        parent = self.owner._prune_manual_service_contexts().get(getattr(context, "parent_id", None)) or {}
        actor = str(parent.get("actor") or "")
        return actor.removeprefix("ha_user:") if actor.startswith("ha_user:") else ""

    def _record_manual_observation(self, event: Any, observed_at: float, *, params: dict | None = None) -> None:
        """Complete learning only; never replay old events into the world model."""
        from .const import SOURCE_DASHBOARD

        owner = self.owner
        entity_id = event.data["entity_id"]
        old, new = event.data["old_state"], event.data["new_state"]
        old_state, new_state = getattr(old, "state", ""), getattr(new, "state", "")
        info = dict(owner.device_info.get(entity_id) or {})
        owner._record_arrival_manual_action_evidence(
            entity_id=entity_id, old_state=old_state, new_state=new_state, new_state_obj=new,
            source_type="用户界面", device_info=info, occurred_at=observed_at,
        )
        owner._record_silent_learning_behavior_sample(
            entity_id, old_state, new_state, "用户界面", old, new, observed_at=observed_at,
        )
        current_time = max(float((getattr(owner, key, {}).get(entity_id) or {}).get("time") or 0)
                           for key in ("_device_priority_map", "_user_overrides", "_user_manual_actions"))
        if current_time >= observed_at:
            return
        owner._record_device_operation(entity_id, SOURCE_DASHBOARD, new_state, params, occurred_at=observed_at)
        owner._record_implicit_reverse_correction(
            entity_id=entity_id, domain=entity_id.split(".", 1)[0], old_state=old_state,
            new_state=new_state, new_state_obj=new, source_type="用户界面", device_info=info,
        )

    def attribution(self, state: Any, entity_id: str) -> dict | None:
        self._prune()
        context = getattr(state, "context", None)
        context_id = str(getattr(context, "id", None) or "")
        parent_id = str(getattr(context, "parent_id", None) or "")
        cache = self.owner._prune_manual_service_contexts()
        for key in (context_id, parent_id):
            found = cache.get(key)
            if found and found.get("native_execution"):
                return dict(found)
        user_id = self._sender_of(state)
        if user_id in self.users:
            return {"origin": "system_action", "actor": "smartagent:unresolved_context", "context_id": context_id}
        if user_id and any(user_id == row["sender"] and (
            not row.get("completed") or row.get("system_user") is None
        ) for row in self.pending.values()):
            return {"origin": "system_action", "actor": "smartagent:unresolved_context", "context_id": context_id}
        if not user_id and not parent_id and any(entity_id in row["entities"] for row in self.pending.values()):
            return {"origin": "observation", "actor": "unknown", "context_id": context_id}
        return None

    def defer(self, event: Any) -> None:
        state = event.data.get("new_state")
        context = getattr(state, "context", None)
        context_id = str(getattr(context, "id", None) or "")
        if context_id:
            self.deferred.setdefault(context_id, []).append((time.monotonic() + 120, event, time.time()))
