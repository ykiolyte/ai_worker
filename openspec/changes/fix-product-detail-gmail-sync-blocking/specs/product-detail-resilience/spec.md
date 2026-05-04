## ADDED Requirements

### Requirement: Product Detail Load Must Not Be Blocked By Optional Gmail Sync

When a user opens a product card from a search request catalog, the WebUI MUST load the product details even if automatic Gmail inbound synchronization fails.

#### Scenario: Gmail sync endpoint is unavailable

- GIVEN the user opens a product details route
- AND automatic Gmail inbound sync returns a non-success response
- WHEN the product details API can return the product
- THEN the WebUI continues to request the product details
- AND the product card is displayed instead of a product load error caused by Gmail sync

#### Scenario: Product details are missing

- GIVEN the user opens a product details route
- WHEN the product details API returns Not Found for that product
- THEN the WebUI displays a product load error
