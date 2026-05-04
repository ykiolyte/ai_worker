## ADDED Requirements

### Requirement: Develop With Test Driven Workflow

Implementation work SHALL follow a test driven workflow.

#### Scenario: A task begins

- GIVEN an implementation task is selected from `tasks.md`
- WHEN the task changes observable behavior
- THEN a failing automated test SHALL be added or updated before production code
- AND the test SHALL reference the related OpenSpec requirement where practical

#### Scenario: A task is completed

- GIVEN implementation has made the test pass
- WHEN the developer marks the task complete
- THEN the relevant tests SHALL be green
- AND the implementation SHALL be refactored only with tests passing

### Requirement: Maintain Test Protocol Traceability

The project SHALL track how implementation and verification map to `test_protocol.md`.

#### Scenario: A feature supports E2E behavior

- GIVEN a feature implements behavior covered by a TC-E2E case
- WHEN the feature is completed
- THEN the TC-E2E case SHALL be mapped to the relevant spec, tests, and tasks

#### Scenario: A TC-E2E case is deferred

- GIVEN a TC-E2E case cannot be automated or completed in the current slice
- WHEN the change is verified
- THEN the deferral SHALL be documented with a reason and follow-up task

### Requirement: Use Production-Like E2E Components

The final E2E acceptance run SHALL use the real components required by `test_protocol.md`.

#### Scenario: E2E preflight starts

- GIVEN the E2E run is about to start
- WHEN the preflight checks execute
- THEN WebUI, Backend API, PostgreSQL, broker, Agent Worker, LLM provider,
  browser MCP connector, email connector, Telegram connector, and controlled
  supplier test contour SHALL be reachable

#### Scenario: E2E run needs test data

- GIVEN the E2E protocol searches for controlled supplier products
- WHEN browser MCP opens the controlled supplier site
- THEN real HTML product pages SHALL be available for email, Telegram, missing-price, invalid-product, and connector-failure scenarios

### Requirement: Forbid E2E Shortcuts

The E2E acceptance run SHALL NOT use shortcuts prohibited by `test_protocol.md`.

#### Scenario: E2E run executes

- GIVEN the E2E run is executing acceptance scenarios
- WHEN product search or supplier contact behavior is exercised
- THEN the run SHALL NOT use mock connectors, a fake worker, manual database insertion, disabled queues, pre-baked LLM output, static UI data, in-memory databases, or pseudo message sending

### Requirement: Produce Final Test Report

The project SHALL produce the final test report defined by `test_protocol.md`.

#### Scenario: E2E run completes

- GIVEN all TC-E2E cases have been executed
- WHEN the tester records the final report
- THEN each TC-E2E case SHALL have PASS, FAIL, or allowed N/A status
- AND the report SHALL include environment, connector, model, defect, and MVP acceptance fields

#### Scenario: Final active-work check runs

- GIVEN the E2E run has completed
- WHEN PostgreSQL is queried for `queued` or `running` agent tasks and contact attempts
- THEN the result SHALL be zero active records unless explicitly documented as a failed run artifact
