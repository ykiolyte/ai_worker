## 0. TDD Ground Rules

- [x] 0.1 Map every implemented behavior to an OpenSpec requirement and, when
  applicable, to one or more `test_protocol.md` TC-E2E cases.
- [x] 0.2 For each implementation task, add or update a failing automated test
  before writing production code.
- [x] 0.3 Keep unit/integration mocks at explicit boundaries only; do not use
  mocks to satisfy production-like E2E acceptance.
- [x] 0.4 Keep OpenSpec artifacts synchronized when implementation discoveries
  change requirements or design.

## 1. Project Setup

- [x] 1.1 Add failing setup checks for required env vars and service URLs.
- [x] 1.2 Initialize backend project structure.
- [x] 1.3 Initialize frontend project structure.
- [x] 1.4 Configure environment variables and examples for local and E2E runs.
- [x] 1.5 Configure PostgreSQL connection.
- [x] 1.6 Configure Redis or selected background job broker.
- [x] 1.7 Add base Docker Compose for local development.
- [x] 1.8 Document startup commands and expected service health checks.

## 2. Database

- [x] 2.1 Add failing migration tests for required tables from `test_protocol.md`.
- [x] 2.2 Create Alembic migration for `search_requests`.
- [x] 2.3 Create Alembic migration for `products`.
- [x] 2.4 Create Alembic migration for `supplier_contacts`.
- [x] 2.5 Create Alembic migration for `contact_attempts`.
- [x] 2.6 Create Alembic migration for `agent_tasks`.
- [x] 2.7 Add indexes for request, product, contact, and task lookup.
- [x] 2.8 Add database-level checks for supported contact/channel/task types.
- [x] 2.9 Add tests for nullable product price and required product URL/title.

## 3. Backend Domain Layer

- [x] 3.1 Add failing tests for search request validation: empty, shorter than 3
  chars, longer than 1000 chars, and valid query.
- [x] 3.2 Implement SearchRequest entity/model and validation.
- [x] 3.3 Add failing tests for Product validation and invalid-card skipping.
- [x] 3.4 Implement Product entity/model.
- [x] 3.5 Add failing tests for SupplierContact email and Telegram validation.
- [x] 3.6 Implement SupplierContact entity/model.
- [x] 3.7 Add failing tests for ContactAttempt active-attempt policy.
- [x] 3.8 Implement ContactAttempt entity/model.
- [x] 3.9 Add failing tests for AgentTask status transitions.
- [x] 3.10 Implement AgentTask entity/model.
- [x] 3.11 Implement status enums and transition guards.
- [x] 3.12 Implement repository layer with repository tests.

## 4. Backend API

- [x] 4.1 Add failing API tests for `POST /api/search-requests`.
- [x] 4.2 Implement `POST /api/search-requests`.
- [x] 4.3 Add failing API tests for `GET /api/search-requests`.
- [x] 4.4 Implement `GET /api/search-requests`.
- [x] 4.5 Add failing API tests for `GET /api/search-requests/{id}`.
- [x] 4.6 Implement `GET /api/search-requests/{id}`.
- [x] 4.7 Add failing API tests for `GET /api/search-requests/{id}/products`.
- [x] 4.8 Implement `GET /api/search-requests/{id}/products`.
- [x] 4.9 Add failing API tests for `GET /api/products/{id}`.
- [x] 4.10 Implement `GET /api/products/{id}`.
- [x] 4.11 Add failing API tests for `POST /api/products/{id}/contact-supplier`.
- [x] 4.12 Implement `POST /api/products/{id}/contact-supplier`.
- [x] 4.13 Add request/response DTOs and validation/error responses.
- [x] 4.14 Verify API response latency for task-creating endpoints does not wait
  for agent completion.

## 5. Agent Runtime

- [x] 5.1 Add failing tests for AgentRuntime orchestration contracts.
- [x] 5.2 Implement AgentRuntime abstraction.
- [x] 5.3 Implement ModelProvider abstraction.
- [x] 5.4 Implement ToolRegistry abstraction.
- [x] 5.5 Implement BrowserMcpConnector interface.
- [x] 5.6 Implement EmailConnector interface.
- [x] 5.7 Implement TelegramConnector interface.
- [x] 5.8 Add failing tests for structured product-search output schemas.
- [x] 5.9 Implement structured output schemas.
- [x] 5.10 Implement validation for agent product output.
- [x] 5.11 Add message-policy tests that prohibit purchase/order commitments.

## 6. Product Search Worker

- [x] 6.1 Add failing worker tests for `product_search` queued-to-running-to-completed.
- [x] 6.2 Implement `product_search` task handler.
- [x] 6.3 Load search request by ID.
- [x] 6.4 Update search request and agent task statuses.
- [x] 6.5 Execute browser research through MCP connector.
- [x] 6.6 Parse and validate product output.
- [x] 6.7 Persist valid products and contacts.
- [x] 6.8 Skip invalid products and store skip reasons in task output.
- [x] 6.9 Store task output summary.
- [x] 6.10 Handle failures and persist user-readable error messages.
- [x] 6.11 Add tests for browser MCP failure and partial valid output.

