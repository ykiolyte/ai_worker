## ADDED Requirements

### Requirement: Supplier Comparison Metrics

The system SHALL expose comparison metrics for each product supplier in product
API responses.

#### Scenario: Product cards include supplier comparison

- **GIVEN** a search request has multiple product cards
- **WHEN** the API returns product catalog items
- **THEN** each product card SHALL include `supplierComparison`
- **AND** `supplierComparison` SHALL include `overallRating`, `ratingLabel`,
  `metrics`, `priceRank`, `priceDeltaPercent`, and `comparedProductsCount`

### Requirement: Price Comparison

The system SHALL compare supplier prices within the same search request and
currency.

#### Scenario: Product has the best price

- **GIVEN** multiple product cards have the same currency and known prices
- **WHEN** supplier comparison is calculated
- **THEN** the lowest priced product SHALL have `priceRank` 1
- **AND** its `priceDeltaPercent` SHALL be 0

#### Scenario: Product has a higher price

- **GIVEN** a product price is higher than the lowest comparable price
- **WHEN** supplier comparison is calculated
- **THEN** the product SHALL have a higher `priceRank`
- **AND** `priceDeltaPercent` SHALL show how far above the best price it is

### Requirement: Overall Supplier Rating

The system SHALL calculate an overall supplier rating from multiple sourcing
signals.

#### Scenario: Supplier has strong sourcing signals

- **GIVEN** a supplier has a competitive price, reachable contact, response
  history, complete product data, and traceable source URL
- **WHEN** supplier comparison is calculated
- **THEN** `overallRating` SHALL be higher than a supplier with weaker signals
- **AND** `ratingLabel` SHALL summarize the score band

### Requirement: Supplier Comparison UI

The WebUI SHALL display supplier comparison on catalog and product details.

#### Scenario: User views product catalog

- **GIVEN** product cards include supplier comparison data
- **WHEN** the user opens the catalog
- **THEN** each card SHALL show the overall supplier rating
- **AND** the card SHALL show the metric breakdown for price, contactability,
  response, data completeness, and source traceability
