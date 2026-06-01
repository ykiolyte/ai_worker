# File Plan And Working Instructions

This file is the implementation map for `enhance-sourcingai-like-search`. It is not production code. Update it when ownership or file scope changes.

## Working Rules

- Do not write production code until the OpenSpec diff has been reviewed.
- Keep work TDD-first: add or update failing tests before implementation.
- Keep changes scoped; avoid unrelated refactors.
- Preserve existing routes and payload compatibility unless the OpenSpec artifacts are updated first.
- Treat `docs/tech_brief.md`, `Main.md`, `test_protocol.md`, `AGENTS.md`, `openspec/project.md`, and `openspec/config.yaml` as sources of truth.
- For final E2E, never use in-memory DB, fake workers, mock connectors, static UI data, disabled queues, or pre-baked LLM output.

## Backend Files Expected To Change

- `backend/app/domain.py`
  - Extend `SearchRequest` and `Product` domain fields.
  - Add/adjust validation helpers for sourcing fields if kept in domain layer.
  - Keep SafeMessagePolicy and ContractDraft safety intact.

- `backend/app/main.py`
  - Use durable repository by default outside explicit test injection.
  - Extend API payload DTOs and serializers.
  - Preserve existing endpoints and response compatibility.

- `backend/app/repositories.py`
  - Keep `InMemoryRepository` for explicit tests.
  - Add repository interface or PostgreSQL-backed implementation hooks if not split into a new file.

- `backend/app/postgres_repository.py` or equivalent new file
  - Implement PostgreSQL-backed repository operations.
  - Ensure two repository instances share state.

- `backend/app/database.py`
  - Reuse/create SQLAlchemy engine/session setup.
  - Keep DATABASE_URL validation.

- `backend/app/broker.py`
  - Wire Redis/RQ or document durable PostgreSQL polling if no broker enqueue/dequeue is added.

- `backend/app/worker.py`
  - Use durable repository/runtime.
  - Process queued AgentTask records visible from API.

- `backend/app/workers.py`
  - Integrate provider router, normalizer, fit evaluator, and extended persistence.
  - Remove/disable demo product injection for acceptance/E2E mode.
  - Preserve supplier contact, Gmail inbound sync, and contract draft behavior.

- `backend/app/connectors.py`
  - Adapt existing search/browser/Made-in-China-related connector code to provider abstraction where appropriate.
  - Keep public-only safety constraints.

- `backend/app/model_providers.py`
  - Avoid direct business logic usage; keep provider calls behind `ModelProvider`.

- New likely backend files:
  - `backend/app/sourcing_schemas.py`
  - `backend/app/search_providers.py`
  - `backend/app/product_normalizer.py`
  - `backend/app/product_fit.py`

- `backend/alembic/versions/*.py`
  - Add migration for extended search/product fields.
  - Update task type constraint for `contract_draft` if needed.

## Frontend Files Expected To Change

- `frontend/src/types.ts`
  - Add extended search request and product card/detail fields.

- `frontend/src/api.ts`
  - Preserve existing functions and payloads.
  - Add advanced search request payload fields.

- `frontend/src/App.tsx`
  - Add `/search` route only if needed; otherwise keep `/` as enhanced search first screen.

- `frontend/src/pages/SearchRequestsPage.tsx`
  - Enhance creation UX with prompt textarea, examples, maxResults, and advanced fields.

- `frontend/src/pages/RequestCatalogPage.tsx`
  - Render normalized intent, missing fields, clarifying questions, filters, facets, guidance, supplier count, and extended cards.

- `frontend/src/pages/ProductDetailsPage.tsx`
  - Render extended product details, fit evidence, supplier badges/location, contacts, attempts, conversation, assistant, and contracts.

- `frontend/src/components/format.ts`
  - Add safe formatting helpers for fit score, MOQ, price range, and counts if needed.

- `frontend/src/styles.css`
  - Add professional operational SourcingAI-like layout styles without static fake data.

## Tests Expected To Change

- `tests/test_domain_contract.py`
  - Domain validation and safety checks.

- `tests/test_database_migration_contract.py`
  - New columns/defaults/constraints.

- `tests/test_api_contract.py`
  - Advanced payload and extended response contracts.

- `tests/test_product_search_worker_contract.py`
  - Provider/normalizer/fit evaluator/lifecycle/partial success/no demo injection.

- `tests/test_supplier_contact_worker_contract.py`
  - Durable repo loading and compatibility.

- `tests/test_gmail_inbound_sync_contract.py`
  - Compatibility checks.

- `tests/test_model_provider_contract.py`
  - Ensure new logic remains behind ModelProvider.

- `tests/test_connectors_contract.py`
  - Provider/public-only discovery behavior.

- `tests/test_frontend_contract.py`
  - Search UX/catalog/detail contracts.

- `tests/test_e2e_support_contract.py`
  - Production-like component requirements.

- `tests/test_smoke_flows.py`
  - End-to-end-ish local flow contracts.

## Docs Expected To Change

- `README.md`
- `docs/development.md`
- `docs/testing.md`
- `docs/connectors.md`
- `docs/one-click-deploy.md`
- `docs/mvp-limitations.md`
- `docs/e2e-report-template.md`

## Suggested Implementation Order

1. Migrations and PostgreSQL repository tests.
2. Durable repository and worker boundary.
3. Sourcing schemas, normalizer, and fit evaluator.
4. Provider router and public provider constraints.
5. Product search worker integration.
6. API DTO/serializer extensions.
7. Frontend type/API/page updates.
8. Supplier contact, Gmail, and contract compatibility passes.
9. Observability and docs.
10. Full verification ladder and OpenSpec validation.

