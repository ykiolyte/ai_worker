# Connectors

## Public Sourcing Providers

The SourcingAI-like search provider layer is clean-room and public-only.
Providers return raw `ProductCandidate` data with provenance; candidates are not
trusted product records until `ProductNormalizer`, `ProductFitEvaluator`, and
domain validation accept them.

The Made-in-China-like provider may use only public pages visible in a normal
browser/search flow. It must not use private or undocumented endpoints, cookies,
tokens, signed request replay, login-only data, CAPTCHA/WAF bypass, or copied
proprietary implementation. If a page is protected or private, the provider must
skip it or fail safely.

Supported provider-related environment variables:

```env
ENABLE_MADE_IN_CHINA_PROVIDER=false
MADE_IN_CHINA_PROVIDER_MAX_RESULTS=20
MADE_IN_CHINA_PROVIDER_RATE_LIMIT_SECONDS=3
SEARCH_PROVIDER_ORDER=made_in_china_public,generic_web,browser_mcp
```

The MVP uses explicit connector interfaces so business logic does not depend on
vendor-specific SDKs.

## BrowserMcpConnector

Purpose: product research through the browser MCP service.

MVP implementation: `PlaywrightMcpBrowserConnector`.

Default local provider:

```text
BROWSER_PROVIDER=playwright_mcp
BROWSER_MCP_URL=
BROWSER_MCP_COMMAND=npx.cmd
BROWSER_MCP_ARGS=--yes @playwright/mcp@latest --headless --isolated --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

If `BROWSER_MCP_URL` is set, the connector uses MCP Streamable HTTP JSON-RPC.
If the URL is empty, it starts a stdio MCP process from
`BROWSER_MCP_COMMAND` and `BROWSER_MCP_ARGS`.

Expected behavior:

- accept a search query;
- open real controlled supplier pages during E2E;
- optionally open a public search result page for normal internet queries;
- return structured product candidates;
- report structured errors when browser research fails.
- restrict browsing to `BROWSER_ALLOWED_DOMAINS`.

Required environment:

- `BROWSER_PROVIDER`
- `BROWSER_MCP_SERVICE_NAME`
- `BROWSER_MCP_URL`
- `BROWSER_MCP_COMMAND`
- `BROWSER_MCP_ARGS`
- `BROWSER_ALLOWED_DOMAINS`
- `BROWSER_RESEARCH_MODE`
- `BROWSER_ALLOW_PUBLIC_INTERNET`
- `INTERNET_SEARCH_URL_TEMPLATE`
- `INTERNET_SEARCH_RESULT_LIMIT`
- `TEST_SUPPLIER_SITE_URL`

Security posture:

- Playwright MCP is the default MVP browser provider.
- Browserbase and Hyperbrowser can be added later behind the same connector
  boundary.
- The MVP connector uses fixed read-only Playwright snippets for page links and
  product details. Model output never supplies arbitrary browser code.
- Every URL must match the configured allowlist before navigation.
- Public internet search requires `BROWSER_RESEARCH_MODE=internet` and
  `BROWSER_ALLOW_PUBLIC_INTERNET=true`. Private, localhost, link-local, and
  internal-looking hosts remain blocked unless explicitly allowlisted.

Wide public-web AI search example:

```text
MODEL_PROVIDER=ollama
MODEL_NAME=mistral-nemo:12b
BROWSER_RESEARCH_MODE=ai_internet
BROWSER_ALLOW_PUBLIC_INTERNET=true
WEB_SEARCH_PROVIDER=multi
WEB_SEARCH_ENGINES=duckduckgo:https://duckduckgo.com/html/,searxng:http://localhost:8888/search
WEB_SEARCH_URL=https://duckduckgo.com/html/
WEB_SEARCH_RESULT_LIMIT=20
AI_SEARCH_QUERY_COUNT=3
AI_SEARCH_CANDIDATE_LIMIT=8
INTERNET_SEARCH_RESULT_LIMIT=5
ALLOW_PRODUCTS_WITHOUT_CONTACTS=true
```

In `ai_internet` mode the agent asks the local Ollama model to generate search
queries, searches through the configured web search provider, asks the model to
select likely product pages, and then extracts selected pages through Browser
MCP. For local no-Docker runs use `WEB_SEARCH_PROVIDER=multi` with
`WEB_SEARCH_ENGINES=duckduckgo:https://duckduckgo.com/html/,searxng:http://localhost:8888/search`
to query several engines and deduplicate URLs before AI selection. Single-engine
modes remain available: use `WEB_SEARCH_PROVIDER=duckduckgo` with
`WEB_SEARCH_URL=https://duckduckgo.com/html/`, or use
`WEB_SEARCH_PROVIDER=searxng` with `WEB_SEARCH_URL=http://localhost:8888/search`.
This is broad public-web discovery, bounded by search-engine availability,
public pages, and the configured result limits. User `maxResults` caps saved
products and is also passed as a candidate breadth hint, but it does not
guarantee exactly that many valid unique cards.

