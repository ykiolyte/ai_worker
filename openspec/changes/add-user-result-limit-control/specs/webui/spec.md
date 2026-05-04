## MODIFIED Requirements

### Requirement: Search Request Form Provides Product Search Controls
The search request page SHALL let the user enter a product query and choose the maximum number of product results to display for that request.

#### Scenario: User creates a bounded search request
- **GIVEN** the user is on the search requests page
- **WHEN** the user enters a query and a maximum result count
- **THEN** the WebUI SHALL submit both `queryText` and `maxResults`
- **AND** the created request row SHALL remain available in the search request list
