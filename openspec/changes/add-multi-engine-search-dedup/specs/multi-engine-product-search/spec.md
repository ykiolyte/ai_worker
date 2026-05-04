## ADDED Requirements

### Requirement: Multi-Engine Web Search Aggregates Unique Results
The system SHALL support web discovery through multiple configured search engines in one product search run.

#### Scenario: Multiple engines return overlapping URLs
- **GIVEN** multi-engine web search is enabled
- **AND** two engines return the same product URL
- **WHEN** the search results are merged
- **THEN** the merged results SHALL contain only one entry for that normalized URL
- **AND** unique results from each engine SHALL remain available for AI candidate selection

### Requirement: Search Uses User Limit As Candidate Breadth Hint
The system SHALL pass the user-selected `maxResults` to browser research connectors that support request-level breadth hints.

#### Scenario: User requests more results than the default candidate limit
- **GIVEN** a search request has `maxResults` greater than the default AI candidate limit
- **WHEN** the worker processes the product-search task
- **THEN** the browser research connector SHALL receive the requested `maxResults`
- **AND** the AI internet connector SHALL use that value when choosing how many unique candidates to extract

### Requirement: Existing Search Providers Remain Compatible
The system SHALL keep existing single-provider search modes working.

#### Scenario: Single provider mode is configured
- **GIVEN** `WEB_SEARCH_PROVIDER` is `duckduckgo` or `searxng`
- **WHEN** the backend builds the web search connector
- **THEN** it SHALL create the same single-provider connector behavior as before
