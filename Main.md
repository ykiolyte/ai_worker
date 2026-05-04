

# Техническое задание

## MVP-сервис поиска товаров и связи с поставщиками через AI-агента

**Версия:** 1.0  
**Статус:** MVP Scope  
**Цель документа:** зафиксировать требования к первому рабочему релизу сервиса, архитектуру, функциональные границы, модель данных, API, сценарии поведения и структуру OpenSpec-спецификаций.

---

## 1. Цель проекта

Необходимо реализовать сервис, позволяющий пользователю через WebUI создавать поисковые запросы на товары, запускать AI-агента для исследования поставщиков в интернете, сохранять найденные карточки товаров в БД, просматривать результаты и инициировать связь с поставщиком через агента.

MVP должен решать две основные задачи:

1. **Поиск товаров по пользовательскому запросу.**  
    Пользователь вводит запрос, агент через браузерный MCP-коннектор выполняет исследование, извлекает товарные карточки и сохраняет их в БД.
    
2. **Связь с поставщиком.**  
    Пользователь открывает карточку товара и нажимает кнопку «Связаться». Агент выбирает подходящий канал связи по типу контакта, отправляет сообщение поставщику и сохраняет результат коммуникации.
    

---

## 2. Границы MVP

### 2.1. Входит в MVP

В MVP должны быть реализованы:

- WebUI:
    
    - список пользовательских поисковых запросов;
        
    - создание нового запроса;
        
    - просмотр статуса обработки запроса;
        
    - каталог найденных товаров по конкретному запросу;
        
    - страница товара;
        
    - кнопка «Связаться с поставщиком»;
        
    - отображение статуса и результата контакта.
        
- Backend API:
    
    - управление поисковыми запросами;
        
    - управление товарами;
        
    - запуск агентских задач;
        
    - получение статусов выполнения;
        
    - получение результатов контакта с поставщиком.
        
- База данных:
    
    - хранение запросов;
        
    - хранение карточек товаров;
        
    - хранение контактов поставщиков;
        
    - хранение истории агентских задач;
        
    - хранение результатов коммуникаций.
        
- AI-агент:
    
    - выполнение поиска товаров через MCP browser connector;
        
    - нормализация найденных данных;
        
    - сохранение найденных товаров;
        
    - инициирование связи с поставщиком через email или Telegram connector;
        
    - сохранение итогов контакта.
        
- Интеграции:
    
    - MCP-коннектор для браузерного исследования;
        
    - email-коннектор;
        
    - Telegram-коннектор.
        

---

### 2.2. Не входит в MVP

Следующие функции должны быть исключены из MVP и вынесены в backlog:

- полноценный CRM-модуль;
    
- автоматическое многошаговое ведение переговоров;
    
- сравнение цен и интеллектуальный рейтинг поставщиков;
    
- дедупликация товаров между разными запросами на продвинутом уровне;
    
- платежи;
    
- личные кабинеты поставщиков;
    
- роли и permissions, кроме минимального admin/user при необходимости;
    
- массовая рассылка;
    
- автоматический перевод переписки;
    
- аналитика закупок;
    
- экспорт в Excel/CSV;
    
- интеграции с ERP/1C;
    
- продвинутый approval workflow;
    
- мультитенантность;
    
- сложная система очередей приоритизации;
    
- fine-tuning модели;
    
- автономная закупка или оформление заказа.
    

---

## 3. Предлагаемая OpenSpec-структура

Так как система создаётся с нуля, рекомендуется оформить MVP как change:

```text
openspec/
  project.md
  changes/
    add-product-sourcing-mvp/
      proposal.md
      design.md
      tasks.md
      specs/
        search-requests/
          spec.md
        product-catalog/
          spec.md
        supplier-contact/
          spec.md
        agent-orchestration/
          spec.md
        webui/
          spec.md
        persistence/
          spec.md
```

Рекомендуемый `change-id`:

```text
add-product-sourcing-mvp
```

OpenSpec-документация использует отдельные change-папки для proposed modifications, а delta-specs описывают новые требования через `ADDED Requirements`; после реализации изменения архивируются и становятся частью основной спецификации. ([GitHub](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md?utm_source=chatgpt.com "OpenSpec/docs/concepts.md at main"))

---

# 4. OpenSpec Proposal

Файл:

```text
openspec/changes/add-product-sourcing-mvp/proposal.md
```

```md
# Change: Add Product Sourcing MVP

## Summary

Implement an MVP service for AI-assisted product sourcing. The system shall provide a WebUI for creating search requests, browsing discovered product cards, viewing product details, and asking an AI agent to contact suppliers via supported communication channels.

## Problem

Users need a centralized tool to search for industrial, computing, and component products, store structured product cards, and initiate supplier communication without manually copying data between browser research, spreadsheets, and messaging tools.

## Goals

- Allow users to create product search requests from WebUI.
- Use an AI agent with a browser MCP connector to research products online.
- Store normalized product cards in a database.
- Display search requests and product catalog in WebUI.
- Allow users to open a product card and request supplier contact.
- Use email or Telegram connector depending on supplier contact type.
- Persist communication attempts and their results.
- Provide clear statuses for search and contact operations.

## Non-Goals

- No autonomous purchasing.
- No payment processing.
- No supplier scoring engine.
- No advanced CRM.
- No multi-user permission model beyond minimal authentication if required.
- No advanced duplicate-resolution workflow.
- No long-running negotiation automation.
- No ERP/1C integration.
- No export features in MVP.

## MVP Success Criteria

- User can create a search request.
- Agent can process the request through a browser MCP connector.
- At least one valid product card can be saved for a successful search.
- User can browse products linked to the request.
- User can open product details.
- User can request supplier contact.
- Agent can select email or Telegram connector based on saved contact type.
- Contact attempt and result are saved and visible on the product page.
- All core operations expose deterministic statuses.
- Errors are stored and visible in a user-readable form.

## Risks

- Browser research quality depends on MCP connector reliability and target websites.
- Supplier contact data may be incomplete or invalid.
- LLM output may be inconsistent without strict schema validation.
- Telegram automation may require account/session management and compliance checks.
- Email deliverability depends on SMTP/provider configuration.

## Rollout

1. Implement database schema and backend domain model.
2. Implement API endpoints.
3. Implement WebUI pages.
4. Implement agent orchestration interface.
5. Implement browser MCP search task.
6. Implement supplier contact task.
7. Add logging, statuses, validation, and basic tests.
```

