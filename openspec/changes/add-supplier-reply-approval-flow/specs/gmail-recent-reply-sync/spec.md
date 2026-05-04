## ADDED Requirements

### Requirement: Gmail Sync Must Prioritize Recent Inbox Messages

Gmail inbound sync MUST inspect the most recent inbox messages first when applying the configured sync limit.

#### Scenario: Inbox contains more messages than the sync limit

- GIVEN Gmail returns message IDs in ascending order
- WHEN the connector fetches messages with a limit
- THEN it SHALL fetch the newest IDs first
- AND recent supplier replies SHALL be eligible for reconciliation
