## Context

The current AI internet path uses one `WebSearchConnector`, then asks the local model to select likely product pages. The connector-level limits (`WEB_SEARCH_RESULT_LIMIT`, `AI_SEARCH_CANDIDATE_LIMIT`, `INTERNET_SEARCH_RESULT_LIMIT`) can be lower than the user-selected `maxResults`. This means `maxResults=8` is currently only an output cap; if discovery/extraction yields four valid unique products, the catalog correctly shows four.

## Goals / Non-Goals

**Goals:**

- Support multiple web search engines in one search run.
- Deduplicate URLs across engines before the model and browser extraction.
- Use user `maxResults` as a hint to inspect enough unique candidates.
- Preserve existing provider modes and security URL filtering.

**Non-Goals:**

- Do not guarantee exactly `maxResults` products.
- Do not add paid search APIs in this change.
- Do not bypass search engine rate limits, CAPTCHAs, robots policies, or blocked pages.

## Decisions

### Decision 1: Add `MultiEngineWebSearchConnector`

The aggregate connector wraps several `WebSearchConnector` instances and returns a merged list. Deduplication is done by normalized URL with fragment stripped.

Rationale: this keeps each engine implementation simple and makes multi-engine behavior testable without changing the AI ranking layer.

### Decision 2: Configure With `WEB_SEARCH_PROVIDER=multi`

`WEB_SEARCH_PROVIDER=multi` enables aggregation. `WEB_SEARCH_ENGINES` accepts comma-separated engine specs:

```text
WEB_SEARCH_ENGINES=duckduckgo:https://duckduckgo.com/html/,searxng:http://localhost:8888/search
```

Rationale: it is explicit, backward compatible, and works for local DuckDuckGo plus local SearXNG.

### Decision 3: Pass `maxResults` To Browser Research Opportunistically

The worker calls `browser.research(query_text, max_results=max_results)` and falls back to `browser.research(query_text)` for older test or connector implementations.

Rationale: this preserves existing connector contracts while allowing the AI internet connector to widen candidate selection for higher user limits.

## Risks / Trade-offs

- More engines can increase latency -> keep limits configurable and dedup early.
- Search engines can rate-limit or change markup -> return partial results from engines that still work.
- Multi-engine result quality varies -> downstream AI selection and product validation remain mandatory.
