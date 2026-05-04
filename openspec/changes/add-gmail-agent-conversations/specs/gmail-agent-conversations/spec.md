## ADDED Requirements

### Requirement: Gmail SMTP Can Send Supplier Messages
The system SHALL support Gmail outbound supplier communication through the existing email connector abstraction.

#### Scenario: Gmail SMTP settings are configured
- **GIVEN** `EMAIL_CONNECTOR_PROVIDER=smtp`
- **AND** Gmail SMTP env values are configured
- **WHEN** the supplier contact worker sends an email contact attempt
- **THEN** the connector SHALL use the configured SMTP host, port, credentials, TLS/SSL flags, and from address
- **AND** secrets SHALL NOT be returned in API responses

### Requirement: Outbound Agent Messages Are Persisted
The system SHALL persist every outbound supplier message created by the agent.

#### Scenario: Email send succeeds
- **GIVEN** a product has an email supplier contact
- **WHEN** the user starts communication
- **AND** the worker successfully sends the email
- **THEN** the system SHALL create a conversation message linked to the product and contact attempt
- **AND** the message SHALL include direction, channel, subject, body, recipient, status, and external message id

#### Scenario: Email send fails
- **GIVEN** a product has an email supplier contact
- **WHEN** the worker cannot send the email
- **THEN** the system SHALL persist a failed outbound conversation message
- **AND** the failure SHALL be visible on the product detail response without exposing secrets

### Requirement: Product Details Show Conversation Timeline
The system SHALL expose saved supplier conversation messages on the product detail API and WebUI.

#### Scenario: User views product after starting communication
- **GIVEN** a product has saved conversation messages
- **WHEN** the user opens the product details page
- **THEN** the UI SHALL show the messages in chronological order
- **AND** the UI SHALL show sent/failed status and message content

### Requirement: Start Communication Is A Single-Product Action
The system SHALL allow starting supplier communication from one product details page only.

#### Scenario: User presses start communication
- **GIVEN** a product has at least one supplier contact
- **WHEN** the user presses "Начать общение"
- **THEN** the API SHALL create one contact attempt and one supplier-contact agent task
- **AND** the UI SHALL prevent duplicate active contact attempts for that product
- **AND** no mass messaging action SHALL be introduced
