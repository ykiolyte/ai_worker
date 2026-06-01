You are working in the repository:

https://github.com/ykiolyte/ai_worker

Project:
Product Sourcing MVP — an AI-assisted supplier discovery and first-contact automation service.

Primary sources of truth:
- Main.md
- test_protocol.md
- AGENTS.md
- openspec/project.md
- openspec/config.yaml
- openspec/changes/add-product-sourcing-mvp/
- existing tests
- docker-compose.yml
- backend/app/
- frontend/src/
- e2e/supplier-site/

If code conflicts with Main.md, test_protocol.md, AGENTS.md, or OpenSpec, do not silently follow the code. First update or create OpenSpec artifacts, then implement.

Your task:
Update the project to provide a professional SourcingAI-like search experience inspired by the public UX and behavior of https://ai.made-in-china.com, while preserving the project’s own architecture, safety boundaries, OpenSpec workflow, and final E2E requirements.

Important legal/safety rule:
Do NOT decompile, reverse engineer, deobfuscate, copy proprietary code/assets/algorithms, scrape private APIs, replay signed requests, bypass CAPTCHA/WAF/rate limits, use unauthorized cookies/sessions, or use any undocumented/internal Made-in-China endpoints.

The goal is clean-room implementation:
- similar UX and product behavior;
- own domain model;
- own provider abstraction;
- public-page/search-provider discovery only;
- strict validation;
- persisted async tasks;
- safe supplier communication.

Core product boundary:
The agent helps search, structure, evaluate, and request supplier information.
The agent must NOT:
- purchase products;
- confirm orders;
- promise payment;
- send bank/payment details;
- create legally binding commitments;
- hide the purpose of the inquiry;
- bypass site restrictions;
- engage in prohibited or deceptive sourcing.

Supplier messages may ask about:
- price;
- availability;
- MOQ;
- lead time;
- delivery terms;
- payment options;
- product documents/specifications;
- next safe step.

Supplier messages must not look like an order confirmation.

Repository context:
Backend:
- Python >= 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Redis
- pytest/httpx

Frontend:
- React 19
- TypeScript
- Vite 7
- TanStack React Query
- lucide-react
- custom CSS

Infra:
- Docker Compose
- PostgreSQL 17
- Redis 7
- Playwright MCP / Browser MCP
- SearXNG
- Ollama
- Mailpit
- Nginx controlled supplier test site

Known important current implementation gap:
The repository has Alembic migrations and DB/broker contracts, but runtime app creation currently uses InMemoryRepository by default, and worker.py also creates its own InMemoryRepository. This does not satisfy production-like E2E because API and worker do not share durable state through PostgreSQL.

This must be treated as a critical architecture gap.

High-level target architecture:

React WebUI
  -> FastAPI Backend API
    -> PostgreSQL durable records
    -> Redis/broker durable task boundary
      -> Agent Worker
        -> ModelProvider
        -> ToolRegistry
        -> Browser MCP / Search connectors
        -> Email connector
        -> Telegram connector
        -> Gmail inbound connector when enabled

Hard rules:
- No placeholders.
- No pseudocode.
- No TODO-only implementation.
- No fake UI-only data.
- No static pre-baked frontend search results.
- No demo product injection in acceptance/E2E flow.
- No in-memory repository for final production-like E2E.
- No fake worker in final E2E.
- No disabled queues in final E2E.
- No mock connectors in final E2E.
- No pre-baked LLM output in final E2E.
- No direct LLM/provider calls from business logic outside ModelProvider.
- No direct connector calls outside connector abstractions.
- No blocking HTTP response while product search/contact/contract generation runs.
- All long-running work must be represented by durable AgentTask records.
- All model/connector output is untrusted until schema/domain validation passes.
- Errors must be persisted in user-readable form and logged in developer-readable form.
- Secrets must never be logged.

