## ADDED Requirements

### Requirement: Process Product Search Task

The system SHALL process product search tasks asynchronously.

#### Scenario: Worker receives product search task

- GIVEN an agent task of type `product_search` exists with status `queued`
- WHEN the worker starts the task
- THEN the system SHALL update the task status to `running`
- AND the worker SHALL execute browser research through the browser MCP connector
- AND the worker SHALL write lifecycle logs with `agent_task_id` and `search_request_id`

### Requirement: Validate Agent Output

The system SHALL validate structured agent output before persisting it.

#### Scenario: Agent returns valid structured output

- GIVEN the agent returns product data matching the expected schema
- WHEN the backend validates the output
- THEN the system SHALL persist valid product cards

#### Scenario: Agent returns malformed output

- GIVEN the agent returns malformed or incomplete product data
- WHEN the backend validates the output
- THEN the system SHALL reject invalid records
- AND the system SHALL store validation errors in the agent task output

#### Scenario: Agent returns mixed valid and invalid records

- GIVEN the agent returns both valid and invalid product records
- WHEN the backend validates the output
- THEN the system SHALL persist valid records
- AND the system SHALL skip invalid records with stored validation reasons

### Requirement: Process Supplier Contact Task

The system SHALL process supplier contact tasks asynchronously.

#### Scenario: Worker receives supplier contact task

- GIVEN an agent task of type `supplier_contact` exists with status `queued`
- WHEN the worker starts the task
- THEN the system SHALL load product and supplier contact data
- AND the worker SHALL send a message using the connector matching the contact type
- AND the worker SHALL write lifecycle logs with `agent_task_id`, `product_id`, and `contact_attempt_id`

### Requirement: Store Agent Task Lifecycle

The system SHALL persist lifecycle information for every agent task.

#### Scenario: Task completes

- GIVEN an agent task is running
- WHEN the task completes successfully
- THEN the system SHALL update the task status to `completed`
- AND the system SHALL persist the output payload

#### Scenario: Task fails

- GIVEN an agent task is running
- WHEN the task fails
- THEN the system SHALL update the task status to `failed`
- AND the system SHALL persist the error message

#### Scenario: Task remains active past timeout

- GIVEN an agent task remains in `queued` or `running` past the configured timeout
- WHEN timeout recovery runs
- THEN the system SHALL move the task to a recoverable terminal state
- AND the system SHALL persist a user-readable error or recovery result
