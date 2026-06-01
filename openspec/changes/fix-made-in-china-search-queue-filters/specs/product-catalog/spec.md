## MODIFIED Requirements

### Requirement: Product Catalog Filtering

The system SHALL expose persisted product and request facets that allow users to filter sourcing results.

#### Scenario: Product cards include filterable supplier fields

- GIVEN product results were produced from public sourcing providers
- WHEN the catalog API returns product cards
- THEN each product SHALL include available supplier name, supplier badges, supplier location, MOQ, price range, customization flag, sample flag, manufacturer/verification flags, and attributes

#### Scenario: Request includes available facets

- GIVEN the provider extracted common filters and grouped product attributes
- WHEN the API returns the SearchRequest detail
- THEN it SHALL include normalized `common_filters` and `product_attributes`
- AND those facets SHALL be derived from persisted provider/model output

#### Scenario: Filtering does not invent data

- GIVEN a product does not include public evidence for a filter value
- WHEN the catalog is filtered
- THEN that product SHALL only match filters supported by its persisted fields or attributes
- AND the system SHALL NOT invent missing values to satisfy a filter
