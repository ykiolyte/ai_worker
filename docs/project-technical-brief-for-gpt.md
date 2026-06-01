# Технический бриф проекта для другого GPT

Документ предназначен для передачи контекста другому чат-боту/агенту GPT, чтобы он мог проектировать новые фичи, интегрировать готовые изменения и не нарушать продуктовые границы проекта.

## 1. Краткая суть проекта

Проект: **Product Sourcing MVP**.

Цель: сервис, в котором пользователь через WebUI создает поисковый запрос на товар, AI-агент исследует поставщиков через браузерный MCP-коннектор, система сохраняет нормализованные карточки товаров и контакты поставщиков, а пользователь может инициировать первое обращение к поставщику через email или Telegram.

Ключевой принцип: агент помогает искать, структурировать и запрашивать информацию. Он **не покупает**, **не подтверждает заказы**, **не обещает оплату**, **не отправляет платежные данные** и **не создает юридические обязательства**.

Основные источники истины:

- `Main.md` - продуктовые и архитектурные требования MVP.
- `test_protocol.md` - acceptance/E2E-протокол.
- `openspec/project.md` и `openspec/config.yaml` - правила OpenSpec workflow.
- `openspec/changes/add-product-sourcing-mvp/` - первый MVP change.
- `AGENTS.md` - инструкции для coding agents.

Если эти источники конфликтуют с кодом или новой задачей, нужно сначала обновить OpenSpec artifacts, а не сразу писать код.

## 2. MVP scope

В MVP входят:

- WebUI:
  - список поисковых запросов;
  - создание нового запроса;
  - просмотр статуса обработки;
  - каталог найденных товаров по запросу;
  - страница товара;
  - контакты поставщика;
  - действие "связаться с поставщиком";
  - история попыток связи и сообщений.
- Backend API:
  - управление search requests;
  - выдача product catalog/details;
  - создание agent tasks;
  - запуск контакта с поставщиком;
  - статусы и результаты коммуникации.
- Persistence:
  - `search_requests`;
  - `products`;
  - `supplier_contacts`;
  - `contact_attempts`;
  - `agent_tasks`;
  - расширение: `conversation_messages`;
  - расширение: `contract_drafts`.
- Agent Worker:
  - `product_search`;
  - `supplier_contact`;
  - расширение: `contract_draft`;
  - Gmail inbound sync/reply flow.
- Integrations:
  - Microsoft Playwright MCP / browser MCP;
  - email SMTP/IMAP;
  - Telegram Bot API;
  - local/real LLM provider through `ModelProvider`;
  - optional SearXNG/DuckDuckGo public search;
  - optional Made-in-China discovery.

## 3. Out of scope / запреты

MVP не должен включать:

- автономную покупку;
- подтверждение заказа;
- платежи;
- передачу банковских или платежных данных без отдельного подтверждения;
- полноценный CRM;
- массовые рассылки;
- long-running negotiation automation;
- supplier scoring как обязательный MVP baseline, хотя в коде уже есть расширенный supplier comparison;
- ERP/1C integration;
- multi-tenant/advanced permissions;
- fine-tuning;
- скрытие назначения товара или обход ограничений.

Supplier messages должны запрашивать информацию: цену, наличие, MOQ, сроки, условия оплаты/доставки, документы, следующий безопасный шаг. Они не должны выглядеть как заказ или юридически значимое согласие.

## 4. Архитектура

Целевая архитектура:

```text
React WebUI
  -> FastAPI Backend API
    -> durable records in PostgreSQL
    -> task queue/broker Redis
      -> Agent Worker
        -> ModelProvider
        -> ToolRegistry
        -> Browser MCP / Search connectors
        -> Email connector
        -> Telegram connector
```

Правила:

- WebUI общается только с Backend API.
- Backend валидирует входные данные, создает durable records и ставит задачи.
- Long-running research/contact work не должен блокировать HTTP request.
- Worker обрабатывает agent tasks асинхронно.
- PostgreSQL должен быть source of truth для production-like E2E.
- LLM/connector output считается недоверенным, пока не прошел schema/domain validation.
- E2E запрещено проходить на mock connectors, fake worker, static UI data, in-memory DB или pre-baked LLM output.

