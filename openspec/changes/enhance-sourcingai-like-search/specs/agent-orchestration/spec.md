## MODIFIED Requirements

### Requirement: Process Product Search Tasks

The system SHALL process product search tasks through durable AgentTask records shared by API and worker.

#### Scenario: Durable worker processes queued search

- GIVEN the API created a `product_search` task with status `queued`
- WHEN a separate worker process polls or dequeues durable task state
- THEN the worker SHALL transition the task to `running`
- AND the worker SHALL transition the linked search request to `running`
- AND those transitions SHALL be visible through the API

#### Scenario: Worker persists SourcingAI-like output

- GIVEN a product search task is running
- WHEN provider routing, normalization, fit evaluation, and validation succeed
- THEN the worker SHALL persist search request sourcing metadata
- AND the worker SHALL persist valid products and supplier contacts
- AND the worker SHALL persist skip reasons for invalid products
- AND the worker SHALL transition task and request to `completed`

#### Scenario: Partial invalid output

- GIVEN provider output contains at least one valid product and at least one invalid product
- WHEN the worker validates output
- THEN the worker SHALL persist valid products
- AND the worker SHALL skip invalid products with reasons
- AND the worker SHALL complete the search instead of failing the entire task

#### Scenario: Critical search failure

- GIVEN no valid product can be saved because of a critical provider, model, repository, or connector failure
- WHEN the worker handles the failure
- THEN the worker SHALL mark the task and request `failed`
- AND the failure SHALL be persisted as a user-readable error

### Requirement: Structured Output Validation

The system SHALL treat all model, provider, and connector output as untrusted until validated.

#### Scenario: SourcingAI-like output is validated

- GIVEN output includes normalized intent, filters, product attributes, products, and sourcing guidance
- WHEN the worker receives the output
- THEN the system SHALL validate it against structured schemas
- AND only trusted normalized fields SHALL be copied into domain records
- AND raw output/provenance SHALL be preserved in `raw_agent_payload`

#### Scenario: Legacy product output is received

- GIVEN a connector returns the existing `{"products": [...]}` output shape
- WHEN the worker validates output
- THEN the system SHALL continue to accept valid legacy products
- AND missing SourcingAI-like fields SHALL default to empty values

### Requirement: Public Provider Orchestration

The system SHALL route product discovery through configured public providers and safe fallbacks.

#### Scenario: Made-in-China-like provider is enabled

- GIVEN `ENABLE_MADE_IN_CHINA_PROVIDER` is enabled and provider order includes `made_in_china_public`
- WHEN the worker runs product search
- THEN the worker SHALL use only public pages visible in a normal browser
- AND the worker SHALL NOT use private APIs, unauthorized sessions, signed request replay, CAPTCHA/WAF bypass, or copied proprietary implementation
- AND provider output SHALL include provenance

#### Scenario: Provider returns no usable products

- GIVEN the first configured provider returns no usable products
- WHEN fallback providers are configured
- THEN the worker SHALL try the next configured provider
- AND the task output SHALL record provider errors or empty results in developer-readable form without leaking secrets

### Requirement: Process Supplier Contact Tasks

The system SHALL preserve asynchronous supplier contact task processing with durable state.

#### Scenario: Supplier contact task uses durable records

- GIVEN a `supplier_contact` task is queued in durable state
- WHEN the worker processes it
- THEN product, supplier contact, and contact attempt SHALL be loaded from the shared repository
- AND message delivery results SHALL be visible to the API/UI

### Requirement: Preserve Contract Task Compatibility

The system SHALL preserve contract draft task processing.

#### Scenario: Contract draft task type is stored

- GIVEN contract draft generation uses `AgentTask`
- WHEN the task is persisted
- THEN database constraints SHALL allow `contract_draft`
- AND contract drafts SHALL remain marked draft/not signed/not binding

