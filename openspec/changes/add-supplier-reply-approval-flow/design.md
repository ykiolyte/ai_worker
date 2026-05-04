## Overview

Gmail IMAP `ALL` returns IDs in ascending order for most servers. The connector should reverse IDs and process the newest messages first. This makes recent supplier replies visible without increasing sync limits dramatically.

Inbound messages are classified after they are matched to a product. If the supplier asks a simple product-identification question that can be answered from the existing product title and URL, the worker can send a safe reply. Otherwise the message is marked as requiring user approval and the frontend shows a continue action.

## Decisions

- Keep the first auto-reply scope intentionally narrow: product/link clarification only.
- Use existing `conversation-reply` endpoint for user-approved continuation.
- Store approval state on `ConversationMessage` so the UI can highlight supplier questions.
- Keep Gmail sync best-effort and idempotent by external message ID.

## Verification

- Connector test proves recent Gmail IDs are fetched first.
- Worker tests prove approval classification and safe auto-reply behavior.
- API/frontend tests prove approval state is serialized and the continue button is available.
