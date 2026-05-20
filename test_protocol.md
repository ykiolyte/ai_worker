# Протокол end-to-end тестирования MVP-сервиса поиска товаров и связи с поставщиками через AI-агента

**Проект:** MVP-сервис поиска товаров и связи с поставщиками через AI-агента
**Версия протокола:** 1.0
**Тип тестирования:** End-to-End, production-like
**Цель:** проверить полный путь пользователя от создания поискового запроса в WebUI до сохранения найденных товаров в БД и отправки сообщения поставщику через реальный email или Telegram-коннектор.

---

# 1. Принципиальное правило E2E-тестирования

В рамках этого протокола запрещено использовать:

* mock-коннекторы;
* fake worker;
* ручную вставку товаров в БД вместо работы агента;
* ручную вставку contact attempts в БД;
* отключённую очередь задач;
* прямой вызов внутренних worker-функций в обход API;
* подмену LLM-output заранее подготовленным JSON;
* UI, работающий на статических данных;
* in-memory БД вместо PostgreSQL;
* псевдоотправку email или Telegram-сообщений.

Допускается использовать **контролируемый тестовый контур поставщика**, то есть реальный HTTP-сайт с тестовыми товарными страницами и реальными тестовыми контактами, принадлежащими команде проекта. Это не является заглушкой, потому что агент действительно открывает страницы через browser MCP, извлекает данные, backend действительно сохраняет их в PostgreSQL, worker действительно выполняет задачи, а email/Telegram-сообщения действительно отправляются в тестовые каналы.

Запрещено в ходе E2E отправлять сообщения реальным внешним поставщикам без отдельного письменного разрешения.

---

# 2. Проверяемый пользовательский путь

E2E-протокол должен целиком имитировать следующий путь пользователя:

1. Пользователь открывает WebUI.
2. Пользователь видит список поисковых запросов.
3. Пользователь создаёт новый поисковый запрос.
4. Backend создаёт `search_request`.
5. Backend создаёт `agent_task` типа `product_search`.
6. Worker забирает задачу из очереди.
7. Агент через browser MCP выполняет исследование.
8. Агент находит товарные карточки.
9. Система валидирует structured output агента.
10. Система сохраняет товары в `products`.
11. Система сохраняет контакты поставщиков в `supplier_contacts`.
12. Пользователь видит завершённый запрос.
13. Пользователь открывает каталог товаров по запросу.
14. Пользователь открывает карточку товара.
15. Пользователь видит контакты поставщика.
16. Пользователь нажимает «Связаться».
17. Backend создаёт `contact_attempt`.
18. Backend создаёт `agent_task` типа `supplier_contact`.
19. Worker забирает задачу.
20. Агент формирует деловое сообщение.
21. Агент выбирает email или Telegram-коннектор.
22. Система отправляет сообщение поставщику.
23. Система сохраняет результат коммуникации.
24. Пользователь видит историю контакта на странице товара.

---

# 3. Тестовый контур

## 3.1. Обязательные компоненты

Перед началом E2E должны быть запущены и доступны:

| Компонент                    | Требование                                                    |
| ---------------------------- | ------------------------------------------------------------- |
| WebUI                        | Реальное frontend-приложение                                  |
| Backend API                  | Реальный backend API                                          |
| PostgreSQL                   | Реальная БД с миграциями проекта                              |
| Redis / брокер очередей      | Реальный брокер задач                                         |
| Agent Worker                 | Реальный worker-процесс                                       |
| LLM provider                 | Реальная модель через `ModelProvider`                         |
| Browser MCP connector        | Реальный browser MCP-коннектор                                |
| Email connector              | Реальный email-коннектор                                      |
| Telegram connector           | Реальный Telegram-коннектор                                   |
| Тестовая витрина поставщика  | Реальный HTTP/HTTPS сайт с тестовыми товарами                 |
| Тестовый email поставщика    | Реальный mailbox, доступный тестировщику                      |
| Тестовый Telegram поставщика | Реальный Telegram bot/account/channel, доступный тестировщику |

---

## 3.2. Переменные тестового контура

Перед запуском теста заполнить таблицу:

| Переменная                    | Значение                    |
| ----------------------------- | --------------------------- |
| `WEBUI_BASE_URL`              | `https://...`               |
| `API_BASE_URL`                | `https://.../api`           |
| `TEST_SUPPLIER_SITE_URL`      | `https://...`               |
| `TEST_SUPPLIER_EMAIL`         | `supplier-e2e@example.test` |
| `TEST_SUPPLIER_TELEGRAM`      | `@supplier_e2e_test`        |
| `POSTGRES_HOST`               |                             |
| `POSTGRES_DB`                 |                             |
| `POSTGRES_USER`               |                             |
| `WORKER_SERVICE_NAME`         |                             |
| `BROWSER_MCP_SERVICE_NAME`    |                             |
| `EMAIL_CONNECTOR_PROVIDER`    |                             |
| `TELEGRAM_CONNECTOR_PROVIDER` |                             |
| `MODEL_PROVIDER`              |                             |
| `MODEL_NAME`                  |                             |

---

# 4. Тестовые данные поставщика

Тестовая витрина поставщика должна содержать реальные HTML-страницы, доступные browser MCP-коннектору.

## 4.1. Товар 1 — email-контакт

| Поле           | Значение                                                              |
| -------------- | --------------------------------------------------------------------- |
| Название       | `E2E UAV Flight Controller FC-100`                                    |
| Цена           | `120.00`                                                              |
| Валюта         | `USD`                                                                 |
| URL            | `${TEST_SUPPLIER_SITE_URL}/products/e2e-uav-flight-controller-fc-100` |
| Поставщик      | `E2E Supplier Email Division`                                         |
| Контакт        | `${TEST_SUPPLIER_EMAIL}`                                              |
| Тип контакта   | `email`                                                               |
| Описание       | `Flight controller for UAV integration testing`                       |
| Характеристики | `voltage=5V`, `interfaces=UART,I2C,SPI`, `weight=12g`                 |
| Изображение    | HTTPS URL изображения товара                                          |

---

## 4.2. Товар 2 — Telegram-контакт

| Поле           | Значение                                                                  |
| -------------- | ------------------------------------------------------------------------- |
| Название       | `E2E Industrial CNC Controller IC-200`                                    |
| Цена           | `840.00`                                                                  |
| Валюта         | `EUR`                                                                     |
| URL            | `${TEST_SUPPLIER_SITE_URL}/products/e2e-industrial-cnc-controller-ic-200` |
| Поставщик      | `E2E Supplier Telegram Division`                                          |
| Контакт        | `${TEST_SUPPLIER_TELEGRAM}`                                               |
| Тип контакта   | `telegram`                                                                |
| Описание       | `Industrial CNC controller for factory automation testing`                |
| Характеристики | `axis=4`, `input_voltage=24V`, `protocol=Modbus`                          |
| Изображение    | HTTPS URL изображения товара                                              |

---

## 4.3. Товар 3 — цена отсутствует