---

# 5. Архитектура MVP

## 5.1. Компоненты системы

```text
┌───────────────────────┐
│        WebUI          │
│  Requests / Products  │
└───────────┬───────────┘
            │ HTTP API
┌───────────▼───────────┐
│      Backend API      │
│  Auth / REST / Jobs   │
└───────────┬───────────┘
            │
┌───────────▼───────────┐
│     Application       │
│ Search / Product /    │
│ Supplier Contact      │
└───────┬───────┬───────┘
        │       │
        │       │
┌───────▼───┐ ┌─▼─────────────┐
│ Database  │ │ Agent Worker  │
│ Postgres  │ │ LLM + Tools   │
└───────────┘ └──────┬────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──────┐ ┌───▼───────┐ ┌──▼────────┐
│ Browser MCP  │ │ Email MCP │ │ Telegram  │
│ Connector    │ │ Connector │ │ Connector │
└──────────────┘ └───────────┘ └───────────┘
```

---

## 5.2. Рекомендуемый стек

Для MVP рекомендуется следующий стек:

### Backend

**Вариант A — Python-first:**

- Python 3.12+
    
- FastAPI
    
- SQLAlchemy 2.x
    
- Alembic
    
- PostgreSQL
    
- Pydantic v2
    
- Celery/RQ/Arq для фоновых задач
    
- Redis как брокер задач
    

### WebUI

- React + TypeScript
    
- Vite или Next.js
    
- TanStack Query
    
- React Router или Next.js routing
    
- UI-kit: shadcn/ui, Ant Design или Mantine
    

### Agent Worker

- Python worker-процесс
    
- LLM provider abstraction
    
- MCP client layer
    
- Structured output validation через Pydantic schemas
    
- Retry policy
    
- Tool execution audit log
    

### Модель

- На уровне MVP модель должна быть конфигурируемой.
    
- По умолчанию можно использовать Qwen-семейство, если оно стабильно работает с tool-use и structured output.
    
- Конкретная модель не должна быть жёстко захардкожена в бизнес-логике.
    

Рекомендуемый принцип:

```text
AgentRuntime
  ├── model_provider
  ├── tool_registry
  ├── instruction_policy
  ├── structured_output_validator
  └── persistence_adapter
```

---

## 5.3. Архитектурный принцип

Система должна быть построена так, чтобы WebUI, backend и агент были слабо связаны.

Запрещается реализовывать агента как прямую функцию UI-запроса, которая блокирует HTTP-response до завершения поиска. Поиск товаров и связь с поставщиком должны выполняться как фоновые задачи с сохранением статуса в БД.

Правильная модель:

```text
User action → API creates task → Worker processes task → DB status updated → UI polls/refetches status
```

---

# 6. Основные сущности

## 6.1. SearchRequest

Пользовательский запрос на поиск товаров.

Обязательные поля:

- `id`
    
- `query_text`
    
- `status`
    
- `created_at`
    
- `updated_at`
    

Дополнительные поля:

- `created_by`
    
- `error_message`
    
- `started_at`
    
- `completed_at`
    
- `agent_task_id`
    

Статусы:

```text
draft
queued
running
completed
failed
cancelled
```

---

## 6.2. ProductCard

Карточка найденного товара.

Обязательные поля:

- `id`
    
- `search_request_id`
    
- `title`
    
- `price`
    
- `product_url`
    
- `created_at`
    
- `updated_at`
    

Опциональные поля:

- `description`
    
- `images`
    
- `attributes`
    
- `currency`
    
- `supplier_name`
    
- `source_domain`
    
- `raw_agent_payload`
    
- `confidence_score`
    

---

## 6.3. SupplierContact

Контакт поставщика.

Обязательные поля:

- `id`
    
- `product_id`
    
- `contact_type`
    
- `contact_value`
    
- `created_at`
    

Поддерживаемые типы:

```text
email
telegram
```

MVP должен проектироваться так, чтобы в будущем можно было добавить:

```text
phone
whatsapp
wechat
website_form
```

Но в MVP реализуются только `email` и `telegram`.

---

## 6.4. ContactAttempt

Попытка связи с поставщиком.

Обязательные поля:

- `id`
    
- `product_id`
    
- `supplier_contact_id`
    
- `status`
    
- `channel`
    
- `message_text`
    
- `created_at`
    
- `updated_at`
    

Дополнительные поля:

- `sent_at`
    
- `completed_at`
    
- `external_message_id`
    
- `response_text`
    
- `summary`
    
- `error_message`
    
- `agent_task_id`
    

Статусы:

```text
queued
running
sent
responded
failed
cancelled
```

---

## 6.5. AgentTask

Техническая сущность для отслеживания агентских задач.

Поля:

- `id`
    
- `task_type`
    
- `status`
    
- `input_payload`
    
- `output_payload`
    
- `error_message`
    
- `created_at`
    
- `started_at`
    
- `completed_at`
    

Типы задач:

```text
product_search
supplier_contact
```

---

# 7. Модель данных PostgreSQL

## 7.1. Таблица `search_requests`

```sql
CREATE TABLE search_requests (
    id UUID PRIMARY KEY,
    query_text TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_by UUID NULL,
    error_message TEXT NULL,
    agent_task_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL
);
```

---

