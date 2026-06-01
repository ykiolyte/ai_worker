## Context

`docs/tech_brief.md` defines a broad enhancement: provide a professional SourcingAI-like search experience, keep the implementation clean-room, and close the critical runtime gap where API and worker currently default to separate `InMemoryRepository` instances. The final E2E protocol still requires real WebUI, Backend API, PostgreSQL, broker, worker, ModelProvider, Browser MCP, email connector, Telegram connector, and controlled supplier test contour.

This change is intentionally split into three implementation tracks that must be developed with TDD:

1. Durable runtime boundary: PostgreSQL-backed repository and real worker-visible AgentTask state.
2. SourcingAI-like search data model and provider/normalization pipeline.
3. WebUI enhancements that expose normalized intent, filters/facets, guidance, and richer product cards without introducing fake data.

## Goals / Non-Goals

**Goals:**

- Preserve the existing MVP flow and routes while adding a richer search experience.
- Ensure API-created tasks and worker updates are visible across processes through durable storage.
- Add advanced search request fields and persisted normalized search output.
- Add extended product fields for sourcing cards and details.
- Add public-only provider discovery and provenance tracking.
- Validate every model/connector/provider output before persistence.
- Keep supplier communication as safe information requests only.
- Preserve Gmail inbound sync and contract draft behavior.
- Make all new behavior testable through domain, repository, worker, API, frontend, and E2E-support tests.

**Non-Goals:**

- No private Made-in-China APIs, undocumented endpoints, signed request replay, decompilation, CAPTCHA/WAF/rate-limit bypass, unauthorized cookies, or copied proprietary assets/code.
- No autonomous purchasing, order confirmation, payments, bank/payment data sharing, or legally binding commitments.
- No SupplierChain-AI integration as the core search implementation.
- No E2E acceptance through mock connectors, fake worker, in-memory DB, static UI data, disabled queue, or pre-baked LLM output.

## Decisions

### Decision 1: New Change Instead Of Reopening MVP Tasks

Use `enhance-sourcingai-like-search` as a dedicated change. The existing `add-product-sourcing-mvp` artifacts represent the baseline MVP and are mostly completed; this work is a new product and architecture iteration with its own acceptance surface.

### Decision 2: Durable Repository Becomes Runtime Default

`create_app()` and `worker.py` must use a PostgreSQL-backed repository when not explicitly injected for tests. `InMemoryRepository` remains allowed for isolated unit tests where injected intentionally. Docker/E2E must not silently use in-memory state.

The repository abstraction should expose the same operations currently used by API and worker, plus queue-oriented task lookup/update operations. The worker may remain repository-polling based if it polls PostgreSQL-backed queued tasks durably, but a broker-backed enqueue/dequeue path is preferred where it fits existing dependencies.

### Decision 3: Migrations Extend Existing Tables

Search request and product records are extended in-place. JSON-like sourcing metadata uses JSONB defaults; booleans use false defaults; fit score is constrained to a 0..1 numeric value. If `contract_draft` is stored in `agent_tasks`, the task type check constraint must be updated to include it.

### Decision 4: Structured Output Schemas Are Separate From Domain Entities

Introduce Pydantic v2 schemas for SourcingAI-like model/provider output:

- `NormalizedIntentSchema`
- `ProductAttributeFacetSchema`
- `MatchedRequirementSchema`
- `SupplierContactSchema`
- `SourcingGuidanceSchema`
- `SourcingProductSchema`
- `SourcingSearchOutputSchema`

These schemas validate untrusted output before conversion into domain objects. Old product output shape remains accepted to avoid breaking existing tests/connectors.

### Decision 5: Provider Layer Produces Candidates, Normalizer Produces Products

Provider discovery must not directly create trusted `Product` records. Providers return raw `ProductCandidate`/`SearchProviderResult` data with provenance. `ProductNormalizer` converts candidates to Sourcing-compatible product payloads, and `ProductFitEvaluator` deterministically scores the product against normalized intent.

### Decision 6: Made-in-China-like Provider Is Public-Only

