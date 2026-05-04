# Product Sourcing MVP

This repository is prepared for OpenSpec-driven development of an MVP service
for AI-assisted product sourcing.

Users create product search requests in WebUI. An AI agent researches suppliers
through a browser MCP connector, stores normalized product cards in PostgreSQL,
and can initiate first contact with a supplier through email or Telegram.

The MVP browser connector is Microsoft Playwright MCP. The local E2E stack also
starts Mailpit so the email path uses a real SMTP send into a controlled test
mailbox.

## One-Click Local Start

For a new Windows workstation:

1. Install Docker Desktop and start it once.
2. Clone or download the repository:

```powershell
git clone https://github.com/ykiolyte/ai_worker.git
cd ai_worker
```

3. Double-click `START_PROJECT.cmd`.

The launcher creates `.env` from `.env.example` when needed, configures the
local Ollama model (`mistral-nemo:12b` by default), downloads the model, runs
`docker compose up --build -d`, waits for Backend/WebUI readiness, and opens:

```text
http://127.0.0.1:5173
```

To stop the project without deleting PostgreSQL or model data, double-click
`STOP_PROJECT.cmd`.

Demo email uses Mailpit at `http://127.0.0.1:8025`. Real Gmail/Telegram sending
still requires local `.env` secrets such as `EMAIL_SMTP_PASSWORD`,
`EMAIL_IMAP_PASSWORD`, and `TELEGRAM_BOT_TOKEN`; the launch scripts preserve an
existing `.env` and do not commit secrets. More detail is in
`docs/one-click-deploy.md`.

## Key Files

- `Main.md`: technical assignment and product source of truth.
- `test_protocol.md`: production-like E2E acceptance protocol.
- `openspec/project.md`: project context for OpenSpec and Codex.
- `openspec/config.yaml`: OpenSpec config and workflow rules.
- `openspec/changes/add-product-sourcing-mvp/`: first MVP change.
- `AGENTS.md`: development instructions for future agent sessions.

## First Change

The first change is already prepared at:

```text
openspec/changes/add-product-sourcing-mvp/
```

It contains:

- `proposal.md`
- `design.md`
- `tasks.md`
- delta specs for search requests, product catalog, supplier contact, agent
  orchestration, WebUI, persistence, and test protocol coverage.
- `test-matrix.md` for mapping `test_protocol.md` cases to implementation work.

## Development Workflow

Use OpenSpec skills and TDD:

1. Pick a task from `openspec/changes/add-product-sourcing-mvp/tasks.md`.
2. Add or update a failing test first.
3. Implement the smallest production change.
4. Run the relevant tests.
5. Update OpenSpec artifacts if the understanding changes.
6. Keep moving outward from unit tests to integration, smoke, and production-like
   E2E verification.

On Windows:

```powershell
openspec.cmd validate add-product-sourcing-mvp --strict --no-interactive
```

Detailed restart and recovery instructions are in
`docs/restart-guide.md`.

Local E2E services:

```powershell
docker compose up --build
python scripts/e2e_preflight.py
```

The checked-in `.env.example` is runnable for a local demo: it uses placeholder
Telegram values and `MODEL_PROVIDER=local_demo`,
`MODEL_NAME=browser-extraction-v0`. That is enough to create a search request
and let Browser MCP extract products from the controlled supplier site. Real
Telegram and model provider values are still required before the final
`test_protocol.md` acceptance run.

Wide public-web AI product search can be enabled by setting:

```env
MODEL_PROVIDER=ollama
MODEL_NAME=mistral-nemo:12b
BROWSER_RESEARCH_MODE=ai_internet
BROWSER_ALLOW_PUBLIC_INTERNET=true
WEB_SEARCH_PROVIDER=multi
WEB_SEARCH_ENGINES=duckduckgo:https://duckduckgo.com/html/,searxng:http://localhost:8888/search
WEB_SEARCH_URL=https://duckduckgo.com/html/
AI_SEARCH_CANDIDATE_LIMIT=8
ALLOW_PRODUCTS_WITHOUT_CONTACTS=true
```

This mode uses local Ollama for AI planning/ranking and a public search provider
for broad web discovery. `WEB_SEARCH_PROVIDER=multi` merges results from the
configured engines and deduplicates URLs before AI selection. Pull the local
model once:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-ollama-portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/start-ollama-local.ps1
powershell -ExecutionPolicy Bypass -File scripts/pull-local-model.ps1 -ModelName mistral-nemo:12b
```

Then start the local app, or use Docker Compose when Docker Desktop is healthy:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
docker compose up --build -d
```

In Docker Compose, backend and worker use the host Ollama runtime by default
through `DOCKER_OLLAMA_BASE_URL=http://host.docker.internal:11434`, so the model
you pulled locally is the one used for supplier messages.

## Acceptance Boundary

The MVP is ready only when it can pass `test_protocol.md`. The final E2E run must
use real services and a controlled supplier test contour. Unit and worker tests
may mock connectors, but production-like E2E may not.