## 7. Supplier Contact Worker

- [x] 7.1 Add failing worker tests for `supplier_contact` lifecycle.
- [x] 7.2 Implement `supplier_contact` task handler.
- [x] 7.3 Load product, supplier contact, and contact attempt.
- [x] 7.4 Generate supplier message with the configured local `ModelProvider`, without hardcoded outbound message templates.
- [x] 7.5 Select connector by contact type.
- [x] 7.6 Send message through selected connector.
- [x] 7.7 Persist sent message and external message ID.
- [x] 7.8 Update contact attempt status.
- [x] 7.9 Handle connector failures and persist user-readable error messages.
- [x] 7.10 Add tests for email success, Telegram success, email failure, Telegram
  failure, and duplicate active attempt prevention.
- [x] 7.11 Add tests for contextual model-generated supplier replies without generic fallback.
- [x] 7.12 Implement contextual model-generated supplier replies without generic fallback.
- [x] 7.13 Add tests for configurable inbound Gmail AI reply approval and auto-reply modes.
- [x] 7.14 Implement configurable inbound Gmail AI reply approval and auto-reply modes.

## 8. WebUI

- [x] 8.1 Add failing frontend tests for search requests loading, empty, and
  error states.
- [x] 8.2 Implement application layout.
- [x] 8.3 Implement search requests list page.
- [x] 8.4 Implement create search request form.
- [x] 8.5 Add failing frontend tests for request catalog states and pagination.
- [x] 8.6 Implement search request detail/catalog page.
- [x] 8.7 Implement product card component.
- [x] 8.8 Add failing frontend tests for product details and contact action states.
- [x] 8.9 Implement product details page.
- [x] 8.10 Implement supplier contacts section.
- [x] 8.11 Implement contact attempts section.
- [x] 8.12 Implement "Contact supplier" action.
- [x] 8.13 Ensure UI never displays raw `undefined`, `null`, `NaN`, or stack traces.
- [x] 8.14 Ensure MVP UI does not expose purchase, payment, CRM, or mass-message actions.
- [x] 8.15 Add tests for the AI reply approval setting on product details.
- [x] 8.16 Implement the AI reply approval setting and pass it to Gmail sync.

## 9. Production-like E2E Support

- [x] 9.1 Define E2E environment variables from `test_protocol.md`.
- [x] 9.2 Provide a controlled supplier test site with required product pages.
- [x] 9.3 Configure real browser MCP access to the controlled supplier site.
- [x] 9.4 Configure real test email sending to the project-owned mailbox.
- [x] 9.5 Configure real test Telegram sending to the project-owned test contour.
- [x] 9.6 Add E2E setup checks for WebUI, Backend API, PostgreSQL, broker, worker,
  LLM provider, browser MCP, email connector, and Telegram connector.
- [x] 9.7 Add E2E cleanup or isolation so queued/running tasks are not left behind.

## 10. Observability and Reliability

- [x] 10.1 Add failing tests or log assertions for required correlation IDs.
- [x] 10.2 Add structured logging.
- [x] 10.3 Add correlation IDs for agent tasks, search requests, products, and
  contact attempts.
- [x] 10.4 Add retry policy for connector failures.
- [x] 10.5 Add timeout and recovery policy for queued/running agent tasks.
- [x] 10.6 Add user-readable error messages.
- [x] 10.7 Add developer-readable error details to logs only.
- [x] 10.8 Add safeguards that prevent connector secrets from appearing in logs,
  frontend responses, or API responses.

## 11. Smoke And Acceptance Tests

- [x] 11.1 Add smoke test for full search request flow.
- [x] 11.2 Add smoke test for supplier contact flow.
- [x] 11.3 Add smoke test for nullable product price display.
- [x] 11.4 Add smoke test for invalid product rejection.
- [x] 11.5 Add smoke test for prohibited MVP actions not being present.
- [ ] 11.6 Run and record the full `test_protocol.md` acceptance checklist.
- [x] 11.7 Verify no `agent_tasks` or `contact_attempts` remain queued/running
  after E2E completion.

## 12. Documentation

- [x] 12.1 Document environment variables.
- [x] 12.2 Document local development startup.
- [x] 12.3 Document supported connector types.
- [x] 12.4 Document MVP limitations.
- [x] 12.5 Document TDD workflow and test command order.
- [x] 12.6 Document manual QA and final E2E report format.

## 13. OpenSpec Verification

- [x] 13.1 Run `openspec.cmd validate add-product-sourcing-mvp --strict --no-interactive`.
- [x] 13.2 Update OpenSpec tasks and specs for any implementation discoveries.
- [x] 13.3 Verify the test-protocol mapping file is current.
- [x] 13.4 Mark implementation tasks complete only after tests pass.
