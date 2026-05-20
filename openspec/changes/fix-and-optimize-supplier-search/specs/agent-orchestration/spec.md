## MODIFIED Requirements

### Requirement: Local Search Task Liveness

The backend SHALL process product search tasks in local/dev runs when auto-processing is enabled through `.env` or environment variables.

#### Scenario: `.env` enables auto-processing

- GIVEN `.env` contains `AUTO_PROCESS_SEARCH_TASKS=true`
- WHEN the backend creates settings
- THEN the setting SHALL be enabled even if the variable was not exported before process start

#### Scenario: local worker loop processes queued search task

- GIVEN an in-memory repository contains a queued `product_search` task
- WHEN the worker loop runs one tick with a runtime
- THEN it SHALL call the product search handler
- AND the task SHALL leave `queued`
## MODIFIED Requirements

### Requirement: Bounded Optimized Supplier Search

Internet supplier search SHALL minimize browser page visits while preserving the existing browser extraction fallback.

#### Scenario: search stops after enough valid products

- GIVEN ranked web-search candidates exceed requested `maxResults`
- WHEN browser extraction returns enough valid product payloads
- THEN the connector SHALL stop visiting additional candidate pages
- AND it SHALL report the number of candidates visited

#### Scenario: contact enrichment is bounded

- GIVEN a product page has no contact data
- WHEN contact enrichment is disabled or the enrichment budget is exhausted
- THEN the connector SHALL return the product without slow unbounded contact-page probing
- AND existing contact enrichment behavior SHALL remain available through configuration
