## ADDED Requirements

### Requirement: Gmail Replies Must Exclude Quoted History

Inbound Gmail messages MUST store only the new supplier reply text when the email body contains quoted previous correspondence.

#### Scenario: Supplier replies above quoted Gmail history

- GIVEN Gmail returns a body with the supplier's answer followed by a localized quote header and quoted previous message
- WHEN the message is synced
- THEN only the supplier's new answer SHALL be stored in conversation history

### Requirement: Agent Follow-Up Replies Must Be Contextual

Agent replies to supplier messages MUST use conversation context and MUST NOT fall back to the initial supplier outreach template.

#### Scenario: Supplier asks which company the user represents

- GIVEN the supplier asks a clarifying question in the dialogue
- WHEN the user asks the agent to continue the conversation
- THEN the agent SHALL answer that question in an employee-like tone
- AND it SHALL NOT repeat the initial price/MOQ/availability request template

### Requirement: Follow-Up Safety Must Not Block AI Authorship

Follow-up reply generation MUST keep the answer authored by the model while preserving MVP boundaries for order, payment, and legal commitments.

#### Scenario: Model returns a safe contextual reply

- GIVEN the model returns a concise answer to a supplier question
- WHEN the worker validates the follow-up reply
- THEN the reply SHALL be accepted if it does not confirm orders, payments, or other commitments

### Requirement: Gmail Supplier Replies Must Always Receive A Contextual AI Response

Matched inbound Gmail supplier replies MUST be followed by an outbound AI response automatically. The response MUST be based on the product and conversation context, and MUST NOT be blocked by the previous manual-approval mode.

#### Scenario: Backend polls Gmail without a page refresh

- GIVEN Gmail inbound sync is configured
- WHEN the backend application is running
- THEN the backend SHALL periodically sync inbound Gmail messages
- AND matched supplier replies SHALL be eligible for automatic AI response without requiring the product page to be opened

#### Scenario: Supplier asks any follow-up question over Gmail

- GIVEN Gmail sync matches a supplier inbound message to an existing product conversation
- WHEN the system stores the inbound message
- THEN the system SHALL generate a contextual follow-up reply
- AND the system SHALL send the reply through the email connector
- AND the system SHALL persist the outbound reply in conversation history

#### Scenario: Supplier asks for company requisites

- GIVEN Gmail sync stores an inbound supplier message asking for company details, legal requisites, INN, KPP, or OGRN
- WHEN the system generates an AI follow-up reply
- THEN the reply SHALL answer the requested company-details question from `docs/ooo.md`
- AND the reply SHALL NOT repeat the initial price, availability, MOQ, lead-time, payment, and delivery request

#### Scenario: AI follow-up generation or sending fails

- GIVEN Gmail sync stores an inbound supplier message and creates an automatic reply attempt
- WHEN model generation, validation, or connector sending fails
- THEN the contact attempt SHALL move to `failed` with a user-readable error
- AND the attempt SHALL NOT remain `queued` or `running` indefinitely

### Requirement: Company Knowledge Must Come From OOO Document

The AI supplier reply prompt MUST include `docs/ooo.md` as authoritative company knowledge.

#### Scenario: Supplier asks which company is represented

- GIVEN `docs/ooo.md` contains company identity, contacts, addresses, and business description
- WHEN the supplier asks who the user represents
- THEN the AI reply prompt SHALL include the OOO document contents
- AND the generated reply SHALL be able to answer from that company knowledge

#### Scenario: Model output is unusable or outside MVP boundaries

- GIVEN Gmail sync matches a supplier inbound message to an existing product conversation
- AND the model returns an empty, repeated-template, or out-of-policy response
- WHEN the system prepares the AI follow-up
- THEN the system SHALL make a second model call to produce a contextual corrected reply
- AND the corrected reply SHALL answer from `docs/ooo.md`, product, and conversation context
- AND the system SHALL NOT replace the model reply with the initial outreach template

### Requirement: Outbound Supplier Messages Must Be Model-Only

Initial supplier outreach and follow-up supplier replies MUST be authored by the configured `ModelProvider`. If the first model output is empty, incomplete, repeated, or outside MVP boundaries, the system MUST make another model call for correction and MUST NOT use a hardcoded outbound message fallback.

#### Scenario: Initial supplier outreach is prepared

- GIVEN the worker prepares a first supplier contact message
- WHEN the message body is generated
- THEN the body SHALL come from the configured model provider
- AND the prompt SHALL include `docs/ooo.md`, the product title, and the product URL
- AND the system SHALL NOT use a static template from application code

#### Scenario: Corrected model output is still unusable

- GIVEN the first model output and corrected model output are unusable
- WHEN the system prepares an outbound supplier message
- THEN the system SHALL fail the send attempt with a user-readable error
- AND the system SHALL NOT send a hardcoded template, contextual fallback, or generic filler message
