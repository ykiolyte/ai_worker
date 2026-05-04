## ADDED Requirements

### Requirement: Gmail Replies Must Match Existing Conversation Threads

Gmail inbound sync MUST match replies to existing product conversations by email reply headers when available.

#### Scenario: Reply sender does not exactly match supplier contact

- GIVEN an outbound conversation message has an external message ID
- AND Gmail returns an inbound reply with `In-Reply-To` or `References` containing that ID
- WHEN Gmail sync runs
- THEN the inbound reply SHALL be stored on the same product conversation

### Requirement: Gmail Sync Should Include Recently Read Replies

Gmail inbound sync MUST inspect recent inbox messages, not only unread messages, so replies opened in Gmail can still be reconciled.

#### Scenario: User opened the reply in Gmail

- GIVEN a supplier reply is already read in Gmail
- WHEN Gmail sync runs
- THEN the system can still process the reply if it is within the configured sync limit and not already stored