| Поле         | Значение                                                         |
| ------------ | ---------------------------------------------------------------- |
| Название     | `E2E Rack Workstation RW-500`                                    |
| Цена         | отсутствует на странице                                          |
| Валюта       | отсутствует                                                      |
| URL          | `${TEST_SUPPLIER_SITE_URL}/products/e2e-rack-workstation-rw-500` |
| Поставщик    | `E2E Supplier Email Division`                                    |
| Контакт      | `${TEST_SUPPLIER_EMAIL}`                                         |
| Тип контакта | `email`                                                          |
| Описание     | `Rack workstation for compute workload testing`                  |

Ожидаемое поведение: карточка сохраняется с `price = NULL`, если проект следует практичной модели из ТЗ. В UI должна отображаться фраза вида `Цена не найдена`.

---

## 4.4. Невалидный товар

| Поле       | Значение                                          |
| ---------- | ------------------------------------------------- |
| Название   | отсутствует                                       |
| URL        | отсутствует или невалидный                        |
| Контакт    | `not-an-email`                                    |
| Назначение | Проверить, что невалидная карточка не сохраняется |

Ожидаемое поведение: товар не должен попасть в `products`; причина пропуска должна быть сохранена в `agent_tasks.output_payload`.

---

# 5. Предусловия запуска E2E

Перед выполнением тестового протокола необходимо проверить:

## 5.1. Состояние БД

База должна быть чистой для E2E-прогона или изолированной по отдельному тестовому tenant/user.

Проверить наличие таблиц:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'search_requests',
    'products',
    'supplier_contacts',
    'contact_attempts',
    'agent_tasks'
  )
ORDER BY table_name;
```

Ожидаемый результат:

```text
agent_tasks
contact_attempts
products
search_requests
supplier_contacts
```

---

## 5.2. Проверка миграций

```sql
SELECT COUNT(*) AS tables_count
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'search_requests',
    'products',
    'supplier_contacts',
    'contact_attempts',
    'agent_tasks'
  );
```

Ожидаемый результат:

```text
tables_count = 5
```

---

## 5.3. Проверка check constraints

```sql
SELECT conname
FROM pg_constraint
WHERE conname IN (
  'supplier_contacts_type_check',
  'contact_attempts_channel_check',
  'agent_tasks_type_check'
)
ORDER BY conname;
```

Ожидаемый результат:

```text
agent_tasks_type_check
contact_attempts_channel_check
supplier_contacts_type_check
```

---

## 5.4. Проверка индексов

```sql
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'idx_products_search_request_id',
    'idx_supplier_contacts_product_id',
    'idx_contact_attempts_product_id',
    'idx_agent_tasks_status',
    'idx_search_requests_status'
  )
ORDER BY indexname;
```

Ожидаемый результат:

```text
idx_agent_tasks_status
idx_contact_attempts_product_id
idx_products_search_request_id
idx_search_requests_status
idx_supplier_contacts_product_id
```

---

# 6. Основной E2E-сценарий №1: полный путь поиска товара

## TC-E2E-001 — Создание поискового запроса через WebUI

**Цель:** проверить, что пользователь может создать запрос, а система создаёт persisted search request и persisted agent task.

### Шаги

1. Открыть WebUI:

```text
${WEBUI_BASE_URL}/search-requests
```

2. Убедиться, что страница загрузилась без ошибок.

3. Нажать кнопку:

```text
Новый запрос
```

4. В поле запроса ввести:

```text
E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}
```

5. Нажать:

```text
Запустить поиск
```

### Ожидаемый результат в UI

* Пользователь перенаправлен на страницу созданного запроса или каталог товаров по запросу.
* Отображается исходный текст запроса.
* Статус отображается как:

```text
В очереди
```

или быстро переходит в:

```text
Выполняется
```

### Проверка API

Выполнить запрос:

```http
GET ${API_BASE_URL}/search-requests
```

Ожидаемый результат:

* В списке есть созданный запрос.
* `queryText` совпадает с введённым текстом.
* `status` равен `queued`, `running` или `completed`, в зависимости от скорости worker.
* `productsCount` на этом этапе может быть `0`.

### Проверка БД

```sql
SELECT id, query_text, status, agent_task_id, created_at, started_at, completed_at
FROM search_requests
WHERE query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}'
ORDER BY created_at DESC
LIMIT 1;
```

Ожидаемый результат:

* Запись существует.
* `query_text` совпадает.
* `status IN ('queued', 'running', 'completed')`.
* `agent_task_id IS NOT NULL`.

Проверить связанную задачу:

```sql
SELECT id, task_type, status, input_payload, created_at, started_at, completed_at
FROM agent_tasks
WHERE id = (
    SELECT agent_task_id
    FROM search_requests
    WHERE query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}'
    ORDER BY created_at DESC
    LIMIT 1
);
```

Ожидаемый результат:

* `task_type = 'product_search'`.
* `status IN ('queued', 'running', 'completed')`.
* `input_payload` содержит `searchRequestId`.
* `input_payload` содержит исходный `queryText`.

---

## TC-E2E-002 — Обработка запроса worker-процессом

**Цель:** проверить, что задача действительно выполняется worker-процессом асинхронно, а не backend API синхронно.

### Шаги

1. На странице запроса наблюдать изменение статуса.
2. Дождаться статуса:

```text
Завершён
```

или статуса:

```text
Ошибка
```

3. Если статус `Ошибка`, перейти к сценарию TC-E2E-010.

### Ожидаемый результат в UI

* Статус переходит по цепочке:

```text
В очереди → Выполняется → Завершён
```

* Страница не блокирует браузер пользователя.
* UI не зависает.
* Пользователь может обновлять страницу и видеть актуальный persisted status.

### Проверка БД

```sql
SELECT status, started_at, completed_at, error_message
FROM search_requests
WHERE query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}'
ORDER BY created_at DESC
LIMIT 1;
```

Ожидаемый результат:

* `status = 'completed'`.
* `started_at IS NOT NULL`.
* `completed_at IS NOT NULL`.
* `error_message IS NULL`.

Проверить агентскую задачу:

```sql
SELECT task_type, status, output_payload, error_message, started_at, completed_at
FROM agent_tasks
WHERE id = (
    SELECT agent_task_id
    FROM search_requests
    WHERE query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}'
    ORDER BY created_at DESC
    LIMIT 1
);
```

Ожидаемый результат:

* `task_type = 'product_search'`.
* `status = 'completed'`.
* `started_at IS NOT NULL`.
* `completed_at IS NOT NULL`.
* `error_message IS NULL`.
* `output_payload` содержит:

  * `productsCreated`;
  * `productsSkipped`;
  * `errors`.

---

## TC-E2E-003 — Проверка сохранения найденного товара

**Цель:** проверить, что агент через browser MCP нашёл товар, structured output прошёл валидацию, а карточка сохранена в БД.

### Проверка БД

```sql
SELECT
    p.id,
    p.search_request_id,
    p.title,
    p.description,
    p.price,
    p.currency,
    p.product_url,
    p.source_domain,
    p.supplier_name,
    p.images,
    p.attributes,
    p.confidence_score
