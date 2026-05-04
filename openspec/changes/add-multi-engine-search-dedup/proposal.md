## Why

Broad product searches can return fewer saved products than the user-selected `maxResults` because current discovery may inspect too few candidate pages and can rely on a single web search provider. The search layer needs multi-engine discovery with deterministic deduplication so the agent has more unique product pages to evaluate without showing duplicate cards.

## What Changes

- Add a multi-engine web search provider that queries several configured engines and merges results.
- Deduplicate search results by normalized URL before AI selection and browser extraction.
- Let the product-search worker pass the user-selected `maxResults` into browser research when supported.
- Let AI internet search treat `maxResults` as a target breadth hint for candidate selection/extraction, while still respecting configured safety limits.
- Document the difference between `maxResults` as an output cap and discovery limits as the practical source of fewer results.
- Keep existing single-provider modes (`duckduckgo`, `searxng`) compatible.

## Capabilities

### New Capabilities

- `multi-engine-product-search`: Multi-engine web discovery, cross-engine deduplication, and `maxResults`-aware candidate breadth.

### Modified Capabilities

- `user-result-limit-control`: Clarify that `maxResults` controls saved output count and is also passed as a search breadth hint.

## Impact

- Backend connectors: add an aggregate web search connector and supported config for multiple engines.
- Worker: call browser research with `maxResults` when the connector supports it.
- Config/docs/env: add `WEB_SEARCH_ENGINES` and document multi-engine mode.
- Tests: connector aggregation/dedup, worker `maxResults` propagation, docs/env coverage.
