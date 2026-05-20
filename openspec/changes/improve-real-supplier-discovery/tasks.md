## 1. Search Query Expansion

- [x] 1.1 Add connector tests for deterministic B2B supplier query variants.
- [x] 1.2 Expand AI-generated queries with manufacturer, distributor, supplier,
  wholesale, MOQ, stock, and contact intent variants.

## 2. Candidate Classification

- [x] 2.1 Add connector tests for supplier candidate scoring and metadata.
- [x] 2.2 Classify candidates as manufacturer, distributor, marketplace,
  product page, contact page, content page, or unknown.
- [x] 2.3 Prefer real supplier/product candidates over content and irrelevant
  pages during selection.
- [x] 2.4 Fill remaining candidate slots from ranked search results when the
  model selects fewer candidates than the requested limit.

## 3. Supplier Enrichment

- [x] 3.1 Add connector tests for supplier-domain contact enrichment.
- [x] 3.2 Search common supplier-domain contact/about/sales/distributor pages
  after product extraction.
- [x] 3.3 Extract contact/sales/support/about links from product page HTML and
  use them before guessed domain paths.
- [x] 3.4 Detect visible, obfuscated, mailto, Cloudflare-protected email, and
  Telegram contacts in extracted page text.
- [x] 3.5 Merge newly discovered contacts into product payloads without
  duplicating contacts.
- [x] 3.6 Add supplier discovery metadata to product attributes.

## 4. Verification

- [x] 4.1 Run focused connector tests.
- [x] 4.2 Run full Python test suite.
- [x] 4.3 Rebuild/restart Docker services and smoke-check API/WebUI.
