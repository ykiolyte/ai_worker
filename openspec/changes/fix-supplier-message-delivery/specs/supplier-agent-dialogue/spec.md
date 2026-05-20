## MODIFIED Requirements

### Requirement: Agent Sends Follow-Up Replies

The system SHALL let the user request an AI-generated follow-up reply for an
existing supplier conversation.

#### Scenario: Worker sends queued supplier reply

- **GIVEN** a product conversation contains an inbound supplier message
- **AND** a queued `supplier_contact` task exists for an agent reply
- **WHEN** the standalone worker processes queued tasks
- **THEN** the worker SHALL generate a reply using `ModelProvider`
- **AND** the worker SHALL send the reply through the connector for the selected
  contact type
- **AND** the system SHALL persist the outbound reply in the conversation
  timeline
- **AND** the contact attempt SHALL transition to `sent`

### Requirement: Worker Processes Supplier Contact Tasks

The standalone Agent Worker SHALL process queued supplier-contact tasks instead
of idling.

#### Scenario: Worker sends initial supplier message

- **GIVEN** a product has a supplier email or Telegram contact
- **AND** a queued `supplier_contact` task exists for the initial outreach
- **WHEN** the standalone worker processes queued tasks
- **THEN** the worker SHALL generate a safe information-request message
- **AND** the worker SHALL call the configured connector
- **AND** the contact attempt SHALL transition to `sent`
- **AND** a sent outbound conversation message SHALL be visible from the product
  detail API

#### Scenario: Connector failure is visible

- **GIVEN** the configured supplier connector rejects the outbound message
- **WHEN** the worker processes the queued supplier-contact task
- **THEN** the contact attempt SHALL transition to `failed`
- **AND** the failure reason SHALL be stored without connector secrets
- **AND** the task SHALL transition to `failed`