FROM products p
JOIN search_requests sr ON sr.id = p.search_request_id
WHERE sr.query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}'
ORDER BY p.created_at DESC;
```

### Ожидаемый результат

Должна существовать минимум одна карточка товара.

Для товара `E2E UAV Flight Controller FC-100` ожидается:

| Поле               | Ожидаемое значение                                                    |
| ------------------ | --------------------------------------------------------------------- |
| `title`            | содержит `E2E UAV Flight Controller FC-100`                           |
| `price`            | `120.00`                                                              |
| `currency`         | `USD`                                                                 |
| `product_url`      | `${TEST_SUPPLIER_SITE_URL}/products/e2e-uav-flight-controller-fc-100` |
| `supplier_name`    | содержит `E2E Supplier Email Division`                                |
| `images`           | JSON array                                                            |
| `attributes`       | JSON object                                                           |
| `confidence_score` | `NULL` или число от `0` до `1`                                        |

---

## TC-E2E-004 — Проверка сохранения контакта поставщика

**Цель:** проверить, что контакт поставщика сохранён отдельно от карточки товара.

### Проверка БД

```sql
SELECT
    sc.id,
    sc.product_id,
    sc.contact_type,
    sc.contact_value,
    sc.is_primary,
    sc.metadata,
    sc.created_at
FROM supplier_contacts sc
JOIN products p ON p.id = sc.product_id
JOIN search_requests sr ON sr.id = p.search_request_id
WHERE sr.query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}'
  AND p.title ILIKE '%E2E UAV Flight Controller FC-100%';
```

### Ожидаемый результат

* Есть минимум один контакт.
* `contact_type = 'email'`.
* `contact_value = '${TEST_SUPPLIER_EMAIL}'`.
* `product_id` указывает на найденный товар.

---

## TC-E2E-005 — Проверка каталога товаров в WebUI

**Цель:** проверить, что пользователь видит найденные товары через UI, а не только в БД.

### Шаги

1. Открыть страницу созданного запроса.
2. Перейти в каталог товаров.
3. Убедиться, что отображается карточка товара.

### Ожидаемый результат в UI

Карточка товара должна отображать:

| UI-элемент       | Ожидаемое значение                 |
| ---------------- | ---------------------------------- |
| Название         | `E2E UAV Flight Controller FC-100` |
| Цена             | `120.00`                           |
| Валюта           | `USD`                              |
| Поставщик        | `E2E Supplier Email Division`      |
| Домен источника  | домен `${TEST_SUPPLIER_SITE_URL}`  |
| Наличие контакта | отображается                       |
| Кнопка           | `Открыть`                          |

---

## TC-E2E-006 — Проверка страницы товара

**Цель:** проверить, что пользователь может открыть карточку товара и увидеть полные данные.

### Шаги

1. В каталоге товаров нажать:

```text
Открыть
```

2. Дождаться загрузки страницы товара.

### Ожидаемый результат в UI

На странице товара отображаются:

| Блок            | Ожидаемое содержимое                                                  |
| --------------- | --------------------------------------------------------------------- |
| Название        | `E2E UAV Flight Controller FC-100`                                    |
| Цена            | `120.00 USD`                                                          |
| Описание        | `Flight controller for UAV integration testing`                       |
| Ссылка на товар | `${TEST_SUPPLIER_SITE_URL}/products/e2e-uav-flight-controller-fc-100` |
| Поставщик       | `E2E Supplier Email Division`                                         |
| Изображения     | минимум одно изображение, если оно есть на странице                   |
| Характеристики  | `voltage=5V`, `interfaces=UART,I2C,SPI`, `weight=12g`                 |
| Контакты        | `${TEST_SUPPLIER_EMAIL}`                                              |
| Кнопка          | `Связаться`                                                           |

### Проверка API

```http
GET ${API_BASE_URL}/products/{productId}
```

Ожидаемый результат:

* `title` соответствует товару.
* `contacts` содержит email-контакт.
* `contactAttempts` пустой массив, если контакт ещё не запускался.

---

# 7. Основной E2E-сценарий №2: связь с поставщиком через email

## TC-E2E-007 — Запрос связи с поставщиком через WebUI

**Цель:** проверить, что пользователь может инициировать контакт, а система создаёт contact attempt и agent task.

### Шаги

1. На странице товара `E2E UAV Flight Controller FC-100` выбрать email-контакт.
2. Нажать:

```text
Связаться
```

3. Подтвердить действие, если UI показывает confirmation dialog.

### Ожидаемый результат в UI

* Кнопка `Связаться` становится недоступной на время активной задачи.
* В истории контактов появляется новая запись со статусом:

```text
В очереди
```

или:

```text
Выполняется
```

### Проверка БД

```sql
SELECT
    ca.id,
    ca.product_id,
    ca.supplier_contact_id,
    ca.agent_task_id,
    ca.channel,
    ca.status,
    ca.message_text,
    ca.external_message_id,
    ca.error_message,
    ca.created_at,
    ca.sent_at,
    ca.completed_at
FROM contact_attempts ca
JOIN products p ON p.id = ca.product_id
WHERE p.title ILIKE '%E2E UAV Flight Controller FC-100%'
ORDER BY ca.created_at DESC
LIMIT 1;
```

Ожидаемый результат:

* Запись существует.
* `channel = 'email'`.
* `status IN ('queued', 'running', 'sent')`.
* `agent_task_id IS NOT NULL`.

Проверить задачу:

```sql
SELECT task_type, status, input_payload
FROM agent_tasks
WHERE id = (
    SELECT ca.agent_task_id
    FROM contact_attempts ca
    JOIN products p ON p.id = ca.product_id
    WHERE p.title ILIKE '%E2E UAV Flight Controller FC-100%'
    ORDER BY ca.created_at DESC
    LIMIT 1
);
```

Ожидаемый результат:

* `task_type = 'supplier_contact'`.
* `input_payload` содержит:

  * `productId`;
  * `supplierContactId`;
  * `contactAttemptId`.

---

## TC-E2E-008 — Проверка отправки email

**Цель:** проверить, что email действительно отправлен через реальный email-коннектор.

### Шаги

1. Дождаться завершения contact attempt.
2. Открыть тестовый mailbox поставщика `${TEST_SUPPLIER_EMAIL}`.
3. Найти новое письмо.

### Ожидаемый результат в mailbox

Письмо должно быть получено на адрес:

```text
${TEST_SUPPLIER_EMAIL}
```

Тело письма должно содержать:

```text
Здравствуйте.
```

```text
Интересует товар: E2E UAV Flight Controller FC-100
```

```text
Актуальна ли цена
```

```text
Есть ли товар в наличии
```

```text
Какая минимальная партия
```

```text
Какие сроки поставки
```

```text
Какие доступны способы оплаты и доставки
```

```text
${TEST_SUPPLIER_SITE_URL}/products/e2e-uav-flight-controller-fc-100
```

Письмо не должно содержать:

```text
Подтверждаем заказ
```

```text
Готовы оплатить
```

```text
Закупаем
```

```text
Обходим ограничения
```

```text
Санкции
```

```text
Конфиденциальные данные
```

### Проверка БД

```sql
SELECT
    ca.status,
    ca.message_text,
    ca.external_message_id,
    ca.error_message,
    ca.sent_at,
    ca.completed_at
