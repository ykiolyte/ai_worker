## ADDED Requirements

### Requirement: Internal Product AI Assistant

The system SHALL provide a product-scoped internal AI assistant that does not
send supplier messages.

#### Scenario: User asks an internal product question

- **GIVEN** the user is viewing a product detail page
- **WHEN** the user asks the internal AI assistant a question
- **THEN** the system SHALL answer using product data, supplier contacts,
  extracted terms, and conversation history
- **AND** the answer SHALL NOT be sent to the supplier
- **AND** the answer SHALL NOT be persisted as a supplier conversation message
- **AND** the assistant thread SHALL be persisted on the product so it remains
  visible after page refresh
- **AND** JSON-like assistant output SHALL be converted into readable
  user-facing text before display

### Requirement: Assistant UI Separation

The product detail page SHALL provide an openable internal AI assistant panel
that is visually separate from supplier conversation.

#### Scenario: User opens product detail

- **GIVEN** the product detail page is loaded
- **WHEN** the user views communication tools
- **THEN** the page SHALL allow opening an AI Assistant panel with quick prompts
  and a free-form input
- **AND** the assistant thread SHALL be displayed separately from the supplier
  conversation timeline
- **AND** the product card SHALL remain visible while the assistant panel is open
