## Why

The MVP now has the right workflows, but the presentation needs a faster, chat-like interface for demos and daily use. Users should move between search requests like conversations, see agent activity as system messages, and work with product cards as message attachments.

## What Changes

- Add a two-column messenger-style shell with a real search-request sidebar.
- Restyle search requests, catalog cards, product details, and supplier history as chat-like panels and bubbles.
- Add light and dark theme tokens without using third-party brand names, logos, or protected assets.
- Add accessible focus states, disabled states, labels, keyboard-friendly controls, and subtle micro-interactions.
- Keep existing APIs and real backend data; do not introduce mock data.

## Impact

- Frontend shell, pages, and CSS.
- Frontend contract tests for the new layout and accessibility hooks.
- No backend contract changes.
