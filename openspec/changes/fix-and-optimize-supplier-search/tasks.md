## 1. Liveness

- [x] 1.1 Add failing tests for `.env` loading of `AUTO_PROCESS_SEARCH_TASKS`.
- [x] 1.2 Implement `.env` loading before `Settings.from_env`.
- [x] 1.3 Add failing worker loop tests for queued product search dispatch.
- [x] 1.4 Implement worker tick dispatch for product search, supplier contact, and contract draft task types.

## 2. Search Optimization

- [x] 2.1 Add failing connector tests for early stop after enough products.
- [x] 2.2 Add failing connector tests for bounded/optional contact enrichment.
- [x] 2.3 Implement early-stop browser extraction while keeping fallback products.
- [x] 2.4 Add configuration for contact enrichment budget/default.
- [x] 2.5 Keep existing `site`, `internet`, and `ai_internet` behavior compatible.

## 3. Verification

- [x] 3.1 Run targeted backend tests.
- [x] 3.2 Run full pytest suite.
- [x] 3.3 Run frontend build.
- [x] 3.4 Validate OpenSpec change strictly.
