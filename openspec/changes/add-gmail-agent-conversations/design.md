## Context

The MVP already has `ContactAttempt`, `SupplierContact`, and an `SmtpEmailConnector`. The missing piece is a durable message timeline that lets the user see what the agent actually sent. Gmail can be supported through SMTP with an app password, which preserves the current connector abstraction and avoids a larger OAuth/Gmail API flow in this change.

## Decisions

### Decision 1: Gmail Uses SMTP Provider

Use the existing SMTP connector with Gmail-specific env configuration:

- `EMAIL_CONNECTOR_PROVIDER=smtp`
- `EMAIL_SMTP_HOST=smtp.gmail.com`
- `EMAIL_SMTP_PORT=587`
- `EMAIL_SMTP_USER=<gmail address>`
- `EMAIL_SMTP_PASSWORD=<gmail app password>`
- `EMAIL_FROM=<gmail address>`
- `EMAIL_USE_TLS=true`
- `EMAIL_USE_SSL=false`

Rationale: Gmail SMTP app-password auth is enough for initial outbound supplier messages and fits the current connector contract.

### Decision 2: Persist Conversation Messages Separately

Add `ConversationMessage` records linked to product/contact attempt/contact. The contact attempt remains the task lifecycle record; conversation messages are the human-readable communication timeline.

Rationale: a single attempt can have an outbound message and later inbound messages without overloading `ContactAttempt.message_text`.

### Decision 3: Outbound Only In This Slice

This change stores outbound agent messages sent through Gmail. It does not implement Gmail inbox sync or automatic reply handling.

Rationale: reply ingestion requires OAuth or IMAP polling, identity matching, and extra safety policy. The user can already see outbound communication after pressing "Начать общение"; inbound sync can be a later change.

### Decision 4: Async Boundary Is Preserved

The WebUI button creates an API request and returns a queued attempt. The worker sends the Gmail message and persists the conversation message when it succeeds or fails.

Rationale: supplier communication is external IO and must not block the HTTP request.

## Data Shape

`ConversationMessage`:

- `id`
- `product_id`
- `contact_attempt_id`
- `supplier_contact_id`
- `direction`: `outbound` or `inbound`
- `channel`: `email` or `telegram`
- `subject`
- `body`
- `from_address`
- `to_address`
- `status`: `queued`, `sent`, `failed`, `received`
- `external_message_id`
- `error_message`
- timestamps

## Verification

- Unit tests cover conversation message validation and repository listing.
- Worker tests cover outbound Gmail/SMTP success and failure persistence.
- API tests cover product detail response including conversation messages.
- Frontend build and frontend contract tests cover "Начать общение" and visible timeline.
- Existing OpenSpec validations and full unit suite must remain green.
