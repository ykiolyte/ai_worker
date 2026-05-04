## ADDED Requirements

### Requirement: Search Requests Must Expose Actual Duration

The API MUST expose the actual elapsed product-search duration in seconds for each search request.

#### Scenario: Completed search request

- GIVEN a search request has started and completed timestamps
- WHEN the API serializes the request
- THEN it SHALL include duration seconds derived from those timestamps

### Requirement: Gmail Message Time Must Be Stored Separately

Conversation messages MUST store a nullable provider timestamp that represents email-provider message time when available.

#### Scenario: Gmail reply is synced

- GIVEN Gmail IMAP returns a message with a Date header
- WHEN the message is stored as inbound conversation history
- THEN the stored conversation message SHALL include that provider timestamp

### Requirement: WebUI Must Display Duration And Email Time

The WebUI MUST show actual search duration and provider email timestamps where available.

#### Scenario: User views a supplier dialogue

- GIVEN a conversation message has provider timestamp
- WHEN the message bubble renders
- THEN it SHALL show the email timestamp distinct from app-created time