## 7.2. Таблица `products`

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY,
    search_request_id UUID NOT NULL REFERENCES search_requests(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NULL,
    price NUMERIC(18, 2) NULL,
    currency VARCHAR(16) NULL,
    product_url TEXT NOT NULL,
    source_domain TEXT NULL,
    supplier_name TEXT NULL,
    images JSONB NOT NULL DEFAULT '[]'::jsonb,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_agent_payload JSONB NULL,
    confidence_score NUMERIC(5, 4) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Примечание: в исходном описании цена указана как обязательное поле. На практике агент может найти товар без цены. Для MVP есть два варианта:

- строгий: не сохранять карточки без цены;
    
- практичный: сохранять `price = NULL`, но помечать карточку как неполную.
    

Для профессионального MVP рекомендую практичный вариант: `price` технически nullable, но UI должен явно показывать «Цена не найдена». Иначе агент будет отбрасывать потенциально ценные поставки.

---

## 7.3. Таблица `supplier_contacts`

```sql
CREATE TABLE supplier_contacts (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    contact_type VARCHAR(32) NOT NULL,
    contact_value TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT supplier_contacts_type_check
        CHECK (contact_type IN ('email', 'telegram'))
);
```

---

## 7.4. Таблица `contact_attempts`

```sql
CREATE TABLE contact_attempts (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    supplier_contact_id UUID NOT NULL REFERENCES supplier_contacts(id),
    agent_task_id UUID NULL,
    channel VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    message_text TEXT NOT NULL,
    external_message_id TEXT NULL,
    response_text TEXT NULL,
    summary TEXT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,

    CONSTRAINT contact_attempts_channel_check
        CHECK (channel IN ('email', 'telegram'))
);
```

---

## 7.5. Таблица `agent_tasks`

```sql
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY,
    task_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,

    CONSTRAINT agent_tasks_type_check
        CHECK (task_type IN ('product_search', 'supplier_contact'))
);
```

---

## 7.6. Индексы

```sql
CREATE INDEX idx_products_search_request_id
    ON products(search_request_id);

CREATE INDEX idx_supplier_contacts_product_id
    ON supplier_contacts(product_id);

CREATE INDEX idx_contact_attempts_product_id
    ON contact_attempts(product_id);

CREATE INDEX idx_agent_tasks_status
    ON agent_tasks(status);

CREATE INDEX idx_search_requests_status
    ON search_requests(status);
```

---

# 8. Backend API

## 8.1. Создание поискового запроса

```http
POST /api/search-requests
```

Request:

```json
{
  "queryText": "Комплектующие для БПЛА"
}
```

Response:

```json
{
  "id": "uuid",
  "queryText": "Комплектующие для БПЛА",
  "status": "queued",
  "createdAt": "2026-04-28T10:00:00Z"
}
```

Поведение:

- API валидирует непустой текст запроса.
    
- Создаёт `search_requests`.
    
- Создаёт `agent_tasks` с типом `product_search`.
    
- Ставит задачу в очередь.
    
- Возвращает пользователю созданный запрос.
    

---

## 8.2. Список запросов

```http
GET /api/search-requests
```

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "queryText": "Комплектующие для БПЛА",
      "status": "completed",
      "productsCount": 12,
      "createdAt": "2026-04-28T10:00:00Z",
      "completedAt": "2026-04-28T10:05:00Z"
    }
  ]
}
```

---

## 8.3. Детали запроса

```http
GET /api/search-requests/{id}
```

Response:

```json
{
  "id": "uuid",
  "queryText": "Комплектующие для БПЛА",
  "status": "completed",
  "errorMessage": null,
  "productsCount": 12,
  "createdAt": "2026-04-28T10:00:00Z",
  "startedAt": "2026-04-28T10:01:00Z",
  "completedAt": "2026-04-28T10:05:00Z"
}
```

---

## 8.4. Каталог товаров по запросу

```http
GET /api/search-requests/{id}/products
```

Query params:

```text
page
pageSize
```

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Flight Controller for UAV",
      "price": 120.00,
      "currency": "USD",
      "productUrl": "https://example.com/product",
      "supplierName": "Example Supplier",
      "imageUrl": "https://example.com/image.jpg",
      "contactsCount": 1
    }
  ],
  "page": 1,
  "pageSize": 20,
  "total": 12
}
```

---

## 8.5. Детали товара

```http
GET /api/products/{id}
```

Response:

```json
{
  "id": "uuid",
  "searchRequestId": "uuid",
  "title": "Flight Controller for UAV",
  "description": "Short product description",
  "price": 120.00,
  "currency": "USD",
  "productUrl": "https://example.com/product",
  "sourceDomain": "example.com",
  "supplierName": "Example Supplier",
  "images": [
    "https://example.com/image.jpg"
  ],
  "attributes": {
    "model": "FC-100",
    "voltage": "5V"
  },
  "contacts": [
    {
      "id": "uuid",
      "type": "email",
      "value": "sales@example.com",
      "isPrimary": true
    }
  ],
  "contactAttempts": [
    {
      "id": "uuid",
      "channel": "email",
      "status": "sent",
      "messageText": "Здравствуйте...",
      "summary": null,
      "createdAt": "2026-04-28T11:00:00Z"
    }
  ]
}
```

---

## 8.6. Запрос связи с поставщиком

```http
POST /api/products/{id}/contact-supplier
```

Request:

```json
{
  "contactId": "uuid",
  "messageOverride": null
}
```

`messageOverride` в MVP опционален. Если не передан, агент использует стандартную инструкцию и шаблон.

Response:

```json
{
  "contactAttemptId": "uuid",
  "status": "queued"
}
```

Поведение:

- API проверяет существование товара.
    
- API проверяет существование контакта.
    
- API проверяет, что тип контакта поддерживается.
    
- Создаёт `contact_attempts`.
    
- Создаёт `agent_tasks` типа `supplier_contact`.
    
- Ставит задачу в очередь.
    
- Возвращает статус.
    

---

# 9. WebUI

## 9.1. Страница «Список запросов»

Route:

```text
/search-requests
```

Функции:

- отображение всех запросов;
    
- статус запроса;
    
- количество найденных товаров;
    
- дата создания;
    
- кнопка создания нового запроса;
    
- переход в каталог товаров по запросу.
    

Колонки:

```text
Запрос | Статус | Найдено товаров | Создан | Завершён | Действия
```

Статусы должны отображаться человекочитаемо:

```text
queued     → В очереди
running    → Выполняется
completed  → Завершён
failed     → Ошибка
cancelled  → Отменён
```

---

## 9.2. Создание запроса

UI должен содержать:

- textarea/input для текста запроса;
    
- кнопку «Запустить поиск»;
    
- базовую валидацию:
    
    - запрос не пустой;
        
    - длина не меньше 3 символов;
        
    - длина не больше 1000 символов.
        

