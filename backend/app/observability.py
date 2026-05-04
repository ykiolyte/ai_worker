from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SECRET_MARKERS = ("password", "token", "secret", "api_key", "apikey", "credential")
REDACTED = "***REDACTED***"


def build_log_event(
    *,
    task_type: str,
    status: str,
    duration_ms: int,
    agent_task_id: str | None = None,
    search_request_id: str | None = None,
    product_id: str | None = None,
    contact_attempt_id: str | None = None,
    error: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    event = {
        "task_type": task_type,
        "status": status,
        "duration_ms": duration_ms,
        "agent_task_id": agent_task_id,
        "search_request_id": search_request_id,
        "product_id": product_id,
        "contact_attempt_id": contact_attempt_id,
    }
    if error:
        event["error"] = error
    if extra:
        event["extra"] = redact_secrets(extra)
    return event


def redact_secrets(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted = {}
        for key, item in value.items():
            if is_secret_key(str(key)):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def is_secret_key(key: str) -> bool:
    normalized = key.lower()
    return any(marker in normalized for marker in SECRET_MARKERS)


def public_error_message(error: Exception) -> str:
    text = str(error)
    if any(marker in text.lower() for marker in SECRET_MARKERS) or "traceback" in text.lower():
        return "Не удалось выполнить операцию. Подробности сохранены в журнале."
    return f"Не удалось выполнить операцию: {text}"

