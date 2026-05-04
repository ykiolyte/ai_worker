# One-Click Local Deployment

This guide is for a Windows workstation where the project should start with as
little manual setup as possible.

## Minimum Prerequisites

- Windows 10/11.
- Docker Desktop installed and started once.
- Git installed, or the repository downloaded as a ZIP.
- Enough disk space for Docker images and the local AI model. The default model
  is `mistral-nemo:12b`.

Repository URL:

```text
https://github.com/ykiolyte/ai_worker.git
```

## First Start On A New Workstation

```powershell
git clone https://github.com/ykiolyte/ai_worker.git
cd ai_worker
```

Then double-click:

```text
START_PROJECT.cmd
```

The launcher runs `scripts/bootstrap-workstation.ps1`. It will:

- create `.env` from `.env.example` if `.env` is missing;
- keep an existing `.env` and preserve secrets;
- configure local Ollama defaults for first run;
- install/start portable Ollama under `.tools` when needed;
- pull `mistral-nemo:12b` unless another model is configured;
- run `docker compose up --build -d`;
- wait for `http://127.0.0.1:8000/health` and `http://127.0.0.1:5173`;
- open WebUI at `http://127.0.0.1:5173`.

## Regular Start

Double-click:

```text
START_PROJECT.cmd
```

Or run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap-workstation.ps1
```

To use another local Ollama model:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap-workstation.ps1 -ModelName qwen2.5:14b
```

To test the flow without changing files, downloading models, or starting
services:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap-workstation.ps1 -DryRun
```

## Stop

Double-click:

```text
STOP_PROJECT.cmd
```

Or run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-project.ps1
```

This runs `docker compose down` without `-v`, so PostgreSQL data and Ollama data
are preserved.

## Update Existing Checkout

```powershell
git pull
START_PROJECT.cmd
```

The start script rebuilds Docker images with:

```powershell
docker compose up --build -d
```

## Demo Mail And Real Secrets

By default the local stack uses Mailpit for demo SMTP:

```text
http://127.0.0.1:8025
```

For real Gmail replies, edit local `.env` only:

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
EMAIL_IMAP_USER=<gmail-address>
EMAIL_IMAP_PASSWORD=<gmail-app-password>
EMAIL_IMAP_MAILBOX=INBOX
```

For Telegram, also set:

```env
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_CHAT_ID=<chat-id>
```

Never commit `.env`. The launch scripts do not write Gmail, Telegram, SMTP,
IMAP, or model API secrets into the repository.

## Diagnostics

Check services:

```powershell
docker compose ps
```

Check logs:

```powershell
docker compose logs --tail=100 backend worker webui
docker compose logs -f backend
```

Common URLs:

- WebUI: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/health`
- Mailpit: `http://127.0.0.1:8025`
- Supplier test site: `http://127.0.0.1:8088`
- SearXNG: `http://127.0.0.1:8888`
- Ollama: `http://127.0.0.1:11434`
