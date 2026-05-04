# Testing

Development follows red, green, refactor:

1. red: add or update a failing test for the OpenSpec task.
2. green: implement the smallest production change that passes.
3. refactor: clean up only while tests stay green.

## Local Test Commands

```powershell
python -m unittest discover -s tests
python scripts/verify_traceability.py
openspec.cmd validate add-product-sourcing-mvp --strict --no-interactive
```

## Test Layers

- Unit tests: validation, status transitions, message policy, structured output.
- API tests: ASGI-level endpoint contracts.
- Worker tests: lifecycle and connector-boundary behavior.
- Frontend contract tests: loading, empty, error, and prohibited action states.
- Smoke tests: local end-to-end flow with in-process services and fake
  connector boundaries.
- Production-like E2E: full `test_protocol.md` with real services and
  controlled test resources.

## Connector Checks

The MVP connector contracts are covered by `tests/test_connectors_contract.py`.
Those tests verify:

- Playwright MCP tool calls through the browser connector boundary.
- Browser URL allowlist enforcement.
- Structured product output returned from MCP extraction.
- SMTP message sending through `SmtpEmailConnector`.
- Telegram Bot API message sending through `TelegramBotConnector`.
- SMTP secret redaction from connector errors.
- Telegram token redaction from connector errors.

For production-like E2E, run `docker compose up --build`, then:

```powershell
python scripts/e2e_preflight.py
```

For a local product-search-only check, the default `.env` placeholders are
acceptable. They let the WebUI/API run and let Browser MCP extract products
from the controlled supplier site. Replace placeholder Telegram and
`local_demo` model values before recording the final acceptance report.

Mailpit at `http://localhost:8025` is the local controlled mailbox used by the
SMTP connector. It is acceptable for local E2E because the system performs a
real SMTP send; it must not be replaced with a fake send function.

## E2E Restrictions

The `test_protocol.md` acceptance run must not use mock connectors, fake worker,
manual database insertion, disabled queues, pre-baked LLM output, static UI data,
in-memory databases, or pseudo email/Telegram sending.
