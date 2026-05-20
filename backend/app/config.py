from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Iterable


REQUIRED_RUNTIME_KEYS = (
    "DATABASE_URL",
    "REDIS_URL",
    "MODEL_PROVIDER",
    "MODEL_NAME",
    "BROWSER_MCP_SERVICE_NAME",
)

REQUIRED_E2E_KEYS = (
    "WEBUI_BASE_URL",
    "API_BASE_URL",
    "TEST_SUPPLIER_SITE_URL",
    "TEST_SUPPLIER_EMAIL",
    "TEST_SUPPLIER_TELEGRAM",
    "EMAIL_CONNECTOR_PROVIDER",
    "TELEGRAM_CONNECTOR_PROVIDER",
)


@dataclass(frozen=True)
class Settings:
    app_env: str
    webui_base_url: str
    api_base_url: str
    database_url: str
    redis_url: str
    model_provider: str
    model_name: str
    ollama_base_url: str
    ollama_timeout_seconds: int
    browser_provider: str
    browser_mcp_service_name: str
    browser_mcp_url: str
    browser_mcp_command: str
    browser_mcp_args: str
    browser_allowed_domains: str
    browser_research_mode: str
    browser_allow_public_internet: bool
    internet_search_url_template: str
    internet_search_result_limit: int
    web_search_provider: str
    web_search_engines: str
    web_search_url: str
    web_search_result_limit: int
    ai_search_query_count: int
    ai_search_candidate_limit: int
    email_connector_provider: str
    email_smtp_host: str
    email_smtp_port: int
    email_smtp_user: str
    email_smtp_password: str
    email_from: str
    email_use_tls: bool
    email_use_ssl: bool
    email_timeout_seconds: int
    email_inbound_provider: str
    email_imap_host: str
    email_imap_port: int
    email_imap_user: str
    email_imap_password: str
    email_imap_mailbox: str
    email_inbound_sync_limit: int
    telegram_connector_provider: str
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_timeout_seconds: int
    test_supplier_site_url: str
    test_supplier_email: str
    test_supplier_telegram: str
    auto_process_search_tasks: bool = False
    auto_process_supplier_contact_tasks: bool = False
    auto_process_contract_tasks: bool = False
    auto_sync_gmail_inbound: bool = True
    gmail_inbound_sync_interval_seconds: float = 30.0
    allow_products_without_contacts: bool = False
    search_contact_enrichment_pages: int = 1
    contracts_database_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        _load_local_env_file()
        return cls(
            app_env=os.getenv("APP_ENV", "local"),
            webui_base_url=os.getenv("WEBUI_BASE_URL", "http://localhost:5173"),
            api_base_url=os.getenv("API_BASE_URL", "http://localhost:8000/api"),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://product_sourcing:change-me@localhost:5432/product_sourcing",
            ),
            contracts_database_url=os.getenv(
                "CONTRACTS_DATABASE_URL",
                "postgresql+psycopg://product_sourcing:change-me@localhost:5432/product_sourcing_contracts",
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            model_provider=os.getenv("MODEL_PROVIDER", ""),
            model_name=os.getenv("MODEL_NAME", ""),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_timeout_seconds=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")),
            browser_provider=os.getenv("BROWSER_PROVIDER", "playwright_mcp"),
            browser_mcp_service_name=os.getenv("BROWSER_MCP_SERVICE_NAME", "browser-mcp"),
            browser_mcp_url=os.getenv("BROWSER_MCP_URL", ""),
            browser_mcp_command=os.getenv("BROWSER_MCP_COMMAND", "npx"),
            browser_mcp_args=os.getenv("BROWSER_MCP_ARGS", "@playwright/mcp@latest --headless --isolated"),
            browser_allowed_domains=os.getenv("BROWSER_ALLOWED_DOMAINS", ""),
            browser_research_mode=os.getenv("BROWSER_RESEARCH_MODE", "site"),
            browser_allow_public_internet=_env_bool("BROWSER_ALLOW_PUBLIC_INTERNET", False),
            internet_search_url_template=os.getenv(
                "INTERNET_SEARCH_URL_TEMPLATE",
                "https://www.adafruit.com/search?q={query}",
            ),
            internet_search_result_limit=int(os.getenv("INTERNET_SEARCH_RESULT_LIMIT", "5")),
            web_search_provider=os.getenv("WEB_SEARCH_PROVIDER", ""),
            web_search_engines=os.getenv("WEB_SEARCH_ENGINES", ""),
            web_search_url=os.getenv("WEB_SEARCH_URL", "http://localhost:8888/search"),
            web_search_result_limit=int(os.getenv("WEB_SEARCH_RESULT_LIMIT", "20")),
            ai_search_query_count=int(os.getenv("AI_SEARCH_QUERY_COUNT", "3")),
            ai_search_candidate_limit=int(os.getenv("AI_SEARCH_CANDIDATE_LIMIT", "5")),
            search_contact_enrichment_pages=int(os.getenv("SEARCH_CONTACT_ENRICHMENT_PAGES", "1")),
            email_connector_provider=os.getenv("EMAIL_CONNECTOR_PROVIDER", ""),
            email_smtp_host=os.getenv("EMAIL_SMTP_HOST", ""),
            email_smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
            email_smtp_user=os.getenv("EMAIL_SMTP_USER", ""),
            email_smtp_password=os.getenv("EMAIL_SMTP_PASSWORD", ""),
            email_from=os.getenv("EMAIL_FROM", ""),
            email_use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() in {"1", "true", "yes", "on"},
            email_use_ssl=os.getenv("EMAIL_USE_SSL", "false").lower() in {"1", "true", "yes", "on"},
            email_timeout_seconds=int(os.getenv("EMAIL_TIMEOUT_SECONDS", "30")),
            email_inbound_provider=os.getenv("EMAIL_INBOUND_PROVIDER", ""),
            email_imap_host=os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com"),
            email_imap_port=int(os.getenv("EMAIL_IMAP_PORT", "993")),
            email_imap_user=os.getenv("EMAIL_IMAP_USER", os.getenv("EMAIL_SMTP_USER", "")),
            email_imap_password=os.getenv("EMAIL_IMAP_PASSWORD", os.getenv("EMAIL_SMTP_PASSWORD", "")),
            email_imap_mailbox=os.getenv("EMAIL_IMAP_MAILBOX", "INBOX"),
            email_inbound_sync_limit=int(os.getenv("EMAIL_INBOUND_SYNC_LIMIT", "20")),
            telegram_connector_provider=os.getenv("TELEGRAM_CONNECTOR_PROVIDER", ""),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            telegram_timeout_seconds=int(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "30")),
            test_supplier_site_url=os.getenv("TEST_SUPPLIER_SITE_URL", ""),
            test_supplier_email=os.getenv("TEST_SUPPLIER_EMAIL", "supplier-e2e@example.test"),
            test_supplier_telegram=os.getenv("TEST_SUPPLIER_TELEGRAM", "@supplier_e2e_test"),
            auto_process_search_tasks=_env_bool("AUTO_PROCESS_SEARCH_TASKS", False),
            auto_process_supplier_contact_tasks=_env_bool("AUTO_PROCESS_SUPPLIER_CONTACT_TASKS", False),
            auto_process_contract_tasks=_env_bool("AUTO_PROCESS_CONTRACT_TASKS", False),
            auto_sync_gmail_inbound=_env_bool("AUTO_SYNC_GMAIL_INBOUND", True),
            gmail_inbound_sync_interval_seconds=float(os.getenv("GMAIL_INBOUND_SYNC_INTERVAL_SECONDS", "30")),
            allow_products_without_contacts=_env_bool("ALLOW_PRODUCTS_WITHOUT_CONTACTS", False),
        )


def missing_env(keys: Iterable[str]) -> list[str]:
    return [key for key in keys if not os.getenv(key)]


def require_runtime_env() -> None:
    missing = missing_env(REQUIRED_RUNTIME_KEYS)
    if missing:
        raise RuntimeError(f"Missing runtime environment variables: {', '.join(missing)}")


def require_e2e_env() -> None:
    missing = missing_env(REQUIRED_RUNTIME_KEYS + REQUIRED_E2E_KEYS)
    if missing:
        raise RuntimeError(f"Missing E2E environment variables: {', '.join(missing)}")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _load_local_env_file(path: str | Path | None = None) -> None:
    if (
        path is None
        and ("PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules)
        and os.getenv("LOAD_DOTENV_IN_TESTS", "").lower() not in {"1", "true", "yes", "on"}
    ):
        return
    env_path = Path(path) if path is not None else Path(os.getcwd()) / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key or normalized_key in os.environ:
            continue
        os.environ[normalized_key] = value.strip().strip('"').strip("'")
