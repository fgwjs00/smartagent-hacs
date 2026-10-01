"""HA transaction audit transport; physical dispatch never retries a lost receipt."""
from __future__ import annotations

import logging
from typing import Any

from .transaction_payloads import decode_transaction_records

_LOGGER = logging.getLogger(__name__)


def mark_transaction_audit(results: list[dict[str, Any]], confirmed: bool) -> None:
    for result in results:
        trace = dict(result.get("decision_trace") or {})
        if confirmed:
            trace.pop("audit_persistence", None)
        else:
            trace["audit_persistence"] = "unknown"
        if trace:
            result["decision_trace"] = trace
        elif "decision_trace" in result:
            result.pop("decision_trace")


class DatabaseTransactionMixin:
    def _persist_transaction_event(self, kind: str, payload: dict, timestamp: str) -> bool:
        post = getattr(self, "_post_internal_event_confirmed", None)
        try:
            receipt = post(kind, payload, ts=timestamp) if callable(post) else None
        except Exception as exc:
            _LOGGER.warning("[Transaction] audit transport failed: kind=%s cause=%s", kind, type(exc).__name__)
            return False
        confirmed = (
            isinstance(receipt, dict)
            and receipt.get("ok") is True
            and receipt.get("persistence_confirmed") is True
        )
        if not confirmed:
            _LOGGER.warning("[Transaction] audit persistence unconfirmed: kind=%s txn_id=%s", kind, payload["transaction_id"])
        return confirmed

    def _begin_transaction_db(
        self,
        trigger_summary: str,
        scene_desc: str,
        confidence: int,
        action_count: int,
        pre_states_json: str,
        actions_json: str,
    ) -> int:
        now = self._ha_db_now_text()
        txn_id = self._ha_transaction_id_ms()
        actions_payload = decode_transaction_records(
            actions_json, operation="DatabaseMixin._begin_transaction_db",
            field="actions_json", transaction_id=txn_id,
        )
        payload = {
            "transaction_id": str(txn_id),
            "created_at": now,
            "status": "pending",
            "trigger_summary": trigger_summary[:200],
            "scene_desc": scene_desc[:200],
            "confidence": int(confidence),
            "action_count": int(action_count),
            "rollback_json": pre_states_json,
            "envelope_json": {"actions": actions_payload},
        }
        if not self._persist_transaction_event("transaction_start", payload, now):
            _LOGGER.warning("[Transaction] begin persistence unconfirmed: trigger=%s", trigger_summary[:60])
            return 0
        return txn_id

    def _complete_transaction_db(
        self,
        txn_id: int,
        dispatched: int,
        blocked: int,
        failed: int,
        results_json: str,
    ) -> bool:
        if not txn_id:
            return False
        action_results = self._decode_transaction_action_results(results_json, transaction_id=txn_id)
        status = self._transaction_end_status(
            action_results,
            dispatched=dispatched,
            blocked=blocked,
            failed=failed,
        )
        timestamp = self._ha_db_now_text()
        payload = {
            "transaction_id": str(txn_id),
            "updated_at": timestamp,
            "status": status,
            "final_outcome": status,
            "blocked_count": int(blocked),
            "failed_count": int(failed),
            "action_results": action_results,
            "result": {
                "dispatched_count": int(dispatched),
                "blocked_count": int(blocked),
                "failed_count": int(failed),
                "action_results": action_results,
                "results": results_json,
            },
        }
        confirmed = self._persist_transaction_event("transaction_end", payload, timestamp)
        mark_transaction_audit(action_results, confirmed)
        self._record_recent_ai_action_results(txn_id, action_results)
        return confirmed

    @staticmethod
    def _decode_transaction_action_results(
        results_json: str, *, transaction_id: int = 0,
    ) -> list[dict[str, Any]]:
        return decode_transaction_records(
            results_json, operation="DatabaseMixin._complete_transaction_db",
            field="results_json", transaction_id=transaction_id,
        )

    @staticmethod
    def _transaction_end_status(
        action_results: list[dict[str, Any]],
        *,
        dispatched: int,
        blocked: int,
        failed: int,
    ) -> str:
        has_scheduled = any(
            str(item.get("status") or "") in {"scheduled", "delayed"}
            for item in action_results
        )
        all_skipped = bool(action_results) and all(
            str(item.get("status") or "").strip().lower() in {"skip", "skipped"}
            or str(item.get("ha_command_status") or "").strip().lower() == "skipped"
            for item in action_results
        )
        if has_scheduled:
            return "scheduled"
        if all_skipped and dispatched == 0 and blocked == 0 and failed == 0:
            return "skipped"
        if failed == 0 and (dispatched > 0 or blocked == 0):
            return "success"
        if dispatched > 0 and failed > 0:
            return "partial"
        if dispatched == 0 and blocked > 0:
            return "blocked"
        return "failed"

    def _rollback_transaction_db(self, txn_id: int) -> dict | None:
        _LOGGER.warning(
            "[Transaction] legacy local rollback lookup disabled; use add-on rollback service: txn_id=%s",
            txn_id,
        )
        return None

    def _query_recent_transactions(self, limit: int = 30) -> list[dict]:
        _LOGGER.warning(
            "[Transaction] legacy local transaction query disabled; use add-on transaction read API: limit=%s",
            limit,
        )
        return []
