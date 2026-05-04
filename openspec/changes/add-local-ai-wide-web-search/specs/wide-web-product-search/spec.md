## ADDED Requirements

### Requirement: Search Beyond A Single Supplier Domain
The system SHALL support wide public-web product discovery through a configurable
web-search provider rather than one fixed supplier/search URL.

#### Scenario: Normal query uses configured web search
- **GIVEN** `BROWSER_RESEARCH_MODE=ai_internet`
- **AND** `WEB_SEARCH_PROVIDER` is `searxng` or `duckduckgo`
- **WHEN** the user submits a product query without `site:<url>`
- **THEN** the agent SHALL query the web-search provider
- **AND** candidate URLs MAY come from multiple public domains
- **AND** selected candidate URLs SHALL be extracted through Browser MCP

#### Scenario: Site query remains bounded
- **GIVEN** `BROWSER_RESEARCH_MODE=ai_internet`
- **AND** the user submits a query containing `site:<url>`
- **WHEN** the product-search task runs
- **THEN** the system SHALL use the bounded site flow
- **AND** it SHALL NOT call the wide web-search provider first

### Requirement: Use AI For Search Strategy And Candidate Selection
The system SHALL use the configured local model to generate search queries and
rank web-search results before page extraction.

#### Scenario: Model generates search queries
- **GIVEN** a product query
- **WHEN** wide-web AI search starts
- **THEN** the agent SHALL ask the local model for multiple search queries
- **AND** it SHALL use those queries with the web-search provider

#### Scenario: Model selects product candidates
- **GIVEN** web-search results are available
- **WHEN** candidate selection runs
- **THEN** the agent SHALL ask the local model to choose likely product pages
- **AND** it SHALL pass only selected safe public URLs to Browser MCP extraction

### Requirement: Protect Wide Web Navigation
The system SHALL preserve public URL safety checks for AI-selected URLs.

#### Scenario: AI selects unsafe URL
- **GIVEN** the local model selects localhost, private IP, link-local, or
  internal-looking URL
- **WHEN** the connector validates selected candidates
- **THEN** the system SHALL reject that URL
- **AND** it SHALL continue with other safe candidates when possible

### Requirement: Persist Useful Partial Results
The system SHALL preserve useful product candidates even when some public pages
block browser extraction.

#### Scenario: Product page blocks Browser MCP
- **GIVEN** a selected public result has a title and URL
- **AND** Browser MCP cannot extract the page
- **WHEN** contactless products are allowed
- **THEN** the system SHALL persist a fallback product card for that URL
- **AND** it SHALL record the extraction error in the connector source payload