FROM contact_attempts ca
JOIN products p ON p.id = ca.product_id
WHERE p.title ILIKE '%E2E UAV Flight Controller FC-100%'
ORDER BY ca.created_at DESC
LIMIT 1;
```

Ожидаемый результат:

* `status = 'sent'`.
* `message_text IS NOT NULL`.
* `message_text` содержит название товара.
* `message_text` содержит URL товара.
* `external_message_id IS NOT NULL`, если email provider возвращает message id.
* `error_message IS NULL`.
* `sent_at IS NOT NULL`.
* `completed_at IS NOT NULL`.

### Проверка UI

На странице товара в истории контактов отображается:

| Поле          | Ожидаемое значение            |
| ------------- | ----------------------------- |
| Канал         | email                         |
| Статус        | Отправлено                    |
| Сообщение     | текст отправленного сообщения |
| Ошибка        | отсутствует                   |
| Дата отправки | заполнена                     |

---

# 8. Основной E2E-сценарий №3: связь с поставщиком через Telegram

## TC-E2E-009 — Полный путь Telegram-контакта

**Цель:** проверить второй поддерживаемый тип контакта — Telegram.

### Шаги поиска

1. Открыть:

```text
${WEBUI_BASE_URL}/search-requests
```

2. Нажать:

```text
Новый запрос
```

3. Ввести:

```text
E2E Industrial CNC Controller IC-200 site:${TEST_SUPPLIER_SITE_URL}
```

4. Нажать:

```text
Запустить поиск
```

5. Дождаться статуса:

```text
Завершён
```

6. Открыть каталог товаров.
7. Открыть товар:

```text
E2E Industrial CNC Controller IC-200
```

### Ожидаемый результат после поиска

В БД должен быть товар:

```sql
SELECT p.title, p.price, p.currency, p.product_url, sc.contact_type, sc.contact_value
FROM products p
JOIN supplier_contacts sc ON sc.product_id = p.id
WHERE p.title ILIKE '%E2E Industrial CNC Controller IC-200%';
```

Ожидаемый результат:

| Поле            | Значение                               |
| --------------- | -------------------------------------- |
| `title`         | `E2E Industrial CNC Controller IC-200` |
| `price`         | `840.00`                               |
| `currency`      | `EUR`                                  |
| `contact_type`  | `telegram`                             |
| `contact_value` | `${TEST_SUPPLIER_TELEGRAM}`            |

### Шаги контакта

1. На странице товара выбрать Telegram-контакт.
2. Нажать:

```text
Связаться
```

3. Дождаться завершения contact attempt.
4. Открыть тестовый Telegram supplier account/bot/channel.
5. Проверить входящее сообщение.

### Ожидаемый результат в Telegram

Сообщение должно содержать:

```text
Интересует товар: E2E Industrial CNC Controller IC-200
```

```text
Актуальна ли цена
```

```text
Есть ли товар в наличии
```

```text
Какая минимальная партия
```

```text
Какие сроки поставки
```

```text
${TEST_SUPPLIER_SITE_URL}/products/e2e-industrial-cnc-controller-ic-200
```

Сообщение не должно содержать подтверждение заказа, обещание оплаты, конфиденциальные данные или запрещённые темы.

### Проверка БД

```sql
SELECT
    ca.channel,
    ca.status,
    ca.message_text,
    ca.external_message_id,
    ca.error_message,
    ca.sent_at,
    ca.completed_at
FROM contact_attempts ca
JOIN products p ON p.id = ca.product_id
WHERE p.title ILIKE '%E2E Industrial CNC Controller IC-200%'
ORDER BY ca.created_at DESC
LIMIT 1;
```

Ожидаемый результат:

* `channel = 'telegram'`.
* `status = 'sent'`.
* `message_text IS NOT NULL`.
* `error_message IS NULL`.
* `sent_at IS NOT NULL`.
* `completed_at IS NOT NULL`.

---

# 9. E2E-сценарии ошибок и граничных случаев

## TC-E2E-010 — Ошибка browser MCP / agent search

**Цель:** проверить, что ошибка поиска не теряется и видна пользователю.

### Условие

Тестовый запрос должен вести к контролируемой ошибке browser MCP, например:

* тестовая витрина временно недоступна;
* DNS тестового домена недоступен;
* browser MCP возвращает ошибку доступа;
* страница отдаёт HTTP 500.

### Шаги

1. Создать запрос:

```text
E2E Browser MCP failure site:https://unavailable-e2e-supplier.invalid
```

2. Дождаться завершения обработки.

### Ожидаемый результат в UI

* Статус запроса:

```text
Ошибка
```

* Пользователь видит понятное сообщение ошибки.
* Каталог товаров не показывает некорректные карточки.
* UI не зависает.

### Проверка БД

```sql
SELECT status, error_message, started_at, completed_at
FROM search_requests
WHERE query_text = 'E2E Browser MCP failure site:https://unavailable-e2e-supplier.invalid'
ORDER BY created_at DESC
LIMIT 1;
```

Ожидаемый результат:

* `status = 'failed'`.
* `error_message IS NOT NULL`.
* `started_at IS NOT NULL`.
* `completed_at IS NOT NULL`.

```sql
SELECT task_type, status, error_message
FROM agent_tasks
WHERE id = (
    SELECT agent_task_id
    FROM search_requests
    WHERE query_text = 'E2E Browser MCP failure site:https://unavailable-e2e-supplier.invalid'
    ORDER BY created_at DESC
    LIMIT 1
);
```

Ожидаемый результат:

* `task_type = 'product_search'`.
* `status = 'failed'`.
* `error_message IS NOT NULL`.

---

## TC-E2E-011 — Невалидная карточка товара не сохраняется

**Цель:** проверить, что система не сохраняет невалидный output агента.

### Шаги

1. Создать запрос:

```text
E2E invalid product card site:${TEST_SUPPLIER_SITE_URL}/invalid-products
```

2. Дождаться завершения обработки.

### Ожидаемый результат

* Если на странице есть хотя бы один валидный товар — запрос может завершиться `completed`.
* Невалидный товар без `title`, без валидного `productUrl` или с невалидным контактом не сохраняется.

### Проверка БД

```sql
SELECT COUNT(*) AS invalid_products_count
FROM products
WHERE product_url IS NULL
   OR product_url = ''
   OR title IS NULL
   OR title = '';
```

Ожидаемый результат:

```text
invalid_products_count = 0
```

Проверка невалидного email:

```sql
SELECT COUNT(*) AS invalid_email_contacts_count
FROM supplier_contacts
WHERE contact_type = 'email'
  AND contact_value NOT LIKE '%@%';
