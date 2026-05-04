## MODIFIED Requirements

### Requirement: Search Requests Accept User Result Limit
The system SHALL let the user specify the maximum number of product results for a search request. The value SHALL cap saved product output and SHALL be passed to supported search connectors as a breadth hint; it SHALL NOT guarantee that the system will find exactly that many valid unique products.

#### Scenario: User creates search with max results
- **GIVEN** the user enters a valid search query
- **AND** the user chooses a valid maximum result count
- **WHEN** the user creates the search request
- **THEN** the API SHALL persist the chosen `maxResults`
- **AND** search request API responses SHALL include `maxResults`

#### Scenario: User omits max results
- **GIVEN** an API client creates a search request without `maxResults`
- **WHEN** the API validates the request
- **THEN** the system SHALL use the default maximum result count

#### Scenario: User enters invalid max results
- **GIVEN** the user or API client supplies a max result count outside the supported range
- **WHEN** the API validates the request
- **THEN** the API SHALL reject the request with a validation error

#### Scenario: Search finds fewer valid products than max results
- **GIVEN** the user chooses `maxResults`
- **AND** discovery or validation yields fewer valid unique product cards
- **WHEN** the search completes
- **THEN** the catalog SHALL show only the valid unique products found
- **AND** the result count MAY be lower than `maxResults`
