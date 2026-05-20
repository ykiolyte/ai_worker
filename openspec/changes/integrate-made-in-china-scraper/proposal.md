## Why

Made-in-China.com is a relevant B2B supplier source for the product sourcing MVP, but the current search path does not have a dedicated adapter for extracting its search-result product data. Integrating the reviewed scraper example gives the agent a more deterministic way to collect product, supplier, price, MOQ, and source fields while preserving the existing async worker and validation boundaries.

## What Changes

- Add a Made-in-China discovery connector based on the reviewed `made-in-china-scraper-example` behavior.
- Normalize Made-in-China search-result fields into the existing product-search output schema.
- Keep the connector behind existing runtime abstractions so product search continues to work when Made-in-China is unavailable or blocked by captcha.
- Detect captcha/protection responses and return structured errors instead of hanging or saving invalid products.
- Add tests for parsing, connector fallback, worker normalization, and configuration.
- No autonomous purchasing, ordering, payment, scraping of protected detail pages, or supplier scoring is introduced.

## Capabilities

### New Capabilities

- `made-in-china-discovery`: Dedicated Made-in-China search-result discovery and normalization for product sourcing.

### Modified Capabilities

- `agent-orchestration`: Product search may use the Made-in-China connector as one real supplier-discovery source while preserving async task behavior and existing browser/search fallbacks.

## Impact

- Backend connectors: add Made-in-China search-result fetch/parse logic and structured result mapping.
- Worker runtime: include the connector in product search discovery when enabled.
- Configuration: add bounded Made-in-China settings such as enable flag, timeout, result limit, and base URL.
- Tests: backend connector and worker contract coverage, plus focused smoke-style parsing tests using controlled HTML.
- E2E posture: production-like E2E still requires real components; unit tests may use controlled HTML fixtures and mocked HTTP fetches.
