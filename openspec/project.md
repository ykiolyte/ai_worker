# Project Overview

## Purpose

This project is a Product Sourcing MVP. Users create product search requests in
WebUI, an AI agent researches suppliers through a browser MCP connector, the
system stores normalized product cards in PostgreSQL, and users can ask the
agent to contact suppliers through email or Telegram.

The product is intentionally controlled: the agent helps find, structure, and
initiate first contact. It must not autonomously purchase, negotiate binding
commitments, place orders, disclose secrets, or perform unauthorized actions.

## Source Of Truth

`Main.md` is the product and architecture source of truth for MVP requirements,
scope boundaries, API shape, data model, validation rules, and acceptance
criteria.

`test_protocol.md` is the verification source of truth. Development is not done
until the implementation is capable of passing the full protocol, including the
production-like E2E constraints.

Operational OpenSpec context is mirrored in `openspec/config.yaml`, because
OpenSpec 1.3.x injects that file into artifact instructions.

## MVP Scope

- Search request creation and listing.
- Search request status tracking.
- Product catalog by search request.
- Product details with supplier contacts and contact attempts.
- Contact supplier action from a product details page.
- Backend API for requests, products, statuses, and contact attempts.
- PostgreSQL persistence for core entities.
- Agent worker for product search and supplier contact tasks.
- Browser MCP, email, and Telegram connector interfaces.
- Tests, structured logging, and developer documentation needed to satisfy
  `test_protocol.md`.

## Out Of Scope

- Autonomous purchasing or order confirmation.
- Payment processing.
- Advanced CRM.
- Supplier scoring engine.
- Advanced duplicate resolution across search requests.
- Long-running negotiation automation.
- Mass messaging.
- ERP/1C integration.
- Excel/CSV export.
- Multi-tenant or advanced permission model.
- Fine-tuning.

## Architecture

The system uses a decoupled architecture:

- WebUI communicates only with Backend API.
- Backend API owns validation, persistence, and task creation.
- Agent Worker processes asynchronous tasks.
- Agent Worker uses MCP and communication connectors through explicit
  interfaces.
- PostgreSQL is the source of truth for statuses and results.
- Redis or an equivalent broker coordinates background tasks.

Long-running product research and supplier communication must not block HTTP
responses. The API creates durable records, queues work, and exposes state for
the UI to poll or refetch.

## Recommended Stack

- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL,
  Pydantic v2.
- Background jobs: Celery, RQ, Arq, or an equivalent broker-backed worker.
- Broker: Redis.
- WebUI: React + TypeScript, Vite or Next.js, TanStack Query, React Router or
  Next.js routing.
- UI kit: shadcn/ui, Ant Design, or Mantine.
- Agent worker: Python process with ModelProvider, ToolRegistry, MCP client
  layer, structured-output validation, retry policy, and audit logs.

## Domain Entities

- `SearchRequest`: user query and search lifecycle.
- `ProductCard`: normalized product data discovered by the agent.
- `SupplierContact`: supported contact channel for a product supplier.
- `ContactAttempt`: a user-requested supplier communication attempt.
- `AgentTask`: durable lifecycle record for agent work.

## Test Driven Development

All implementation work should follow red, green, refactor:

1. Start each task by adding or updating a failing test that expresses the
   relevant OpenSpec scenario.
2. Implement the smallest production change that makes the test pass.
3. Refactor only with tests green.
4. Extend outward from unit tests to integration/API tests, worker tests,
   frontend tests, smoke tests, and finally production-like E2E verification.

Unit and narrow worker tests may use mocked connectors. The E2E protocol may not
use mock connectors, fake workers, static UI data, in-memory databases,
pre-baked LLM output, or pseudo email/Telegram sending.

## OpenSpec Workflow

Development is expected to use Codex OpenSpec skills from `.codex/skills`.

The first change is:

```text
openspec/changes/add-product-sourcing-mvp/
```

Use this rhythm:

1. Create or update change artifacts in `openspec/changes/<change-id>/`.
2. Implement via the apply workflow, starting with tests.
3. Verify implementation against specs, tasks, and `test_protocol.md`.
4. Archive the completed change so canonical specs move into `openspec/specs/`.

On Windows, use `openspec.cmd` in terminal commands because `openspec.ps1` can
be blocked by PowerShell execution policy.

## Quality Gate

A change is ready to archive only after:

- `openspec.cmd validate <change-id> --strict --no-interactive` passes.
- Relevant automated tests pass.
- `test_protocol.md` coverage is updated or intentionally deferred with a
  documented reason.
- No E2E-prohibited shortcuts are used in acceptance verification.
