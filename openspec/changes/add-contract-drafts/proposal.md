## Why

After supplier conversations, users need a controlled way to turn collected commercial and legal information into a downloadable contract draft without copying messages into external documents. The feature must keep the MVP safety boundary: the AI may draft and structure text, but must not sign, approve, confirm an order, promise payment, or create a binding commitment.

## What Changes

- Add contract draft generation from an existing supplier conversation and product card.
- Extract contract-relevant fields from supplier messages using the configured `ModelProvider`, then validate the structured result before persistence.
- Store contract drafts in a separate contracts database connection/schema to avoid mixing contract records with sourcing records.
- Expose backend API endpoints to create, list, retrieve, and download contract draft files.
- Add a "Contracts" tab to each supplier/product card showing existing drafts for that supplier and a generate/download action.
- Add safety validation so generated drafts are clearly marked as drafts and do not include signatures, payment instructions, autonomous order confirmation, or legal commitment language.

## Capabilities

### New Capabilities

- `contract-drafts`: Generate, persist, list, and download AI-created supplier contract drafts from validated conversation data while preserving MVP non-goals.

### Modified Capabilities

- None.

## Impact

- Backend domain, repository, API, worker orchestration, and configuration for a separate contracts database URL/session.
- Agent prompt and structured-output validation for contract data extraction and draft generation.
- Frontend API client, product/supplier detail UI, and routing/tab state.
- Tests for domain validation, API behavior, worker behavior, download responses, and UI visibility.
- `docker-compose.yml` and environment documentation for the contracts database service/configuration.
