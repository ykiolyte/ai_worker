## ADDED Requirements

### Requirement: Supplier Questions Must Request User Approval When The Agent Is Not Confident

When an inbound supplier message contains a question that cannot be safely answered from known product data, the system MUST mark it as requiring user approval.

#### Scenario: Supplier asks for unavailable business decision

- GIVEN a supplier reply asks whether the user wants to place an order
- WHEN Gmail sync stores the inbound message
- THEN the message SHALL be visible in the product conversation
- AND the UI SHALL offer a "Продолжить общение" action instead of auto-sending a commitment

### Requirement: Agent May Auto-Reply To Narrow Product Clarification Questions

The agent MUST automatically answer supplier questions only when the answer is available from known product data and does not create a commitment.

#### Scenario: Supplier asks which product is being discussed

- GIVEN a supplier reply asks for the product link or product name
- WHEN Gmail sync stores the inbound message
- THEN the system MAY send a reply containing the known product title and product URL
- AND the reply SHALL still avoid order confirmation, payment promises, and legal commitments
