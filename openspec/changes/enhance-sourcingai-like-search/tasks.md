## 0. OpenSpec And Planning

- [x] 0.1 Review `docs/tech_brief.md`, `Main.md`, `test_protocol.md`, `AGENTS.md`, `openspec/project.md`, `openspec/config.yaml`, and baseline `add-product-sourcing-mvp` artifacts before implementation.
- [x] 0.2 Confirm this change remains clean-room and does not use private Made-in-China APIs, reverse engineering, CAPTCHA/WAF bypass, unauthorized sessions, or copied proprietary assets/code.
- [x] 0.3 Keep `file-plan.md` updated when implementation file ownership changes.
- [x] 0.4 Run `openspec.cmd validate enhance-sourcingai-like-search --strict --no-interactive` before coding and after artifact updates.

## 1. Durable Persistence And Worker Boundary

- [x] 1.1 Add failing repository tests proving two repository instances share SearchRequest and AgentTask state through PostgreSQL.
- [x] 1.2 Add failing worker/API integration tests proving API-created queued tasks are visible to worker runtime and worker updates are visible to API.
- [x] 1.3 Implement or wire a PostgreSQL-backed repository for search requests, products, supplier contacts, contact attempts, conversation messages, agent tasks, and contract drafts as needed.
- [x] 1.4 Make `create_app()` use a durable repository from `DATABASE_URL` by default outside explicit test injection.
- [x] 1.5 Make `worker.py` use the same durable repository and process queued AgentTask records from durable state.
- [x] 1.6 Wire Redis/RQ or an equivalent broker-backed boundary if it fits current architecture; otherwise ensure PostgreSQL task polling is durable and documented.
- [x] 1.7 Keep `InMemoryRepository` available only for explicitly injected unit/local isolated tests.
- [x] 1.8 Add or update tests proving no production-like Docker/E2E path silently uses `InMemoryRepository`.

## 2. Migrations And Domain Fields

- [x] 2.1 Add failing migration tests for extended `search_requests` columns and JSONB/integer defaults.
- [x] 2.2 Add failing migration tests for extended `products` columns, JSONB defaults, boolean defaults, and 0..1 `fit_score` behavior.
- [x] 2.3 Add migration for `search_requests` sourcing metadata fields.
- [x] 2.4 Add migration for `products` sourcing card/detail fields.
- [x] 2.5 Update `agent_tasks` task type constraint to include `contract_draft` if the main table stores contract draft tasks.
- [x] 2.6 Extend domain entities while preserving compatibility with existing constructor/default behavior.

## 3. Structured Output, Normalization, And Fit Evaluation

- [x] 3.1 Add failing tests for `NormalizedIntentSchema`, `ProductAttributeFacetSchema`, `MatchedRequirementSchema`, `SupplierContactSchema`, `SourcingGuidanceSchema`, `SourcingProductSchema`, and `SourcingSearchOutputSchema`.
- [x] 3.2 Add failing tests for legacy `{"products": [...]}` output compatibility.
- [x] 3.3 Add failing tests for invalid URL/email/Telegram, product without contacts, invalid images, invalid matched requirements, and out-of-range fit score.
- [x] 3.4 Implement Pydantic v2 sourcing output schemas.
- [x] 3.5 Implement `ProductNormalizer` to convert raw candidates into validated sourcing product payloads without inventing missing fields.
- [x] 3.6 Implement deterministic `ProductFitEvaluator` with evidence-based matched requirements and missing requirements.
- [x] 3.7 Preserve raw provenance in `raw_agent_payload` while keeping unvalidated fields out of trusted domain data.

## 4. Provider Discovery

- [x] 4.1 Add failing tests for `SearchProvider`, `ProductCandidate`, `SearchProviderResult`, and `SearchProviderRouter`.
- [x] 4.2 Add failing tests for provider ordering, fallback, partial failure, and no private/unauthorized provider behavior.
- [x] 4.3 Implement provider abstractions consistent with existing connector architecture.
- [x] 4.4 Implement `MadeInChinaPublicProvider` using public pages/search-visible content only.
- [x] 4.5 Implement or adapt `GenericWebSearchProvider` if needed for fallback behavior.
- [x] 4.6 Add configuration for `ENABLE_MADE_IN_CHINA_PROVIDER`, `MADE_IN_CHINA_PROVIDER_MAX_RESULTS`, `MADE_IN_CHINA_PROVIDER_RATE_LIMIT_SECONDS`, and `SEARCH_PROVIDER_ORDER`.
- [x] 4.7 Store provider provenance: `source_url`, `source_domain`, `extracted_at`, `extraction_method`, `confidence`, and field-level evidence where available.

## 5. Product Search Worker

