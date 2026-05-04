## ADDED Requirements

### Requirement: Continue Supplier Conversation From Product Page

The product detail page SHALL let the user continue supplier dialogue without
exposing purchasing or payment actions.

#### Scenario: User adds supplier reply and asks agent to answer

- **GIVEN** the user is viewing a product conversation
- **WHEN** the user enters an inbound supplier message
- **THEN** the WebUI SHALL submit it to the backend and refresh the timeline
- **WHEN** the user clicks the agent reply action
- **THEN** the WebUI SHALL request an agent follow-up reply and refresh the
  timeline
