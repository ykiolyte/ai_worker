## Backend And Agent

- [x] Add tests for supplier message language/style generation.
- [x] Add API tests for passing language/style to supplier contact and reply tasks.
- [x] Add Gmail sync tests for reply-header matching and read-message fetching.
- [x] Implement language/style message generation and payload propagation.
- [x] Implement Gmail reply header parsing and reconciliation.

## Frontend

- [x] Add frontend contract tests for auto-refresh, progress UI, non-blocking Gmail sync, and message preference controls.
- [x] Implement polling on search requests, catalog, and product details.
- [x] Implement approximate progress display.
- [x] Implement language/style controls for supplier messages.
- [x] Move Gmail sync after initial product detail load and refresh conversation data when sync creates messages.

## Verification

- [x] Run focused backend and frontend contract tests.
- [x] Run full Python test suite.
- [x] Run frontend build.
- [x] Validate OpenSpec change.
- [x] Restart local project and smoke-check API/WebUI availability.
