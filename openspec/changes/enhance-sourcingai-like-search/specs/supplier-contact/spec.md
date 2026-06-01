## MODIFIED Requirements

### Requirement: Request Supplier Contact

The system SHALL allow a user to request safe first contact with a supplier for a product loaded from durable state.

#### Scenario: User requests supplier contact for extended product

- GIVEN a product with extended sourcing fields and at least one supported supplier contact exists in durable storage
- WHEN the user requests supplier contact
- THEN the system SHALL create a durable `contact_attempt`
- AND the system SHALL create a durable `agent_task` of type `supplier_contact`
- AND the API response SHALL return without waiting for connector delivery

#### Scenario: Product has active contact attempt

- GIVEN a product has a contact attempt in `queued` or `running`
- WHEN the user requests another supplier contact
- THEN the system SHALL reject the request with a conflict response

### Requirement: Send Safe Supplier Message

The worker SHALL generate and send only safe supplier information requests.

#### Scenario: Worker sends extended product inquiry

- GIVEN a `supplier_contact` task is queued
- WHEN the worker processes the task
- THEN the worker SHALL load product, contact, and attempt from durable state
- AND the worker SHALL generate the message through `ModelProvider`
- AND the worker SHALL validate the message through `SafeMessagePolicy`
- AND the worker SHALL select email or Telegram connector by contact type
- AND the worker SHALL create an outbound `ConversationMessage`
- AND the worker SHALL update the contact attempt to `sent` or `failed`

#### Scenario: Generated message violates safety policy

- GIVEN the model generates a message that confirms an order, promises payment, sends payment details, or creates a legal commitment
- WHEN the worker validates the message
- THEN the worker SHALL NOT send the message
- AND the contact attempt SHALL be marked `failed` with a user-readable error

### Requirement: Preserve Conversation Compatibility

The system SHALL preserve existing conversation, Gmail inbound sync, and reply behavior with extended product records.

#### Scenario: Gmail inbound reply is synced

- GIVEN an outbound email conversation message exists for an extended product
- WHEN Gmail inbound sync receives a matching supplier reply
- THEN the system SHALL create an inbound `ConversationMessage`
- AND the matching contact attempt MAY transition from `sent` to `responded`

