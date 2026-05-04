# Гайд по запуску и перезапуску проекта

Этот проект можно запускать двумя способами: через Docker Compose или локально
скриптом `scripts/start-local.ps1`. Для демонстрации с WebUI, backend, worker,
Browser MCP, Postgres, Redis, Ollama и Gmail удобнее использовать Docker Compose.

## Быстрый запуск через Docker

Из корня проекта:

```powershell
cd D:\AI_agent
docker compose up --build -d
```

После запуска проверьте:

```powershell
docker compose ps
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5173/ -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8088/ -UseBasicParsing
```

Ожидаемые адреса:

- WebUI: `http://localhost:5173/`
- Backend health: `http://localhost:8000/health`
- Supplier test site: `http://localhost:8088/`
- Mailpit demo mailbox: `http://localhost:8025/`
- Browser MCP: `http://localhost:8931/`
- SearXNG: `http://localhost:8888/`
- Ollama: `http://localhost:11434/`

## Обычный перезапуск

Когда код не менялся:

```powershell
cd D:\AI_agent
docker compose restart backend worker webui
```

Когда менялся backend, worker, frontend или `docker-compose.yml`:

```powershell
cd D:\AI_agent
docker compose up --build -d
```

Когда Docker показывает старый дизайн WebUI, почти всегда нужен rebuild:

```powershell
cd D:\AI_agent
docker compose up --build -d webui
```

Если всё ещё виден старый UI, очистите браузерный cache или откройте WebUI в
инкогнито. Vite-контейнер пересобирает `frontend/src` в image, поэтому простой
`docker compose restart webui` не подтягивает изменения файлов.

## Жёсткий перезапуск без удаления базы

Эта команда останавливает контейнеры и поднимает их заново, но сохраняет
PostgreSQL volume:

```powershell
cd D:\AI_agent
docker compose down
docker compose up --build -d
```

Не используйте `docker compose down -v`, если хотите сохранить данные.

## Если порты заняты

После локального запуска могут остаться процессы на портах `5173`, `8000`,
`8088` или `8931`. Найти их:

```powershell
netstat -ano | Select-String ':5173|:8000|:8088|:8931'
```

Посмотреть процессы:

```powershell
Get-Process -Id <PID>
```

Если это старые процессы проекта (`python -m uvicorn`, `python -m http.server`,
`vite`, `@playwright/mcp`), остановить:

```powershell
Stop-Process -Id <PID> -Force
```

Потом снова:

```powershell
docker compose up --build -d
```

## Gmail replies в Docker

Для Gmail в `.env` должны быть заполнены:

```env
EMAIL_CONNECTOR_PROVIDER=smtp
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=<gmail-address>
EMAIL_SMTP_PASSWORD=<gmail-app-password>
EMAIL_FROM=<gmail-address>
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false

EMAIL_INBOUND_PROVIDER=gmail_imap
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_USER=<gmail-address>
EMAIL_IMAP_PASSWORD=<gmail-app-password>
EMAIL_IMAP_MAILBOX=INBOX
EMAIL_INBOUND_SYNC_LIMIT=20
```

Важно: `EMAIL_SMTP_PASSWORD` и `EMAIL_IMAP_PASSWORD` должны быть Gmail App
Password, а не обычным паролем аккаунта.

Проверить, что Docker реально видит Gmail, а не Mailpit:

```powershell
docker compose exec -T backend python -c "import os; print(os.environ.get('EMAIL_SMTP_HOST')); print(os.environ.get('EMAIL_FROM')); print(os.environ.get('EMAIL_INBOUND_PROVIDER'))"
```

Ожидаемо для Gmail:

```text
smtp.gmail.com
<ваш gmail>
gmail_imap
```

Если хотите принудительно оставить Docker в Mailpit-demo режиме, задайте в
`.env`:

```env
DOCKER_EMAIL_SMTP_HOST=mailpit
DOCKER_EMAIL_SMTP_PORT=1025
DOCKER_EMAIL_SMTP_USER=
DOCKER_EMAIL_SMTP_PASSWORD=
DOCKER_EMAIL_FROM=product-sourcing-agent@example.test
DOCKER_EMAIL_USE_TLS=false
DOCKER_EMAIL_USE_SSL=false
```

## Проверка ответа на входящее Gmail-сообщение

1. Откройте WebUI: `http://localhost:5173/`.
2. Откройте карточку продукта, где уже был отправлен supplier contact.
3. Держите backend запущенным: если Gmail inbound настроен, backend
   периодически синхронизирует Gmail и автоматически отправляет ответ ИИ на
   сопоставленное письмо поставщика.
4. Открытие карточки товара также делает best-effort sync через
   `POST /api/conversations/sync-gmail`.
5. Если supplier reply найден, он появится в истории переписки, а ответ агента
   будет отправлен через SMTP Gmail.

Важно: текущий MVP хранит состояние переписки в памяти backend-процесса. После
`docker compose up --build -d` старые карточки и связи с Gmail-письмами могут
сброситься; для проверки после rebuild создайте карточку/первое письмо заново.

Ручная проверка endpoint:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/conversations/sync-gmail -Method POST -UseBasicParsing
```

## Логи

```powershell
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f webui
docker compose logs -f browser-mcp
```

Для последней сотни строк:

```powershell
docker compose logs --tail=100 backend worker
```

## Локальный запуск без Docker

Если Docker Desktop не нужен:

```powershell
cd D:\AI_agent
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

Этот способ поднимает backend, supplier test site и frontend отдельными
скрытыми PowerShell-процессами. Для Docker-запуска перед этим способом лучше
остановить старые локальные процессы на портах `5173`, `8000`, `8088`, `8931`.

## Минимальная диагностика после перезагрузки ПК

```powershell
cd D:\AI_agent
docker compose ps
netstat -ano | Select-String ':5173|:8000|:8088|:8931'
docker compose up --build -d
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

Если `docker compose up --build -d` сообщает, что порт занят, остановите старый
локальный процесс на этом порту и повторите команду.
