## Overview

Contract drafts are generated as asynchronous agent work from an existing product/supplier conversation. The backend creates durable records and returns quickly; the worker loads product, supplier contact, and conversation messages, asks the configured `ModelProvider` for structured contract data, validates the result, renders a draft document, and stores it in the contracts database.

The output is a downloadable draft only. It must be visibly marked as a draft and must not contain signatures, payment data, order confirmation, or language that commits the company or supplier.

## Data Model

Use a separate contracts database connection configured by `CONTRACTS_DATABASE_URL`. For local development and tests, this may point to a second PostgreSQL database in the same server; it must not reuse sourcing tables.

Contract draft fields:

- `id`
- `product_id`
- `supplier_name`
- `supplier_contact_id`
- `status`: `queued`, `running`, `ready`, `failed`
- `title`
- `extracted_data`
- `draft_text`
- `file_name`
- `content_type`
- `error_message`
- `created_at`, `updated_at`, `completed_at`

The sourcing database remains the owner of products, contacts, conversations, contact attempts, and agent tasks. The contracts database stores only contract draft records and generated content.

## API

- `GET /api/products/{product_id}/contracts`: list contract drafts for the product supplier.
- `POST /api/products/{product_id}/contracts`: create a draft generation task and a queued contract draft.
- `GET /api/contracts/{contract_id}`: retrieve draft metadata and content preview.
- `GET /api/contracts/{contract_id}/download`: download the ready draft as a text document.

HTTP create calls must not run model generation inline. They create records and queue work through the same worker boundary as existing agent tasks.

## Agent And Validation

The worker prompt includes product details, supplier identity, conversation history, and explicit safety rules. The model must return structured JSON with parties, product, quantity if known, price if known, delivery terms, payment terms if already provided, validity dates if known, missing fields, and proposed draft text.

Validation rejects output when:

- it is not parseable as the required schema;
- it omits the draft marker;
- it includes signing, approval, order confirmation, payment instructions, bank/payment data, or commitment phrases;
- it invents required commercial/legal terms not present in the product or conversation context.

When validation fails, the draft moves to `failed` with a user-readable error.

## Frontend

The product/supplier detail page gets a `Contracts` tab next to existing supplier conversation/contact sections. The tab lists drafts with status, creation time, title, missing fields, and a download button for `ready` drafts. A generate action creates a new draft and refreshes the list.

The UI must not present the draft as signed, approved, purchased, ordered, or payable.

## Testing

Unit tests may mock `ModelProvider` and repositories. Integration/API tests verify durable create/list/download behavior and the separate contracts repository. Worker tests verify status transitions, structured extraction, file rendering, and safety rejection. Frontend tests verify that the Contracts tab lists drafts and exposes download only when ready.

Production-like E2E should extend `test_protocol.md` with a controlled supplier conversation that produces a draft through real WebUI, API, PostgreSQL contracts database, broker, worker, and configured `ModelProvider`.