Pull the local model once:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-ollama-portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/start-ollama-local.ps1
powershell -ExecutionPolicy Bypass -File scripts/pull-local-model.ps1 -ModelName mistral-nemo:12b
```

In Docker Compose, use the `DOCKER_*` variables for the backend/worker view of
browser targets:

```text
DOCKER_TEST_SUPPLIER_SITE_URL=http://supplier-site
DOCKER_BROWSER_ALLOWED_DOMAINS=supplier-site,localhost,127.0.0.1
```

For public internet mode, the public URL gate is controlled by
`BROWSER_ALLOW_PUBLIC_INTERNET`; `DOCKER_BROWSER_ALLOWED_DOMAINS` can remain
limited to local controlled services.

## EmailConnector

Purpose: send the initial supplier inquiry to an email contact.

MVP implementation: `SmtpEmailConnector`.

Default local E2E provider:

```text
EMAIL_CONNECTOR_PROVIDER=smtp
EMAIL_SMTP_HOST=localhost
EMAIL_SMTP_PORT=1025
EMAIL_FROM=product-sourcing-agent@example.test
EMAIL_USE_TLS=false
EMAIL_USE_SSL=false
```

`docker compose up --build` starts Mailpit on SMTP port `1025` and mailbox UI
port `8025`. This is a real SMTP send into a controlled mailbox, not a mocked
or pseudo send.

Gmail SMTP provider:

```text
EMAIL_CONNECTOR_PROVIDER=smtp
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-gmail-address@gmail.com
EMAIL_SMTP_PASSWORD=<Gmail app password>
EMAIL_FROM=your-gmail-address@gmail.com
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
```

Use a Gmail app password, not the normal account password. Keep it only in
`.env` or the deployment secret store. The connector redacts
`EMAIL_SMTP_PASSWORD` from structured send errors before the message appears in
the product conversation timeline.

Expected behavior:

- accept recipient, subject, and message body;
- send through a real test mailbox/provider in E2E;
- return success with external message id when available;
- return a structured error without leaking SMTP secrets.

Required environment:

- `EMAIL_CONNECTOR_PROVIDER`
- `EMAIL_SMTP_HOST`
- `EMAIL_SMTP_PORT`
- `EMAIL_SMTP_USER`
- `EMAIL_SMTP_PASSWORD`
- `EMAIL_FROM`
- `EMAIL_USE_TLS`
- `EMAIL_USE_SSL`
- `EMAIL_TIMEOUT_SECONDS`

## TelegramConnector

Purpose: send the initial supplier inquiry to a Telegram test contact.

MVP implementation: `TelegramBotConnector` using the Telegram Bot API.

Required local/E2E provider:

```text
TELEGRAM_CONNECTOR_PROVIDER=telegram_bot
TELEGRAM_BOT_TOKEN=<project-owned-test-bot-token>
TELEGRAM_CHAT_ID=<project-owned-test-chat-or-channel>
```

For a local product-search-only demo, placeholder values may be used so the
services start without a real Telegram contour:

```text
TELEGRAM_BOT_TOKEN=telegram-placeholder-not-used
TELEGRAM_CHAT_ID=telegram-placeholder-chat-not-used
```

Do not use those placeholder values for supplier-contact acceptance checks.

The bot must have permission to write to the configured controlled test contour.
For contacts extracted as `@username` or `https://t.me/username`, the worker
passes that contact value as the destination chat.

Expected behavior:

- accept chat/user/channel and message body;
- send through a real Telegram test contour in E2E;
- return success with external message id when available;
- return a structured error without leaking bot tokens or session secrets.

Required environment:

- `TELEGRAM_CONNECTOR_PROVIDER`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_TIMEOUT_SECONDS`

## Supplier Dialogue Operations

The product page supports a controlled dialogue loop:

1. Start the first supplier message with `Начать общение`.
2. When a supplier replies in Gmail, the backend periodically requests Gmail
   inbound sync and stores matching supplier replies in the conversation.
3. The backend generates a contextual follow-up through `ModelProvider`, sends
   it through the configured email connector, and stores the outbound message
   in the same timeline.
4. Opening the product page also triggers a best-effort Gmail sync. The manual
   `Ответ поставщика` form remains available as a fallback.

For Gmail sending, configure SMTP with a Gmail app password:

```text
EMAIL_CONNECTOR_PROVIDER=smtp
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-gmail-address@gmail.com
EMAIL_SMTP_PASSWORD=<Gmail app password>
EMAIL_FROM=your-gmail-address@gmail.com
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
AUTO_PROCESS_SUPPLIER_CONTACT_TASKS=true
```

For automatic Gmail inbound reading, enable IMAP in Gmail settings and configure:

```text
EMAIL_INBOUND_PROVIDER=gmail_imap
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_USER=your-gmail-address@gmail.com
EMAIL_IMAP_PASSWORD=<Gmail app password>
EMAIL_IMAP_MAILBOX=INBOX
EMAIL_INBOUND_SYNC_LIMIT=20
```

The sync matches inbound email senders to stored supplier email contacts and
deduplicates messages by Gmail `Message-ID`. Product pages call the sync
endpoint automatically before loading the timeline, so the user does not need to
paste Gmail replies into the UI.

For Telegram sending, configure a project-owned bot and chat:

```text
TELEGRAM_CONNECTOR_PROVIDER=telegram_bot
TELEGRAM_BOT_TOKEN=<project-owned-test-bot-token>
TELEGRAM_CHAT_ID=<project-owned-test-chat-or-channel>
AUTO_PROCESS_SUPPLIER_CONTACT_TASKS=true
```

Each agent reply is user-triggered. Gmail inbox reading is automatic on product
page load, but the MVP still does not run autonomous negotiation.

## E2E Rule

Unit and worker tests may use mocks at connector boundaries. The final
`test_protocol.md` run must use real BrowserMcpConnector, EmailConnector, and
TelegramConnector implementations against controlled test resources.