```

Ожидаемый результат:

```text
invalid_email_contacts_count = 0
```

Проверить `agent_tasks.output_payload`:

```sql
SELECT output_payload
FROM agent_tasks
WHERE id = (
    SELECT agent_task_id
    FROM search_requests
    WHERE query_text = 'E2E invalid product card site:${TEST_SUPPLIER_SITE_URL}/invalid-products'
    ORDER BY created_at DESC
    LIMIT 1
);
```

Ожидаемый результат:

* `output_payload` содержит `productsSkipped >= 1`.
* `output_payload` содержит причину пропуска.

---

## TC-E2E-012 — Товар без цены сохраняется корректно

**Цель:** проверить практичное поведение из ТЗ: цена может быть `NULL`, но UI должен явно показывать отсутствие цены.

### Шаги

1. Создать запрос:

```text
E2E Rack Workstation RW-500 site:${TEST_SUPPLIER_SITE_URL}
```

2. Дождаться статуса:

```text
Завершён
```

3. Открыть каталог.
4. Открыть товар:

```text
E2E Rack Workstation RW-500
```

### Проверка БД

```sql
SELECT title, price, currency
FROM products
WHERE title ILIKE '%E2E Rack Workstation RW-500%'
ORDER BY created_at DESC
LIMIT 1;
```

Ожидаемый результат:

* `title` содержит `E2E Rack Workstation RW-500`.
* `price IS NULL`.
* `currency IS NULL`.

### Ожидаемый результат в UI

Вместо пустого значения или `0` UI должен показать:

```text
Цена не найдена
```

Запрещено показывать:

```text
0
```

```text
NaN
```

```text
undefined
```

```text
null
```

---

## TC-E2E-013 — Валидация пустого поискового запроса

**Цель:** проверить frontend/backend validation.

### Шаги

1. Открыть форму создания запроса.
2. Оставить поле пустым.
3. Нажать:

```text
Запустить поиск
```

### Ожидаемый результат в UI

* Запрос не создаётся.
* Пользователь видит ошибку валидации:

```text
Запрос не может быть пустым
```

или эквивалентное сообщение.

### Проверка БД

```sql
SELECT COUNT(*) AS empty_query_count
FROM search_requests
WHERE query_text = '';
```

Ожидаемый результат:

```text
empty_query_count = 0
```

---

## TC-E2E-014 — Валидация запроса короче 3 символов

### Шаги

1. Открыть форму создания запроса.
2. Ввести:

```text
ПК
```

3. Нажать:

```text
Запустить поиск
```

### Ожидаемый результат

* Запрос не создаётся.
* UI показывает сообщение о минимальной длине.
* В БД нет новой записи с `query_text = 'ПК'`.

```sql
SELECT COUNT(*) AS too_short_query_count
FROM search_requests
WHERE query_text = 'ПК';
```

Ожидаемый результат:

```text
too_short_query_count = 0
```

---

## TC-E2E-015 — Валидация запроса длиннее 1000 символов

### Шаги

1. Открыть форму создания запроса.
2. Ввести строку длиной 1001 символ.
3. Нажать:

```text
Запустить поиск
```

### Ожидаемый результат

* Запрос не создаётся.
* UI показывает сообщение о превышении максимальной длины.
* Backend не создаёт `search_request`.
* Backend не создаёт `agent_task`.

---

## TC-E2E-016 — Нельзя создать повторный активный contact attempt

**Цель:** проверить, что пользователь не может запустить несколько одновременных контактов по одному товару.

### Предусловие

Есть товар с активным contact attempt в статусе:

```text
queued
```

или:

```text
running
```

### Шаги

1. Открыть страницу товара.
2. Проверить кнопку `Связаться`.
3. Попытаться нажать кнопку повторно.

### Ожидаемый результат в UI

* Кнопка недоступна.
* Пользователь видит объяснение:

```text
Связь с поставщиком уже выполняется
```

или эквивалентное сообщение.

### Проверка API

При прямой попытке вызвать:

```http
POST ${API_BASE_URL}/products/{productId}/contact-supplier
```

Ожидаемый результат:

* HTTP `409 Conflict` или другой явно определённый код бизнес-конфликта.
* Новая запись в `contact_attempts` не создаётся.

### Проверка БД

```sql
SELECT COUNT(*) AS active_attempts_count
FROM contact_attempts
WHERE product_id = '{productId}'
  AND status IN ('queued', 'running');
