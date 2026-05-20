## MODIFIED Requirements

### Requirement: Deduplicate Supplier Results

The system SHALL keep the main supplier result list deduplicated by supplier
identity while preserving duplicate candidates for review.

#### Scenario: Duplicate supplier candidates are separated

- **GIVEN** search output contains multiple product candidates from the same
  supplier website or supplier identity
- **WHEN** the worker processes the search output
- **THEN** the main product list SHALL contain only the primary candidate for
  that supplier
- **AND** duplicate candidates SHALL be stored in the search task output
- **AND** the product catalog API SHALL return duplicate candidates separately
- **AND** the WebUI SHALL provide a separate duplicates category for that search
  request
