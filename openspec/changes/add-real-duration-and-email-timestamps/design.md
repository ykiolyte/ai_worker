## Design

### Search Duration

Search request duration is derived from `started_at` and `completed_at`. For active searches the API returns elapsed time from `started_at` or `created_at` to the current server time. This avoids storing redundant duration state.

### Email Provider Time

Conversation messages get a nullable `provider_timestamp` field. For Gmail inbound messages it is parsed from the RFC 5322 `Date` header. For outbound SMTP messages the connector sets a `Date` header on the message and returns that same timestamp in `ConnectorResult.payload.providerTimestamp`.

The UI labels this as email time. If provider time is unavailable, it explicitly says that email time is unavailable instead of pretending app storage time is Gmail time.

### Persistence

The in-memory domain is updated immediately. A migration adds nullable `provider_timestamp` to `conversation_messages` so the schema remains aligned.
