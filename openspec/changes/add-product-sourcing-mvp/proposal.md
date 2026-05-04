## Why

Users need a centralized tool to search for industrial, computing, and component
products, store structured product cards, and initiate supplier communication
without manually copying data between browser research, spreadsheets, and
messaging tools.

This MVP establishes the first working version of an AI-assisted product
sourcing system while keeping the agent bounded to research and initial contact.
The implementation must be driven by tests and must be designed to pass the full
production-like protocol in `test_protocol.md`.

## What Changes

- Add WebUI workflows for creating search requests, browsing discovered products,
  viewing product details, and initiating supplier contact.
- Add Backend API endpoints for search requests, product catalogs, product
  details, and contact-supplier requests.
- Add PostgreSQL persistence for search requests, products, supplier contacts,
  contact attempts, and agent tasks.
- Add asynchronous agent task processing for product search and supplier contact.
- Add connector boundaries for browser MCP research, email contact, and Telegram
  contact.
- Add validation, deterministic statuses, persisted errors, and structured
  observability for agent-driven workflows.
- Add a TDD verification capability that maps implementation work to
  `test_protocol.md`.

## Capabilities

### New Capabilities

- `search-requests`: Create, list, view, validate, and track product search
  requests.
- `product-catalog`: Persist product cards and supplier contacts, browse
  products by request, and view product details.
- `supplier-contact`: Request supplier contact, select a connector by contact
  type, and persist contact attempt results.
- `agent-orchestration`: Process product search and supplier contact tasks
  asynchronously with validated structured output.
- `webui`: Provide the MVP user interface for requests, products, and contact
  workflows.
- `persistence`: Persist all MVP domain entities and lifecycle records in a
  relational database.
- `test-protocol`: Drive development with tests and verify the implementation
  against the production-like E2E protocol.

### Modified Capabilities

- None. This is the first change for a new project.

## Impact

- New backend service, domain layer, API routes, persistence models, migrations,
  worker runtime, and connector interfaces.
- New frontend application for request and product workflows.
- New local development configuration for PostgreSQL, Redis or selected broker,
  and environment variables.
- New tests for validation, repositories, API behavior, worker behavior,
  frontend states, smoke flows, and production-like E2E acceptance.
- New documentation for setup, supported connectors, MVP limits, TDD workflow,
  and manual QA.

## Verification

- Every implementation task starts with a failing automated test whenever the
  behavior is automatable.
- Narrow unit and integration tests may use mocks for connector boundaries.
- Smoke and E2E acceptance must exercise real services according to
  `test_protocol.md`.
- Final readiness requires strict OpenSpec validation and a completed
  test-protocol coverage check.
