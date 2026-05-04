## ADDED Requirements

### Requirement: Windows One-Click Start
The project SHALL provide a root-level Windows launcher that starts the local MVP with no manual command entry after the repository is present on the workstation.

#### Scenario: User starts project from repository root
- **GIVEN** the repository exists on a Windows workstation
- **AND** Docker Desktop is installed and available
- **WHEN** the user launches the root start command
- **THEN** the script SHALL prepare local configuration if needed
- **AND** the script SHALL ensure the configured local AI model is available
- **AND** the script SHALL start the Docker Compose stack
- **AND** the script SHALL wait for Backend API and WebUI readiness
- **AND** the script SHALL open or print the WebUI URL

#### Scenario: Existing local secrets are preserved
- **GIVEN** `.env` already exists
- **WHEN** the user launches the root start command
- **THEN** the script SHALL NOT overwrite `.env`
- **AND** the script SHALL NOT replace Gmail, Telegram, SMTP, IMAP, or model API secrets with placeholders

### Requirement: Model Bootstrap
The local deployment flow SHALL ensure the configured Ollama model is downloaded before the worker is expected to generate AI responses.

#### Scenario: Default model is missing
- **GIVEN** the configured model is not present in local Ollama
- **WHEN** the bootstrap flow runs
- **THEN** it SHALL start or install local Ollama using repository scripts
- **AND** it SHALL pull the configured model name
- **AND** Docker backend and worker services SHALL be configured to reach that local Ollama endpoint

#### Scenario: Model name is overridden
- **GIVEN** the operator passes a model name override
- **WHEN** the bootstrap flow runs
- **THEN** it SHALL use that model name for the pull/check operation
- **AND** it SHALL avoid hardcoding a different model in business logic

### Requirement: Prerequisite Diagnostics
The local deployment flow SHALL fail with actionable diagnostics when required workstation prerequisites are not available.

#### Scenario: Docker is unavailable
- **GIVEN** Docker CLI or Docker Engine is unavailable
- **WHEN** the bootstrap flow runs
- **THEN** it SHALL stop before running Docker Compose
- **AND** it SHALL explain that Docker Desktop must be installed and running
- **AND** it SHALL NOT modify application data volumes

#### Scenario: Health checks fail
- **GIVEN** Docker Compose starts but Backend API or WebUI health checks do not become ready
- **WHEN** the bootstrap flow reaches its timeout
- **THEN** it SHALL print the failing URL or service name
- **AND** it SHALL suggest checking Docker Compose logs

### Requirement: Clean Stop
The project SHALL provide a root-level Windows stop launcher for shutting down local MVP services without deleting persistent data.

#### Scenario: User stops project
- **GIVEN** the local MVP stack is running
- **WHEN** the user launches the root stop command
- **THEN** it SHALL run Docker Compose shutdown without volume deletion
- **AND** it SHALL preserve PostgreSQL and Ollama data

### Requirement: New Workstation Documentation
The repository SHALL document the new-workstation path from GitHub repository to running WebUI.

#### Scenario: User reads deployment instructions
- **GIVEN** the user has a new workstation
- **WHEN** the user opens the README or deployment guide
- **THEN** the documentation SHALL include the repository URL
- **AND** it SHALL list the minimum prerequisites
- **AND** it SHALL describe first start, regular start, stop, update, and secret configuration
- **AND** it SHALL distinguish Mailpit demo mode from real Gmail/Telegram credentials
