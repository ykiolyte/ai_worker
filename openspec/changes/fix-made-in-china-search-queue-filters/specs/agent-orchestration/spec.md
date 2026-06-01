## MODIFIED Requirements

### Requirement: Process Product Search Tasks

The system SHALL prevent supported product search tasks from remaining indefinitely queued.

#### Scenario: Local auto-processing starts search task

- GIVEN the API is configured with product search auto-processing enabled
- WHEN a user creates a product search request
- THEN the created AgentTask SHALL be processed by the runtime background task
- AND the linked SearchRequest SHALL transition from `queued` to either `running`, `completed`, or `failed`
- AND the task SHALL NOT remain `queued` after the background task completes

#### Scenario: Search runtime failure is persisted

- GIVEN a product search task cannot run because the provider, browser connector, model provider, or worker runtime fails
- WHEN the failure is detected
- THEN the task SHALL transition to `failed`
- AND the linked SearchRequest SHALL transition to `failed`
- AND a user-readable error SHALL be persisted

#### Scenario: Worker polling sees durable queued searches

- GIVEN a separate worker process is running
- WHEN product search AgentTask records are queued in durable storage
- THEN the worker SHALL poll or dequeue them
- AND process them through the same product search workflow as local auto-processing