Before coding:
1. Inspect repository structure.
2. Read Main.md.
3. Read test_protocol.md.
4. Read AGENTS.md.
5. Read openspec/project.md and openspec/config.yaml.
6. Inspect openspec/changes/add-product-sourcing-mvp/.
7. Inspect backend/app/main.py.
8. Inspect backend/app/domain.py.
9. Inspect backend/app/workers.py.
10. Inspect backend/app/repositories.py.
11. Inspect backend/app/database.py.
12. Inspect backend/app/broker.py.
13. Inspect backend/app/connectors.py.
14. Inspect backend/app/model_providers.py.
15. Inspect frontend/src/api.ts, frontend/src/types.ts, and existing pages.
16. Inspect tests and E2E support.
17. Inspect docker-compose.yml.
18. Determine existing test commands and package managers.

OpenSpec workflow:
Use OpenSpec first.

If openspec/changes/add-product-sourcing-mvp/ is still the active MVP change, extend it.
If it is archived or not appropriate, create a new change:

openspec/changes/enhance-sourcingai-like-search/

The change must include or update:
- proposal.md
- design.md
- tasks.md
- specs/search-requests/spec.md
- specs/product-catalog/spec.md
- specs/supplier-contact/spec.md
- specs/agent-orchestration/spec.md
- specs/webui/spec.md
- specs/persistence/spec.md

Use ADDED Requirements or MODIFIED Requirements correctly.

OpenSpec must cover:
1. SourcingAI-like search page.
2. Search request advanced fields.
3. Intent normalization.
4. Missing fields.
5. Clarifying questions.
6. Common filters.
7. Product attribute facets.
8. Sourcing guidance.
9. Extended product cards.
10. Supplier badges.
11. MOQ and price range.
12. Product fit score and matched requirements.
13. Safe public search provider behavior.
14. Made-in-China-like public provider constraints.
15. Product output validation.
16. Product search worker lifecycle.
17. Supplier contact worker lifecycle.
18. Conversation message persistence.
19. Gmail inbound sync compatibility.
20. Contract draft compatibility.
21. PostgreSQL-backed runtime repository requirement.
22. Broker-backed worker boundary requirement.
23. Final E2E constraints.

Run OpenSpec validation before final response:

On Windows prefer:
openspec.cmd validate <change-id> --strict --no-interactive

Otherwise:
openspec validate <change-id> --strict

If the command differs, inspect scripts/docs and use the correct one.

Implementation scope:

PART 1 — Fix production-like persistence/runtime boundary

The project cannot satisfy final E2E while API and worker use separate InMemoryRepository instances.

Implement a PostgreSQL-backed repository or wire the existing database layer into runtime.

Requirements:
1. create_app() must be able to use a PostgreSQL-backed repository from DATABASE_URL.
2. worker.py must use the same PostgreSQL-backed repository.
3. API-created SearchRequest and AgentTask must be visible to the external worker process.
4. Worker-created Products, SupplierContacts, ContactAttempts, ConversationMessages, and ContractDraft status changes must be visible to API/UI.
5. Keep InMemoryRepository only for unit tests/local isolated tests where explicitly injected.
6. Do not make InMemoryRepository the default for production-like docker/e2e.
7. Add config switch only if necessary, but default docker/e2e path must use PostgreSQL.
8. Update tests to prove API and worker share state through repository abstraction.

If Redis/RQ is already suitable:
- wire AgentTask enqueue/dequeue to Redis/RQ or existing broker abstraction.

If current worker loop is repository-polling based:
- make it durable against PostgreSQL.
- ensure it can pick queued AgentTasks from DB.
- ensure status transitions are persisted.

Add or update tests:
- API creates task in DB.
- Worker reads queued task from DB.
- Worker updates task and request statuses.
- API can read updated statuses and products.

PART 2 — Preserve and extend existing domain model

Existing domain entities:
- SearchRequest
- Product
- SupplierContact
- ContactAttempt
- ConversationMessage
- AgentTask
- ContractDraft

Existing AgentTask types:
- product_search
- supplier_contact
- contract_draft

Important migration issue:
Initial DB check constraint for agent_tasks.task_type may only allow product_search and supplier_contact, while code domain includes contract_draft.
If contract_draft is stored in main agent_tasks table, add a migration updating the check constraint to include contract_draft.

