## 1. Configuration And Safety

- [x] 1.1 Add tests for internet-search configuration defaults and env keys.
- [x] 1.2 Add Settings fields for research mode, search URL template, page
  limit, public internet opt-in, and contactless product persistence.
- [x] 1.3 Add tests for public URL validation and private/internal URL blocking.
- [x] 1.4 Implement public URL safety checks while preserving explicit allowlist
  behavior for controlled E2E sites.

## 2. Search Result Discovery

- [x] 2.1 Add connector tests for search-engine URL creation and result parsing.
- [x] 2.2 Implement internet mode so non-`site:` queries open a configured search
  result page through browser MCP.
- [x] 2.3 Extract and normalize public search result links, including redirected
  result URLs.
- [x] 2.4 Keep `site:<url>` queries on the existing bounded supplier-site path.

## 3. Product Extraction

- [x] 3.1 Add tests for JSON-LD Product extraction.
- [x] 3.2 Add tests for metadata/visible-text fallback extraction.
- [x] 3.3 Extend browser extraction code for JSON-LD, metadata, price hints,
  images, supplier names, and contact hints.
- [x] 3.4 Enforce configurable page limits for internet search candidates.

## 4. Contactless Product Persistence

- [x] 4.1 Add worker tests for `ALLOW_PRODUCTS_WITHOUT_CONTACTS=true`.
- [x] 4.2 Wire contactless-product validation into product search processing.
- [x] 4.3 Verify WebUI product detail behavior remains disabled for products
  without supplier contacts.

## 5. Documentation And Verification

- [x] 5.1 Document real internet-search environment variables and usage.
- [x] 5.2 Update `.env.example` and Docker Compose support for internet mode.
- [x] 5.3 Run backend/frontend/unit checks.
- [x] 5.4 Run strict OpenSpec validation for this change.
