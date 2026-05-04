## ADDED Requirements

### Requirement: Search Requests Page

The WebUI SHALL provide a search requests page.

#### Scenario: User views search requests

- GIVEN search requests exist
- WHEN the user opens the search requests page
- THEN the WebUI SHALL display a table of requests
- AND each row SHALL include query text, status, product count, and creation date

#### Scenario: Search requests are loading

- GIVEN the WebUI is fetching search requests
- WHEN the request has not completed
- THEN the WebUI SHALL show a loading state

#### Scenario: No search requests exist

- GIVEN no search requests exist
- WHEN the user opens the search requests page
- THEN the WebUI SHALL show an empty state

### Requirement: Product Catalog Page

The WebUI SHALL provide a product catalog page for each search request.

#### Scenario: User views products for request

- GIVEN a search request has associated products
- WHEN the user opens the request catalog page
- THEN the WebUI SHALL display product cards for that request

#### Scenario: Product catalog fails to load

- GIVEN the product catalog API returns an error
- WHEN the user opens the request catalog page
- THEN the WebUI SHALL show a user-readable error state
- AND it SHALL NOT show a stack trace

### Requirement: Product Details Page

The WebUI SHALL provide a product details page.

#### Scenario: User views product details

- GIVEN a product exists
- WHEN the user opens the product details page
- THEN the WebUI SHALL display product data, supplier contacts, and contact attempts
- AND it SHALL NOT display raw `undefined`, `null`, or `NaN` values

### Requirement: Contact Supplier Action

The WebUI SHALL provide a contact supplier action on the product details page.

#### Scenario: Contact is available

- GIVEN a product has a supported supplier contact
- WHEN the user views the product details page
- THEN the WebUI SHALL enable the "Contact supplier" action

#### Scenario: Contact task is active

- GIVEN a product has a contact attempt with status `queued` or `running`
- WHEN the user views the product details page
- THEN the WebUI SHALL disable creating another contact attempt

### Requirement: Automatic Gmail Reply Sync

The WebUI SHALL request Gmail inbound sync in automatic AI reply mode when a product details page is opened.

#### Scenario: Product page syncs supplier replies

- GIVEN the user opens a product details page
- WHEN the page requests Gmail sync
- THEN the WebUI SHALL pass auto-reply mode to Gmail sync
- AND matched inbound supplier messages SHALL be eligible for automatic contextual AI replies

### Requirement: Exclude Non-MVP Actions

The WebUI SHALL NOT expose autonomous purchase, payment, CRM, or mass messaging actions in the MVP.

#### Scenario: User views MVP pages

- GIVEN the user opens search request, product catalog, or product details pages
- WHEN the pages render
- THEN the WebUI SHALL NOT show purchase, order confirmation, payment, CRM pipeline, or mass-message actions
