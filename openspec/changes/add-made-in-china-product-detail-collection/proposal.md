## Why

Made-in-China search results are already supported, but product cards from Made-in-China showroom pages contain richer fields that the current connector ignores. The user provided a saved card sample, so the next step is to import detail-page collection while preserving the existing MVP sourcing boundaries.

## What Changes

- Add Made-in-China product detail collection for public product/showroom pages, including pages reached through `wholesaler.made-in-china.com` or supplier subdomains.
- Extract normalized product title, canonical product URL, price/currency, image URLs, supplier name, supplier URL, inquiry URL, contact person when present, availability, and Basic Info attributes.
- Allow the Made-in-China connector to fetch a direct product detail URL when the search query contains a `site:https://...made-in-china...` target.
- Persist Made-in-China products that expose supplier/inquiry metadata even when they do not expose email or Telegram contacts.
- Show Made-in-China results in a dedicated catalog column with key sourcing fields.
- Keep search-result collection behavior unchanged for normal keyword queries.
- Do not add purchasing, ordering, payment, captcha bypass, or protected-data scraping.

## Capabilities

### New Capabilities
- `made-in-china-product-detail-collection`: Collection and normalization of public Made-in-China product detail pages.

### Modified Capabilities
- `made-in-china-discovery`: Direct Made-in-China product URLs can be collected as detail pages in addition to keyword search result pages.

## Impact

- Backend connector code in `backend/app/connectors.py`.
- Product-search worker validation in `backend/app/workers.py`.
- WebUI catalog presentation in `frontend/src/pages/RequestCatalogPage.tsx`.
- Connector contract tests in `tests/test_connectors_contract.py`.
- Existing Made-in-China runtime configuration and worker integration remain compatible.
- Verification covers parser tests, worker persistence tests, catalog UI contract tests, direct URL fetch behavior, OpenSpec validation, and the saved `made_in_china/` HTML sample as a local fixture check.
