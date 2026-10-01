"""Own one fast-path event claim until its terminal acknowledgement is verified."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
import logging

_LOGGER = logging.getLogger("custom_components.smart_agent.fast_path_listener")


def _terminal_response(terminal: Any) -> tuple[int, dict[str, Any], bool]:
    terminal_status = int(terminal.get("__status") or 0) if isinstance(terminal, dict) else 0
    terminal_claim = (
        terminal.get("event_claim")
        if isinstance(terminal, dict) and isinstance(terminal.get("event_claim"), dict)
        else {}
    )
    return (
        terminal_status,
        terminal_claim,
        not (
            not isinstance(terminal, dict)
            or terminal.get("ok") is not True
            or not (200 <= terminal_status < 300)
            or terminal_claim.get("state") != "finalized"
            or terminal_claim.get("current_stage") != "terminal"
            or terminal_claim.get("continuation_token")
        ),
    )


@dataclass(slots=True)
class FastPathClaim:
    host: Any
    client: Any
    entity_id: str
    request_id: str
    current: dict[str, Any]

    async def _send(self, finalizer: Callable[..., Awaitable[Any]], outcome: str) -> Any:
        try:
            terminal = await finalizer(
                event_claim=dict(self.current),
                attempt_id=self.request_id,
                outcome=outcome,
            )
        except Exception as exc:
            _LOGGER.debug(
                "[Listeners] fast-path event claim finalize failed: %s",
                exc,
            )
            terminal = None
        return terminal

    async def finalize(self, outcome: str, *, required_for_action: bool = False) -> bool:
        if not self.current:
            if required_for_action:
                self.host._sys_log(
                    "ERROR",
                    "[Add-on FastPath] action blocked; terminal event claim is missing "
                    f"| entity={self.entity_id} request_id={self.request_id}",
                )
                return False
            return True
        finalizer = getattr(
            self.client,
            "finalize_decision_fast_path_claim",
            None,
        )
        if not callable(finalizer):
            self.host._sys_log(
                "ERROR",
                "[Add-on FastPath] terminal claim endpoint unavailable "
                f"| entity={self.entity_id} claim_id={self.current.get('claim_id') or '-'}",
            )
            return False
        terminal = await self._send(finalizer, outcome)
        terminal_status, terminal_claim, accepted = _terminal_response(terminal)
        if not accepted:
            self.host._sys_log(
                "ERROR",
                "[Add-on FastPath] terminal claim rejected; action delivery remains blocked "
                f"| entity={self.entity_id} claim_id={self.current.get('claim_id') or '-'} "
                f"status={terminal_status}",
            )
            return False
        self.current = dict(terminal_claim)
        return True
