## MODIFIED Requirements

### Requirement: Made-in-China search result discovery

The system SHALL provide an optional Made-in-China discovery connector that searches Made-in-China product result pages and returns normalized product candidates for product sourcing. The same connector SHALL also collect a direct Made-in-China product detail URL when the query explicitly provides one.

#### Scenario: Search results are extracted
- **GIVEN** the Made-in-China connector receives a product query
- **WHEN** Made-in-China returns a readable search result page
- **THEN** the connector SHALL extract product title, product URL, supplier name, supplier URL when present, price text, MOQ text, supplier location, business type, image URL, and result position when available
- **AND** the connector SHALL normalize the result into the product-search candidate schema used by the worker

#### Scenario: Direct product detail URL is extracted
- **GIVEN** the Made-in-China connector receives a query containing a direct Made-in-China product detail URL
- **WHEN** the URL is readable and not protected
- **THEN** the connector SHALL fetch that URL instead of constructing a keyword search URL
- **AND** it SHALL return the normalized product detail candidate