```

Ожидаемый результат:

```text
active_attempts_count = 1
```

---

## TC-E2E-017 — Нельзя связаться с товаром без контактов

**Цель:** проверить UI и backend protection.

### Предусловие

Существует товар без supplier contacts. Такой товар может быть создан только через легитимный поток, если в конфигурации явно разрешено `ALLOW_PRODUCTS_WITHOUT_CONTACTS=true`. Если по ТЗ такое сохранение запрещено, этот тест считается неприменимым.

### Шаги

1. Открыть страницу товара без контактов.
2. Проверить состояние кнопки `Связаться`.

### Ожидаемый результат в UI

* Кнопка `Связаться` недоступна.
* Отображается сообщение:

```text
Нет доступных контактов поставщика
```

### Проверка API

```http
POST ${API_BASE_URL}/products/{productId}/contact-supplier
```

Ожидаемый результат:

* HTTP `400 Bad Request` или `422 Unprocessable Entity`.
* `contact_attempts` не создаётся.
* `agent_tasks` типа `supplier_contact` не создаётся.

---

## TC-E2E-018 — Ошибка email-коннектора сохраняется

**Цель:** проверить, что ошибка отправки email не теряется.

### Условие

Использовать тестовый email-контакт, для которого email provider гарантированно возвращает ошибку отправки. Например, невалидный домен в контролируемом тестовом товаре:

```text
supplier-fail@invalid-e2e-domain.invalid
```

Этот контакт должен быть извлечён агентом как email, но отправка должна завершиться ошибкой коннектора.

### Шаги

1. Создать поисковый запрос на товар с failure email.
2. Дождаться сохранения товара.
3. Открыть страницу товара.
4. Нажать `Связаться`.
5. Дождаться завершения contact attempt.

### Ожидаемый результат

* Contact attempt получает статус:

```text
failed
```

* В UI отображается понятное сообщение ошибки.
* Worker не падает.
* Agent task получает статус `failed`.

### Проверка БД

```sql
SELECT ca.status, ca.error_message, at.status AS agent_task_status, at.error_message AS agent_task_error
FROM contact_attempts ca
JOIN agent_tasks at ON at.id = ca.agent_task_id
WHERE ca.channel = 'email'
ORDER BY ca.created_at DESC
LIMIT 1;
```

Ожидаемый результат:

* `ca.status = 'failed'`.
* `ca.error_message IS NOT NULL`.
* `agent_task_status = 'failed'`.
* `agent_task_error IS NOT NULL`.

---

## TC-E2E-019 — Ошибка Telegram-коннектора сохраняется

**Цель:** проверить обработку ошибки Telegram.

### Условие

Использовать тестовый Telegram contact value, который проходит форматную валидацию, но недоступен для отправки:

```text
@e2e_unreachable_supplier_test
```

### Шаги

1. Создать поисковый запрос на товар с таким Telegram-контактом.
2. Дождаться сохранения товара.
3. Открыть страницу товара.
4. Нажать `Связаться`.
5. Дождаться завершения contact attempt.

### Ожидаемый результат

* Contact attempt получает статус `failed`.
* Ошибка видна пользователю.
* Ошибка сохранена в `contact_attempts.error_message`.
* Worker продолжает обрабатывать последующие задачи.

---

# 10. Проверка API поверх полного E2E

## TC-E2E-020 — Проверка `GET /api/search-requests`

### Запрос

```http
GET ${API_BASE_URL}/search-requests
```

### Ожидаемый результат

* HTTP `200`.
* Response содержит `items`.
* Созданные в E2E запросы присутствуют.
* Для завершённых запросов:

  * `status = completed`;
  * `productsCount > 0`;
  * `completedAt` заполнен.

---

## TC-E2E-021 — Проверка `GET /api/search-requests/{id}`

### Ожидаемый результат

* HTTP `200`.
* Возвращается корректный `id`.
* `queryText` совпадает.
* `status` совпадает с БД.
* `productsCount` совпадает с фактическим количеством товаров в БД.

Проверка количества:

```sql
SELECT COUNT(*) AS products_count
FROM products
WHERE search_request_id = '{searchRequestId}';
```

---

## TC-E2E-022 — Проверка `GET /api/search-requests/{id}/products`

### Ожидаемый результат

* HTTP `200`.
* Response содержит:

  * `items`;
  * `page`;
  * `pageSize`;
  * `total`.
* `items.length <= pageSize`.
* Каждый товар содержит:

  * `id`;
  * `title`;
  * `productUrl`;
  * `contactsCount`.

---

## TC-E2E-023 — Проверка `GET /api/products/{id}`

### Ожидаемый результат

* HTTP `200`.
* Response содержит:

  * `id`;
  * `searchRequestId`;
  * `title`;
  * `productUrl`;
  * `contacts`;
  * `contactAttempts`.
* `contacts` содержит только поддерживаемые типы:

  * `email`;
  * `telegram`.

---

## TC-E2E-024 — Проверка `POST /api/products/{id}/contact-supplier`

### Ожидаемый результат

* HTTP `200` или `202 Accepted`.
* Response содержит:

  * `contactAttemptId`;
  * `status = queued`.
* В БД создана запись `contact_attempts`.
* В БД создана запись `agent_tasks` типа `supplier_contact`.

---

# 11. Проверка жизненного цикла статусов

## TC-E2E-025 — SearchRequest status transitions

Для каждого успешно завершённого запроса проверить:

```sql
SELECT status, started_at, completed_at, error_message
FROM search_requests
WHERE id = '{searchRequestId}';
```

Ожидаемый результат:

* Финальный статус `completed`.
* `started_at IS NOT NULL`.
* `completed_at IS NOT NULL`.
* `completed_at >= started_at`.
* `error_message IS NULL`.

Для failed-запроса:

* Финальный статус `failed`.
* `error_message IS NOT NULL`.
* `completed_at IS NOT NULL`.

---

## TC-E2E-026 — AgentTask status transitions

```sql
SELECT task_type, status, started_at, completed_at, error_message
FROM agent_tasks
WHERE id = '{agentTaskId}';
```

Ожидаемый результат для успешной задачи:

* `status = completed`.
* `started_at IS NOT NULL`.
* `completed_at IS NOT NULL`.
* `error_message IS NULL`.

Ожидаемый результат для failed-задачи:

* `status = failed`.
* `error_message IS NOT NULL`.
* `completed_at IS NOT NULL`.

---

## TC-E2E-027 — ContactAttempt status transitions

```sql
SELECT channel, status, sent_at, completed_at, error_message
FROM contact_attempts
WHERE id = '{contactAttemptId}';
```

Ожидаемый результат для успешной отправки:

* `status = sent`.
* `sent_at IS NOT NULL`.
* `completed_at IS NOT NULL`.
* `error_message IS NULL`.

Ожидаемый результат для ошибки:

* `status = failed`.
* `sent_at IS NULL` или заполнен только если ошибка произошла после частичной отправки.
* `completed_at IS NOT NULL`.
* `error_message IS NOT NULL`.

---

# 12. Проверка UI-состояний

## TC-E2E-028 — Loading states

### Проверить

* При создании запроса кнопка `Запустить поиск` показывает состояние загрузки или блокируется.
* При загрузке списка запросов отображается loading state.
* При загрузке каталога отображается loading state.
* При загрузке страницы товара отображается loading state.
* При запуске контакта кнопка `Связаться` блокируется.

### Ожидаемый результат

UI не позволяет выполнить повторные действия во время активной операции.

---

## TC-E2E-029 — Empty states

### Сценарии

1. Нет поисковых запросов.
2. Запрос завершён, но товаров не найдено.
3. У товара нет попыток связи.

### Ожидаемый результат

UI показывает понятные сообщения:

```text
Запросов пока нет
```

```text
Товары не найдены
```

```text
История контактов пуста
```

или эквивалентные тексты.

---

## TC-E2E-030 — Error states

### Проверить

* Ошибка поиска отображается на странице запроса.
* Ошибка отправки email отображается на странице товара.
* Ошибка отправки Telegram отображается на странице товара.
* Ошибка API не приводит к белому экрану.
* Пользователь видит человекочитаемый текст, а не stack trace.

---

# 13. Проверка безопасности агентского сообщения

## TC-E2E-031 — Сообщение поставщику не нарушает ограничения

Для каждого успешного contact attempt проверить `message_text`.

```sql
SELECT message_text
FROM contact_attempts
WHERE status = 'sent'
ORDER BY created_at DESC;
```

Каждое сообщение должно содержать:

* приветствие;
* название товара;
* вопрос об актуальности цены;
* вопрос о наличии;
* вопрос о минимальной партии;
* вопрос о сроках поставки;
* вопрос об оплате и доставке;
* ссылку на товар;
* нейтральный деловой тон.

Каждое сообщение не должно содержать:

* подтверждение заказа;
* обещание оплаты;
* запрос обхода ограничений;
* передачу персональных данных;
* передачу платёжных данных;
* формулировки, создающие юридическое обязательство.

---

# 14. Проверка observability

## TC-E2E-032 — Логи product_search

В логах worker должны быть записи с:

| Поле                | Требование                                |
| ------------------- | ----------------------------------------- |
| `agent_task_id`     | заполнено                                 |
| `search_request_id` | заполнено                                 |
| `task_type`         | `product_search`                          |
| `status`            | `running`, затем `completed` или `failed` |
| `duration_ms`       | заполнено                                 |
| `error`             | только при ошибке                         |

Ожидаемый результат:

* По `agent_task_id` можно связать события worker с записью в БД.
* В логах нет секретов коннекторов.
* В логах нет паролей, токенов, SMTP credentials, Telegram session secrets.

---

## TC-E2E-033 — Логи supplier_contact

В логах worker должны быть записи с:

| Поле                 | Требование                           |
| -------------------- | ------------------------------------ |
| `agent_task_id`      | заполнено                            |
| `product_id`         | заполнено                            |
| `contact_attempt_id` | заполнено                            |
| `channel`            | `email` или `telegram`               |
| `status`             | `running`, затем `sent` или `failed` |
| `duration_ms`        | заполнено                            |
| `error`              | только при ошибке                    |

---

# 15. Проверка производительности MVP

## TC-E2E-034 — Создание поискового запроса

### Шаги

1. Открыть DevTools Network.
2. Создать новый поисковый запрос.
3. Измерить время ответа `POST /api/search-requests`.

### Ожидаемый результат

* HTTP-response приходит не дольше `500 ms` без учёта внешних задержек сети.
* Backend не ждёт полного завершения агентского поиска.
* Response возвращает `status = queued`.

---

## TC-E2E-035 — Список запросов при 1000 записях

### Условие

В БД существует 1000 поисковых запросов, созданных легитимным API-методом или подготовленных отдельным нагрузочным прогоном. Для чистого E2E-прогона прямое ручное создание через SQL не используется.

### Шаги

1. Открыть:

```text
${WEBUI_BASE_URL}/search-requests
```

2. Измерить время загрузки данных.

### Ожидаемый результат

* API отвечает не дольше `1 секунды`.
* UI не зависает.
* Таблица отображается корректно.
* Пагинация или lazy loading работают корректно, если реализованы.

---

## TC-E2E-036 — Каталог товаров с пагинацией

### Шаги

1. Открыть каталог запроса, где больше 20 товаров.
2. Проверить первую страницу.
3. Перейти на вторую страницу.

### Ожидаемый результат

* Размер страницы не превышает допустимый `pageSize`.
* `total` соответствует количеству товаров в БД.
* Переход между страницами не ломает фильтрацию по `search_request_id`.

---

# 16. Проверка устойчивости

## TC-E2E-037 — Перезапуск WebUI не теряет состояние

### Шаги

1. Создать поисковый запрос.
2. Дождаться статуса `running`.
3. Обновить страницу браузера.
4. Вернуться на страницу запроса.

### Ожидаемый результат

* Статус берётся из БД.
* Запрос не исчезает.
* UI корректно продолжает отображать процесс.

---

## TC-E2E-038 — Перезапуск worker во время queued-задачи

### Шаги

1. Остановить worker.
2. Создать поисковый запрос.
3. Убедиться, что запрос имеет статус `queued`.
4. Запустить worker.
5. Дождаться завершения обработки.

### Ожидаемый результат

* Задача не потеряна.
* После запуска worker задача переходит в `running`.
* После обработки запрос получает `completed` или `failed`.
* В БД есть persisted lifecycle.

---

## TC-E2E-039 — Перезапуск worker во время supplier_contact

### Шаги

1. Создать contact attempt.
2. Остановить worker во время обработки, если это технически возможно в тестовом окружении.
3. Запустить worker.
4. Проверить финальное состояние.

### Ожидаемый результат

Допустимы два корректных варианта, зависящие от реализации идемпотентности:

1. Задача безопасно завершается один раз.
2. Задача переводится в `failed` с понятной ошибкой и не создаёт дублирующих отправок.

Недопустимо:

* два email на один contact attempt;
* два Telegram-сообщения на один contact attempt;
* зависший статус `running` без timeout/recovery;
* потеря записи `contact_attempts`.

---

# 17. Проверка запрета лишних MVP-функций

## TC-E2E-040 — В MVP нет автономной покупки

### Проверить UI

На страницах не должно быть действий:

```text
Купить
```

```text
Оформить заказ
```

```text
Оплатить
```

```text
Подтвердить поставку
```

### Проверить сообщение агента

`message_text` не должен содержать подтверждения сделки.

---

## TC-E2E-041 — В MVP нет CRM-функций

В UI не должно быть обязательных разделов:

* сделки;
* pipeline;
* счета;
* оплаты;
* статусы коммерческого предложения;
* автоматическая цепочка переговоров.

---

## TC-E2E-042 — В MVP нет массовой рассылки

Проверить, что пользователь может инициировать контакт только из конкретной карточки товара, а не массово по всем товарам запроса.

---

# 18. Итоговый сквозной сценарий приёмки MVP

Этот сценарий выполняется последним и считается главным acceptance test.

## TC-E2E-ACCEPTANCE-001 — Полный happy path

### Шаг 1. Открыть WebUI

Открыть:

```text
${WEBUI_BASE_URL}/search-requests
```

Ожидается:

* страница загружена;
* список запросов доступен;
* нет frontend crash.

---

### Шаг 2. Создать поисковый запрос

Ввести:

```text
E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}
```

Нажать:

```text
Запустить поиск
```

Ожидается:

* создан search request;
* статус `queued`;
* создан agent task типа `product_search`.

---

### Шаг 3. Дождаться обработки агентом

Ожидается:

* статус переходит в `running`;
* затем в `completed`;
* `started_at` и `completed_at` заполнены.

---

### Шаг 4. Проверить найденный товар

Ожидается:

* найден `E2E UAV Flight Controller FC-100`;
* товар сохранён в `products`;
* контакт сохранён в `supplier_contacts`;
* каталог отображает товар.

---

### Шаг 5. Открыть карточку товара

Ожидается:

* отображается название;
* отображается цена;
* отображается ссылка;
* отображается описание;
* отображаются характеристики;
* отображается контакт поставщика;
* кнопка `Связаться` доступна.

---

### Шаг 6. Связаться с поставщиком

Нажать:

```text
Связаться
```

Ожидается:

* создан `contact_attempt`;
* создан `agent_task` типа `supplier_contact`;
* contact attempt получает статус `queued`, затем `running`, затем `sent`.

---

### Шаг 7. Проверить фактическую отправку

Открыть mailbox `${TEST_SUPPLIER_EMAIL}`.

Ожидается:

* письмо реально получено;
* письмо содержит название товара;
* письмо содержит вопросы из шаблона;
* письмо содержит ссылку на товар;
* письмо не содержит запрещённых формулировок.

---

### Шаг 8. Проверить отображение результата в UI

Вернуться на страницу товара.

Ожидается:

* в истории контактов отображается запись;
* канал `email`;
* статус `Отправлено`;
* текст сообщения отображается;
* ошибки нет.

---

### Шаг 9. Проверить финальное состояние БД

```sql
SELECT sr.status AS search_status,
       at.status AS search_task_status
