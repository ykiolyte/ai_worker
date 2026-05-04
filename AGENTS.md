# Agent Instructions

## Sources Of Truth

- Product and architecture requirements: `Main.md`.
- Acceptance and verification protocol: `test_protocol.md`.
- OpenSpec project context: `openspec/project.md` and `openspec/config.yaml`.
- First change: `openspec/changes/add-product-sourcing-mvp/`.

If these sources conflict, stop and update OpenSpec artifacts before coding.

## Required Workflow

Use the local OpenSpec skills in `.codex/skills` for change work:

- Explore unclear requirements before proposing implementation.
- Keep change artifacts in `openspec/changes/<change-id>/`.
- Implement with the apply workflow.
- Verify against OpenSpec specs, tasks, and `test_protocol.md`.
- Archive only after implementation and verification are complete.

On Windows, prefer `openspec.cmd` for CLI commands.

## TDD Rules

- Write or update a failing automated test before production code whenever the
  behavior is automatable.
- Make the smallest production change that passes the test.
- Refactor only while tests are green.
- Keep tests mapped to OpenSpec requirements and TC-E2E cases where relevant.
- Mark OpenSpec tasks complete only after the related tests pass.

## E2E Rules

The final E2E protocol must use real components:

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

Do not satisfy E2E by using mock connectors, fake workers, manual DB insertion,
disabled queues, pre-baked LLM output, static UI data, in-memory databases, or
pseudo message sending.

## Product Boundaries

The MVP must not include autonomous purchasing, order confirmation, payments,
advanced CRM, mass messaging, supplier scoring, ERP/1C integration, exports, or
long-running negotiation automation.

Supplier messages must ask for information only. They must not confirm an order,
promise payment, transmit payment data, or create legal commitments.

