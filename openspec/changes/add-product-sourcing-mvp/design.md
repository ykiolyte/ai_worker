## Context

The project starts from an empty implementation and a detailed MVP brief in
`Main.md`. The system must let users create product search requests, let an AI
agent research suppliers through a browser MCP connector, store normalized
product cards, and let users request first contact with suppliers.

Product research and supplier communication are long-running operations. They
must run as background tasks with durable status records instead of blocking
HTTP responses.

`test_protocol.md` defines the acceptance boundary. It requires a real WebUI,
Backend API, PostgreSQL database, broker, worker process, LLM provider, browser
MCP connector, email connector, Telegram connector, and controlled supplier
test contour for E2E verification.

## Goals / Non-Goals

**Goals:**

- Keep WebUI, Backend API, and Agent Worker loosely coupled.
- Use PostgreSQL as the source of truth for statuses and results.
- Persist every search request, product, supplier contact, contact attempt, and
  agent task lifecycle.
- Validate all LLM and connector output before persistence.
- Keep model and connector implementations configurable behind interfaces.
- Expose user-readable errors and developer-readable structured logs.
- Drive implementation through tests before production code.

**Non-Goals:**

- Autonomous purchasing, order confirmation, or binding negotiation.
- Payments, ERP/1C integration, exports, supplier scoring, or advanced CRM.
- Advanced cross-request duplicate resolution.
- Fine-tuning or hard-coding a specific model into business logic.
- Blocking HTTP requests while the agent researches or contacts suppliers.
- Passing E2E by replacing real components with mocks or static data.

## Decisions

### Decision 1: Decoupled System Boundary

WebUI communicates only with Backend API. Backend API owns validation,
persistence, and task creation. Agent Worker owns research execution, extraction
attempts, message generation, and connector invocation.

The agent does not own database schema or UI state.

### Decision 2: Asynchronous Agent Tasks

The API creates durable `agent_tasks` records and queues background work for
`product_search` and `supplier_contact`. The UI observes progress by reading
persisted request, task, product, and contact attempt state.

This keeps request latency predictable and prevents browser research or message
sending from tying up HTTP responses.

### Decision 3: Database-Owned Lifecycle

PostgreSQL stores lifecycle state for:

- `search_requests`
- `products`
- `supplier_contacts`
- `contact_attempts`
- `agent_tasks`

Workers update statuses as they run. Failed work stores a user-readable error in
the database and a structured developer-readable log entry.

### Decision 4: Configurable Model Provider

The LLM must be accessed through a `ModelProvider` abstraction.
`mistral-nemo:12b` is the current local default for the user's RTX 4070 SUPER
machine, but business logic must not depend on a concrete model name.

### Decision 5: Explicit Tool Connectors

MVP connector interfaces:

- `BrowserMcpConnector` for product research.
- `EmailConnector` for email contact.
- `TelegramConnector` for Telegram contact.

Each connector returns structured success or error results. Connector secrets
come from environment variables or a secrets manager and must not appear in
frontend responses, API responses, or logs.

Primary MVP browser implementation is Microsoft Playwright MCP behind a local
`BrowserResearchProvider`/`BrowserMcpConnector` boundary. The implementation
supports MCP Streamable HTTP through `BROWSER_MCP_URL` and stdio fallback through
`BROWSER_MCP_COMMAND`/`BROWSER_MCP_ARGS`. Browserbase and Hyperbrowser remain
future provider options behind the same boundary.

The MVP Playwright connector only runs fixed read-only extraction snippets and
requires every navigation target to match `BROWSER_ALLOWED_DOMAINS`. Model
output does not provide arbitrary browser code.

Primary MVP email implementation is SMTP. Local production-like E2E uses a
controlled Mailpit mailbox so the system performs an actual SMTP send without
contacting external suppliers.

Primary MVP Telegram implementation is the Telegram Bot API. The E2E contour
must use a project-owned bot token and chat/channel configured through
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

### Decision 6: Strict Validation Boundary

All agent output is untrusted until validated. Product search output must be
checked against structured schemas before products and contacts are persisted.
Malformed records are rejected or skipped with stored validation errors.

### Decision 7: Simple MVP Duplicate Policy

Within a single search request, the same `product_url` should not be stored
twice. Advanced deduplication across requests remains out of scope.

### Decision 8: Contact Attempt Policy

Only one active contact attempt per product is allowed at a time. Active statuses
are `queued` and `running`.

### Decision 9: TDD Verification Ladder

Implementation should progress through a verification ladder:

1. Unit tests for validators, status transitions, schema parsing, and message
   policy.
2. Repository and migration tests for PostgreSQL persistence constraints.
3. API tests for request/response contracts and task creation side effects.
4. Worker tests with mocked connector interfaces for lifecycle and error paths.
5. Frontend tests for loading, empty, error, and critical interaction states.
6. Smoke tests for search and supplier-contact flows.
7. Production-like E2E runs following `test_protocol.md`.

Mocks are useful in steps 1-5 where the boundary itself is being tested. They
are prohibited in the production-like E2E acceptance stage.

### Decision 10: Controlled E2E Supplier Contour

E2E tests use a controlled supplier site, mailbox, and Telegram contour owned by
the project team. This allows real browser MCP extraction and real message
sending without contacting external suppliers.

## Risks / Trade-offs

- Browser research quality depends on MCP connector reliability and target
  websites.
- Supplier contact data can be incomplete or invalid.
- LLM output may be inconsistent without strict schema validation.
- Telegram automation may require account/session management and compliance
  checks.
- Email deliverability depends on SMTP or provider configuration.
- Keeping workers asynchronous adds broker and operational complexity, but it is
  necessary for reliable long-running agent work.
- Production-like E2E is heavier than mocked testing, but it is required by the
  acceptance protocol and should be reserved for final confidence gates.
