from __future__ import annotations

import asyncio
import json
from typing import Any


def request_json(app, method: str, path: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
    return asyncio.run(_request_json(app, method, path, payload, headers or {}))


async def _request_json(app, method: str, path: str, payload: dict[str, Any] | None, headers: dict[str, str]):
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else b""
    messages = []
    raw_headers = [(b"content-type", b"application/json")]
    raw_headers.extend((key.lower().encode("ascii"), value.encode("ascii")) for key, value in headers.items())

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    sent_request = False

    async def receive():
        nonlocal sent_request
        if not sent_request:
            sent_request = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)

    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    if not response_body:
        return status, None
    text = response_body.decode("utf-8")
    try:
        return status, json.loads(text)
    except json.JSONDecodeError:
        return status, text