После создания запроса пользователь должен быть перенаправлен либо:

- на страницу списка запросов, либо
    
- на страницу конкретного запроса.
    

Рекомендуется перенаправление на страницу конкретного запроса.

---

## 9.3. Страница «Каталог товаров по запросу»

Route:

```text
/search-requests/:id/products
```

Функции:

- отображение текста исходного запроса;
    
- отображение статуса обработки;
    
- список карточек товаров;
    
- переход в карточку товара;
    
- отображение пустого состояния, если товаров нет;
    
- отображение ошибки, если поиск завершился с ошибкой.
    

Карточка товара должна показывать:

- изображение, если есть;
    
- название;
    
- цену;
    
- валюту;
    
- поставщика;
    
- домен источника;
    
- наличие контакта;
    
- кнопку «Открыть».
    

---

## 9.4. Страница товара

Route:

```text
/products/:id
```

Функции:

- просмотр полной информации о товаре;
    
- просмотр ссылки на источник;
    
- просмотр изображений;
    
- просмотр характеристик;
    
- просмотр контактов поставщика;
    
- выбор контакта, если их несколько;
    
- кнопка «Связаться»;
    
- просмотр истории попыток связи.
    

Кнопка «Связаться» должна быть недоступна, если:

- у товара нет контактов;
    
- уже есть активная попытка связи со статусом `queued` или `running`;
    
- контакт имеет неподдерживаемый тип.
    

---

# 10. AI-агент

## 10.1. Общие требования

Агент должен быть реализован как отдельный worker или сервис, не как часть UI.

Агент должен:

- принимать строго типизированные задачи;
    
- использовать модель через абстракцию `ModelProvider`;
    
- использовать инструменты через `ToolRegistry`;
    
- валидировать все структурированные ответы;
    
- писать результаты в БД через application service;
    
- логировать ошибки;
    
- не сохранять непроверенный LLM-output без валидации;
    
- быть идемпотентным на уровне задачи, насколько возможно.
    

---

## 10.2. Агентская задача `product_search`

Input:

```json
{
  "searchRequestId": "uuid",
  "queryText": "Комплектующие для БПЛА"
}
```

Output:

```json
{
  "productsCreated": 12,
  "productsSkipped": 3,
  "errors": []
}
```

Алгоритм:

1. Получить задачу.
    
2. Перевести `agent_tasks.status` в `running`.
    
3. Перевести `search_requests.status` в `running`.
    
4. Сформировать инструкцию для агента.
    
5. Вызвать browser MCP connector.
    
6. Выполнить исследование.
    
7. Получить структурированный список товаров.
    
8. Провалидировать каждый товар.
    
9. Сохранить валидные товары и контакты.
    
10. Перевести запрос в `completed`, если не было критической ошибки.
    
11. При ошибке перевести запрос в `failed` и сохранить `error_message`.
    

---

## 10.3. Structured output для поиска товаров

Агент должен возвращать данные строго в схеме:

```json
{
  "products": [
    {
      "title": "string",
      "price": 100.0,
      "currency": "USD",
      "productUrl": "https://example.com/product",
      "supplierName": "string",
      "contacts": [
        {
          "type": "email",
          "value": "sales@example.com"
        }
      ],
      "images": [
        "https://example.com/image.jpg"
      ],
      "description": "string",
      "attributes": {
        "key": "value"
      },
      "confidenceScore": 0.85
    }
  ]
}
```

Правила валидации:

- `title` обязателен;
    
- `productUrl` обязателен и должен быть URL;
    
- должен быть хотя бы один контакт поставщика;
    
- `contact.type` должен быть `email` или `telegram`;
    
- email должен проходить базовую email-валидацию;
    
- Telegram должен быть username, link или channel handle в поддерживаемом формате;
    
- `price` может быть `null`, если цена не найдена;
    
- `images` должны быть массивом URL;
    
- `attributes` должен быть JSON object.
    

---

## 10.4. Агентская задача `supplier_contact`

Input:

```json
{
  "productId": "uuid",
  "supplierContactId": "uuid",
  "contactAttemptId": "uuid",
  "messageOverride": null
}
```

Output:

```json
{
  "status": "sent",
  "externalMessageId": "provider-message-id",
  "summary": "Message sent successfully"
}
```

Алгоритм:

1. Получить задачу.
    
2. Загрузить товар и контакт из БД.
    
3. Проверить тип контакта.
    
4. Сформировать сообщение поставщику.
    
5. Выбрать коннектор:
    
    - `email` → email connector;
        
    - `telegram` → Telegram connector.
        
6. Отправить сообщение.
    
7. Сохранить текст сообщения.
    
8. Сохранить `external_message_id`, если доступен.
    
9. Обновить статус `contact_attempts`.
    
10. При ошибке сохранить ошибку и статус `failed`.
    

---

## 10.5. Базовая инструкция агента для связи с поставщиком

```text
Ты представляешь пользователя, который заинтересован в покупке или уточнении условий поставки товара.

Твоя задача:
1. Вежливо обратиться к поставщику.
2. Указать название товара.
3. Уточнить актуальность цены.
4. Уточнить наличие товара.
5. Уточнить минимальную партию.
6. Уточнить сроки поставки.
7. Уточнить возможные способы оплаты и доставки.
8. Не давать юридически или финансово обязывающих обещаний.
9. Не подтверждать заказ.
10. Не передавать конфиденциальные данные.
11. Не обсуждать обход санкций, нелегальные поставки или запрещённые товары.
12. Сохранить нейтральный деловой тон.
```

Шаблон сообщения:

```text
Здравствуйте.

Интересует товар: {product_title}

Подскажите, пожалуйста:
1. Актуальна ли цена, указанная на странице товара?
2. Есть ли товар в наличии?
3. Какая минимальная партия для заказа?
4. Какие сроки поставки?
5. Какие доступны способы оплаты и доставки?
6. Можете ли вы прислать дополнительные характеристики или спецификацию?

Ссылка на товар:
{product_url}

Спасибо.
```

---

# 11. Безопасность и ограничения агента

Агент не должен:

- оформлять заказ;
    
- подтверждать покупку;
    
- договариваться о поставке от имени пользователя;
    
