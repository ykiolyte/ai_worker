## Why

Product detail loading regressed after automatic Gmail inbound sync was added. If the sync endpoint is unavailable or returns an error, the WebUI stops before requesting the product and shows a misleading "Not Found" product load failure.

## What Changes

- Keep Gmail inbound sync as a best-effort background refresh when opening a product card.
- Ensure the product detail request still runs when Gmail sync fails.
- Surface product load errors only from the product detail API call, not from optional sync failures.

## Capabilities

### New Capabilities

- `product-detail-resilience`: Product details remain available when optional conversation sync fails.

### Modified Capabilities

- None.

## Impact

- Affects the product details WebUI load flow.
- Adds frontend contract coverage for best-effort Gmail sync.
- No API, database, connector, or MVP scope boundary changes.
