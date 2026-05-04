## Context

`add-gmail-agent-conversations` intentionally implemented outbound-only
conversation visibility. This change extends that model into a controlled
dialogue: the user records or syncs a supplier reply, then explicitly asks the
agent to answer.

## Decisions

### Decision 1: User-Initiated Reply Loop

The MVP shall not run autonomous background negotiation. The user must trigger
each agent reply from WebUI/API after reviewing the conversation state.

### Decision 2: Reuse Supplier Contact Tasks

Follow-up replies reuse `AgentTaskType.SUPPLIER_CONTACT` and `ContactAttempt`.
The task payload marks the mode as `conversation_reply`. The worker loads the
product, selected contact, contact attempt, and conversation history, generates a
safe follow-up message, then sends it through the channel connector.

### Decision 3: Inbound Capture First, Connector Sync Later

The implementation provides an API/UI path to record inbound supplier messages.
This makes the dialogue loop testable and usable immediately. Full Gmail IMAP or
Telegram update polling can be added later behind connector-specific sync jobs.

### Decision 4: Safety Gate Before Sending

Generated replies must pass `SafeMessagePolicy`. If model output is missing or
invalid, the worker uses a deterministic safe information-request fallback. If
the final message still violates policy, the task fails and no connector send is
performed.

## Verification

- Domain tests cover inbound conversation messages.
- Worker tests cover conversation-reply generation, sending, persistence, and
  policy failures.
- API tests cover inbound capture and reply task creation.
- Frontend contract tests cover the new controls and API client methods.
- OpenSpec validation and automated tests must pass.