SearchRequest currently has:
- id
- query_text
- max_results
- status
- error_message
- agent_task_id
- timestamps

Extend SearchRequest with SourcingAI-like fields:
- normalized_intent JSON/dict
- missing_fields list[str]
- clarifying_questions list[str]
- common_filters list[str]
- product_attributes list[dict]
- sourcing_guidance dict
- suppliers_count int

Product currently has:
- id
- search_request_id
- title
- description
- price
- currency
- product_url
- images
- attributes
- supplier_name
- source_domain
- raw_agent_payload
- contacts

Extend Product with:
- moq: str | None
- price_range: str | None
- fit_score: Decimal | float | None
- fit_summary: str | None
- matched_requirements: list[dict]
- missing_requirements: list[str]
- supplier_badges: list[str]
- supplier_country: str | None
- supplier_city: str | None
- is_verified_supplier: bool
- is_audited_supplier: bool
- supports_customization: bool
- sample_available: bool

Keep backward compatibility with existing API fields and existing old product payloads.

PART 3 — Database migrations

Create Alembic migration(s).

search_requests:
- normalized_intent JSONB NOT NULL DEFAULT '{}'::jsonb
- missing_fields JSONB NOT NULL DEFAULT '[]'::jsonb
- clarifying_questions JSONB NOT NULL DEFAULT '[]'::jsonb
- common_filters JSONB NOT NULL DEFAULT '[]'::jsonb
- product_attributes JSONB NOT NULL DEFAULT '[]'::jsonb
- sourcing_guidance JSONB NOT NULL DEFAULT '{}'::jsonb
- suppliers_count INTEGER NOT NULL DEFAULT 0

products:
- moq TEXT NULL
- price_range TEXT NULL
- fit_score NUMERIC(5,4) NULL
- fit_summary TEXT NULL
- matched_requirements JSONB NOT NULL DEFAULT '[]'::jsonb
- missing_requirements JSONB NOT NULL DEFAULT '[]'::jsonb
- supplier_badges JSONB NOT NULL DEFAULT '[]'::jsonb
- supplier_country TEXT NULL
- supplier_city TEXT NULL
- is_verified_supplier BOOLEAN NOT NULL DEFAULT false
- is_audited_supplier BOOLEAN NOT NULL DEFAULT false
- supports_customization BOOLEAN NOT NULL DEFAULT false
- sample_available BOOLEAN NOT NULL DEFAULT false

agent_tasks:
- if needed, update task_type check constraint to include contract_draft.

Add/update migration tests:
- columns exist;
- JSONB defaults work;
- boolean defaults work;
- fit_score accepts 0..1;
- contract_draft task type is allowed if applicable.

PART 4 — Structured SourcingAI-like output schemas

Implement Pydantic v2 schemas.

Create or update:
- NormalizedIntentSchema
- ProductAttributeFacetSchema
- MatchedRequirementSchema
- SupplierContactSchema
- SourcingGuidanceSchema
- SourcingProductSchema
- SourcingSearchOutputSchema

Expected structured output shape:

