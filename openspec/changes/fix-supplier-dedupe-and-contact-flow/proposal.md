## Why

After search optimization, supplier results can show multiple cards from the same supplier website because deduplication only compares product URLs. Supplier communication also needs a verified end-to-end backend path so the UI action creates and processes an AI supplier message instead of leaving users with a non-working conversation.

## What Changes

- Deduplicate search results by supplier identity, not just exact product URL.
- Use supplier domain/contact domain as the primary supplier key and keep the best available card per supplier.
- Preserve skipped duplicate details in task output for traceability.
- Add API/worker coverage proving supplier contact auto-processing sends the generated AI message and persists conversation history.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `product-catalog`: search results must not display several supplier cards from the same supplier site for one request.
- `supplier-contact`: contact supplier action must process through the configured `ModelProvider` and connector when auto-processing is enabled.

## Impact

- Product search worker deduplication.
- Supplier contact API/worker regression tests.
- OpenSpec verification and full project test/build run.
