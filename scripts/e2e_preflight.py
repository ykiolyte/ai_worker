from __future__ import annotations

import os
import json
import socket
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


REQUIRED_ENV = [
    "WEBUI_BASE_URL",
    "API_BASE_URL",
    "TEST_SUPPLIER_SITE_URL",
    "TEST_SUPPLIER_EMAIL",
    "TEST_SUPPLIER_TELEGRAM",
    "POSTGRES_HOST",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "WORKER_SERVICE_NAME",
    "BROWSER_PROVIDER",
    "BROWSER_MCP_SERVICE_NAME",
    "BROWSER_MCP_URL",
    "EMAIL_CONNECTOR_PROVIDER",
    "EMAIL_SMTP_HOST",
    "EMAIL_SMTP_PORT",
    "EMAIL_FROM",
    "TELEGRAM_CONNECTOR_PROVIDER",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "MODEL_PROVIDER",
    "MODEL_NAME",
]


def load_env_file(path: Path | None = None) -> None:
    env_path = path or Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env() -> list[str]:
    return [key for key in REQUIRED_ENV if not os.getenv(key)]


def require_url(name: str, path: str = "") -> str | None:
    base = os.getenv(name)
    if not base:
        return f"{name} is not set"
    try:
        with urlopen(f"{base.rstrip('/')}{path}", timeout=5) as response:
            if response.status >= 400:
                return f"{name} returned HTTP {response.status}"
    except Exception as exc:
        return f"{name} is not reachable: {exc}"
    return None


def require_api_health() -> str | None:
    base = os.getenv("API_BASE_URL")
    if not base:
        return "API_BASE_URL is not set"
    parsed = urlsplit(base)
    health_url = urlunsplit((parsed.scheme, parsed.netloc, "/health", "", ""))
    try:
        with urlopen(health_url, timeout=5) as response:
            if response.status >= 400:
                return f"API health returned HTTP {response.status}"
    except Exception as exc:
        return f"API health is not reachable: {exc}"
    return None


def require_tcp(host_name: str, port_name: str) -> str | None:
    host = os.getenv(host_name)
    port = os.getenv(port_name)
    if not host or not port:
        return f"{host_name}/{port_name} is not set"
    try:
        with socket.create_connection((host, int(port)), timeout=5):
            return None
    except Exception as exc:
        return f"{host_name}:{port} is not reachable: {exc}"


def require_browser_mcp() -> str | None:
    endpoint = os.getenv("BROWSER_MCP_URL")
    if not endpoint:
        return "BROWSER_MCP_URL is not set"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "product-sourcing-e2e-preflight", "version": "0.1.0"},
        },
    }
    try:
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8").strip()
            if response.status >= 400:
                return f"BROWSER_MCP_URL returned HTTP {response.status}"
            if body and "jsonrpc" not in body and "data:" not in body:
                return "BROWSER_MCP_URL did not return an MCP JSON-RPC response"
    except Exception as exc:
        return f"BROWSER_MCP_URL is not reachable: {exc}"
    return None


def main() -> int:
    load_env_file()
    errors = [f"missing env: {key}" for key in require_env()]
    errors.extend(
        error
        for error in [
            require_url("WEBUI_BASE_URL"),
            require_api_health(),
            require_url("TEST_SUPPLIER_SITE_URL"),
            require_browser_mcp(),
            require_tcp("EMAIL_SMTP_HOST", "EMAIL_SMTP_PORT"),
        ]
        if error
    )

    if errors:
        print("E2E preflight failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("E2E preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
