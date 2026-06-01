## MODIFIED Requirements

### Requirement: Persist Search Requests

The system SHALL persist search requests and extended sourcing metadata in PostgreSQL for production-like runtime.

#### Scenario: Extended search request is created

- GIVEN a user submits a valid basic or advanced search request
- WHEN the backend accepts the request
- THEN the system SHALL store the request with status `queued`
- AND the extended sourcing metadata columns SHALL exist with empty defaults
- AND the search request SHALL be visible to a separate repository instance

### Requirement: Persist Products

The system SHALL persist product cards and extended sourcing fields in PostgreSQL.

#### Scenario: Extended product card is created

- GIVEN validated product data includes extended sourcing fields
- WHEN the worker stores the product
- THEN the database SHALL persist price/range, MOQ, supplier badges, supplier location, fit score, fit summary, matched requirements, missing requirements, and supplier flags
- AND the product SHALL be visible to the API through a separate repository instance

### Requirement: Persist Agent Tasks

The system SHALL persist agent task lifecycle data in a way that API and worker can share.

#### Scenario: API-created task is visible to worker

- GIVEN the API creates an `agent_task` with status `queued`
- WHEN a separate worker process starts
- THEN the worker SHALL be able to read the queued task from durable state
- AND the worker SHALL be able to persist status/output/error changes visible to the API

#### Scenario: Supported task types are enforced

- GIVEN the system persists an agent task
- WHEN the task type is `product_search`, `supplier_contact`, or `contract_draft`
- THEN database constraints SHALL allow the task type
- AND unsupported task types SHALL be rejected

### Requirement: Runtime Must Not Default To In-Memory Storage

The production-like runtime SHALL NOT use in-memory storage as the default.

#### Scenario: Backend starts without injected test repository

- GIVEN the backend starts in local, docker, or E2E runtime mode
- WHEN `create_app()` is called without an explicitly injected test repository
- THEN the backend SHALL use a PostgreSQL-backed repository configured by `DATABASE_URL`
- AND it SHALL fail fast with a clear error if required database configuration is unavailable

#### Scenario: Worker starts

- GIVEN the worker process starts in local, docker, or E2E runtime mode
- WHEN it builds runtime dependencies
- THEN it SHALL use the same PostgreSQL-backed repository configuration
- AND it SHALL process durable queued tasks instead of a private in-memory task store

### Requirement: Preserve Conversation And Contract Persistence

The system SHALL preserve conversation message and contract draft persistence with extended products.

#### Scenario: Conversation message is created for extended product

- GIVEN an extended product has a contact attempt
- WHEN an outbound or inbound conversation message is created
- THEN the message SHALL be persisted and retrievable for the product details page

#### Scenario: Contract draft is created for extended product

- GIVEN an extended product has a supplier contact
- WHEN a contract draft is requested
- THEN the draft SHALL be persisted with safe draft status and retrievable/downloadable only when ready

### Requirement: Support E2E Database Inspection

The database SHALL expose required tables, constraints, indexes, defaults, and lifecycle fields for `test_protocol.md`.

#### Scenario: E2E preflight inspects extended schema

- GIVEN migrations have been applied
- WHEN E2E preflight queries PostgreSQL metadata
- THEN required base and extended tables/columns/constraints SHALL exist
- AND no queued/running work SHALL remain after completed E2E without an active run reason

