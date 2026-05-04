## ADDED Requirements

### Requirement: Persist Product Cards

The system SHALL persist product cards discovered by the agent.

#### Scenario: Agent saves valid product card

- GIVEN the agent has discovered a product with title, URL, and at least one supplier contact
- WHEN the product passes validation
- THEN the system SHALL persist the product card
- AND the system SHALL associate it with the originating search request

#### Scenario: Agent saves product without price

- GIVEN the agent has discovered a product with title, URL, and at least one supplier contact
- AND the product price is not available
- WHEN the product passes validation
- THEN the system SHALL persist the product card with `price` set to `NULL`
- AND the UI SHALL display that price was not found

#### Scenario: Agent discovers invalid product card

- GIVEN the agent has discovered a product without title or URL
- WHEN the product is validated
- THEN the system SHALL skip the product
- AND the system SHALL record the skip reason in the agent task output

#### Scenario: Agent discovers product with invalid contact

- GIVEN the agent has discovered a product with an invalid supplier contact
- WHEN the product and contact are validated
- THEN the system SHALL NOT persist the invalid supplier contact
- AND the system SHALL record the validation reason in the agent task output

### Requirement: Store Supplier Contacts

The system SHALL store supplier contacts associated with product cards.

#### Scenario: Product has email contact

- GIVEN a discovered product includes an email contact
- WHEN the product card is persisted
- THEN the system SHALL persist the supplier contact with type `email`

#### Scenario: Product has Telegram contact

- GIVEN a discovered product includes a Telegram contact
- WHEN the product card is persisted
- THEN the system SHALL persist the supplier contact with type `telegram`

### Requirement: Browse Products By Search Request

The system SHALL allow users to browse products associated with a search request.

#### Scenario: User opens product catalog for a request

- GIVEN a completed search request has products
- WHEN the user opens the product catalog page
- THEN the system SHALL display product cards linked to that search request
- AND the catalog SHALL support pagination for product counts above one page

### Requirement: View Product Details

The system SHALL allow users to view full product details.

#### Scenario: User opens product details

- GIVEN a product exists
- WHEN the user opens the product details page
- THEN the system SHALL display title, price, URL, supplier name, contacts, description, images, and attributes when available

### Requirement: Prevent Duplicate Products Per Request

The system SHALL prevent duplicate products with the same URL inside one search request.

#### Scenario: Duplicate product URL is discovered

- GIVEN a search request already has a product with a product URL
- WHEN the agent output contains another product with the same product URL for that request
- THEN the system SHALL avoid storing a duplicate product card
- AND the system SHALL record the duplicate in the agent task output summary
