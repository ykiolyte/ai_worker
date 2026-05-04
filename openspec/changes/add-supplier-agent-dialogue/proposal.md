## Why

The current supplier communication flow sends and displays the first outbound
message, but it does not let the user continue the conversation when a supplier
answers. Users need the AI agent to keep asking follow-up sourcing questions
inside the same product conversation while staying inside the MVP safety
boundary.

## What Changes

- Add support for recording inbound supplier messages on a product.
- Add an agent reply action that uses the existing `ModelProvider`, conversation
  history, and email/Telegram connector to send a follow-up message.
- Persist every inbound and outbound message in the existing conversation
  timeline.
- Keep replies user-initiated from the product page; no autonomous long-running
  negotiation loop is added.
- Keep supplier messages limited to information requests. Replies must not
  confirm orders, promise payment, send payment data, or create commitments.

## Impact

- Backend domain: inbound conversation message factory.
- Backend worker: supplier-contact tasks can generate a follow-up reply from
  conversation history.
- Backend API: endpoints to record inbound supplier messages and request an
  agent reply.
- Frontend: product details page exposes inbound-message capture and
  user-triggered agent reply controls.
- Docs: explain Gmail/SMTP/Telegram setup and the operational steps required for
  supplier correspondence.
