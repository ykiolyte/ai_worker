## MODIFIED Requirements

### Requirement: Supplier-Level Deduplication

Search results SHALL NOT persist multiple supplier cards from the same supplier website for one search request.

#### Scenario: duplicate supplier website results are skipped

- GIVEN validated search output contains several product pages from the same supplier domain
- WHEN the product search worker persists results
- THEN only one product card for that supplier domain SHALL be saved for the search request
- AND skipped duplicate supplier results SHALL be reported in the agent task output
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
