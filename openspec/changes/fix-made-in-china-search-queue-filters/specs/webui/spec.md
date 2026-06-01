## MODIFIED Requirements

### Requirement: Catalog Filter UI

The WebUI SHALL render and apply catalog filters from API data.

#### Scenario: Filter panel renders request facets

- GIVEN a search request has common filters and product attribute facets
- WHEN the user opens the request catalog
- THEN the WebUI SHALL render price inputs, common boolean filters, and grouped attribute chips
- AND selected filters SHALL be visibly indicated

#### Scenario: User filters products

- GIVEN product cards include supplier/product fields and attributes
- WHEN the user selects attribute chips or common filters
- THEN the catalog SHALL show only matching products
- AND the product count SHALL update without requiring static fixture data

#### Scenario: Empty filtered state

- GIVEN filters exclude all products
- WHEN the filtered catalog is empty
- THEN the WebUI SHALL show an empty filtered state
- AND allow the user to clear filters
