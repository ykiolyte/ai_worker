## Why

Users need to see how long product search actually took and when supplier messages were sent or received according to the email provider, not only when the app stored records.

## What Changes

- Add actual search duration to search request API responses.
- Capture provider email timestamps for outbound SMTP messages and inbound Gmail IMAP messages.
- Store and serialize provider timestamps on conversation messages.
- Display search duration and message email timestamps in the WebUI.

## Impact

- Backend domain and serialization.
- SMTP and Gmail IMAP connectors.
- Frontend types, formatting helpers, and pages.
- Alembic migration metadata for conversation message provider timestamps.