{
  "normalizedIntent": {
    "rawQuery": "ПК, вычислительные компьютеры, ноутбуки",
    "productCategory": "computers and computing equipment",
    "targetMarket": null,
    "quantity": null,
    "budget": null,
    "certifications": [],
    "supplierPreference": "manufacturer_first",
    "mustHave": [],
    "niceToHave": []
  },
  "missingFields": [
    "targetMarket",
    "quantity",
    "budget",
    "requiredCertifications"
  ],
  "clarifyingQuestions": [
    "Для какого рынка нужны компьютеры?",
    "Какой объём закупки планируется?",
    "Нужны ли сертификаты CE/RoHS/FCC?"
  ],
  "commonFilters": [
    "Manufacturer",
    "Audited Supplier",
    "Customization Available",
    "Sample Available"
  ],
  "productAttributes": [
    {
      "name": "Application",
      "values": ["Industrial", "Office", "Embedded"]
    },
    {
      "name": "Processor",
      "values": ["Intel", "AMD", "ARM"]
    }
  ],
  "products": [
    {
      "title": "Industrial Fanless Mini PC",
      "price": null,
      "priceRange": "Negotiable",
      "currency": "USD",
      "moq": "10 Pieces",
      "productUrl": "https://example.com/product",
      "supplierName": "Example Technology Co., Ltd.",
      "supplierCountry": "China",
      "supplierCity": "Shenzhen",
      "supplierBadges": ["Manufacturer", "Customization Available"],
      "isVerifiedSupplier": true,
      "isAuditedSupplier": false,
      "supportsCustomization": true,
      "sampleAvailable": true,
      "fitScore": 0.86,
      "fitSummary": "Matches the request: industrial computing product and supplier appears to support customization.",
      "matchedRequirements": [
        {
          "requirement": "computer supplier",
          "evidence": "Listing title and category match computing equipment"
        }
      ],
      "missingRequirements": [
        "No public certification information found"
      ],
      "contacts": [
        {
          "type": "email",
          "value": "sales@example.com"
        }
      ],
      "images": [],
      "description": null,
      "attributes": {}
    }
  ],
  "sourcingGuidance": {
    "qualityIndicators": [
      "Check CE/RoHS/FCC certificates if the target market requires them.",
      "Request datasheet, real product photos, and batch photos."
    ],
    "negotiationTips": [
      "Ask for sample MOQ and bulk MOQ separately.",
      "Request tiered pricing for 50/100/500 units."
    ],
    "riskWarnings": [
      "Verify whether the supplier is a manufacturer or trading company.",
      "Be careful with unusually low prices without specifications."
    ],
    "crossBorderNotes": [
      "Clarify Incoterms: EXW, FOB, CIF, DDP.",
      "Check import restrictions for electronics in the target market."
    ],
    "relatedQueries": [
      "industrial mini PC manufacturer",
      "fanless embedded computer supplier",
      "laptop OEM ODM factory"
    ]
  }
}

Validation rules:
- products must be a list.
- title is required.
- productUrl must be valid http/https URL.
- contacts must contain at least one valid contact if ALLOW_PRODUCTS_WITHOUT_CONTACTS=false.
- supported contact types for MVP are email and telegram.
- email must pass existing email validation.
- telegram must be @username or https://t.me/username or existing supported Telegram format.
- price may be null.
- priceRange may be "Negotiable" or non-empty text.
- fitScore must be between 0 and 1.
- matchedRequirements must contain requirement and evidence.
- missingRequirements must be list[str].
- images must be list of valid URLs.
- attributes must be JSON object.
- sourcingGuidance must be saved even if empty.
- old {"products": [...]} output must remain supported.
- raw_agent_payload must preserve original/provenance data, but unvalidated LLM fields must not become trusted domain data.

PART 5 — Search provider layer

Add a provider abstraction, do not hardcode one website.

Create:
- SearchProvider Protocol/interface
- ProductCandidate DTO/model
- SearchProviderResult DTO/model
- SearchProviderRouter
- MadeInChinaPublicProvider
- GenericWebSearchProvider if consistent with existing search connector architecture

MadeInChinaPublicProvider:
1. Use only public pages visible in a normal browser.
2. Do not use private/undocumented APIs.
3. Do not use cookies, tokens, signed requests, CAPTCHA bypass, WAF bypass, login-only data, or unauthorized sessions.
4. Respect robots.txt, Terms of Use, rate limits, and config.
5. Extract only publicly visible fields when available:
   - product title
   - product URL
   - image URL
   - price text
   - MOQ text
   - supplier name
   - supplier badges
   - source domain
   - public contact hints if visible
6. Return raw ProductCandidate objects for normalization.
7. Store provenance:
   - source_url
   - source_domain
   - extracted_at
   - extraction_method
   - confidence
   - field-level evidence where possible
8. Do not claim verification/audit/certification unless public evidence exists.

