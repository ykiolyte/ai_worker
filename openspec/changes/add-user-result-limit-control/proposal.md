## Why

Users need control over how many products a search request returns so local AI/browser runs can stay fast, focused, and predictable. A per-request limit also prevents the UI from showing an unexpectedly large catalog when broad internet search is enabled.

## What Changes

- Add a user-selectable `maxResults` value when creating a search request.
- Validate and persist `maxResults` on `SearchRequest`.
- Pass `maxResults` into the product-search task and cap persisted products for that request.
- Expose `maxResults` in search request API responses.
- Add a WebUI numeric control for the maximum number of product results.
- Keep connector-wide crawl/search limits in configuration; the user limit is an output cap, not a promise that the agent will always find that many products.

## Capabilities

### New Capabilities

- `user-result-limit-control`: User-selected maximum product result count for search requests.

### Modified Capabilities

- `webui`: Search request form lets the user choose maximum output results.

## Impact

- Backend domain/API: `SearchRequest` gains `max_results`, payload validation, serialization, and task payload propagation.
- Worker: product-search processing respects per-request output cap before persisting products.
- Persistence: Alembic schema gains a nullable/defaulted `max_results` column for search requests.
- Frontend: search form, API client, and TypeScript contract include `maxResults`.
- Tests: domain/API/worker/frontend/migration contracts cover the new limit behavior.
