## 1. OpenSpec And Safety

- [x] 1.1 Validate the change artifacts with `openspec.cmd validate add-contract-drafts --strict --no-interactive`.
- [x] 1.2 Update `test_protocol.md` with contract-draft E2E coverage and prohibited commitment checks.

## 2. Backend Domain And Storage

- [x] 2.1 Add failing domain tests for contract draft status transitions and safety validation.
- [x] 2.2 Implement contract draft domain model, statuses, extracted-data schema, and renderer.
- [x] 2.3 Add failing repository tests proving contracts use a separate contracts repository/session.
- [x] 2.4 Implement contracts repository and contracts database configuration.
- [x] 2.5 Add migration or initialization support for contract draft tables in the contracts database.

## 3. API

- [x] 3.1 Add failing API tests for creating, listing, retrieving, and downloading contract drafts.
- [x] 3.2 Implement `POST /api/products/{product_id}/contracts`.
- [x] 3.3 Implement `GET /api/products/{product_id}/contracts`.
- [x] 3.4 Implement `GET /api/contracts/{contract_id}`.
- [x] 3.5 Implement `GET /api/contracts/{contract_id}/download`.

## 4. Agent Worker

- [x] 4.1 Add failing worker tests for contract draft lifecycle with a mocked `ModelProvider`.
- [x] 4.2 Implement model prompt and structured JSON parsing for contract data extraction.
- [x] 4.3 Implement contract draft generation, validation, and status transitions.
- [x] 4.4 Add tests for rejecting unsafe drafts with payment/order/signature/commitment language.

## 5. Frontend

- [x] 5.1 Add failing frontend tests or smoke coverage for the Contracts tab.
- [x] 5.2 Add frontend API client methods and contract draft types.
- [x] 5.3 Add the Contracts tab to the product/supplier card.
- [x] 5.4 Add generate, refresh, status, missing-fields, error, and download UI states.

## 6. Configuration And Verification

- [x] 6.1 Add contracts database environment variables and local compose initialization.
- [x] 6.2 Run relevant backend and frontend automated tests.
- [x] 6.3 Run `openspec.cmd validate add-contract-drafts --strict --no-interactive`.
- [x] 6.4 Confirm the implementation does not add purchase, order confirmation, payment, signing, export, or advanced CRM behavior.