Config:
- ENABLE_MADE_IN_CHINA_PROVIDER=true/false
- MADE_IN_CHINA_PROVIDER_MAX_RESULTS=20
- MADE_IN_CHINA_PROVIDER_RATE_LIMIT_SECONDS=3
- SEARCH_PROVIDER_ORDER=made_in_china_public,generic_web,browser_mcp
- ALLOW_PRODUCTS_WITHOUT_CONTACTS=false by default unless already explicitly configured otherwise

Optional:
If existing connectors.py already has made_in_china/search connectors, adapt to existing abstractions rather than creating parallel incompatible systems.

PART 6 — ProductNormalizer and ProductFitEvaluator

Implement ProductNormalizer:
- Converts ProductCandidate into validated SourcingProduct-compatible data.
- Normalizes price and priceRange.
- Normalizes MOQ.
- Normalizes supplier badges.
- Extracts source_domain from productUrl.
- Validates and normalizes contacts.
- Preserves provenance in raw_agent_payload.
- Does not invent missing fields.

Implement ProductFitEvaluator:
Input:
- normalized_intent
- product candidate / normalized product

Output:
- fit_score
- fit_summary
- matched_requirements
- missing_requirements
- supplier_badges

Rules:
- Deterministic score from 0 to 1.
- Manufacturer-first query rewards manufacturer/factory evidence.
- Customization query rewards OEM/ODM/customization evidence.
- Sample requirement rewards sample availability.
- Certification requirements reward matching public evidence only.
- Missing critical fields reduce score.
- Never create claims without evidence.
- Every matched requirement must include evidence.
- Keep it testable without LLM calls.

PART 7 — Worker integration

Update product_search worker:
1. Load AgentTask and SearchRequest by ID from durable repository.
2. Move AgentTask status queued -> running.
3. Move SearchRequest status queued -> running.
4. Build normalized intent from query_text, max_results, and optional advanced fields.
5. Run provider router.
6. If made_in_china provider returns no usable products, fallback to browser_mcp/search connectors according to existing behavior.
7. Normalize candidates.
8. Evaluate fit.
9. Validate structured output.
10. Persist:
   - SearchRequest.normalized_intent
   - SearchRequest.missing_fields
   - SearchRequest.clarifying_questions
   - SearchRequest.common_filters
   - SearchRequest.product_attributes
   - SearchRequest.sourcing_guidance
   - SearchRequest.suppliers_count
   - Products
   - SupplierContacts
11. Deduplicate by product_url and supplier key.
12. Skip invalid products and store skip reasons in AgentTask.output_payload.
13. Partial invalid output must not fail the whole search if at least one valid product is saved.
14. On success, mark SearchRequest completed and AgentTask completed.
15. On critical failure, mark SearchRequest failed and AgentTask failed with user-readable error.
16. Do not call _ensure_demo_product or any demo injection in acceptance/E2E mode.
17. Keep task handling idempotent where possible.

Update supplier_contact worker only as needed:
- Load product/contact/attempt from durable repository.
- Generate safe supplier inquiry via ModelProvider.
- Validate using SafeMessagePolicy.
- Select connector by contact type.
- Send via email or Telegram.
- Create outbound ConversationMessage.
- Update ContactAttempt status sent or failed.
- Do not confirm orders or create obligations.

Update Gmail inbound sync only if affected:
- Preserve existing behavior.
- Inbound messages create ConversationMessage.
- Matching by reply headers or supplier email.
- ContactAttempt can move sent -> responded.
- Auto-reply must require approval unless existing safe runtime explicitly supports it.

Update contract draft flow only if affected:
- Preserve existing ContractDraft behavior.
- Drafts must be clearly marked draft/not signed/not binding.
- Validation must reject binding language, payment instructions, signatures, bank/payment details.
- If contract_draft uses AgentTask table, ensure DB constraint supports it.

PART 8 — Backend API

Keep existing routes working:
GET  /health

POST /api/search-requests
GET  /api/search-requests
GET  /api/search-requests/{request_id}
GET  /api/search-requests/{request_id}/products

