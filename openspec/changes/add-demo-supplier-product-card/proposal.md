## Why

Live supplier sites can return access denied or unstable search results during a stakeholder demo. The project needs a reliable built-in demo product card so the user can demonstrate supplier communication end-to-end using their own mailbox.

## What Changes

- Add one deterministic demo product card to every completed product search.
- The demo card includes supplier email `ezmmr4us@gmail.com`.
- The demo card is added in addition to normal search results and does not consume the user's `maxResults` limit.
- The card is deduplicated per search request so refresh/retry does not create multiple demo cards.

## Capabilities

### New Capabilities

- `demo-supplier-product-card`: Every search result catalog includes a controlled demo product card for stakeholder presentations.

### Modified Capabilities

- None.

## Impact

- Product-search worker adds a deterministic product and supplier contact.
- API and UI use the existing product card/detail/contact flows.
- No change to autonomous purchasing boundaries.
