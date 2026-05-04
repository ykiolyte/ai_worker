## ADDED Requirements

### Requirement: Validate Contactless Internet Product Output
The system SHALL optionally allow product-search output without supplier
contacts when configured for internet discovery.

#### Scenario: Contactless product allowed
- **GIVEN** `ALLOW_PRODUCTS_WITHOUT_CONTACTS` is enabled
- **AND** the browser connector returns a product with title and URL but no
  supplier contacts
- **WHEN** the worker validates product-search output
- **THEN** the system SHALL persist the product card
- **AND** the product SHALL have zero supplier contacts

#### Scenario: Contactless product not allowed
- **GIVEN** `ALLOW_PRODUCTS_WITHOUT_CONTACTS` is disabled
- **AND** the browser connector returns a product with title and URL but no
  supplier contacts
- **WHEN** the worker validates product-search output
- **THEN** the system SHALL skip the product
- **AND** the task output SHALL include the validation reason