GET  /api/products/{product_id}
POST /api/products/{product_id}/contact-supplier
POST /api/products/{product_id}/conversation-messages
POST /api/products/{product_id}/conversation-reply
POST /api/products/{product_id}/assistant-chat

POST /api/products/{product_id}/contracts
GET  /api/products/{product_id}/contracts
GET  /api/contracts/{contract_id}
GET  /api/contracts/{contract_id}/download

POST /api/conversations/sync-gmail
GET  /api/products/{product_id}/export.xlsx

Extend POST /api/search-requests:
Existing payload must still work:
{
  "queryText": "industrial cnc controller",
  "maxResults": 5
}

Add optional SourcingAI-like advanced fields:
{
  "queryText": "ПК, вычислительные компьютеры, ноутбуки",
  "maxResults": 5,
  "targetMarket": null,
  "quantity": null,
  "budget": null,
  "certifications": [],
  "supplierPreference": "manufacturer_first"
}

Validation:
- queryText required
- 3..1000 chars
- maxResults 1..50

Extend GET /api/search-requests/{id}:
Include:
- normalizedIntent
- missingFields
- clarifyingQuestions
- commonFilters
- productAttributes
- sourcingGuidance
- suppliersCount
- productsCount
- status
- errorMessage
- timestamps

Extend GET /api/search-requests/{id}/products:
Include:
- id
- title
- price
- priceRange
- currency
- moq
- productUrl
- supplierName
- sourceDomain
- supplierBadges
- supplierCountry
- supplierCity
- isVerifiedSupplier
- isAuditedSupplier
- supportsCustomization
- sampleAvailable
- fitScore
- fitSummary
- matchedRequirements
- missingRequirements
- imageUrl
- contactsCount

Extend GET /api/products/{id}:
Include full extended fields, contacts, contactAttempts, conversationMessages, and contract drafts if current UI/API expects them.

POST /api/products/{id}/contact-supplier:
Preserve existing payload:
{
  "supplierContactId": "uuid-or-null",
  "language": "ru",
  "style": "formal"
}

If convenient, also accept:
{
  "contactId": "uuid",
  "messageOverride": null
}

But do not break existing frontend/API contract.

PART 9 — Frontend UX

Current frontend routes:
- /
- /search-requests/{id}/products
- /products/{id}

Add or update SourcingAI-like UX without breaking existing operational interface.

Either:
- add /search as a new route; or
- enhance / while preserving existing search request list.

Search creation UI:
- large sourcing prompt textarea
- examples
- maxResults control
- optional advanced fields:
  - target market
  - quantity
  - budget
  - certifications
  - supplier preference
- Start search button
- client validation:
  - required
  - min length 3
  - max length 1000
  - maxResults 1..50
- after creation, redirect to request catalog/detail.

Catalog page:
- original query
- status
- products count
- suppliers count
- missing fields
- clarifying questions
- common filters as chips
- product attributes/facets as chips
- product cards
- SourcingGuidancePanel
- loading state for queued/running
- empty state for completed with zero products
- error state for failed

Product card:
- image
- title
- price or priceRange or "Цена не найдена"
- currency
- MOQ
- supplier name
- source domain
- supplier badges
- "Satisfies N requirements"
- fit score
- buttons:
  - Open
  - Contact supplier where appropriate

Product details:
- title
- source URL as safe external link
- price / price range
- MOQ
- description
- images
- attributes
- supplier info
- badges
- fit summary
- matched requirements with evidence
- missing requirements
- contacts
- contact attempts
- conversation timeline
- contract drafts if already present
- assistant chat if already present

Disable "Contact supplier" if:
- no contacts exist
- unsupported contact type
- active ContactAttempt exists with queued/running status

Security:
- Do not render unsanitized HTML from agent output.
- Treat agent output as text unless sanitized.
- External links must use target="_blank" and rel="noopener noreferrer".

PART 10 — Tests

Follow TDD where behavior is automatable.

Add/update backend unit tests:
- query validation
- maxResults validation
- old product payload validation
- new SourcingAI-like payload validation
- invalid URL rejection
- invalid email rejection
- invalid telegram rejection
- fitScore range validation
- matchedRequirements validation
- products without contacts behavior
- SafeMessagePolicy still rejects prohibited supplier messages
- ContractDraft validation still rejects binding/payment/signature language