FROM search_requests sr
JOIN agent_tasks at ON at.id = sr.agent_task_id
WHERE sr.query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}'
ORDER BY sr.created_at DESC
LIMIT 1;
```

Ожидается:

```text
search_status = completed
search_task_status = completed
```

```sql
SELECT COUNT(*) AS products_count
FROM products p
JOIN search_requests sr ON sr.id = p.search_request_id
WHERE sr.query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}';
```

Ожидается:

```text
products_count >= 1
```

```sql
SELECT COUNT(*) AS contacts_count
FROM supplier_contacts sc
JOIN products p ON p.id = sc.product_id
JOIN search_requests sr ON sr.id = p.search_request_id
WHERE sr.query_text = 'E2E UAV Flight Controller FC-100 site:${TEST_SUPPLIER_SITE_URL}';
```

Ожидается:

```text
contacts_count >= 1
```

```sql
SELECT ca.status, ca.channel, ca.message_text, ca.error_message
FROM contact_attempts ca
JOIN products p ON p.id = ca.product_id
WHERE p.title ILIKE '%E2E UAV Flight Controller FC-100%'
ORDER BY ca.created_at DESC
LIMIT 1;
```

Ожидается:

```text
status = sent
channel = email
message_text IS NOT NULL
error_message IS NULL
```

---

# 19. Критерии прохождения E2E-прогона

E2E-прогон считается успешным, если выполнены все условия:

1. Пользовательский путь через WebUI полностью проходит без ручного вмешательства в БД.
2. Поисковый запрос создаётся через UI/API.
3. Worker асинхронно обрабатывает задачу.
4. Browser MCP реально вызывается агентом.
5. Валидные товары сохраняются в БД.
6. Невалидные товары не сохраняются.
7. Контакты поставщиков сохраняются отдельно.
8. Каталог товаров отображает данные из backend API.
9. Страница товара отображает полные данные товара.
10. Contact supplier action создаёт persisted contact attempt.
11. Email-коннектор реально отправляет письмо в тестовый mailbox.
12. Telegram-коннектор реально отправляет сообщение в тестовый Telegram-контур.
13. Результаты отправки сохраняются в БД.
14. История контактов отображается в UI.
15. Ошибки поиска и отправки сохраняются и видны пользователю.
16. Нет зависших задач в статусе `queued` или `running` после завершения теста.
17. В логах есть correlation identifiers.
18. В логах нет секретов.
19. UI не показывает `undefined`, `null`, `NaN`, stack traces.
20. В MVP отсутствуют действия автономной покупки, оплаты и массовой рассылки.

---

# 20. Финальная проверка отсутствия зависших задач

После завершения всех тестов выполнить:

```sql
SELECT task_type, status, COUNT(*) AS count
FROM agent_tasks
WHERE status IN ('queued', 'running')
GROUP BY task_type, status;
```

Ожидаемый результат:

```text
0 rows
```

Проверить активные contact attempts:

```sql
SELECT status, COUNT(*) AS count
FROM contact_attempts
WHERE status IN ('queued', 'running')
GROUP BY status;
```

Ожидаемый результат:

```text
0 rows
```

---

# 21. Финальный отчёт тестового прогона

По итогам тестирования должен быть заполнен отчёт:

```text
Проект:
Версия сборки:
Дата прогона:
Окружение:
WebUI URL:
API URL:
Model provider:
Model name:
Browser MCP connector:
Email connector:
Telegram connector:
Тестировщик:

