## Why

Users now rely on Gmail replies and long-running product searches, but the UI still requires manual refreshes and product details can feel slow because Gmail sync runs before the product is displayed. Supplier outreach also needs language and tone controls because suppliers may prefer Chinese, English, or Russian and messages should not all look identical.

## What Changes

- Add soft auto-refresh for search requests, product catalogs, and product details while work is in progress.
- Show an approximate progress bar/time hint for queued/running searches.
- Load product details before optional Gmail sync, then refresh the conversation timeline after sync completes.
- Improve Gmail reply matching using email reply headers in addition to supplier sender addresses.
- Let users select supplier communication language: Chinese, English, or Russian.
- Let users select supplier communication style: concise, formal, or friendly.

## Capabilities

### New Capabilities

- `live-ui-refresh`: WebUI refreshes active searches and contact/dialogue state without a manual browser refresh.
- `supplier-message-preferences`: Users can select language and communication style for supplier messages.
- `gmail-reply-reconciliation`: Gmail replies are reconciled to product conversations using reply headers and recent messages.

### Modified Capabilities

- None.

## Impact

- Frontend search list, catalog, product detail UI, API client, and styles.
- Backend supplier contact payloads, agent message generation, worker task payloads, and Gmail inbound connector parsing.
- No autonomous purchasing, payment, mass messaging, or binding negotiation is introduced.