Add/update migration tests:
- new columns exist
- JSONB defaults work
- boolean defaults work
- fit_score works
- contract_draft task_type check constraint if applicable

Add/update repository tests:
- PostgreSQL-backed repository persists SearchRequest extended fields
- Product extended fields persist
- SupplierContacts persist
- ConversationMessages persist
- ContactAttempts persist
- AgentTasks persist
- API-created task is visible to worker repository instance
- worker changes are visible to API repository instance

Add/update worker tests:
- product_search queued -> running -> completed
- product_search critical error -> failed
- valid products persist
- invalid products skipped with reasons
- partial invalid output does not fail entire search
- provider router called
- ProductNormalizer called
- ProductFitEvaluator called
- raw_agent_payload provenance stored
- no demo product injection in acceptance mode
- supplier_contact selects email connector
- supplier_contact selects Telegram connector
- supplier_contact creates outbound ConversationMessage
- supplier_contact failure is persisted
- Gmail inbound sync remains compatible
- contract_draft task remains compatible if affected

Add/update API tests:
- POST /api/search-requests old body
- POST /api/search-requests with advanced fields
- GET /api/search-requests/{id} returns extended fields
- GET /api/search-requests/{id}/products returns extended cards
- GET /api/products/{id} returns extended details and existing timeline/contract fields
- POST /api/products/{id}/contact-supplier preserves supplierContactId payload
- active contact attempt blocks new attempt
- unsupported/missing contact is rejected

Add/update frontend tests:
- search creation UI renders
- validation errors render
- successful create redirects
- catalog loading state
- catalog empty state
- catalog failed state
- catalog renders filters/facets/guidance/product cards
- product card shows "Satisfies N requirements"
- product detail shows matched requirements and contacts
- contact button disabled for active attempt
- existing conversation/contract/assistant UI remains functional if already covered

Final E2E:
Must use:
- real WebUI
- real Backend API
- real PostgreSQL
- real broker
- real Agent Worker
- real ModelProvider
- real Browser MCP connector
- real email connector
- real Telegram connector where test secrets/control are available
- controlled supplier test site from e2e/supplier-site/

Forbidden in final E2E:
- mock connectors
- fake worker
- manual DB insertion replacing agent behavior
- disabled queues
- pre-baked LLM output
- static UI data
- in-memory database
- pseudo email/Telegram sending

Controlled scenario:
1. Start Docker Compose stack.
2. Open WebUI.
3. Create search:
   "ПК, вычислительные компьютеры, ноутбуки"
   maxResults = 5
4. Backend creates SearchRequest queued.
5. Backend creates AgentTask product_search queued.
6. Worker picks task and marks request/task running.
7. Browser MCP/search provider visits controlled supplier site and/or allowed public provider.
8. Agent/normalizer validates product output.
9. Products saved with:
   - price or Negotiable
   - MOQ
   - supplier badges
   - fit score
   - matched requirements
10. UI shows:
   - products count
   - suppliers count
   - filters
   - product attribute chips
   - product cards
   - sourcing guidance
11. User opens product.
12. User clicks Contact supplier.
13. ContactAttempt queued is created.
14. Worker sends through Mailpit SMTP for email contact and/or controlled Telegram test connector when configured.
15. Outbound ConversationMessage appears.
16. Product page shows ContactAttempt status sent or failed with user-readable result.
17. If Gmail/IMAP sync is enabled, inbound controlled reply creates inbound ConversationMessage and may move attempt sent -> responded.

If Telegram cannot be executed safely in local CI because secrets are missing:
- keep Telegram connector tests at contract/integration level with explicit config gating.
- do not fake Telegram in final E2E and do not claim it passed.
- document exact missing env vars.

PART 11 — Observability

Add/update structured logs:
- agent_task_id
- search_request_id
- product_id
- contact_attempt_id
- task_type
- status
- error
- duration_ms

