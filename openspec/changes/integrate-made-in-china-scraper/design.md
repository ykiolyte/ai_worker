## Context

The current product search worker already supports structured product extraction and connector-based discovery. The reviewed `made-in-china-scraper-example` is a small Node/Cheerio implementation that fetches Made-in-China search result pages, detects captcha pages, and extracts product name, URL, price, MOQ, supplier name, supplier URL, location, business type, and image URL.

The project backend is Python-first, so the integration should port the extraction behavior into the existing Python connector layer instead of introducing a separate Node runtime. The connector must remain optional and bounded because Made-in-China may return captcha/protection pages or change markup.

## Goals / Non-Goals

**Goals:**

- Add a Python Made-in-China connector that fetches and parses search-result pages.
- Normalize extracted results into the existing product-search schema used by the worker.
- Keep product search resilient when Made-in-China returns captcha, timeout, or no results.
- Add deterministic parser tests with controlled HTML and worker tests with mocked connector responses.
- Preserve the production-like E2E boundary: real E2E must still use real services, worker, broker, browser/connector implementations, and controlled supplier test contour.

**Non-Goals:**

- Do not scrape protected detail pages or bypass captcha.
- Do not add autonomous purchasing, ordering, payment, or checkout behavior.
- Do not add supplier scoring beyond existing comparison indicators.
- Do not make Apify a required dependency for product search.
- Do not replace the browser MCP connector; Made-in-China discovery is an additional source.

## Decisions

1. Port the scraper to Python inside `backend/app/connectors.py`.

   Rationale: the backend and worker are Python-first, tests already exercise connector classes, and adding Node as a runtime dependency would increase deployment complexity. The Node repository remains a reference for selectors and field mapping.

2. Use standard-library HTTP and HTML parsing helpers already acceptable in the project rather than requiring a new scraping framework.

   Rationale: this keeps dependency risk low. The parser can use regex/HTML parser logic scoped to Made-in-China result cards and tested with controlled fixtures.

3. Return structured `ProductSearchResult` values and structured connector errors.

   Rationale: the worker already validates product output before persistence. Captcha, timeout, or malformed markup must not create partial invalid products.

4. Keep the connector optional via configuration.

   Rationale: Made-in-China access may be unstable from local or CI networks. Existing search behavior must remain available if this connector is disabled or fails.

5. Treat prices and MOQs as extracted attributes unless a single numeric price can be safely normalized.

   Rationale: search results often contain ranges such as `US$10-20`; the existing product schema has one nullable `price` field. Raw price and MOQ should remain visible in `attributes`.

## Risks / Trade-offs

- Made-in-China markup changes -> Mitigation: parser tests isolate selector assumptions and connector failure falls back to other sources.
- Captcha/protection page returned -> Mitigation: detect captcha markers and report a structured error without saving products.
- Search result pages may omit direct supplier contacts -> Mitigation: save only cards that pass existing contact validation, or let the worker skip incomplete results according to current policy.
- Optional connector creates inconsistent result counts across environments -> Mitigation: bounded max results and explicit enable flag.
- Live web E2E may be flaky -> Mitigation: unit/worker tests use controlled HTML; production-like E2E should continue relying on the controlled supplier test site unless a real Made-in-China test contour is explicitly added.
