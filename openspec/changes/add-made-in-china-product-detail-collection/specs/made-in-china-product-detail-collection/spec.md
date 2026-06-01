## ADDED Requirements

### Requirement: Made-in-China product detail collection

The system SHALL collect public Made-in-China product detail pages and normalize them into product candidates compatible with the existing product-search worker flow.

#### Scenario: Product detail page is normalized
- **GIVEN** the Made-in-China connector receives readable public product detail HTML
- **WHEN** the connector parses the detail page
- **THEN** it SHALL extract the main product title, canonical product URL, supplier name, product images, description, price, currency, availability, supplier URL, inquiry URL, contact person, and Basic Info attributes when present
- **AND** it SHALL normalize these values into the existing product candidate schema
- **AND** it SHALL not treat recommendation cards as the main product

#### Scenario: Search result price is enriched from detail page
- **GIVEN** a Made-in-China search result product does not expose price in the search result card
- **WHEN** the product detail page exposes price metadata
- **THEN** the connector SHALL enrich the search result candidate with price and currency from the detail page
- **AND** it SHALL mark the price source as product detail metadata

#### Scenario: Unsupported contact links stay as metadata
- **GIVEN** a Made-in-China product detail page exposes an inquiry URL but no email or Telegram contact
- **WHEN** the connector normalizes the product
- **THEN** the product candidate SHALL keep `contacts` empty
- **AND** it SHALL store the inquiry URL as metadata instead of creating an unsupported supplier contact

#### Scenario: Inquiry-only Made-in-China product is persisted
- **GIVEN** Made-in-China returns a product candidate with supplier or inquiry metadata but no email or Telegram contact
- **WHEN** the product-search worker validates discovered candidates
- **THEN** it SHALL persist the Made-in-China product candidate
- **AND** it SHALL not create unsupported supplier contact records from inquiry URLs

### Requirement: Made-in-China product detail safety

Made-in-China product detail collection MUST remain limited to public information gathering and MUST NOT perform purchasing, ordering, payment, captcha bypass, or supplier messaging.

#### Scenario: Protection page is detected during detail collection
- **GIVEN** Made-in-China returns a captcha or protection page for a direct product URL
- **WHEN** the connector processes the response
- **THEN** the connector SHALL report a structured captcha/protection error
- **AND** it SHALL NOT return invalid partial product data
