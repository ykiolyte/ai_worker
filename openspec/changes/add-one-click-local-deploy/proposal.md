## Why

The project currently has several useful local start scripts, but a new workstation still requires remembering the correct order for Docker, Ollama, model download, environment files, and health checks. This change makes the MVP easy to deploy from the repository in a few clicks while preserving the real local components required by the E2E protocol.

## What Changes

- Add root-level Windows launchers for starting and stopping the local project without typing commands.
- Add a bootstrap PowerShell workflow that prepares `.env`, ensures a local Ollama endpoint and model are available, starts Docker Compose services, waits for health checks, and opens the WebUI.
- Add a safe status/diagnostic flow for missing prerequisites such as Docker Desktop or Git.
- Document a new-machine setup path using the GitHub repository URL.
- Keep real Gmail/Telegram secrets out of source control; the scripts may create defaults but must not invent or commit private credentials.

## Capabilities

### New Capabilities
- `local-one-click-deployment`: Local workstation bootstrap and launch flow for the full MVP stack, including model download and service health checks.

### Modified Capabilities
- None.

## Impact

- Affected code: root launcher scripts, `scripts/`, developer documentation, and deployment-script contract tests.
- Affected systems: local Windows workstation setup, Docker Compose services, local Ollama model provider, WebUI and Backend API health checks.
- No API or domain model changes are expected.
- Verification will use script contract tests, PowerShell parse/syntax checks, OpenSpec validation, and existing backend/frontend test suites where relevant.
