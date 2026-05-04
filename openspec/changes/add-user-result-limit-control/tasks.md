## 1. Backend Contracts And Domain

- [x] 1.1 Add domain tests for `SearchRequest.max_results` default and validation.
- [x] 1.2 Add `max_results` to the `SearchRequest` domain entity.
- [x] 1.3 Add API tests for `maxResults` creation, serialization, and invalid values.
- [x] 1.4 Update API payload handling, task payload propagation, and serialization.

## 2. Worker And Persistence

- [x] 2.1 Add worker tests proving product persistence is capped by `maxResults`.
- [x] 2.2 Update product-search worker to cap persisted products and report skipped overflow.
- [x] 2.3 Add Alembic migration for `search_requests.max_results`.

## 3. WebUI

- [x] 3.1 Add/update frontend contract tests for the "Максимум результатов" input and API payload.
- [x] 3.2 Update frontend types and API client to send `maxResults`.
- [x] 3.3 Update the search request form UI.

## 4. Verification

- [x] 4.1 Run backend unit tests.
- [x] 4.2 Run frontend build.
- [x] 4.3 Run OpenSpec validation for this change.
- [x] 4.4 Restart local project and smoke-check API/WebUI availability.
