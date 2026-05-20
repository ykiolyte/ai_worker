## MODIFIED Requirements

### Requirement: Supplier Contact Auto-Processing

When supplier contact auto-processing is enabled, the backend SHALL process the contact attempt through the AI message generator and configured connector.

#### Scenario: contact supplier action sends message

- GIVEN a product has a supported supplier contact
- AND supplier contact auto-processing is enabled
- WHEN the user requests supplier contact
- THEN the contact attempt SHALL transition to `sent`
- AND an outbound conversation message SHALL be persisted
- AND the message SHALL contain the product title
