## Why

Supplier searches can remain queued in local/dev runs when environment flags from `.env` are not loaded into the backend process, and the dedicated worker process does not currently process durable tasks. Search also spends too much time visiting candidate pages sequentially, even when search API results are enough to rank likely suppliers.

## What Changes

- Load local `.env` settings before constructing backend settings so `AUTO_PROCESS_SEARCH_TASKS` and search configuration apply consistently.
- Add a real dev/local worker loop that can process queued product search, supplier contact, and contract draft tasks when sharing the in-memory repository.
- Optimize supplier search without removing the current browser extraction implementation:
  - prefer web-search JSON/API candidate discovery before browser page extraction in `ai_internet` mode;
  - rank and deduplicate candidates before browser work;
  - stop extracting once enough valid products have been found;
  - avoid slow contact-page enrichment unless configured or needed;
  - keep existing browser/page extraction as the quality-preserving fallback.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-orchestration`: queued search tasks must be processed reliably in local/dev execution.
- `wide-web-product-search`: internet supplier search must use bounded, ranked, early-stopping candidate extraction for materially faster results without removing current search behavior.

## Impact

- Backend settings initialization.
- Worker runtime loop.
- Browser/search connector candidate extraction and defaults.
- Tests for `.env` loading, worker task processing, early stop, and no regression in existing connector behavior.