- отправлять платежные данные;
    
- передавать персональные данные без явного разрешения;
    
- вести переговоры о запрещённых товарах;
    
- обходить ограничения сайтов;
    
- использовать украденные аккаунты или неавторизованные сессии;
    
- скрывать, что сообщение является коммерческим запросом.
    

Если поставщик просит перейти к сделке, агент должен только зафиксировать ответ и показать пользователю.

---

# 12. OpenSpec Delta Specs

## 12.1. Search Requests Spec

Файл:

```text
openspec/changes/add-product-sourcing-mvp/specs/search-requests/spec.md
```

```md
## ADDED Requirements

### Requirement: Create Search Request

The system SHALL allow a user to create a product search request using free-text input.

#### Scenario: User creates a valid search request

- GIVEN the user is on the search request creation page
- WHEN the user submits a non-empty query text
- THEN the system SHALL create a search request
- AND the search request status SHALL be `queued`
- AND the system SHALL create a corresponding agent task of type `product_search`

#### Scenario: User submits an empty search request

- GIVEN the user is on the search request creation page
- WHEN the user submits an empty query text
- THEN the system SHALL reject the request
- AND the system SHALL display a validation error

### Requirement: List Search Requests

The system SHALL provide a page and API endpoint for listing search requests.

#### Scenario: User opens search requests list

- GIVEN at least one search request exists
- WHEN the user opens the search requests page
- THEN the system SHALL display query text, status, creation date, and product count for each request

### Requirement: Track Search Request Status

The system SHALL persist and expose the processing status of each search request.

#### Scenario: Agent starts processing

- GIVEN a search request has status `queued`
- WHEN the agent starts processing the request
- THEN the system SHALL update the status to `running`
- AND the system SHALL set `started_at`

#### Scenario: Agent completes processing

- GIVEN a search request has status `running`
- WHEN the agent successfully saves search results
- THEN the system SHALL update the status to `completed`
- AND the system SHALL set `completed_at`

#### Scenario: Agent fails processing

- GIVEN a search request has status `running`
- WHEN the agent encounters a critical error
- THEN the system SHALL update the status to `failed`
- AND the system SHALL persist a user-readable error message
```

---

## 12.2. Product Catalog Spec

Файл:

```text
openspec/changes/add-product-sourcing-mvp/specs/product-catalog/spec.md
```

```md
## ADDED Requirements

### Requirement: Persist Product Cards

The system SHALL persist product cards discovered by the agent.

#### Scenario: Agent saves valid product card

- GIVEN the agent has discovered a product with title, URL, and at least one supplier contact
- WHEN the product passes validation
- THEN the system SHALL persist the product card
- AND the system SHALL associate it with the originating search request

#### Scenario: Agent discovers invalid product card

- GIVEN the agent has discovered a product without title or URL
- WHEN the product is validated
- THEN the system SHALL skip the product
- AND the system SHALL record the skip reason in the agent task output

### Requirement: Store Supplier Contacts

The system SHALL store supplier contacts associated with product cards.

#### Scenario: Product has email contact

- GIVEN a discovered product includes an email contact
- WHEN the product card is persisted
- THEN the system SHALL persist the supplier contact with type `email`

#### Scenario: Product has Telegram contact

- GIVEN a discovered product includes a Telegram contact
- WHEN the product card is persisted
- THEN the system SHALL persist the supplier contact with type `telegram`

### Requirement: Browse Products By Search Request

The system SHALL allow users to browse products associated with a search request.

#### Scenario: User opens product catalog for a request

- GIVEN a completed search request has products
- WHEN the user opens the product catalog page
- THEN the system SHALL display product cards linked to that search request

### Requirement: View Product Details

The system SHALL allow users to view full product details.

#### Scenario: User opens product details

- GIVEN a product exists
- WHEN the user opens the product details page
- THEN the system SHALL display title, price, URL, supplier name, contacts, description, images, and attributes when available
```

---

## 12.3. Supplier Contact Spec

Файл:

```text
openspec/changes/add-product-sourcing-mvp/specs/supplier-contact/spec.md
```

```md
## ADDED Requirements

### Requirement: Request Supplier Contact

The system SHALL allow a user to request that the agent contacts a supplier for a product.

#### Scenario: User requests supplier contact

- GIVEN a product has at least one supported supplier contact
- WHEN the user clicks "Contact supplier"
- THEN the system SHALL create a contact attempt
- AND the contact attempt status SHALL be `queued`
- AND the system SHALL create an agent task of type `supplier_contact`

#### Scenario: Product has no supplier contacts

- GIVEN a product has no supplier contacts
- WHEN the user opens the product details page
- THEN the system SHALL disable the "Contact supplier" action
- AND the system SHALL explain that no supplier contact is available

### Requirement: Select Connector By Contact Type

The system SHALL select the communication connector based on supplier contact type.

#### Scenario: Contact type is email

- GIVEN a supplier contact has type `email`
- WHEN the agent processes the supplier contact task
- THEN the system SHALL use the email connector

#### Scenario: Contact type is Telegram

- GIVEN a supplier contact has type `telegram`
- WHEN the agent processes the supplier contact task
- THEN the system SHALL use the Telegram connector

### Requirement: Persist Contact Attempt Result

The system SHALL persist the result of each supplier contact attempt.

#### Scenario: Message sent successfully

- GIVEN the agent successfully sends a supplier message
- WHEN the connector returns success
- THEN the system SHALL update the contact attempt status to `sent`
- AND the system SHALL persist the sent message text
- AND the system SHALL persist external message identifier when available

#### Scenario: Message sending fails

- GIVEN the agent attempts to contact a supplier
- WHEN the connector returns an error
- THEN the system SHALL update the contact attempt status to `failed`
- AND the system SHALL persist a user-readable error message
```

---

## 12.4. Agent Orchestration Spec

Файл:

```text
openspec/changes/add-product-sourcing-mvp/specs/agent-orchestration/spec.md
```

