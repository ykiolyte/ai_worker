## 1. Configuration And Local Services

- [x] 1.1 Add tests for Ollama and SearXNG configuration defaults/env keys.
- [x] 1.2 Add Settings fields for Ollama URL, web-search provider, SearXNG URL,
  search limits, AI query count, and AI candidate limits.
- [x] 1.3 Add Docker Compose services for Ollama and SearXNG.
- [x] 1.4 Add SearXNG settings with JSON search enabled.

## 2. Local Model Provider

- [x] 2.1 Add tests for Ollama HTTP request/response parsing.
- [x] 2.2 Implement `OllamaModelProvider` with JSON response helper.
- [x] 2.3 Wire model provider factory to `MODEL_PROVIDER=ollama`.
- [x] 2.4 Keep `MODEL_PROVIDER=local_demo` working for controlled tests.

## 3. Web Search Connector

- [x] 3.1 Add tests for SearXNG search request construction and result parsing.
- [x] 3.2 Implement `SearxngWebSearchConnector`.
- [x] 3.3 Deduplicate, limit, and safety-filter web-search result URLs.

## 4. AI-Assisted Research Connector

- [x] 4.1 Add tests that AI search asks the model for search queries.
- [x] 4.2 Add tests that AI search asks the model to rank/select candidates.
- [x] 4.3 Implement `AiInternetProductSearchConnector`.
- [x] 4.4 Preserve `site:<url>` bounded Browser MCP behavior.
- [x] 4.5 Persist fallback product cards for selected URLs when extraction fails
  and contactless products are enabled.

## 5. Runtime Wiring And Documentation

- [x] 5.1 Register AI-assisted connector when `BROWSER_RESEARCH_MODE=ai_internet`.
- [x] 5.2 Update `.env.example`, `.env`, README, and connector docs.
- [x] 5.3 Add local model pull/run instructions.

## 6. Verification

- [x] 6.1 Run backend unit tests.
- [x] 6.2 Run frontend build.
- [x] 6.3 Run OpenSpec validation for this change.
- [x] 6.4 Start local services, pull the local model if needed, and run a live
  wide-web AI product search.
