## Why

Product search fails when one configured web search engine is unavailable. In local Gmail-enabled setup, `WEB_SEARCH_PROVIDER=multi` includes SearXNG on `localhost:8888`; if that service is not running, a connection-refused error marks the entire search request as failed even though other engines can still return results.

## What Changes

- Make multi-engine web search tolerant of individual engine failures.
- Continue merging unique results from remaining engines when at least one engine succeeds.
- Return a failure only when every configured engine fails and no results are available.

## Capabilities

### New Capabilities

- `multi-engine-search-resilience`: Multi-engine product search remains usable when one configured engine is temporarily unavailable.

### Modified Capabilities

- None.

## Impact

- Affects the multi-engine web search connector.
- Adds backend connector contract coverage.
- No API, database, frontend, or MVP scope changes.
