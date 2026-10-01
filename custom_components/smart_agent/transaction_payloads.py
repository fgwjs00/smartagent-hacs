"""Strict transaction record decoding before audit projection or persistence."""
from __future__ import annotations

import json
from typing import Any


class TransactionPayloadError(ValueError):
    """Expose location and transaction identity without embedding private JSON."""

    def __init__(self, *, operation: str, field: str, transaction_id: int, reason: str, index: int | None = None) -> None:
        self.operation = operation
        self.field = field
        self.transaction_id = transaction_id
        self.reason = reason
        self.index = index
        super().__init__(
            f"transaction_payload_invalid: operation={operation} field={field} "
            f"transaction_id={transaction_id} reason={reason}"
            + (f" index={index}" if index is not None else "")
        )


def decode_transaction_records(
    value: str, *, operation: str, field: str, transaction_id: int = 0,
) -> list[dict[str, Any]]:
    """Keep an explicit empty list valid; never turn corrupt records into no actions."""
    try:
        decoded = json.loads(value)
    except (ValueError, TypeError) as exc:
        raise TransactionPayloadError(
            operation=operation, field=field, transaction_id=transaction_id, reason="invalid_json",
        ) from exc
    if not isinstance(decoded, list):
        raise TransactionPayloadError(
            operation=operation, field=field, transaction_id=transaction_id, reason="expected_list",
        )
    for index, item in enumerate(decoded):
        if not isinstance(item, dict):
            raise TransactionPayloadError(
                operation=operation, field=field, transaction_id=transaction_id,
                reason="expected_record", index=index,
            )
    return decoded
