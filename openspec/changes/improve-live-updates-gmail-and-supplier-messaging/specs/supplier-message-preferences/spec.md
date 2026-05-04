## ADDED Requirements

### Requirement: Supplier Contact Supports Language Selection

The user MUST be able to choose Russian, English, or Chinese for supplier communication before starting contact or sending an agent reply.

#### Scenario: User selects English

- GIVEN the product has an email supplier contact
- WHEN the user starts communication with language set to English
- THEN the outbound supplier message SHALL be written in English
- AND it SHALL remain limited to information requests about the product

### Requirement: Supplier Contact Supports Style Selection

The user MUST be able to choose concise, formal, or friendly supplier communication style.

#### Scenario: User selects concise style

- GIVEN the product has a supplier contact
- WHEN the user starts communication with concise style
- THEN the outbound message SHALL use a shorter business wording
- AND it SHALL still ask for price, availability, MOQ, delivery timing, payment terms, and delivery terms
