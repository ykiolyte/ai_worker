## Why

Users need a stronger way to steer supplier communication without every AI
interaction becoming an outbound supplier message. Product detail should include
an internal AI chat for analysis, next-step planning, risk review, and draft
support.

## What Changes

- Add an internal product assistant endpoint that uses product, contacts,
  extracted terms, and conversation history as context.
- Keep assistant responses separate from supplier conversation history and
  outbound sending.
- Add a WebUI assistant panel with quick prompts and a free-form input.

## Impact

- Backend API: new `POST /api/products/{product_id}/assistant-chat`.
- Frontend: product detail page gains internal AI Assistant chat.
- Tests: API and frontend contracts.
