## ADDED Requirements

### Requirement: Record Supplier Inbound Messages

The system SHALL allow a user or connector sync process to record inbound
supplier messages in the product conversation.

#### Scenario: User records supplier reply

- **GIVEN** a product has a supplier contact
- **WHEN** the user records an inbound message from that supplier
- **THEN** the system SHALL persist a conversation message with direction
  `inbound`
- **AND** the product detail API SHALL return the inbound message in the
  conversation timeline

### Requirement: Agent Sends Follow-Up Replies

The system SHALL let the user request an AI-generated follow-up reply for an
existing supplier conversation.

#### Scenario: User requests agent reply

- **GIVEN** a product conversation contains an inbound supplier message
- **WHEN** the user requests an agent reply
- **THEN** the system SHALL create a durable supplier-contact task
- **AND** the worker SHALL generate a reply using `ModelProvider`
- **AND** the worker SHALL send the reply through the connector for the selected
  contact type
- **AND** the system SHALL persist the outbound reply in the conversation
  timeline

### Requirement: Keep Dialogue Inside MVP Safety Boundary

The system SHALL keep agent replies limited to information requests.

#### Scenario: Generated reply violates policy

- **GIVEN** the model generates a reply containing purchase commitment,
  payment promise, payment data, or order confirmation
- **WHEN** the worker validates the reply
- **THEN** the system SHALL NOT send the reply
- **AND** the system SHALL persist a user-readable task error
