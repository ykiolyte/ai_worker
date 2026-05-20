## Why

Broad web search needs to return more real suppliers, not only product-like
pages. The current AI internet mode already searches multiple engines and opens
candidate pages, but it can miss suppliers when a product page lacks contacts,
when search wording is too narrow, or when supplier evidence lives on contact,
about, sales, or distributor pages.

## What Changes

- Expand query generation with deterministic B2B sourcing query variants.
- Score and classify candidate URLs before extraction.
- Prefer likely manufacturer, distributor, marketplace, and product-detail
  pages over content pages and irrelevant results.
- Enrich extracted product cards with supplier type, confidence, and discovery
  evidence in `attributes`.
- Add a supplier-domain contact enrichment pass that searches/open common
  supplier pages such as contact, about, sales, and distributors.
- Keep all changes additive and schema-free by storing enrichment metadata in
  existing product attributes and contacts.

## Capabilities

### New Capabilities

- `real-supplier-discovery`: AI internet search discovers and enriches real
  supplier candidates from multiple search queries and supplier-domain pages.

### Modified Capabilities

- `wide-web-product-search`: Search query generation and candidate selection
  become broader and more B2B-oriented.
- `product-catalog`: Product attributes include supplier discovery metadata.

## Impact

- Backend connector: richer query generation, candidate scoring, candidate
  enrichment, supplier contact discovery, and metadata normalization.
- Worker/API: no schema changes.
- Frontend: no required changes; enriched metadata remains available through
  existing `attributes`.
- Tests: connector contracts cover query expansion, candidate classification,
  and contact enrichment.
