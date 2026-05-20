## 1. Tests First

- [x] 1.1 Add connector parser tests for Made-in-China result HTML, bounded results, raw price, MOQ, supplier fields, and captcha detection.
- [x] 1.2 Add worker/runtime tests that Made-in-China candidates are used when enabled and skipped safely when disabled or failing.
- [x] 1.3 Add configuration tests for Made-in-China enable flag, base URL, timeout, and max result settings.

## 2. Connector Implementation

- [x] 2.1 Add Made-in-China configuration fields with conservative defaults.
- [x] 2.2 Implement Made-in-China search URL construction, HTTP fetch, captcha detection, and HTML result parsing.
- [x] 2.3 Normalize Made-in-China fields into existing product-search candidate payloads without bypassing validation.

## 3. Worker Integration

- [x] 3.1 Add the Made-in-China connector to runtime construction when enabled.
- [x] 3.2 Merge Made-in-China candidates into product search processing while preserving existing fallback behavior.
- [x] 3.3 Persist connector errors in task output without saving invalid partial products.

## 4. Verification

- [x] 4.1 Run focused connector, worker, and configuration tests.
- [x] 4.2 Run the relevant backend test suite.
- [x] 4.3 Run `openspec.cmd validate integrate-made-in-china-scraper --strict --no-interactive`.
- [x] 4.4 Confirm `test_protocol.md` E2E constraints remain satisfied or document any deferred live Made-in-China coverage.