Важное состояние текущей реализации: в коде есть Alembic migrations и database/broker contracts, но `create_app()` по умолчанию использует `InMemoryRepository`. `worker.py` также создает отдельный `InMemoryRepository`. Для полного соответствия `test_protocol.md` нужна реальная PostgreSQL-backed repository и реальный broker-backed worker boundary либо доказуемая production-like интеграция.

## 5. Технологический стек

Backend:

- Python `>=3.12`;
- FastAPI;
- Pydantic v2;
- SQLAlchemy 2.x;
- Alembic;
- PostgreSQL;
- Redis;
- RQ указан в зависимостях, но текущий worker loop работает поверх repository abstraction;
- pytest/httpx для тестов.

Frontend:

- React 19;
- TypeScript;
- Vite 7;
- TanStack React Query;
- lucide-react icons;
- собственные CSS/styles.

Infra/local:

- Docker Compose;
- PostgreSQL 17;
- Redis 7;
- Playwright MCP;
- SearXNG;
- Ollama;
- Mailpit;
- Nginx supplier test site.

## 6. Основные директории

```text
backend/app/
  main.py              FastAPI app and API routes
  domain.py            domain entities, validation, status transitions
  agent.py             ModelProvider protocol, ToolRegistry, prompts, safety policy
  connectors.py        MCP, search, email, Telegram, Gmail connectors
  workers.py           product search, supplier contact, Gmail sync, contract draft processing
  worker.py            worker loop entrypoint
  repositories.py      current in-memory repository
  database.py          DB URL validation and engine factory
  broker.py            Redis URL validation and connection factory
  model_providers.py   local_demo and Ollama providers
  config.py            environment settings

frontend/src/
  App.tsx
  api.ts
  types.ts
  pages/
  components/
  styles.css

openspec/
  project.md
  config.yaml
  changes/

docs/
  development/testing/connectors/deploy docs

e2e/supplier-site/
  controlled supplier HTML pages
```

## 7. Domain model

### SearchRequest

Поля: `id`, `query_text`, `max_results`, `status`, `error_message`, `agent_task_id`, timestamps.

Статусы:

- `queued`;
- `running`;
- `completed`;
- `failed`;
- `cancelled`.

Валидация:

- `queryText` обязателен;
- длина 3..1000 символов;
- `maxResults` 1..50.

### Product

Поля: `id`, `search_request_id`, `title`, `description`, `price`, `currency`, `product_url`, `images`, `attributes`, `supplier_name`, `source_domain`, `raw_agent_payload`, `contacts`.

Валидация agent output:

- title обязателен;
- `productUrl` должен быть http/https URL;
- минимум один contact, если `ALLOW_PRODUCTS_WITHOUT_CONTACTS=false`;
- contacts валидируются по типу.

### SupplierContact

Типы:

- `email`;
- `telegram`.

Email должен соответствовать простому email regex. Telegram должен быть `@username` или `https://t.me/username`.

### ContactAttempt

Поля: `product_id`, `supplier_contact_id`, `channel`, `message_text`, `agent_task_id`, `status`, `external_message_id`, timestamps, errors.

Статусы:

- `queued`;
- `running`;
- `sent`;
- `responded`;
- `failed`;
- `cancelled`.

Активные попытки (`queued`/`running`) блокируют создание новой попытки для товара.

### ConversationMessage

Расширение для timeline переписки.

Поля: `product_id`, `supplier_contact_id`, `contact_attempt_id`, `direction`, `channel`, `body`, `subject`, addresses, `status`, `external_message_id`, `provider_timestamp`, `requires_user_approval`, timestamps.

Directions:

- `outbound`;
- `inbound`.

Statuses:

- `queued`;
- `sent`;
- `failed`;
- `received`.

### AgentTask

Типы:

- `product_search`;
- `supplier_contact`;
- `contract_draft` - расширение.

Статусы:

- `queued`;
- `running`;
- `completed`;
- `failed`;
- `cancelled`.

