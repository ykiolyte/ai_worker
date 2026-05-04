## MODIFIED Requirements

### Requirement: Product Details Provide Communication Controls
The product details page SHALL let the user start supplier communication and inspect saved communication.

#### Scenario: Product has supplier contact
- **GIVEN** a product has at least one supplier contact
- **WHEN** the user opens product details
- **THEN** the page SHALL show a button labeled "Начать общение"
- **AND** pressing it SHALL call the supplier-contact API for that product

#### Scenario: Conversation messages exist
- **GIVEN** the product detail API returns conversation messages
- **WHEN** the product details page renders
- **THEN** the page SHALL show a conversation timeline with message status and body
