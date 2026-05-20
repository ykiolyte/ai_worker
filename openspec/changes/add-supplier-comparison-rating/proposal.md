## Why

Users need a quick way to compare suppliers returned for the same sourcing
request. Product cards currently show individual facts, but do not rank offers
by price, contactability, response history, data quality, or source confidence.

## What Changes

- Add computed supplier comparison metrics to product API responses.
- Compare prices within the same search request and currency.
- Add contactability, response, data completeness, and source traceability
  scores.
- Add a weighted `overallRating` and qualitative `ratingLabel` to each product
  supplier card.
- Show the rating and metric breakdown in the catalog and product detail UI.

## Capabilities

### New Capabilities

- `supplier-comparison-rating`: Supplier cards expose comparison metrics and an
  overall rating.

### Modified Capabilities

- `product-catalog`: Product cards include supplier rating fields.
- `webui`: Catalog and product details display supplier comparison metrics.

## Impact

- Backend API: product serializers compute `supplierComparison` from existing
  product, contact, attempt, and conversation data.
- Persistence: no schema change; the rating is derived from persisted facts.
- Frontend: product types and UI display the overall rating and metric chips.
- Tests: API and frontend contract tests cover rating serialization and display.
