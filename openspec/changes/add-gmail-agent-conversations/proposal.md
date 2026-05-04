## Why

Supplier contact currently creates a one-off contact attempt, but the user needs the agent to initiate real supplier communication through Gmail and keep the resulting messages visible in the product UI. This turns contact attempts into an inspectable conversation record without expanding the MVP into autonomous negotiation.

## What Changes

- Add Gmail-backed email sending through the existing email connector abstraction.
- Persist outbound supplier messages as conversation messages linked to the contact attempt and product.
- Expose conversation messages through product detail API responses.
- Rename the product action in WebUI to "Начать общение" and show the saved conversation timeline.
- Keep the existing async worker boundary: the button creates a supplier-contact task; the worker sends through Gmail/SMTP and records the result.
- Keep MVP safety boundaries: no autonomous purchase, no automatic follow-up negotiation, no mass messaging.

## Capabilities

### New Capabilities
- `gmail-agent-conversations`: Gmail SMTP configuration, outbound supplier message persistence, and product-level conversation visibility.

### Modified Capabilities
- `supplier-contact`: The supplier contact action now starts a visible conversation record, not only a status-only contact attempt.
- `webui`: Product details expose a "Начать общение" action and show saved messages.

## Impact

- Backend domain: add conversation message entity and serialization.
- Backend repository: store and list conversation messages.
- Worker: save outbound message content, subject, recipients, provider message id, status, and errors.
- Connectors/config: document Gmail SMTP settings and keep secrets in env only.
- Frontend: update types, API rendering, button copy, and conversation timeline.
- Tests: add domain/API/worker/frontend contracts for Gmail conversation behavior.
