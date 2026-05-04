## ADDED Requirements

### Requirement: Display Contactless Product Cards
The WebUI SHALL display product cards discovered through internet search even
when no supplier contacts are available.

#### Scenario: User opens contactless product details
- **GIVEN** a product exists with no supplier contacts
- **WHEN** the user opens the product details page
- **THEN** the WebUI SHALL display the product title, URL, price when available,
  description when available, and source information
- **AND** the WebUI SHALL disable the contact supplier action
- **AND** the WebUI SHALL explain that no supplier contact is available