The Made-in-China-like provider may use only public pages visible to a normal browser/search user. It must not use private/internal endpoints, credentials, session cookies, CAPTCHA/WAF bypass, signed request replay, or reverse engineered assets/code. Claims such as verified/audited supplier must only be set when public evidence is visible.

### Decision 7: Worker Owns Lifecycle And Partial Success

The product search worker loads queued tasks from durable storage, marks task/request running, runs provider routing and fallback, validates products, persists valid products, skips invalid ones with reasons, persists normalized search metadata, and completes the task if at least one valid product is saved. Critical failures mark both task and request failed with user-readable errors.

### Decision 8: UI Renders Persisted Data Only

The frontend must render only API data from persisted records. It may show loading, empty, and failed states, but it must not ship static sourcing results or demo-only product cards for acceptance.

## Data Model Changes

`search_requests` adds:

- `normalized_intent JSONB NOT NULL DEFAULT '{}'::jsonb`
- `missing_fields JSONB NOT NULL DEFAULT '[]'::jsonb`
- `clarifying_questions JSONB NOT NULL DEFAULT '[]'::jsonb`
- `common_filters JSONB NOT NULL DEFAULT '[]'::jsonb`
- `product_attributes JSONB NOT NULL DEFAULT '[]'::jsonb`
- `sourcing_guidance JSONB NOT NULL DEFAULT '{}'::jsonb`
- `suppliers_count INTEGER NOT NULL DEFAULT 0`

`products` adds:

- `moq TEXT NULL`
- `price_range TEXT NULL`
- `fit_score NUMERIC(5,4) NULL`
- `fit_summary TEXT NULL`
- `matched_requirements JSONB NOT NULL DEFAULT '[]'::jsonb`
- `missing_requirements JSONB NOT NULL DEFAULT '[]'::jsonb`
- `supplier_badges JSONB NOT NULL DEFAULT '[]'::jsonb`
- `supplier_country TEXT NULL`
- `supplier_city TEXT NULL`
- `is_verified_supplier BOOLEAN NOT NULL DEFAULT false`
- `is_audited_supplier BOOLEAN NOT NULL DEFAULT false`
- `supports_customization BOOLEAN NOT NULL DEFAULT false`
- `sample_available BOOLEAN NOT NULL DEFAULT false`

## API Changes

Existing routes remain stable. `POST /api/search-requests` continues to accept `queryText` and `maxResults`, and additionally accepts optional `targetMarket`, `quantity`, `budget`, `certifications`, and `supplierPreference`.

`GET /api/search-requests/{id}` returns the extended sourcing metadata.

`GET /api/search-requests/{id}/products` returns extended product card fields, including MOQ, price range, supplier badges, supplier location, verification flags, fit score/summary, matched/missing requirements, contacts count, and existing compatibility fields.

`GET /api/products/{id}` returns full extended details plus existing contacts, attempts, conversation messages, assistant messages, and contract-related data where already supported.

## Test Strategy

- Domain/schema tests first for advanced request validation, structured output validation, product payload compatibility, fit score range, contact validation, SafeMessagePolicy, and contract draft safety.
- Migration tests for new columns/defaults/constraints and `contract_draft` task type compatibility if applicable.
- Repository tests proving API repository instance and worker repository instance share PostgreSQL state.
- Worker tests for lifecycle, provider routing, normalization, fit evaluation, invalid product skipping, partial success, no demo injection in acceptance mode, supplier contact compatibility, Gmail sync compatibility, and contract draft compatibility.
- API tests for old and new request payloads plus extended response contracts.
- Frontend tests for search creation, catalog states, filters/facets/guidance, product cards, product details, disabled contact states, and preservation of conversation/contract/assistant UI.
- Final E2E remains governed by `test_protocol.md` and must use real components.

## Risks / Trade-offs

- PostgreSQL-backed runtime integration is larger than UI work but is required before acceptance can be credible.
- Public provider extraction may be brittle; provenance and fallback behavior reduce risk.
- Fit scoring must remain deterministic and evidence-based to avoid invented supplier claims.
- The Made-in-China-like UX must remain clean-room and public-only; this may limit available fields when public pages hide data.
- Frontend additions should preserve existing routes to avoid breaking current tests and demos.

