## ADDED Requirements

### Requirement: Made-in-China search result discovery

The system SHALL provide an optional Made-in-China discovery connector that searches Made-in-China product result pages and returns normalized product candidates for product sourcing.

#### Scenario: Search results are extracted
- **GIVEN** the Made-in-China connector receives a product query
- **WHEN** Made-in-China returns a readable search result page
- **THEN** the connector SHALL extract product title, product URL, supplier name, supplier URL when present, price text, MOQ text, supplier location, business type, image URL, and result position when available
- **AND** the connector SHALL normalize the result into the product-search candidate schema used by the worker

#### Scenario: Search result limit is bounded
- **GIVEN** the Made-in-China connector is configured with a maximum result count
- **WHEN** more results are present on the page
- **THEN** the connector SHALL return no more than the configured maximum number of candidates

### Requirement: Made-in-China connector failure handling

The system SHALL handle Made-in-China connector failures without breaking the product search task lifecycle.

#### Scenario: Captcha page is detected
- **GIVEN** Made-in-China returns a captcha or protection page
- **WHEN** the connector processes the response
- **THEN** the connector SHALL report a structured captcha/protection error
- **AND** the worker SHALL preserve the product search task lifecycle and continue with other available discovery sources when possible

#### Scenario: Network failure occurs
- **GIVEN** the Made-in-China connector cannot fetch a search result page due to timeout or network error
- **WHEN** the worker processes a product search task
- **THEN** the error SHALL be captured in task output or logs
- **AND** invalid partial Made-in-China products SHALL NOT be persisted

### Requirement: Made-in-China MVP boundary

The Made-in-China integration MUST remain limited to information gathering and MUST NOT perform purchasing, ordering, payment, captcha bypass, or protected detail-page scraping.

#### Scenario: Connector runs within sourcing boundaries
- **WHEN** Made-in-China discovery runs
- **THEN** it SHALL only request search-result information for supplier research
- **AND** it SHALL NOT initiate checkout, place orders, confirm purchases, transmit payment data, or bypass captcha/protection mechanisms
