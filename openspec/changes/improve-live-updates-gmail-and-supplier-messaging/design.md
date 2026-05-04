## Overview

The UI should keep the user oriented during asynchronous search and supplier communication. Polling is sufficient for this MVP because the backend already exposes current status through existing endpoints.

Gmail sync should be best-effort and non-blocking for the product card. Product details load first; then the page can sync Gmail in the background and reload details if new messages were created.

Supplier message customization is implemented as request-level preferences passed into the supplier-contact task. The worker generates the actual message using safe templates and keeps the existing safety policy.

## Decisions

- Use interval polling in the frontend instead of introducing WebSockets/SSE.
- Show approximate progress based on status and elapsed time, capped below completion until the backend reports a terminal state.
- Extend `InboundEmailMessage` with `in_reply_to` and `references` so replies can match outbound conversation message IDs even when sender matching is imperfect.
- Generate first-contact messages from deterministic templates for Russian, English, and Chinese, with concise/formal/friendly variants.
- Pass language/style to agent replies as well, so follow-up messages use the selected communication preference.

## Verification

- Frontend contract tests cover polling, progress UI, non-blocking Gmail sync, and message preference controls.
- API/worker tests cover language/style payload propagation and message generation.
- Gmail sync tests cover reply-header matching.
- Full Python tests and frontend build verify integration.
