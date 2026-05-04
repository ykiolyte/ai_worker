## Overview

The product details page currently awaits `syncGmailInbound()` inside the same `try` block as `getProduct(productId)`. That makes optional conversation refresh a blocking dependency for the core product details view.

The fix is to isolate Gmail sync errors from product loading. The page should attempt sync, ignore/log non-fatal sync failures, and always continue to `getProduct(productId)`.

## Decisions

- Keep automatic sync before product fetch so successful sync results can appear immediately in the conversation timeline.
- Treat sync failure as non-fatal for the product detail page.
- Do not add a visible blocking error for sync failure in this bugfix; the user's reported regression is that the product card cannot open.

## Verification

- Frontend contract test verifies `syncGmailInbound()` failure is handled before `getProduct(productId)` is awaited.
- Existing API and worker tests continue to cover Gmail sync behavior itself.
- Build verification ensures TypeScript accepts the change.
