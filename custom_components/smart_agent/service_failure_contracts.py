"""Stable transport error codes preserve the existing legacy retry classifiers."""
from __future__ import annotations


def is_service_missing_error(error: Exception | str) -> bool:
    text = str(error).lower()
    return text in {"ha_service_missing", "ha_service_missing_params_rejected"} or (
        "not found" in text or "unknown" in text or "does not exist" in text
    )


def service_failure_error_type(error: Exception | str) -> str:
    return "service_missing" if is_service_missing_error(error) else "ha_service_error"


def is_param_rejection(error: Exception | str) -> bool:
    text = str(error).lower()
    return text in {"ha_service_params_rejected", "ha_service_missing_params_rejected"} or (
        "extra keys" in text or "not allowed" in text or "unexpected" in text
    )


def service_failure_code(error: Exception | str) -> str:
    missing = is_service_missing_error(error)
    if is_param_rejection(error):
        return "ha_service_missing_params_rejected" if missing else "ha_service_params_rejected"
    return "ha_service_missing" if missing else "ha_service_call_failed"
