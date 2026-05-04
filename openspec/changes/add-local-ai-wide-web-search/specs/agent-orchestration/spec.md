## ADDED Requirements

### Requirement: Orchestrate AI Wide-Web Product Search
The product-search worker SHALL be able to use an AI-assisted research connector
that combines local model planning, web search, Browser MCP extraction, and
existing validation.

#### Scenario: AI wide-web connector succeeds
- **GIVEN** an agent task of type `product_search`
- **AND** `BROWSER_RESEARCH_MODE=ai_internet`
- **WHEN** the worker processes the task
- **THEN** the worker SHALL invoke the AI-assisted research connector through
  the existing tool registry
- **AND** the search request SHALL transition through `running` to `completed`
  when at least one valid product is persisted

#### Scenario: AI wide-web connector fails safely
- **GIVEN** the local model or web-search provider is unavailable
- **WHEN** the worker processes a wide-web product-search task
- **THEN** the task SHALL fail with a user-readable error
- **AND** no invalid product output SHALL be persisted
