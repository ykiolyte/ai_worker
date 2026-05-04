## Overview

The worker is the right insertion point because it already owns product persistence and deduplication for search results. After normal validated products are stored and capped by `maxResults`, the worker appends a deterministic demo product with a stable URL based on the search request ID.

The demo product is not part of external browser research and is intentionally marked as a demo supplier card in its title/attributes/source domain.

## Decisions

- Use `ezmmr4us@gmail.com` as the supplier email contact exactly as requested.
- Add the demo card beyond `maxResults`, because the request says it should be additional.
- Deduplicate by a stable `productUrl` per search request.

## Verification

- Worker contract tests prove every processed search gets the demo card.
- Worker tests prove `maxResults` still caps real products while the demo card is extra.
- Full test suite verifies existing contact supplier flow works with the demo card.