```md
## ADDED Requirements

### Requirement: Process Product Search Task

The system SHALL process product search tasks asynchronously.

#### Scenario: Worker receives product search task

- GIVEN an agent task of type `product_search` exists with status `queued`
- WHEN the worker starts the task
- THEN the system SHALL update the task status to `running`
- AND the worker SHALL execute browser research through the browser MCP connector

### Requirement: Validate Agent Output

The system SHALL validate structured agent output before persisting it.

#### Scenario: Agent returns valid structured output

- GIVEN the agent returns product data matching the expected schema
- WHEN the backend validates the output
- THEN the system SHALL persist valid product cards

#### Scenario: Agent returns malformed output

- GIVEN the agent returns malformed or incomplete product data
- WHEN the backend validates the output
- THEN the system SHALL reject invalid records
- AND the system SHALL store validation errors in the agent task output

### Requirement: Process Supplier Contact Task

The system SHALL process supplier contact tasks asynchronously.

#### Scenario: Worker receives supplier contact task

- GIVEN an agent task of type `supplier_contact` exists with status `queued`
- WHEN the worker starts the task
- THEN the system SHALL load product and supplier contact data
- AND the worker SHALL send a message using the connector matching the contact type

### Requirement: Store Agent Task Lifecycle

The system SHALL persist lifecycle information for every agent task.

#### Scenario: Task completes

- GIVEN an agent task is running
- WHEN the task completes successfully
- THEN the system SHALL update the task status to `completed`
- AND the system SHALL persist the output payload

#### Scenario: Task fails

- GIVEN an agent task is running
- WHEN the task fails
- THEN the system SHALL update the task status to `failed`
- AND the system SHALL persist the error message
```

---

## 12.5. WebUI Spec

Файл:

```text
openspec/changes/add-product-sourcing-mvp/specs/webui/spec.md
```

```md
## ADDED Requirements

### Requirement: Search Requests Page

The WebUI SHALL provide a search requests page.

#### Scenario: User views search requests

- GIVEN search requests exist
- WHEN the user opens the search requests page
- THEN the WebUI SHALL display a table of requests
- AND each row SHALL include query text, status, product count, and creation date

### Requirement: Product Catalog Page

The WebUI SHALL provide a product catalog page for each search request.

#### Scenario: User views products for request

- GIVEN a search request has associated products
- WHEN the user opens the request catalog page
- THEN the WebUI SHALL display product cards for that request

### Requirement: Product Details Page

The WebUI SHALL provide a product details page.

#### Scenario: User views product details

- GIVEN a product exists
- WHEN the user opens the product details page
- THEN the WebUI SHALL display product data, supplier contacts, and contact attempts

### Requirement: Contact Supplier Action

The WebUI SHALL provide a contact supplier action on the product details page.

#### Scenario: Contact is available

- GIVEN a product has a supported supplier contact
- WHEN the user views the product details page
- THEN the WebUI SHALL enable the "Contact supplier" action

#### Scenario: Contact task is active

- GIVEN a product has a contact attempt with status `queued` or `running`
- WHEN the user views the product details page
- THEN the WebUI SHALL disable creating another contact attempt
```

---

## 12.6. Persistence Spec

Файл:

```text
openspec/changes/add-product-sourcing-mvp/specs/persistence/spec.md
```

```md
## ADDED Requirements

### Requirement: Persist Search Requests

The system SHALL persist search requests in a relational database.

#### Scenario: Search request is created

- GIVEN a user submits a valid query
- WHEN the backend accepts the request
- THEN the system SHALL store the request with status `queued`

### Requirement: Persist Products

The system SHALL persist product cards in a relational database.

#### Scenario: Product card is created

- GIVEN validated product data exists
- WHEN the backend stores the product
- THEN the system SHALL associate it with a search request

### Requirement: Persist Supplier Contacts

The system SHALL persist supplier contacts in a relational database.

#### Scenario: Supplier contact is created

- GIVEN a product has a supported supplier contact
- WHEN the product is stored
- THEN the system SHALL store the contact with the product

### Requirement: Persist Contact Attempts

The system SHALL persist supplier contact attempts in a relational database.

#### Scenario: Contact attempt is created

- GIVEN the user requests supplier contact
- WHEN the backend creates a contact attempt
- THEN the system SHALL persist the attempt with status `queued`

### Requirement: Persist Agent Tasks

The system SHALL persist agent task lifecycle data.

#### Scenario: Agent task is created

- GIVEN the system needs asynchronous agent processing
- WHEN the backend creates an agent task
- THEN the system SHALL persist task type, status, input payload, and timestamps
```

---

# 13. Implementation Tasks

Файл:

```text
openspec/changes/add-product-sourcing-mvp/tasks.md
```

