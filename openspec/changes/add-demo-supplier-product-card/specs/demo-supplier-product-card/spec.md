## ADDED Requirements

### Requirement: Search Catalogs Must Include A Demo Supplier Product Card

Every completed product search MUST include one additional demo product card with supplier email `ezmmr4us@gmail.com`.

#### Scenario: Search returns normal products

- GIVEN the agent finds normal product cards
- WHEN the product-search worker stores results
- THEN the catalog SHALL include those valid product cards
- AND it SHALL include one additional demo card with email contact `ezmmr4us@gmail.com`

#### Scenario: Search reaches the user result limit

- GIVEN the user requested `maxResults=1`
- AND the agent returns multiple valid products
- WHEN the product-search worker stores results
- THEN only one normal product SHALL be stored
- AND one additional demo card SHALL still be stored

#### Scenario: Worker is retried

- GIVEN a search request already has the demo card
- WHEN product-search processing runs again
- THEN it SHALL NOT create a duplicate demo card
