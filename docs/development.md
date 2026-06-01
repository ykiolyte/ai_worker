# Development

## SourcingAI-like Search Runtime

The `enhance-sourcingai-like-search` change adds a clean-room SourcingAI-like
search flow. The implementation uses the project's own domain model and
connectors; it does not copy Made-in-China code/assets, call private APIs,
replay signed requests, use unauthorized sessions, or bypass CAPTCHA/WAF/rate
limits.

Production-like runtime must use durable storage:

- Backend `create_app()` uses a SQLAlchemy/PostgreSQL-backed repository by
  default outside explicit unit-test injection.
- Worker runtime uses the same `DATABASE_URL` repository and processes durable
  queued `AgentTask` records.
- `InMemoryRepository` is only for explicitly injected tests/local isolated
  contracts.

Provider configuration:

```env
ENABLE_MADE_IN_CHINA_PROVIDER=false
MADE_IN_CHINA_PROVIDER_MAX_RESULTS=20
MADE_IN_CHINA_PROVIDER_RATE_LIMIT_SECONDS=3
SEARCH_PROVIDER_ORDER=made_in_china_public,generic_web,browser_mcp
DISABLE_DEMO_PRODUCT_INJECTION=true
```

Set `DISABLE_DEMO_PRODUCT_INJECTION=true` or `APP_ENV=e2e` for acceptance runs.
Final E2E still requires real WebUI, Backend API, PostgreSQL, broker, worker,
ModelProvider, Browser MCP, email connector, Telegram connector when configured,
and the controlled supplier test site.

## Prerequisites

- Python 3.12+
- Node.js 24+
- Docker with Docker Compose
- OpenSpec CLI

On Windows, prefer `openspec.cmd` and `npm.cmd` from PowerShell.

## Environment

Start from `.env.example` and provide real values for local development and E2E:

- PostgreSQL connection: `DATABASE_URL`, `POSTGRES_*`
- Broker: `REDIS_URL`
- Model provider: `MODEL_PROVIDER`, `MODEL_NAME`
- Local model runtime: `OLLAMA_BASE_URL`, `OLLAMA_TIMEOUT_SECONDS`
- Browser MCP: `BROWSER_PROVIDER`, `BROWSER_MCP_SERVICE_NAME`,
  `BROWSER_MCP_URL`, `BROWSER_MCP_COMMAND`, `BROWSER_MCP_ARGS`,
  `BROWSER_ALLOWED_DOMAINS`, `BROWSER_RESEARCH_MODE`,
  `BROWSER_ALLOW_PUBLIC_INTERNET`, `INTERNET_SEARCH_URL_TEMPLATE`,
  `INTERNET_SEARCH_RESULT_LIMIT`
- Wide web search: `WEB_SEARCH_PROVIDER`, `WEB_SEARCH_URL`,
  `WEB_SEARCH_RESULT_LIMIT`, `AI_SEARCH_QUERY_COUNT`,
  `AI_SEARCH_CANDIDATE_LIMIT`
- Email connector: `EMAIL_CONNECTOR_PROVIDER`, `EMAIL_SMTP_*`,
  `EMAIL_USE_TLS`, `EMAIL_USE_SSL`
- Telegram connector: `TELEGRAM_CONNECTOR_PROVIDER`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, `TELEGRAM_TIMEOUT_SECONDS`
- Controlled supplier contour: `TEST_SUPPLIER_*`

For local UI/API checks, `.env.example` uses:

```text
MODEL_PROVIDER=local_demo
MODEL_NAME=browser-extraction-v0
TELEGRAM_BOT_TOKEN=telegram-placeholder-not-used
TELEGRAM_CHAT_ID=telegram-placeholder-chat-not-used
AUTO_PROCESS_SEARCH_TASKS=true
AUTO_PROCESS_SUPPLIER_CONTACT_TASKS=true
```

`local_demo` means the MVP does not call a real LLM for product search yet; the
worker path extracts structured product data through Browser MCP. Replace these
values before the final `test_protocol.md` acceptance run. In production-like
runs, `MODEL_PROVIDER` is the model vendor/runtime identifier, for example
`openai`, `openrouter`, `anthropic`, `qwen`, or an internal gateway name.
`MODEL_NAME` is the exact model id accepted by that provider, for example
`gpt-4.1-mini`, `qwen-plus`, or a provider-specific hosted model name.

To search broadly across the public web with local AI instead of only the
controlled supplier site, set these values in `.env`, pull the model, and
recreate the stack:

