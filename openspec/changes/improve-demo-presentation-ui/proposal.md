## Why

The current WebUI exposes the required sourcing flow, but it is still too table-heavy for a live demo. Users need clearer progress, faster scanning of product cards, and a more natural supplier-dialogue workspace.

## What Changes

- Add dashboard metrics, colored statuses, and human-readable search stages.
- Add catalog filters for contact availability, demo products, and contact channels.
- Show supplier contacts on product cards so users can decide which card to open.
- Redesign product detail into information and conversation panels.
- Render supplier messages as a chat thread with approval actions.
- Replace language/style selects with segmented controls and add an outgoing-message preview.
- Add friendly error summaries with expandable technical details.
- Add a demo-mode banner so presentation-only cards are clearly labeled.

## Impact

- Frontend pages: search requests, request catalog, product details, shared styles and format helpers.
- Backend API: product-card serialization includes supplier contacts for catalog filtering.
- Tests: frontend contract and API/product catalog contract coverage.
