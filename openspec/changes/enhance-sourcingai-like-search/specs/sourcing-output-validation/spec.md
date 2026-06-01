## ADDED Requirements

### Requirement: Validate SourcingAI-like Structured Output

The system SHALL validate SourcingAI-like output through strict schemas before persistence.

#### Scenario: Valid structured output is received

- GIVEN output includes normalized intent, missing fields, clarifying questions, common filters, product attributes, products, and sourcing guidance
- WHEN the output is validated
- THEN the system SHALL accept valid values
- AND it SHALL make the data available to the worker for persistence

#### Scenario: Product has invalid fit score

- GIVEN a product output includes `fitScore` below 0 or above 1
- WHEN validation runs
- THEN the product SHALL be rejected or skipped with a validation reason

#### Scenario: Matched requirement lacks evidence

- GIVEN a product output includes a matched requirement without requirement text or evidence
- WHEN validation runs
- THEN that product SHALL be rejected or skipped with a validation reason

### Requirement: Normalize Product Candidates

The system SHALL normalize raw product candidates into validated product payloads without inventing claims.

#### Scenario: Normalizer receives candidate with partial data

- GIVEN a candidate has title, URL, supplier name, price text, MOQ text, and public badges
- WHEN the normalizer processes it
- THEN it SHALL normalize supported fields
- AND it SHALL leave unavailable fields empty or null
- AND it SHALL NOT claim verification, audit, certification, sample availability, or customization without evidence

### Requirement: Evaluate Product Fit Deterministically

The system SHALL evaluate product fit using deterministic, evidence-based rules.

#### Scenario: Manufacturer-first query matches manufacturer evidence

- GIVEN normalized intent has supplier preference `manufacturer_first`
- AND a product candidate has public manufacturer/factory evidence
- WHEN fit evaluation runs
- THEN the product SHALL receive positive fit contribution
- AND the matched requirement SHALL include evidence

#### Scenario: Required certification is missing

- GIVEN normalized intent requires a certification
- AND no public evidence for that certification exists
- WHEN fit evaluation runs
- THEN the missing certification SHALL be listed in missing requirements
- AND the system SHALL NOT invent certification evidence

