## ADDED Requirements

### Requirement: Search Public Web For Products
The system SHALL support a configurable public internet product-search mode.

#### Scenario: Query without site target uses internet search
- **GIVEN** public internet search mode is enabled
- **AND** the user submits a product query without a `site:` target
- **WHEN** the product search task runs
- **THEN** the browser connector SHALL open a configured search result page
- **AND** the connector SHALL extract candidate result URLs
- **AND** the connector SHALL visit candidate product pages through browser MCP

#### Scenario: Query with site target remains bounded
- **GIVEN** public internet search mode is enabled
- **AND** the user submits a query containing `site:<url>`
- **WHEN** the product search task runs
- **THEN** the browser connector SHALL use the specified site target directly
- **AND** it SHALL NOT use the public search result page first

### Requirement: Protect Public Browser Navigation
The system SHALL prevent public internet mode from navigating to internal or
private network targets unless explicitly allowlisted.

#### Scenario: Search result points to private address
- **GIVEN** public internet search mode is enabled
- **AND** a search result URL points to localhost, private IP, link-local,
  multicast, or an internal-looking host
- **WHEN** the browser connector validates candidate URLs
- **THEN** the connector SHALL reject that URL
- **AND** the connector SHALL continue with other safe candidates when possible

#### Scenario: Search result points to public HTTPS site
- **GIVEN** public internet search mode is enabled
- **AND** a search result URL points to a public HTTP or HTTPS host
- **WHEN** the browser connector validates candidate URLs
- **THEN** the connector SHALL allow the URL for extraction

### Requirement: Extract Product Cards From Real Pages
The system SHALL extract product data from heterogeneous public product pages.

#### Scenario: Product page has structured data
- **GIVEN** a visited product page contains JSON-LD Product data
- **WHEN** the browser connector extracts product details
- **THEN** the connector SHALL use title, price, currency, description, image,
  supplier, and URL fields when available

#### Scenario: Product page lacks structured data
- **GIVEN** a visited product page does not contain JSON-LD Product data
- **WHEN** the browser connector extracts product details
- **THEN** the connector SHALL fallback to visible headings, metadata,
  price-like text, images, and contact hints

### Requirement: Configure Internet Search Limits
The system SHALL limit internet search breadth through configuration.

#### Scenario: Search has many result links
- **GIVEN** a search result page contains more links than the configured limit
- **WHEN** the browser connector chooses candidate pages
- **THEN** the connector SHALL visit no more than the configured product page
  limit
