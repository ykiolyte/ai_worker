## ADDED Requirements

### Requirement: Create Search Request

The system SHALL allow a user to create a product search request using free-text
input.

#### Scenario: User creates a valid search request

- GIVEN the user is on the search request creation page
- WHEN the user submits a query text from 3 to 1000 characters
- THEN the system SHALL create a search request
- AND the search request status SHALL be `queued`
- AND the system SHALL create a corresponding agent task of type `product_search`
- AND the API response SHALL return without waiting for agent search completion

#### Scenario: User submits an empty search request

- GIVEN the user is on the search request creation page
- WHEN the user submits an empty query text
- THEN the system SHALL reject the request
- AND the system SHALL display a validation error

#### Scenario: User submits a short search request

- GIVEN the user is on the search request creation page
- WHEN the user submits a query text shorter than 3 characters
- THEN the system SHALL reject the request
- AND the system SHALL display a validation error

#### Scenario: User submits an overlong search request

- GIVEN the user is on the search request creation page
- WHEN the user submits a query text longer than 1000 characters
- THEN the system SHALL reject the request
- AND the system SHALL display a validation error

### Requirement: List Search Requests

The system SHALL provide a page and API endpoint for listing search requests.

#### Scenario: User opens search requests list

- GIVEN at least one search request exists
- WHEN the user opens the search requests page
- THEN the system SHALL display query text, status, creation date, and product count for each request
- AND the list SHALL support 1000 search requests within the MVP performance target

### Requirement: Track Search Request Status

The system SHALL persist and expose the processing status of each search request.

#### Scenario: Agent starts processing

- GIVEN a search request has status `queued`
- WHEN the agent starts processing the request
- THEN the system SHALL update the status to `running`
- AND the system SHALL set `started_at`

#### Scenario: Agent completes processing

- GIVEN a search request has status `running`
- WHEN the agent successfully saves search results
- THEN the system SHALL update the status to `completed`
- AND the system SHALL set `completed_at`

#### Scenario: Agent fails processing

- GIVEN a search request has status `running`
- WHEN the agent encounters a critical error
- THEN the system SHALL update the status to `failed`
- AND the system SHALL persist a user-readable error message

#### Scenario: Invalid terminal status transition is attempted

- GIVEN a search request has status `completed` or `failed`
- WHEN code attempts to move it back to `running`
- THEN the system SHALL reject the transition
