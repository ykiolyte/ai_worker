## ADDED Requirements

### Requirement: Persist Search Requests

The system SHALL persist search requests in a relational database.

#### Scenario: Search request is created

- GIVEN a user submits a valid query
- WHEN the backend accepts the request
- THEN the system SHALL store the request with status `queued`
- AND the system SHALL store timestamps needed for lifecycle inspection

### Requirement: Persist Products

The system SHALL persist product cards in a relational database.

#### Scenario: Product card is created

- GIVEN validated product data exists
- WHEN the backend stores the product
- THEN the system SHALL associate it with a search request
- AND the database SHALL allow `price` and `currency` to be `NULL`

### Requirement: Persist Supplier Contacts

The system SHALL persist supplier contacts in a relational database.

#### Scenario: Supplier contact is created

- GIVEN a product has a supported supplier contact
- WHEN the product is stored
- THEN the system SHALL store the contact with the product
- AND the database SHALL enforce supported contact types

### Requirement: Persist Contact Attempts

The system SHALL persist supplier contact attempts in a relational database.

#### Scenario: Contact attempt is created

- GIVEN the user requests supplier contact
- WHEN the backend creates a contact attempt
- THEN the system SHALL persist the attempt with status `queued`
- AND the database SHALL enforce supported contact channels

### Requirement: Persist Agent Tasks

The system SHALL persist agent task lifecycle data.

#### Scenario: Agent task is created

- GIVEN the system needs asynchronous agent processing
- WHEN the backend creates an agent task
- THEN the system SHALL persist task type, status, input payload, and timestamps
- AND the database SHALL enforce supported task types

### Requirement: Support E2E Database Inspection

The database SHALL expose the tables, constraints, indexes, and lifecycle fields required by `test_protocol.md`.

#### Scenario: E2E preflight inspects schema

- GIVEN migrations have been applied
- WHEN the E2E preflight queries PostgreSQL metadata
- THEN tables for search requests, products, supplier contacts, contact attempts, and agent tasks SHALL exist
- AND required check constraints and lookup indexes SHALL exist

#### Scenario: E2E final state inspects active work

- GIVEN an E2E run has completed
- WHEN the final checks query active agent tasks and contact attempts
- THEN no records SHALL remain in `queued` or `running` without an active run reason
