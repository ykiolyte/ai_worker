## Overview

`MultiEngineWebSearchConnector.search()` currently calls each engine directly. Any exception from one engine bubbles up to `AiInternetProductSearchConnector.research()`, which marks the whole product-search task as failed.

The fix keeps multi-engine search best-effort across engines. Each engine call is isolated. Successful results are merged and deduplicated as before. If all engines fail, the connector raises a concise aggregate error so the product-search task still records a useful failure.

## Decisions

- Preserve existing deduplication by normalized URL.
- Do not expose search-engine operational errors in frontend-specific UI in this change.
- Avoid adding a logging framework change; this is a connector behavior fix.

## Verification

- Add a connector contract test proving a failed engine does not discard results from a healthy engine.
- Run focused connector tests and full Python tests.
- Validate this OpenSpec change.
