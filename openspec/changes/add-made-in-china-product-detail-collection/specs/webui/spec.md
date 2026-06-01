## ADDED Requirements

### Requirement: Made-in-China catalog column

The WebUI SHALL show Made-in-China search results in a dedicated catalog column so users can review that supplier source separately from other discovery sources.

#### Scenario: Catalog separates Made-in-China products
- **GIVEN** a search request has products from Made-in-China and products from other sources
- **WHEN** the user opens the request catalog
- **THEN** Made-in-China products SHALL appear in a dedicated Made-in-China column
- **AND** other products SHALL appear in a separate column
- **AND** Made-in-China cards SHALL display available supplier parameters such as MOQ, supplier location, business type, and inquiry link when present
