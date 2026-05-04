## Tests

- [x] Add backend connector/domain/API tests for search duration and email provider timestamps.
- [x] Add frontend contract tests for duration and email timestamp display.

## Backend

- [x] Capture outbound SMTP message Date timestamp.
- [x] Parse inbound Gmail Date header.
- [x] Store provider timestamp on conversation messages and serialize it.
- [x] Serialize actual search duration seconds.
- [x] Add Alembic migration for provider timestamp.

## Frontend

- [x] Add duration and email timestamp types/formatters.
- [x] Display real search duration in search list/catalog.
- [x] Display provider email timestamps in supplier message bubbles.

## Verification

- [x] Run focused backend/frontend tests.
- [x] Run full Python test suite.
- [x] Build frontend.
- [x] Validate OpenSpec change.
- [x] Restart local project and smoke-check API/WebUI.
