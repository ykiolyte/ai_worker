## 1. Tests First

- [x] 1.1 Add connector tests for Made-in-China product detail HTML parsing, including title, canonical URL, supplier, inquiry URL, Basic Info attributes, price/currency, images, and empty contacts for inquiry-only pages.
- [x] 1.2 Add connector tests for direct Made-in-China product URL detection and fetch behavior.
- [x] 1.3 Add failure tests for captcha/protection handling on direct detail pages.
- [x] 1.4 Add worker tests that Made-in-China inquiry-only candidates are persisted without creating unsupported supplier contacts.
- [x] 1.5 Add WebUI contract tests for a separate Made-in-China catalog column.

## 2. Connector Implementation

- [x] 2.1 Implement a Made-in-China product detail parser that prioritizes page metadata and product-detail sections.
- [x] 2.2 Add direct detail URL detection to the existing Made-in-China connector without changing keyword search behavior.
- [x] 2.3 Normalize detail-page data into the existing product candidate payload schema.
- [x] 2.4 Allow Made-in-China supplier/inquiry metadata to satisfy product persistence while keeping contacts empty unless email or Telegram is present.
- [x] 2.5 Split catalog cards into regular and Made-in-China columns with Made-in-China supplier parameters visible.
- [x] 2.6 Enable Made-in-China discovery in local/example configuration.
- [x] 2.7 Prioritize Made-in-China discovery before browser discovery and skip browser discovery when Made-in-China returns products.
- [x] 2.8 Normalize Russian technical camera queries into Made-in-China English/ASCII search slugs.
- [x] 2.9 Enrich Made-in-China search-result cards with price/currency from product detail pages when the search card omits price.

## 3. Verification

- [x] 3.1 Run focused connector tests.
- [x] 3.2 Run the backend test suite.
- [x] 3.3 Run `openspec.cmd validate add-made-in-china-product-detail-collection --strict --no-interactive`.
- [x] 3.4 Parse the saved `made_in_china/` HTML sample locally and confirm it yields a normalized product candidate.
