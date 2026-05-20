## Decision

Keep the existing worker processing functions as the single source of behavior
for product search, supplier contact, and contract draft tasks. The worker entry
point should build the normal runtime and repeatedly call the shared task tick
instead of idling.

## Approach

- Add a runnable worker loop that initializes `Settings`, `InMemoryRepository`,
  and `AgentRuntime` the same way the API does.
- Keep `run_worker_tick` available for deterministic tests.
- Ensure a supplier contact task processed by the worker transitions from
  `queued` to `sent` and persists the outbound conversation message.
- Keep connector errors redacted and stored on both the attempt and task.

## Non-Goals

- Introducing a new queue backend in this fix.
- Replacing SMTP, IMAP, or Telegram connectors.
- Changing the supplier message template or safety policy.