### ContractDraft

Расширение для черновиков договоров. Черновик должен быть явно помечен как draft/not signed/not binding. Запрещены тексты с order confirmation, payment details, signatures, legally binding wording.

## 8. Database schema

Alembic migrations:

- `0001_initial_schema.py`:
  - `agent_tasks`;
  - `search_requests`;
  - `products`;
  - `supplier_contacts`;
  - `contact_attempts`;
  - indexes and check constraints.
- `0002_conversation_messages.py`:
  - `conversation_messages`;
  - direction/status/channel checks.
- `0003_search_request_max_results.py`:
  - `search_requests.max_results`.
- `0004_conversation_message_provider_timestamp.py`:
  - `conversation_messages.provider_timestamp`.

Contracts DB:

- `scripts/contracts_schema.sql` создает `contract_drafts`.
- В `docker-compose.yml` есть отдельный `contracts-postgres` на host port `5433`.

Важно: `0001_initial_schema.py` check constraint для `agent_tasks.task_type` содержит только `product_search` и `supplier_contact`; кодовый domain уже содержит `contract_draft`. Если переносить `contract_draft` в основной `agent_tasks`, нужна миграция check constraint.

## 9. API surface

Base API: `http://localhost:8000/api`.

Routes:

```text
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
```

Important payloads:

```json
POST /api/search-requests
{
  "queryText": "industrial cnc controller",
  "maxResults": 5
}
```

```json
POST /api/products/{product_id}/contact-supplier
{
  "supplierContactId": "uuid-or-null",
  "language": "ru",
  "style": "formal"
}
```

```json
POST /api/products/{product_id}/conversation-reply
{
  "supplierContactId": "uuid",
  "replyToMessageId": "uuid-or-null",
  "language": "ru",
  "style": "formal"
}
```

```json
POST /api/products/{product_id}/assistant-chat
{
  "message": "Что еще нужно запросить у поставщика?"
}
```

## 10. Agent workflow

### Product search

1. API создает `SearchRequest`.
2. API создает `AgentTask(type=product_search)`.
3. Worker переводит task/request в `running`.
4. Worker вызывает optional `made_in_china` connector.
5. Если продуктов нет, вызывает `browser_mcp`.
6. Connector возвращает payload `{ products: [...] }`.
7. Worker валидирует каждый product payload.
8. Worker дедуплицирует по `product_url` и supplier key.
9. Worker сохраняет товары и contacts.
10. Worker обновляет `AgentTask.output_payload` и завершает request.

Текущий код добавляет demo product для презентации через `_ensure_demo_product()`.

### Supplier contact

1. API проверяет product existence.
2. API блокирует новый контакт, если есть active attempt.
3. API выбирает contact.
4. API создает `ContactAttempt` и `AgentTask(type=supplier_contact)`.
5. Worker генерирует сообщение через `ModelProvider`.
6. `SafeMessagePolicy` проверяет forbidden phrases и required topics.
7. Worker отправляет через email или Telegram connector.
8. Worker создает outbound `ConversationMessage`.
9. Worker переводит attempt в `sent` или `failed`.

### Gmail inbound sync

1. Connector fetches unseen IMAP messages.
2. Система сопоставляет письмо по reply headers или email contact.
3. Создается inbound `ConversationMessage`.
4. Attempt может перейти `sent -> responded`.
5. Анализ supplier reply обновляет product attributes.
6. При наличии runtime может быть auto reply; без runtime message помечается как requiring approval.

### Contract draft

1. API создает `ContractDraft`.
2. API создает `AgentTask(type=contract_draft)`.
3. Worker генерирует draft через model provider.
4. Domain validation запрещает обязательства, платежные инструкции, подписи, bank/payment details.
5. Draft становится `ready` и доступен для download.

## 11. ModelProvider

Protocol:

```python
class ModelProvider(Protocol):
    name: str
    def complete(self, prompt: str, tools: list[str] | None = None) -> Any: ...
```

Реализации:

- `LocalDemoModelProvider`:
  - используется для local demo/browser extraction;
  - не подходит для полноценного contextual supplier replies.