TC-E2E-001: PASS / FAIL
TC-E2E-002: PASS / FAIL
TC-E2E-003: PASS / FAIL
TC-E2E-004: PASS / FAIL
TC-E2E-005: PASS / FAIL
TC-E2E-006: PASS / FAIL
TC-E2E-007: PASS / FAIL
TC-E2E-008: PASS / FAIL
TC-E2E-009: PASS / FAIL
TC-E2E-010: PASS / FAIL
TC-E2E-011: PASS / FAIL
TC-E2E-012: PASS / FAIL
TC-E2E-013: PASS / FAIL
TC-E2E-014: PASS / FAIL
TC-E2E-015: PASS / FAIL
TC-E2E-016: PASS / FAIL
TC-E2E-017: PASS / FAIL / N/A
TC-E2E-018: PASS / FAIL
TC-E2E-019: PASS / FAIL
TC-E2E-020: PASS / FAIL
TC-E2E-021: PASS / FAIL
TC-E2E-022: PASS / FAIL
TC-E2E-023: PASS / FAIL
TC-E2E-024: PASS / FAIL
TC-E2E-025: PASS / FAIL
TC-E2E-026: PASS / FAIL
TC-E2E-027: PASS / FAIL
TC-E2E-028: PASS / FAIL
TC-E2E-029: PASS / FAIL
TC-E2E-030: PASS / FAIL
TC-E2E-031: PASS / FAIL
TC-E2E-032: PASS / FAIL
TC-E2E-033: PASS / FAIL
TC-E2E-034: PASS / FAIL
TC-E2E-035: PASS / FAIL
TC-E2E-036: PASS / FAIL
TC-E2E-037: PASS / FAIL
TC-E2E-038: PASS / FAIL
TC-E2E-039: PASS / FAIL
TC-E2E-040: PASS / FAIL
TC-E2E-041: PASS / FAIL
TC-E2E-042: PASS / FAIL
TC-E2E-ACCEPTANCE-001: PASS / FAIL

Итог:
PASS / FAIL

Критические дефекты:
1.
2.
3.

Некритические дефекты:
1.
2.
3.

Решение:
MVP принят / MVP не принят
```

---

# 22. Блокирующие дефекты

MVP не может быть принят, если найден хотя бы один из следующих дефектов:

* поисковый запрос не создаётся через WebUI;
* agent task не создаётся;
* worker не обрабатывает задачу;
* browser MCP не вызывается;
* товары сохраняются без schema validation;
* карточки не отображаются в UI;
* контакты поставщиков не сохраняются;
* кнопка `Связаться` не создаёт contact attempt;
* email или Telegram отправка фактически не выполняется;
* результат отправки не сохраняется;
* ошибки теряются;
* статусы зависают в `queued` или `running`;
* UI показывает технический stack trace пользователю;
* agent message подтверждает покупку или содержит запрещённые формулировки;
* секреты коннекторов попадают в frontend, API response или логи;
* backend выполняет долгий агентский поиск синхронно внутри HTTP-запроса.

---

# 23. Итог

Этот протокол проверяет не отдельные функции, а полный жизненный цикл MVP:

```text
Пользователь → WebUI → Backend API → БД → Очередь → Agent Worker → LLM → Browser MCP → БД → WebUI → Contact Action → Agent Worker → Email/Telegram Connector → БД → WebUI
```

Только успешное прохождение этого протокола подтверждает, что MVP действительно работает end-to-end, а не демонстрирует разрозненные части системы на заглушках.
---

# 24. Contract Draft E2E Extension

## TC-E2E-043 — Contract draft generation remains non-binding

Open a product/supplier card with supplier conversation history, select the `Договоры` tab, and request a contract draft.

Expected:

* a contract draft is created through WebUI/API;
* generation is processed by the real Agent Worker and configured `ModelProvider`;
* contract records are stored in the separate contracts PostgreSQL database configured by `CONTRACTS_DATABASE_URL`;
* the draft appears on the supplier/product card;
* ready drafts expose a download button;
* queued, running, and failed drafts do not expose an enabled download button;
* the downloaded file contains a visible draft marker;
* the downloaded file does not contain order confirmation, purchase confirmation, signatures, payment instructions, payment data, or legally binding commitment language.
