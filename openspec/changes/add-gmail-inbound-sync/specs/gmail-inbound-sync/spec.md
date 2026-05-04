## ADDED Requirements

### Requirement: Gmail Inbound Sync Reads Supplier Replies

The system SHALL read inbound supplier replies from Gmail and store them as
conversation messages.

#### Scenario: Gmail contains supplier reply

- **GIVEN** Gmail inbound sync is configured
- **AND** an unread email sender matches a supplier email contact
- **WHEN** inbound sync runs
- **THEN** the system SHALL create an inbound conversation message for the
  matching product
- **AND** the product detail API SHALL return the message in the conversation
  timeline

### Requirement: Gmail Inbound Sync Deduplicates Messages

The system SHALL avoid storing the same Gmail message twice.

#### Scenario: Sync runs more than once

- **GIVEN** a Gmail message has already been stored with its external message id
- **WHEN** inbound sync reads the same message again
- **THEN** the system SHALL skip the duplicate

### Requirement: WebUI Automatically Requests Gmail Sync

The WebUI SHALL request Gmail inbound sync without requiring the user to paste
supplier replies manually.

#### Scenario: User opens product details

- **GIVEN** Gmail inbound sync is configured
- **WHEN** the user opens a product details page
- **THEN** the WebUI SHALL call the Gmail sync endpoint
- **AND** it SHALL then load the product conversation timeline