- `OllamaModelProvider`:
  - вызывает `/api/generate`;
  - `format=json`;
  - low temperature;
  - используется с `MODEL_PROVIDER=ollama`, например `mistral-nemo:12b`.
- `ConfiguredModelProvider`/`ConfiguredWorkerModelProvider`:
  - placeholders, direct completions not wired.

Новые provider integrations должны идти через `ModelProvider`, а не напрямую в business logic.

## 12. Connectors

Tool registry names:

- `browser_mcp`;
- `email`;
- `telegram`;
- `gmail_inbound`;
- `made_in_china` optional;
- search engines optional.

Browser:

- Microsoft Playwright MCP;
- stdio or HTTP MCP client;
- controlled allowed domains by `BROWSER_ALLOWED_DOMAINS`;
- public internet gated by `BROWSER_ALLOW_PUBLIC_INTERNET`.

Search:

- SearXNG JSON;
- DuckDuckGo HTML;
- multi-engine dedup.

Email:

- SMTP outbound;
- IMAP inbound/Gmail-like sync;
- Mailpit local demo on `http://127.0.0.1:8025`.

Telegram:

- Telegram Bot API connector.

Security:

- connector errors redact secrets;
- browser public network access must be explicit;
- E2E cannot send to uncontrolled external suppliers without written permission.

## 13. Frontend

WebUI is a messenger-style operational interface.

Routes:

- `/` - search requests page;
- `/search-requests/{id}/products` - request catalog;
- `/products/{id}` - product details.

API client: `frontend/src/api.ts`.

Types: `frontend/src/types.ts`.

Main screens:

- `SearchRequestsPage.tsx`;
- `RequestCatalogPage.tsx`;
- `ProductDetailsPage.tsx`.

Features visible from current types/API:

- create/list search requests;
- max results control;
- product catalog;
- duplicate supplier candidates;
- product detail;
- contact supplier;
- record inbound message;
- request AI reply;
- sync Gmail;
- internal product assistant chat;
- list/create/download contract drafts;
- product export as `.xlsx` via HTML Excel response;
- supplier comparison/rating fields.

## 14. Local run

One-click Windows:

```powershell
START_PROJECT.cmd
STOP_PROJECT.cmd
```

Docker Compose:

```powershell
docker compose up --build -d
```

URLs:

- WebUI: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- Mailpit: `http://127.0.0.1:8025`
- Supplier site: `http://127.0.0.1:8088`
- SearXNG: `http://127.0.0.1:8888`
- Ollama: `http://127.0.0.1:11434`
- Browser MCP: `http://127.0.0.1:8931/mcp`

Local `.env.example` defaults:

- `MODEL_PROVIDER=local_demo`;
- `MODEL_NAME=browser-extraction-v0`;
- `AUTO_PROCESS_SEARCH_TASKS=true`;
- `AUTO_PROCESS_SUPPLIER_CONTACT_TASKS=true`;
- `AUTO_PROCESS_CONTRACT_TASKS=true`;
- `EMAIL_CONNECTOR_PROVIDER=smtp`;
- SMTP points to Mailpit;
- Telegram placeholders are present but real Telegram requires secrets.

For broader local AI search:

```env
MODEL_PROVIDER=ollama
MODEL_NAME=mistral-nemo:12b
BROWSER_RESEARCH_MODE=ai_internet
BROWSER_ALLOW_PUBLIC_INTERNET=true
WEB_SEARCH_PROVIDER=multi
```

## 15. E2E acceptance protocol

Final E2E must use:

- real WebUI;
- real Backend API;
- real PostgreSQL;
- real broker;
- real Agent Worker;
- real LLM provider through `ModelProvider`;
- real browser MCP connector;
- real email connector;
- real Telegram connector;
- controlled supplier test site and test contacts owned by the project.

Forbidden in final E2E:

- mock connectors;
- fake worker;
- manual DB insertion instead of agent behavior;
- disabled queues;
- pre-baked LLM output;
- static UI data;
- in-memory database;
- pseudo email/Telegram sending.

