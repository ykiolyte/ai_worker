## Why

Supplier messages can remain queued and never reach the email or Telegram
connector when the project relies on the standalone worker process. The worker
entry point currently idles instead of processing queued `agent_task` records,
so supplier contact attempts may appear created in the UI while no outbound
message is sent or received by the supplier mailbox.

## What Changes

- Make the standalone worker execute queued supplier contact tasks through the
  existing task processors.
- Preserve the current API-triggered background processing behavior.
- Add regression coverage for worker-driven supplier message delivery and
  visible failure handling.

## Impact

- Restores supplier outreach and AI follow-up sending when the worker process is
  used.
- Reduces the risk of stuck `queued`/`running` contact attempts.
- Does not expand MVP boundaries: messages still ask for supplier information
  only and continue to pass `SafeMessagePolicy`.
