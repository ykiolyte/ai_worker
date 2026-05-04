## ADDED Requirements

### Requirement: Use Local Ollama Model Provider
The system SHALL support a local Ollama model provider for agent planning and
structured ranking tasks.

#### Scenario: Ollama provider returns structured JSON
- **GIVEN** `MODEL_PROVIDER=ollama`
- **AND** `OLLAMA_BASE_URL` and `MODEL_NAME` are configured
- **WHEN** the agent requests structured JSON from the model
- **THEN** the system SHALL call the local Ollama endpoint
- **AND** it SHALL parse the model response as JSON
- **AND** it SHALL reject or fallback from invalid JSON without crashing the
  search task

#### Scenario: Local demo provider remains available
- **GIVEN** `MODEL_PROVIDER=local_demo`
- **WHEN** controlled supplier-site tests run
- **THEN** the system SHALL continue to run without requiring Ollama

### Requirement: Keep Model Provider Configurable
The system SHALL keep business logic independent from a hardcoded model name.

#### Scenario: User changes local model name
- **GIVEN** `MODEL_PROVIDER=ollama`
- **AND** `MODEL_NAME` is changed to another locally installed Ollama model
- **WHEN** a product-search task runs
- **THEN** the system SHALL use the configured model name
- **AND** no product-search business logic SHALL depend on a specific model id
