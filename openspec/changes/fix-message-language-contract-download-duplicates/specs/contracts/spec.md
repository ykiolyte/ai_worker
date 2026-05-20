## MODIFIED Requirements

### Requirement: Downloadable Contract Drafts

The system SHALL let a user create and download non-binding supplier contract
drafts from a supplier/product card.

#### Scenario: Model provider fails during contract drafting

- **GIVEN** a product has enough known supplier/product data to create a review
  draft
- **WHEN** the configured model provider returns an HTTP error or unavailable
  response
- **THEN** the system SHALL create a safe non-binding fallback contract draft
- **AND** the draft SHALL be marked ready
- **AND** the user SHALL be able to download the draft
- **AND** the draft SHALL NOT contain order confirmation, payment instructions,
  signatures, or legally binding commitment language
