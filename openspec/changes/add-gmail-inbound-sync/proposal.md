## Why

Users should not have to manually paste supplier replies into the WebUI. Once
Gmail is configured, inbound supplier emails should be read automatically and
saved into the existing product conversation timeline.

## What Changes

- Add a Gmail IMAP inbound connector.
- Match inbound emails to supplier contacts by sender email address.
- Deduplicate inbound messages by external email/message id.
- Expose a backend sync endpoint that reads Gmail and stores received messages.
- Trigger Gmail sync automatically from the product details page before loading
  the conversation timeline.

## Impact

- Backend config and connector layer gain Gmail IMAP settings.
- Backend API gains `POST /api/conversations/sync-gmail`.
- Frontend calls Gmail sync automatically on product detail load.
- Docs/env describe Gmail IMAP setup alongside SMTP sending.