- [x] 5.1 Add failing worker tests for durable queued -> running -> completed search lifecycle.
- [x] 5.2 Add failing worker tests for critical failure -> failed and partial invalid output -> completed with skip reasons when at least one valid product is saved.
- [x] 5.3 Add failing worker tests proving provider router, normalizer, and fit evaluator are invoked.
- [x] 5.4 Add failing worker tests proving no demo product injection occurs in acceptance/E2E mode.
- [x] 5.5 Update `product_search` processing to persist normalized intent, missing fields, clarifying questions, common filters, product attributes, sourcing guidance, supplier count, products, and contacts.
- [x] 5.6 Deduplicate by product URL and supplier key while storing duplicate/skip reasons in `AgentTask.output_payload`.
- [x] 5.7 Persist user-readable critical errors and developer-readable structured logs with correlation IDs.

## 6. Supplier Contact, Gmail, And Contracts Compatibility

- [x] 6.1 Add/update tests proving supplier contact worker loads product/contact/attempt from durable repository.
- [x] 6.2 Preserve email and Telegram connector selection and outbound `ConversationMessage` creation.
- [x] 6.3 Preserve active contact attempt blocking.
- [x] 6.4 Preserve `SafeMessagePolicy` checks prohibiting orders, payment promises, bank/payment details, and legal commitments.
- [x] 6.5 Add/update tests proving Gmail inbound sync still creates inbound `ConversationMessage` and can move attempts `sent -> responded`.
- [x] 6.6 Add/update tests proving contract draft generation remains draft/not signed/not binding and rejects binding/payment/signature language.

## 7. Backend API

- [x] 7.1 Add failing API tests for old `POST /api/search-requests` payload compatibility.
- [x] 7.2 Add failing API tests for new advanced search request fields.
- [x] 7.3 Extend request DTOs and validation without breaking existing frontend calls.
- [x] 7.4 Extend `GET /api/search-requests/{id}` response with sourcing metadata and supplier count.
- [x] 7.5 Extend `GET /api/search-requests/{id}/products` response with extended product card fields.
- [x] 7.6 Extend `GET /api/products/{id}` response with extended detail fields while preserving contacts, attempts, conversation messages, assistant messages, and contract behavior.
- [x] 7.7 Preserve `POST /api/products/{id}/contact-supplier` payload compatibility and add optional `contactId`/`messageOverride` only if it does not complicate compatibility.

## 8. Frontend UX

- [x] 8.1 Add failing frontend tests for SourcingAI-like search creation UI, validation, and successful redirect.
- [x] 8.2 Add or enhance first-screen search route with prompt textarea, examples, max results, and optional advanced fields.
- [x] 8.3 Add failing frontend tests for catalog loading, empty, failed, filters/facets/guidance, and product cards.
- [x] 8.4 Render missing fields, clarifying questions, common filters, product attribute facets, sourcing guidance, supplier count, and products count.
- [x] 8.5 Update product cards with image, price/price range, MOQ, supplier badges, fit score, and "Satisfies N requirements".
- [x] 8.6 Add failing frontend tests for product detail matched requirements, missing requirements, contacts, and disabled contact states.
- [x] 8.7 Extend product details while preserving conversation timeline, assistant chat, and contract draft UI if already present.
- [x] 8.8 Ensure external links use `target="_blank"` and `rel="noopener noreferrer"` and agent output is rendered as text, not unsanitized HTML.

## 9. Observability And Documentation

- [x] 9.1 Add/update structured logs with `agent_task_id`, `search_request_id`, `product_id`, `contact_attempt_id`, `task_type`, `status`, `error`, and `duration_ms`.
- [x] 9.2 Add tests or assertions preventing SMTP, IMAP, Telegram, model provider, cookie/token, or payment/bank secrets from logs and responses.
- [x] 9.3 Update documentation for local run, provider config, clean-room Made-in-China-like constraints, PostgreSQL runtime mode, broker/worker mode, and E2E protocol.
- [x] 9.4 Document Telegram E2E gating if project-owned secrets are unavailable; do not fake Telegram acceptance.

## 10. Verification

- [x] 10.1 Run backend tests relevant to domain, migrations, repositories, API, workers, connectors, and smoke flows.
- [x] 10.2 Run frontend build/tests available in `frontend/package.json`.
- [ ] 10.3 Run Alembic upgrade against test/local PostgreSQL where available. Blocked locally: `python -m alembic upgrade head` timed out because PostgreSQL was not reachable.
- [x] 10.4 Run `openspec.cmd validate enhance-sourcingai-like-search --strict --no-interactive`.
- [ ] 10.5 Run or document production-like E2E using real WebUI, Backend, PostgreSQL, broker, worker, ModelProvider, Browser MCP, email connector, Telegram connector when configured, and controlled supplier site. Blocked locally: `docker compose ps` cannot connect to the Docker Desktop Linux engine pipe, so the production-like stack cannot be started in this environment.
