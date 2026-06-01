## MODIFIED Requirements

### Requirement: Persist Product Cards

The system SHALL persist validated product cards with extended sourcing fields while preserving existing product card compatibility.

#### Scenario: Agent saves extended product card

- GIVEN the worker has a validated product with title, product URL, supplier data, MOQ, price range, badges, fit score, and fit evidence
- WHEN the product is persisted
- THEN the system SHALL store the extended product fields
- AND the system SHALL associate the product with the originating search request
- AND existing consumers SHALL still receive title, URL, price, currency, supplier name, images, attributes, and contacts

#### Scenario: Product price is unknown but price range exists

- GIVEN a discovered product has no numeric price
- AND the product has a non-empty `priceRange` such as `Negotiable`
- WHEN the product passes validation
- THEN the system SHALL persist `price` as null
- AND the UI SHALL display the price range or a user-readable "price not found" state

#### Scenario: Product fit evidence is stored

- GIVEN a product has `fitScore`, `fitSummary`, `matchedRequirements`, and `missingRequirements`
- WHEN the product is stored
- THEN `fitScore` SHALL be between 0 and 1
- AND each matched requirement SHALL include a requirement and evidence
- AND missing requirements SHALL be stored as a list of strings

### Requirement: Validate Product Output

The system SHALL validate all product output before persistence.

#### Scenario: Invalid product card is skipped

- GIVEN product output is missing title or has an invalid non-http URL
- WHEN the worker validates the product
- THEN the system SHALL skip that product
- AND the system SHALL record the skip reason in `AgentTask.output_payload`

#### Scenario: Product contact validation fails

- GIVEN a product contains an invalid email or Telegram contact
- WHEN the worker validates the product
- THEN the invalid contact SHALL NOT be persisted
- AND the validation reason SHALL be recorded

#### Scenario: Product has no contacts

- GIVEN `ALLOW_PRODUCTS_WITHOUT_CONTACTS` is false
- AND a product has no supported supplier contact
- WHEN the worker validates the product
- THEN the product SHALL be skipped with a user-readable reason

### Requirement: Browse Products By Search Request

The system SHALL allow users to browse extended product cards associated with a search request.

#### Scenario: User opens extended product catalog

- GIVEN a completed search request has products
- WHEN the user opens the product catalog page
- THEN the system SHALL display product title, image when available, price or price range, currency, MOQ, supplier name, source domain, supplier badges, fit score, and matched requirement count
- AND the system SHALL display supplier count, missing fields, clarifying questions, common filters, product attribute facets, and sourcing guidance for the request

### Requirement: View Product Details

The system SHALL allow users to view full extended product details.

#### Scenario: User opens extended product details

- GIVEN a product exists
- WHEN the user opens the product details page
- THEN the system SHALL display title, URL, price or price range, MOQ, description, images, attributes, supplier location, supplier badges, fit summary, matched requirements with evidence, missing requirements, contacts, contact attempts, and conversation timeline
- AND existing assistant chat and contract draft UI SHALL remain available when supported

### Requirement: Prevent Duplicate Products Per Request

The system SHALL prevent duplicate products with the same URL or duplicate supplier key inside one search request.

#### Scenario: Duplicate supplier candidate is discovered

- GIVEN a search request already has a product from a supplier
- WHEN the worker discovers another product with the same supplier key for that request
- THEN the system SHALL avoid storing a duplicate supplier candidate as a normal product
- AND the system SHALL record the duplicate reason in the agent task output