```powershell
MODEL_PROVIDER=ollama
MODEL_NAME=mistral-nemo:12b
BROWSER_RESEARCH_MODE=ai_internet
BROWSER_ALLOW_PUBLIC_INTERNET=true
WEB_SEARCH_PROVIDER=duckduckgo
WEB_SEARCH_URL=https://duckduckgo.com/html/
WEB_SEARCH_RESULT_LIMIT=20
AI_SEARCH_QUERY_COUNT=3
AI_SEARCH_CANDIDATE_LIMIT=5
INTERNET_SEARCH_RESULT_LIMIT=5
ALLOW_PRODUCTS_WITHOUT_CONTACTS=true
powershell -ExecutionPolicy Bypass -File scripts/install-ollama-portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/start-ollama-local.ps1
powershell -ExecutionPolicy Bypass -File scripts/pull-local-model.ps1 -ModelName mistral-nemo:12b
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

This uses local Ollama for query planning and result selection, a public web
search provider for discovery, and Browser MCP for extracting selected public
product pages. Docker Compose can still use local SearXNG by setting
`WEB_SEARCH_PROVIDER=searxng` and `WEB_SEARCH_URL=http://localhost:8888/search`.
Your RTX 4070 SUPER and 32 GB RAM are a good fit for `mistral-nemo:12b` as the
local default for search planning/ranking. It is substantially stronger than
the previous 3B model while still fitting comfortably on the project drive.
Docker Desktop still needs working NVIDIA/WSL GPU passthrough for GPU speed.

Queries containing `site:https://example.com` remain bounded to that site even
when internet mode is enabled.

## Local Services

Without Docker:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

This starts:

- Backend API: `http://localhost:8000`
- WebUI: `http://localhost:5173`
- Controlled supplier site: `http://localhost:8088`

Docker Compose:

```powershell
docker compose up --build
```

Expected service health:

- Backend: `GET http://localhost:8000/health`
- WebUI: `http://localhost:5173`
- PostgreSQL: healthy through `pg_isready`
- Redis: healthy through `redis-cli ping`
- Browser MCP: `http://localhost:8931/mcp`
- SearXNG metasearch: `http://localhost:8888`
- Ollama local model API: `http://localhost:11434`
- Mailpit mailbox: `http://localhost:8025`

The compose stack runs Microsoft Playwright MCP as the primary browser
connector, SearXNG as local web discovery, host Ollama as the local model
runtime, and Mailpit as a controlled SMTP mailbox for E2E email sending. For host-only local
runs, keep `BROWSER_MCP_URL=` so the backend uses stdio Playwright MCP,
`OLLAMA_BASE_URL=http://localhost:11434`,
`WEB_SEARCH_PROVIDER=duckduckgo`, `WEB_SEARCH_URL=https://duckduckgo.com/html/`,
and `EMAIL_SMTP_HOST=localhost`. Inside compose, backend and worker are
overridden to use `browser-mcp`, host Ollama via
`DOCKER_OLLAMA_BASE_URL=http://host.docker.internal:11434`, `searxng`,
`mailpit`, and `supplier-site` service names.

For a live local Gmail check, set `AUTO_PROCESS_SUPPLIER_CONTACT_TASKS=true`
and replace the local Mailpit SMTP values with Gmail SMTP values from
`docs/connectors.md`. The product page button still creates a supplier-contact
task first; the backend then schedules the worker in the background so the UI
can show the saved outbound message after refresh.

Telegram E2E requires a project-owned bot and chat/channel. Set
`TELEGRAM_CONNECTOR_PROVIDER=telegram_bot`, `TELEGRAM_BOT_TOKEN`, and
`TELEGRAM_CHAT_ID` in `.env` before running the full acceptance checklist.
You can fill local secrets without printing them to the terminal history:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/configure-secrets.ps1
```

## Test Order

Use TDD for each OpenSpec task:

1. Add or update a failing test.
2. Implement the smallest production change.
3. Run the targeted test.
4. Run the wider test suite.

Current repository-level checks:

```powershell
python -m unittest discover -s tests
python scripts/verify_traceability.py
openspec.cmd validate add-product-sourcing-mvp --strict --no-interactive
```

Before the production-like E2E run:

```powershell
python scripts/e2e_preflight.py
```

## E2E Boundary

The final `test_protocol.md` run must use real services and controlled test
contacts. Do not use mock connectors, fake workers, manual database insertion,
static UI data, in-memory databases, pre-baked LLM output, or pseudo
email/Telegram sending for E2E acceptance.
