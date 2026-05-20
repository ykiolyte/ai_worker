## Overview

The fix separates liveness from optimization.

Liveness: local and dev runs must not depend on manually exported environment variables. The backend should read `.env` before constructing `Settings`, and the worker runtime should have an executable loop for the in-memory/dev repository. In production-like E2E, the existing requirement remains: real PostgreSQL and broker-backed workers are required.

Optimization: keep the browser extraction path, but make it the expensive second phase. Search APIs and model-free ranking are used to choose the smallest useful candidate set first. Browser extraction stops when enough valid products are found, and contact enrichment is bounded behind a setting.

## Search Strategy

1. Generate or derive a small number of supplier-oriented queries.
2. Use SearXNG/DuckDuckGo/multi-engine search APIs to collect JSON/HTML search results.
3. Deduplicate URLs and score candidates by supplier/product likelihood.
4. Extract candidates through the existing Playwright MCP page extractor.
5. Stop when `maxResults` valid product payloads have been collected.
6. Enrich contacts only when enabled or when the candidate has no contacts and the configured enrichment budget allows it.
7. Preserve fallback product payloads for pages that fail to load.

## Worker Strategy

FastAPI `BackgroundTasks` remains supported for local same-process work. A concrete worker loop is added for development and tests, but production-like E2E still requires real database and broker process boundaries.

## Safety

No purchasing, payment, order confirmation, mass messaging, or CRM behavior is added. Search optimization only changes candidate discovery/extraction order and liveness behavior.

## Verification

- Unit tests for `.env` loading and worker task dispatch.
- Connector tests for early stopping and bounded contact enrichment.
- Full pytest suite and frontend build.
- OpenSpec strict validation.
