## Why

The current MVP has the foundations for product sourcing, but the search experience and runtime boundary are not yet strong enough for a professional SourcingAI-like workflow or the final production-like E2E protocol. Users need a richer sourcing search flow with intent normalization, supplier-oriented result cards, guidance, and durable API/worker state shared through PostgreSQL instead of isolated in-memory repositories.

This change implements a clean-room, public-source-only SourcingAI-like search experience inspired by the visible behavior of `https://ai.made-in-china.com`, while preserving the project's own architecture, connector abstractions, safety boundaries, and OpenSpec/TDD workflow.

## What Changes

- Add a SourcingAI-like search creation experience with a large sourcing prompt, max result control, and optional advanced fields such as target market, quantity, budget, certifications, and supplier preference.
- Extend search request results with normalized intent, missing fields, clarifying questions, common filters, product attribute facets, sourcing guidance, and supplier count.
- Extend product cards and details with MOQ, price range, supplier badges, supplier location, verification/audit/customization/sample flags, fit score, fit summary, matched requirements, and missing requirements.
- Add strict structured output schemas for SourcingAI-like search output while preserving compatibility with existing `{"products": [...]}` agent output.
- Add a provider abstraction for public product discovery, including a Made-in-China-like public provider constrained to public pages only and a router/fallback path for generic web/browser MCP search.
- Add deterministic product normalization and fit evaluation so product fit scoring is testable without LLM calls.
- Fix the critical production-like runtime gap by requiring API and worker to share durable PostgreSQL-backed state and a broker-backed or durable task boundary.
- Preserve supplier contact, Gmail inbound sync, and contract draft compatibility.
- Prohibit demo product injection, static UI data, in-memory repositories, fake workers, disabled queues, and pre-baked LLM output in acceptance/E2E flows.
- Document clean-room constraints: no private APIs, reverse engineering, CAPTCHA/WAF bypass, unauthorized sessions, or proprietary code/assets.

## Capabilities

### New Capabilities

- `sourcingai-search-experience`: SourcingAI-like search creation, advanced fields, intent summary, filters, facets, sourcing guidance, and user-visible search states.
- `sourcing-provider-discovery`: Public-only provider abstraction, provider routing, Made-in-China-like public discovery constraints, candidate provenance, and provider fallback behavior.
- `sourcing-output-validation`: Pydantic structured output schemas, backward-compatible old product output parsing, product normalization, and deterministic product fit evaluation.

### Modified Capabilities

- `search-requests`: Extend search requests with advanced request fields, normalized intent, missing fields, clarifying questions, common filters, product attributes, sourcing guidance, and supplier count.
- `product-catalog`: Extend product cards/details with sourcing-specific supplier/product fields and fit evidence while preserving existing product API compatibility.
- `supplier-contact`: Preserve safe supplier inquiry behavior while ensuring contact flow uses durable repository state and remains compatible with extended products.
- `agent-orchestration`: Require durable product search and supplier contact task processing through PostgreSQL-visible AgentTask records and a real worker boundary.
- `webui`: Replace or enhance the first-screen search workflow and catalog/detail screens with the SourcingAI-like UX while preserving existing routes.
- `persistence`: Add migrations and repository behavior for extended search/product fields, conversation compatibility, contract task compatibility, and PostgreSQL-backed runtime defaults.

## Impact

- Backend domain models, schemas, repository layer, migrations, API serializers, worker lifecycle, provider layer, and observability.
- Frontend routes/pages/types/API client/styles for search creation, catalog cards, guidance, facets, and details.
- Docker/local runtime behavior so API and worker share durable PostgreSQL state and real task records.
- Tests across domain validation, migrations, repository sharing, worker lifecycle, API contracts, frontend states, and production-like E2E support.
- Documentation for clean-room provider constraints, runtime mode, environment variables, and verification steps.