Do not log:
- SMTP password
- Telegram token
- IMAP password
- model provider secrets
- cookies/tokens
- payment/bank data

User-facing error:
- short and understandable.

Developer logs:
- structured and detailed.

PART 12 — Documentation

Update docs/README where appropriate:
- local run
- Docker Compose services
- backend URL
- frontend URL
- Mailpit URL
- supplier site URL
- SearXNG URL
- Ollama URL
- Browser MCP URL
- environment variables
- provider configuration
- Made-in-China-like provider safety constraints
- PostgreSQL-backed runtime mode
- broker/worker mode
- tests
- E2E protocol
- OpenSpec validation

Document:
- this is a clean-room SourcingAI-like implementation.
- it does not use Made-in-China private APIs.
- it does not bypass anti-bot controls.
- it does not copy proprietary implementation.
- Made-in-China discovery is optional and public-only.

PART 13 — SupplyChain-AI

Do not integrate https://github.com/VaishnaviThakre/SupplyChain-AI as the core sourcing/search implementation.

It is RAG/chatbot-oriented and not a replacement for this MVP.

Optional backlog documentation only:
- future knowledge assistant for supplier PDFs/spec sheets/datasheets.

Do not implement that unless OpenSpec scope explicitly includes it.

PART 14 — Commands to run

Identify actual repo commands before running.

Run as applicable:

Backend:
- pytest
- ruff check .
- mypy .
- alembic upgrade head

Frontend:
- cd frontend
- npm install if needed
- npm run build
- npm run test if present
- npm run lint if present

OpenSpec:
- openspec.cmd validate <change-id> --strict --no-interactive
or
- openspec validate <change-id> --strict

Docker/E2E:
- docker compose up --build -d
- run existing E2E command if present
- otherwise add/document exact E2E command

If a command cannot run:
Report:
- exact command
- exact error
- missing dependency/service/env var
- whether code changes were still made safely

PART 15 — Final response format

When done, respond with:

1. OpenSpec change ID used.
2. Summary of product behavior added.
3. Architecture changes.
4. Database migrations.
5. Backend/API changes.
6. Worker changes.
7. Frontend changes.
8. Tests added/updated.
9. Commands run and results.
10. Any command failures with exact reasons.
11. Remaining limitations.
12. Manual verification steps.

Acceptance criteria:
The work is acceptable only if:

OpenSpec:
- OpenSpec change exists.
- Specs/tasks reflect implementation.
- OpenSpec validation passes or exact failure is reported.

Architecture:
- API and worker can share durable PostgreSQL state.
- Worker uses durable AgentTask records.
- InMemoryRepository is not the production-like default.
- Long-running work does not block HTTP requests.

Search:
- SourcingAI-like search UX exists.
- Intent normalization fields are persisted.
- Missing fields and clarifying questions are persisted and shown.
- Common filters and product attribute facets are persisted and shown.
- Sourcing guidance is persisted and shown.
- Product cards show MOQ, price range, supplier badges, fit score, and "Satisfies N requirements".

Safety:
- No Made-in-China private APIs.
- No decompilation/reverse engineering.
- No CAPTCHA/WAF/rate-limit bypass.
- No unauthorized sessions.
- No purchase/order/payment/legal commitment actions.
- Supplier messages remain safe inquiries.

Validation:
- Agent output is validated before persistence.
- Invalid product records are skipped with reasons.
- Raw provenance is preserved.

Contact:
- Contact supplier flow still works.
- Active attempts block duplicate attempts.
- Outbound ConversationMessage is created.
- Email/Telegram connector selection remains correct.

Contracts/Gmail:
- Existing Gmail inbound sync is not broken.
- Existing contract draft flow is not broken.
- contract_draft AgentTask DB constraint is fixed if needed.

E2E:
- Final E2E path uses real WebUI, Backend, PostgreSQL, broker, worker, ModelProvider, Browser MCP, email connector, and controlled supplier site.
- No fake UI-only data.
- No in-memory DB.
- No fake worker.
- No disabled queue.
- No pre-baked LLM output.