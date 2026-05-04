## Context

The system already sends email via SMTP and stores conversation messages. The
missing piece is inbound Gmail ingestion.

## Decisions

### Decision 1: Use Gmail IMAP With App Password

Use standard IMAP over SSL with Gmail app-password credentials. This avoids a
larger OAuth/Gmail API implementation while preserving connector boundaries.

### Decision 2: Match By Supplier Email Address

Each inbound email is matched to existing `SupplierContact` records where
`contact_type=email` and `contact_value` equals the email sender. If multiple
products share that contact, each matching product can receive the message.

### Decision 3: Deduplicate By External Message ID

The sync stores `external_message_id` on `ConversationMessage` and skips any
message that has already been stored.

### Decision 4: WebUI-Initiated Automatic Sync

The product detail page calls the sync endpoint before fetching product detail.
This avoids requiring a dedicated scheduler in the current local MVP while still
removing manual message entry from the user's workflow.

## Verification

- Connector tests cover IMAP parsing and secret redaction.
- Sync worker tests cover matching, persistence, and deduplication.
- API tests cover sync endpoint behavior.
- Frontend contract tests cover automatic sync call on product load.