```md
# Tasks: Product Sourcing MVP

## 1. Project Setup

- [ ] 1.1 Initialize backend project structure.
- [ ] 1.2 Initialize frontend project structure.
- [ ] 1.3 Configure environment variables.
- [ ] 1.4 Configure PostgreSQL connection.
- [ ] 1.5 Configure Redis or selected background job broker.
- [ ] 1.6 Add base Docker Compose for local development.

## 2. Database

- [ ] 2.1 Create Alembic migration for search_requests.
- [ ] 2.2 Create Alembic migration for products.
- [ ] 2.3 Create Alembic migration for supplier_contacts.
- [ ] 2.4 Create Alembic migration for contact_attempts.
- [ ] 2.5 Create Alembic migration for agent_tasks.
- [ ] 2.6 Add indexes for request, product, contact, and task lookup.
- [ ] 2.7 Add database-level checks for supported contact/channel types.

## 3. Backend Domain Layer

- [ ] 3.1 Implement SearchRequest entity/model.
- [ ] 3.2 Implement Product entity/model.
- [ ] 3.3 Implement SupplierContact entity/model.
- [ ] 3.4 Implement ContactAttempt entity/model.
- [ ] 3.5 Implement AgentTask entity/model.
- [ ] 3.6 Implement status enums.
- [ ] 3.7 Implement repository layer.

## 4. Backend API

- [ ] 4.1 Implement POST /api/search-requests.
- [ ] 4.2 Implement GET /api/search-requests.
- [ ] 4.3 Implement GET /api/search-requests/{id}.
- [ ] 4.4 Implement GET /api/search-requests/{id}/products.
- [ ] 4.5 Implement GET /api/products/{id}.
- [ ] 4.6 Implement POST /api/products/{id}/contact-supplier.
- [ ] 4.7 Add request/response DTOs.
- [ ] 4.8 Add validation and error responses.

## 5. Agent Runtime

- [ ] 5.1 Implement AgentRuntime abstraction.
- [ ] 5.2 Implement ModelProvider abstraction.
- [ ] 5.3 Implement ToolRegistry abstraction.
- [ ] 5.4 Implement BrowserMcpConnector interface.
- [ ] 5.5 Implement EmailConnector interface.
- [ ] 5.6 Implement TelegramConnector interface.
- [ ] 5.7 Implement structured output schemas.
- [ ] 5.8 Implement validation for agent product output.

## 6. Product Search Worker

- [ ] 6.1 Implement product_search task handler.
- [ ] 6.2 Load search request by ID.
- [ ] 6.3 Update search request and agent task statuses.
- [ ] 6.4 Execute browser research through MCP connector.
- [ ] 6.5 Parse and validate product output.
- [ ] 6.6 Persist products and contacts.
- [ ] 6.7 Store task output summary.
- [ ] 6.8 Handle failures and persist error messages.

## 7. Supplier Contact Worker

- [ ] 7.1 Implement supplier_contact task handler.
- [ ] 7.2 Load product, supplier contact, and contact attempt.
- [ ] 7.3 Generate supplier message from instruction template.
- [ ] 7.4 Select connector by contact type.
- [ ] 7.5 Send message through selected connector.
- [ ] 7.6 Persist sent message and external message ID.
- [ ] 7.7 Update contact attempt status.
- [ ] 7.8 Handle failures and persist error messages.

## 8. WebUI

- [ ] 8.1 Implement application layout.
- [ ] 8.2 Implement search requests list page.
- [ ] 8.3 Implement create search request form.
- [ ] 8.4 Implement search request detail/catalog page.
- [ ] 8.5 Implement product card component.
- [ ] 8.6 Implement product details page.
- [ ] 8.7 Implement supplier contacts section.
- [ ] 8.8 Implement contact attempts section.
- [ ] 8.9 Implement "Contact supplier" action.
- [ ] 8.10 Implement loading, empty, and error states.

## 9. Testing

- [ ] 9.1 Add backend unit tests for validation.
- [ ] 9.2 Add backend API tests.
- [ ] 9.3 Add repository tests.
- [ ] 9.4 Add worker tests with mocked connectors.
- [ ] 9.5 Add frontend component tests for critical pages.
- [ ] 9.6 Add smoke test for full search request flow.
- [ ] 9.7 Add smoke test for supplier contact flow.

## 10. Observability and Reliability

- [ ] 10.1 Add structured logging.
- [ ] 10.2 Add correlation IDs for agent tasks.
- [ ] 10.3 Add retry policy for connector failures.
- [ ] 10.4 Add timeout policy for agent tasks.
- [ ] 10.5 Add user-readable error messages.
- [ ] 10.6 Add developer-readable error details to logs only.

## 11. Documentation

- [ ] 11.1 Document environment variables.
- [ ] 11.2 Document local development startup.
- [ ] 11.3 Document supported connector types.
- [ ] 11.4 Document MVP limitations.
- [ ] 11.5 Document manual QA checklist.
```

---

# 14. Design Document

Файл:

```text
openspec/changes/add-product-sourcing-mvp/design.md
```

```md
# Design: Product Sourcing MVP

## Architecture Decision

The system will use a decoupled architecture:

- WebUI communicates only with Backend API.
- Backend API owns validation, persistence, and task creation.
- Agent Worker processes asynchronous tasks.
- Agent Worker uses MCP connectors through explicit interfaces.
- Database is the source of truth for statuses and results.

## Why Async Workers

Product research and supplier communication are long-running operations. They must not block HTTP requests. The API creates durable task records and enqueues work. The UI observes progress by reading persisted state.

## Data Ownership

The backend owns:

- search request lifecycle;
- product persistence;
- supplier contact persistence;
- contact attempt lifecycle;
- agent task lifecycle.

The agent owns:

- research execution;
- extraction attempt;
- message generation;
- connector invocation.

The agent does not own database schema or UI state.

## Model Provider

The LLM must be configurable. Qwen-family models may be used, but business logic must depend on a `ModelProvider` interface rather than a concrete model name.

## Tool Connectors

MVP requires:

- Browser MCP connector for research.
- Email connector for email contact.
- Telegram connector for Telegram contact.

Each connector must expose a deterministic interface and return structured success/error results.

## Validation Boundary

All LLM output must be treated as untrusted until validated against strict schemas.

## Error Handling

Errors must be persisted in two forms:

- user-readable error message in database;
- developer-readable structured log entry.

## Duplicate Handling

MVP will use simple duplicate prevention per search request:

- same `product_url` within one search request SHOULD NOT be stored twice.

Advanced cross-request deduplication is out of MVP.

## Contact Attempt Policy

Only one active contact attempt per product is allowed at a time.

Active statuses:

- queued
- running

## Security

The agent must not commit to purchases, disclose secrets, or perform unauthorized actions. Supplier communication is limited to inquiry messages.
```

---

# 15. Статусы и переходы

## 15.1. SearchRequest

```text
queued → running → completed
queued → running → failed
queued → cancelled
running → cancelled
```

Запрещённые переходы:

```text
completed → running
failed → running
completed → failed
```

Для повторного поиска в будущем нужно создавать новый SearchRequest или отдельную функцию retry. В MVP retry можно не реализовывать.

---

## 15.2. AgentTask

```text
queued → running → completed
queued → running → failed
queued → cancelled
running → cancelled
```

---

## 15.3. ContactAttempt

```text
queued → running → sent
queued → running → responded
queued → running → failed
queued → cancelled
running → cancelled
```

В MVP статус `responded` можно зарезервировать для будущей обработки входящих ответов. Если входящие ответы пока не реализуются, достаточно `sent` и `failed`.

---

# 16. Требования к валидации

## 16.1. SearchRequest

- `queryText` обязателен.
    
- Минимальная длина: 3 символа.
    
- Максимальная длина: 1000 символов.
    
- Запрос должен сохраняться в исходном виде, но UI может trim-ить пробелы по краям.
    

