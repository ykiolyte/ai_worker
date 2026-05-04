## ADDED Requirements

### Requirement: Search Requests Accept User Result Limit
The system SHALL let the user specify the maximum number of product results for a search request.

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

### Requirement: Product Search Respects User Result Limit
The system SHALL NOT persist more product cards for a search request than the request's `maxResults`.

#### Scenario: Connector returns more products than allowed
- **GIVEN** a product search request has `maxResults` set to a lower number than the connector output
- **WHEN** the worker processes the product search task
- **THEN** the worker SHALL persist no more than `maxResults` products for that request
- **AND** skipped products SHALL be reported in the task output

### Requirement: WebUI Provides Result Limit Control
The WebUI SHALL let the user choose maximum product results before starting a search.

#### Scenario: User starts search from WebUI
- **GIVEN** the user opens the search request form
- **WHEN** the page renders
- **THEN** the form SHALL show a "Максимум результатов" numeric input
- **AND** submitting the form SHALL send `maxResults` to the create-search API