Controlled test supplier data lives in `e2e/supplier-site/` and includes products such as:

- `E2E UAV Flight Controller FC-100`;
- `E2E Industrial CNC Controller IC-200`;
- `E2E Rack Workstation RW-500`;
- failure/invalid scenarios.

## 16. OpenSpec workflow for future GPT

Use local skills in `.codex/skills`:

- explore unclear requirements;
- create/update `openspec/changes/<change-id>/`;
- implement via apply workflow;
- verify against specs, tasks, and `test_protocol.md`;
- archive only after implementation and verification are complete.

On Windows prefer:

```powershell
openspec.cmd validate <change-id> --strict --no-interactive
```

TDD rules:

1. Add/update failing automated test before production code when behavior is automatable.
2. Make the smallest production change that passes.
3. Refactor only while tests are green.
4. Keep tests mapped to OpenSpec requirements and TC-E2E cases.
5. Mark OpenSpec tasks complete only after related tests pass.

## 17. Test suite map

Current tests include contract and behavior checks:

- API contract;
- agent runtime contract;
- worker runtime contract;
- product search worker contract;
- supplier contact worker contract;
- model provider contract;
- connector contract;
- database migration contract;
- frontend contract;
- E2E support contract;
- traceability;
- smoke flows;
- setup/config/observability/docs contracts;
- Gmail inbound sync contract.

Use `pytest` from repository root after backend dependencies are installed.

Frontend build:

```powershell
cd frontend
npm run build
```

## 18. Known implementation risks / gaps

These are important for future work:

- Runtime repository is currently in-memory by default, despite PostgreSQL being required by product/E2E sources of truth.
- Worker process creates its own in-memory repository, so it does not share state with API unless replaced/integrated.
- Redis/RQ dependency exists, but durable queue integration is not fully represented by current `worker.py`.
- `contract_draft` exists in domain/worker/API, but initial DB check constraint only allowed `product_search` and `supplier_contact`.
- `ConfiguredModelProvider` is a placeholder; real non-Ollama providers need implementation behind `ModelProvider`.
- Some frontend/API strings show mojibake in one fallback error message in `frontend/src/api.ts`; check encoding when editing.
- `Main.md` and `test_protocol.md` may display mojibake in PowerShell unless read as UTF-8; treat files as UTF-8.
- Some features implemented after MVP are beyond original MVP boundaries; when expanding them, create/update OpenSpec changes explicitly.

## 19. Safe extension guidance

When adding a feature:

- First determine whether it is MVP-compatible or an extension.
- If unclear, use OpenSpec explore/propose before coding.
- Keep all external actions behind connector abstractions.
- Keep all model calls behind `ModelProvider`.
- Validate all model outputs with Pydantic/domain validation before persistence.
- Never let LLM text directly trigger purchase/payment/order actions.
- Add tests at the closest level first: domain -> worker -> API -> frontend -> smoke/E2E.
- Update docs and `test_protocol.md` coverage when acceptance behavior changes.

When integrating a ready-made feature:

- Map it to existing domain entities first.
- Check whether it needs a new `AgentTaskType`, status, DB migration, API endpoint, or frontend route.
- Check whether it violates MVP non-goals.
- Add OpenSpec delta specs and tasks before implementation if behavior changes.
- Prefer adapting to current abstractions over adding parallel subsystems.

## 20. Minimal prompt to give another GPT

Use this repository as a Product Sourcing MVP for AI-assisted supplier discovery and first-contact automation. Follow `Main.md`, `test_protocol.md`, `openspec/project.md`, `openspec/config.yaml`, and `AGENTS.md` as sources of truth. Use OpenSpec changes for new work, TDD for implementation, and never bypass the final E2E constraints. The core flow is: WebUI creates search request -> Backend creates durable request/task -> Worker uses Browser MCP/search/model providers -> Products and contacts are validated and persisted -> User opens product -> Agent sends safe supplier information request through email/Telegram -> Conversation and statuses are tracked. Do not implement autonomous purchasing, order confirmation, payments, mass messaging, advanced CRM, ERP exports, or binding legal commitments unless the project scope is formally changed.