---

## 16.2. Product

- `title` обязателен.
    
- `productUrl` обязателен.
    
- `productUrl` должен быть валидным URL.
    
- `price` может быть `null`.
    
- `currency` может быть `null`.
    
- `images` — массив URL.
    
- `attributes` — JSON object.
    
- Должен быть минимум один supplier contact, иначе карточка считается неполной. Для MVP рекомендую сохранять такую карточку только если явно включён флаг `ALLOW_PRODUCTS_WITHOUT_CONTACTS=false/true`. По умолчанию — не сохранять.
    

---

## 16.3. SupplierContact

- `contactType` обязателен.
    
- Поддерживаемые значения MVP:
    
    - `email`;
        
    - `telegram`.
        
- `contactValue` обязателен.
    
- Email должен проходить базовую проверку формата.
    
- Telegram должен быть:
    
    - `@username`;
        
    - или `https://t.me/username`;
        
    - или иной заранее разрешённый формат.
        

---

# 17. Нефункциональные требования

## 17.1. Надёжность

- Потеря worker-процесса не должна удалять созданные запросы.
    
- Все задачи должны иметь persisted status.
    
- Ошибки агента должны сохраняться в БД.
    
- Некорректный output агента не должен ломать весь поиск, если часть товаров валидна.
    

---

## 17.2. Производительность MVP

Ориентиры:

- список запросов: до 1 секунды при 1000 запросах;
    
- каталог товаров: пагинация, не более 20–50 товаров на страницу;
    
- создание запроса: до 500 мс без учёта фоновой обработки;
    
- запуск связи с поставщиком: до 500 мс без учёта фоновой отправки.
    

---

## 17.3. Безопасность

- Секреты коннекторов должны храниться в env/secrets manager.
    
- Секреты не должны попадать в логи.
    
- Все external URLs должны отображаться как внешние ссылки.
    
- Backend должен валидировать ID и права доступа.
    
- Agent output должен проходить schema validation.
    
- UI не должен рендерить HTML из agent output без sanitization.
    

---

## 17.4. Наблюдаемость

Логи должны включать:

- `agent_task_id`;
    
- `search_request_id`, если применимо;
    
- `product_id`, если применимо;
    
- тип задачи;
    
- статус;
    
- ошибку;
    
- длительность выполнения.
    

---

# 18. Acceptance Criteria

MVP считается готовым, если выполнены следующие критерии:

1. Пользователь может создать поисковый запрос.
    
2. Запрос появляется в списке со статусом `queued`.
    
3. Worker забирает задачу и переводит запрос в `running`.
    
4. Агент вызывает browser MCP connector.
    
5. Валидные карточки товаров сохраняются в БД.
    
6. После завершения поиска статус становится `completed`.
    
7. Пользователь видит каталог товаров по запросу.
    
8. Пользователь открывает карточку товара.
    
9. Пользователь видит контакты поставщика.
    
10. Пользователь нажимает «Связаться».
    
11. Создаётся contact attempt.
    
12. Worker выбирает email или Telegram connector по типу контакта.
    
13. Сообщение отправляется или ошибка сохраняется.
    
14. Результат контакта отображается на странице товара.
    
15. Ошибки не теряются и видны пользователю в понятной форме.
    
16. Все agent outputs проходят validation перед сохранением.
    
17. Backend API покрыт базовыми тестами.
    
18. Worker logic покрыт тестами с mocked connectors.
    
19. UI имеет loading, empty и error states для основных страниц.
    

---

# 19. Рекомендуемый порядок реализации

Лучший порядок, чтобы не получить хаотичный MVP:

1. БД и миграции.
    
2. Backend domain models.
    
3. API без агента, с mock-данными.
    
4. WebUI на реальных API.
    
5. Очередь задач и AgentTask lifecycle.
    
6. Product search worker с mock MCP connector.
    
7. Реальный browser MCP connector.
    
8. Supplier contact worker с mock email/telegram.
    
9. Реальные email/telegram connectors.
    
10. Обработка ошибок.
    
11. Smoke tests.
    
12. OpenSpec validation.
    
13. MVP demo flow.
    

---

# 20. Минимальный MVP Demo Flow

Для демонстрации MVP должен стабильно работать следующий сценарий:

1. Пользователь открывает `/search-requests`.
    
2. Нажимает «Новый запрос».
    
3. Вводит:
    

```text
ПК, вычислительные компьютеры, ноутбуки
```

4. Система создаёт запрос со статусом `queued`.
    
5. Worker переводит запрос в `running`.
    
6. Агент выполняет browser research.
    
7. Сохраняются карточки товаров.
    
8. Запрос получает статус `completed`.
    
9. Пользователь открывает каталог.
    
10. Пользователь открывает один товар.
    
11. Видит цену, ссылку, описание и контакт.
    
12. Нажимает «Связаться».
    
13. Агент отправляет сообщение через email или Telegram.
    
14. На странице товара появляется история контакта со статусом `sent` или `failed`.
    

---

# 21. Ключевые инженерные замечания

Самое важное для качества MVP:

- **Не смешивать агента и backend API.** Агент должен быть worker-компонентом.
    
- **Не доверять LLM-output.** Только structured output + validation.
    
- **Сохранять статусы всего.** Без статусов UI станет непредсказуемым.
    
- **Не блокировать HTTP-запросы долгими агентскими операциями.**
    
- **Сразу заложить расширяемые contact types.**
    
- **Сразу заложить connector interfaces.**
    
- **Не делать CRM раньше времени.**
    
- **Не делать автономные переговоры в MVP.**
    
- **Не хардкодить конкретную модель.**
    
- **Не хранить только финальный результат — хранить lifecycle задач.**
    

---

# 22. Итоговая формулировка MVP

MVP — это не «агент, который сам всё закупает».  
MVP — это контролируемая система, где пользователь создаёт запрос, агент помогает найти и структурировать товары, пользователь проверяет карточки, а агент выполняет только первичный безопасный контакт с поставщиком и сохраняет результат.

Именно такая граница позволит быстро получить рабочий продукт, не превратив первый релиз в нестабильную смесь браузерной автоматизации, CRM, закупочного отдела и автономных переговоров.