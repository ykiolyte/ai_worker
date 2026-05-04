## Context

Search creation currently accepts only `queryText`. The browser/AI connectors already have configuration-level limits for crawl breadth, but the user cannot choose how many product cards the service should keep for a specific request. The WebUI catalog also has pagination, which controls display pages but not the actual search output size.

## Goals / Non-Goals

**Goals:**

- Let the user choose a per-search maximum number of product results.
- Store and return that value with the search request.
- Ensure the worker does not persist more products than the request allows.
- Keep the HTTP task-creation boundary asynchronous.

**Non-Goals:**

- This change does not guarantee the agent will find exactly the requested number.
- This change does not replace connector-level safety limits like `WEB_SEARCH_RESULT_LIMIT` or `INTERNET_SEARCH_RESULT_LIMIT`.
- This change does not add ranking/scoring changes.

## Decisions

### Decision 1: Store `max_results` On SearchRequest

`SearchRequest` gains `max_results` with a default of 5 and validation range 1..50.

Rationale: the limit belongs to the user request and should be visible in listing/detail responses and reproducible by the worker.

### Decision 2: Worker Caps Persisted Products

`process_product_search` reads `maxResults` from the task payload and stops persisting new product records when the cap is reached. Additional valid products are counted as skipped with a clear reason.

Rationale: this keeps product catalogs bounded even when a connector returns more candidates than expected.

### Decision 3: WebUI Uses A Number Input

The search form adds a numeric "Максимум результатов" input with min 1, max 50, and default 5.

Rationale: this is simple, accessible, and maps directly to API validation.

## Risks / Trade-offs

- User sets a high value but connector config is lower -> the system can return fewer products. Mitigation: document that user limit is an output cap, while connector limits still bound discovery.
- Existing API clients omit `maxResults` -> default validation keeps backward compatibility.
- Existing database rows lack `max_results` -> migration adds a default value.
