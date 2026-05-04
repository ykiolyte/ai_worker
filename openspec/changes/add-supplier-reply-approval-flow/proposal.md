## Why

Supplier replies are still not reliably appearing in product conversations because Gmail sync can inspect older inbox messages before recent replies. Users also need a controlled way for the agent to continue supplier dialogue: automatic replies only when the answer is safe and clear, otherwise the UI should notify the user and ask for approval.

## What Changes

- Fetch the most recent Gmail inbox messages first during inbound sync.
- Mark inbound supplier questions that need user approval.
- Auto-answer only narrow, high-confidence supplier questions using product data already known to the system.
- Add a visible "Продолжить общение" action for supplier questions that require user approval.

## Capabilities

### New Capabilities

- `supplier-reply-approval-flow`: Supplier inbound questions are classified into safe auto-reply or user-approval-required paths.
- `gmail-recent-reply-sync`: Gmail inbound sync prioritizes recent inbox messages so fresh supplier replies appear in product conversations.

### Modified Capabilities

- None.

## Impact

- Backend Gmail connector ordering and inbound sync worker.
- Conversation message serialization and frontend product detail dialogue.
- No autonomous purchasing, commitments, payments, or order confirmation.
