## ADDED Requirements

### Requirement: Contract Draft Generation

The system SHALL allow a user to request a contract draft from an existing supplier/product conversation.

#### Scenario: User requests a contract draft

- GIVEN a product has a supplier contact and conversation history
- WHEN the user requests a contract draft
- THEN the backend SHALL create a queued contract draft record
- AND the backend SHALL create asynchronous worker work without running model generation inside the HTTP request
- AND the response SHALL include the contract draft identifier and status

### Requirement: Contract Data Extraction

The agent worker SHALL extract contract-relevant data from product details and supplier conversation history using the configured `ModelProvider`.

#### Scenario: Worker extracts contract data

- GIVEN a queued contract draft
- WHEN the worker processes it
- THEN it SHALL provide product details, supplier details, and conversation history to the model
- AND it SHALL validate the model output against a strict structured schema
- AND it SHALL persist validated extracted data with the draft

### Requirement: Contract Draft Safety Boundary

Generated contract documents SHALL remain non-binding drafts.

#### Scenario: Draft output is safe

- GIVEN the model returns contract text
- WHEN the worker validates the draft
- THEN the draft SHALL include a visible draft marker
- AND the draft SHALL NOT contain autonomous purchase confirmation, order confirmation, signatures, payment instructions, payment data, or language that creates a legal commitment

#### Scenario: Unsafe draft output is rejected

- GIVEN the model returns unsafe contract text
- WHEN the worker validates the draft
- THEN the contract draft SHALL move to `failed`
- AND the error message SHALL be user-readable
- AND no downloadable ready file SHALL be exposed

### Requirement: Separate Contracts Database

The system SHALL persist contract draft records through a separate contracts database configuration.

#### Scenario: Contracts storage is isolated

- GIVEN the application is configured
- WHEN contract draft records are stored or read
- THEN contract storage SHALL use `CONTRACTS_DATABASE_URL` or the contracts repository/session
- AND contract records SHALL NOT be stored in sourcing tables such as products, supplier contacts, contact attempts, or conversation messages

### Requirement: Supplier Contracts Tab

The WebUI SHALL show contract drafts on a Contracts tab for each supplier/product card.

#### Scenario: User views supplier contracts

- GIVEN a product has one or more contract drafts
- WHEN the user opens the product/supplier card and selects the Contracts tab
- THEN the WebUI SHALL list existing drafts for that supplier/product
- AND each draft SHALL show status, title, created time, and missing fields when available
- AND ready drafts SHALL expose a download button

### Requirement: Contract Download

The system SHALL allow downloading ready contract draft files.

#### Scenario: User downloads a ready draft

- GIVEN a contract draft has status `ready`
- WHEN the user clicks the download action
- THEN the backend SHALL return the generated draft as a file response
- AND the file name and content type SHALL match the stored contract draft metadata

#### Scenario: User cannot download unfinished draft

- GIVEN a contract draft is queued, running, or failed
- WHEN the user requests its download
- THEN the backend SHALL return an error response
- AND the WebUI SHALL not show an enabled download action for that draft
