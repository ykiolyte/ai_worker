## MODIFIED Requirements

### Requirement: Provide Search Request UI

The WebUI SHALL provide a professional SourcingAI-like search creation experience while preserving existing routes.

#### Scenario: User opens search page

- GIVEN the user opens the WebUI
- WHEN the first screen loads
- THEN the UI SHALL show a large sourcing prompt input, example prompts, max results control, and optional advanced fields
- AND the UI SHALL NOT show static product results before a real request is created

#### Scenario: User submits valid search

- GIVEN the user enters a valid query and max results
- WHEN the user submits the search
- THEN the UI SHALL call `POST /api/search-requests`
- AND the UI SHALL navigate to the request catalog or detail view for the created request

#### Scenario: User submits invalid search

- GIVEN the query is missing, too short, too long, or max results is outside 1..50
- WHEN the user submits
- THEN the UI SHALL display validation feedback without creating a request

### Requirement: Display Search Request Status

The WebUI SHALL display queued, running, completed, failed, and empty states from API data.

#### Scenario: Search is running

- GIVEN a search request has status `queued` or `running`
- WHEN the catalog page loads
- THEN the UI SHALL show a loading/progress state based on persisted request status

#### Scenario: Search failed

- GIVEN a search request has status `failed`
- WHEN the catalog page loads
- THEN the UI SHALL show the persisted user-readable error message

#### Scenario: Search completed with no products

- GIVEN a search request has status `completed` and zero products
- WHEN the catalog page loads
- THEN the UI SHALL show an empty state rather than fake product data

### Requirement: Display Extended Product Catalog

The WebUI SHALL display SourcingAI-like catalog context and product cards.

#### Scenario: Catalog has sourcing metadata

- GIVEN a completed search request includes missing fields, clarifying questions, common filters, product attributes, sourcing guidance, product count, and supplier count
- WHEN the user opens the catalog
- THEN the UI SHALL render that metadata as operational panels/chips
- AND the UI SHALL render product cards from API data

#### Scenario: Product card has fit evidence

- GIVEN a product card includes fit score and matched requirements
- WHEN the card is displayed
- THEN the UI SHALL show fit score and "Satisfies N requirements"
- AND the UI SHALL display price/range, MOQ, supplier badges, supplier name, and source domain where available

### Requirement: Display Extended Product Details

The WebUI SHALL display extended product details and preserve existing workflows.

#### Scenario: User opens product details

- GIVEN a product includes extended sourcing fields
- WHEN the user opens the product details page
- THEN the UI SHALL show fit summary, matched requirements with evidence, missing requirements, supplier badges/location, price/range, MOQ, contacts, attempts, conversation timeline, assistant chat, and contract drafts where supported

#### Scenario: Contact button must be disabled

- GIVEN a product has no supported contact or has an active contact attempt
- WHEN the product details page renders
- THEN the contact supplier action SHALL be disabled or rejected with user-readable feedback

### Requirement: Render Agent Output Safely

The WebUI SHALL render agent/provider output safely.

#### Scenario: Agent output includes text fields

- GIVEN API responses include text from model, provider, or connector output
- WHEN the UI renders those fields
- THEN the UI SHALL render them as text or sanitized content
- AND external links SHALL use `target="_blank"` and `rel="noopener noreferrer"`

