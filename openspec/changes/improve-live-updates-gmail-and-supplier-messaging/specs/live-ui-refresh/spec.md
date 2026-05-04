## ADDED Requirements

### Requirement: Active Searches Must Auto-Refresh

The WebUI MUST periodically refresh active search requests while any request is queued or running.

#### Scenario: Search is still running

- GIVEN a search request is running
- WHEN the user stays on the search requests page
- THEN the page SHALL refresh search request data automatically
- AND it SHALL show approximate progress for the active search

### Requirement: Product Catalog Must Auto-Refresh While Search Runs

The catalog page MUST periodically refresh products for the current search request so new product cards appear without a manual browser refresh.

#### Scenario: Products arrive after catalog is opened

- GIVEN the user opens a catalog before the search completes
- WHEN the backend stores product cards
- THEN the catalog SHALL refresh automatically and show the cards

### Requirement: Product Details Must Not Wait For Gmail Sync

The product detail page MUST display product details before optional Gmail sync completes.

#### Scenario: Gmail sync is slow

- GIVEN Gmail sync takes longer than product detail loading
- WHEN the user opens a product card
- THEN product details SHALL render from the product API
- AND Gmail sync SHALL continue in the background
