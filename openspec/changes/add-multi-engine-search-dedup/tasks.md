## 1. Connector Contracts

- [x] 1.1 Add tests for multi-engine web search aggregation and URL deduplication.
- [x] 1.2 Add tests for `WEB_SEARCH_PROVIDER=multi` and `WEB_SEARCH_ENGINES` config.
- [x] 1.3 Implement `MultiEngineWebSearchConnector` and config parsing.

## 2. Max Results Breadth

- [x] 2.1 Add worker test proving `maxResults` is passed to browser research when supported.
- [x] 2.2 Update product-search worker to pass `maxResults` with backward-compatible fallback.
- [x] 2.3 Add AI internet connector tests for request-level candidate breadth.
- [x] 2.4 Update browser/AI internet connectors to accept optional `max_results`.

## 3. Docs And Defaults

- [x] 3.1 Add env/docs tests for `WEB_SEARCH_ENGINES` and multi-engine mode.
- [x] 3.2 Update `.env`, `.env.example`, and docs for multi-engine search.

## 4. Verification

- [x] 4.1 Run backend unit tests.
- [x] 4.2 Run frontend build if frontend contracts are touched.
- [x] 4.3 Run OpenSpec validation for this change.
- [x] 4.4 Restart local project and smoke-check API/WebUI availability.
