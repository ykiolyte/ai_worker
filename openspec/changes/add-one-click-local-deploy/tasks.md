## 1. Contract Tests

- [x] 1.1 Add deployment-script contract tests for root launchers, bootstrap behavior, dry-run support, model bootstrap, and stop behavior.
- [x] 1.2 Add documentation contract coverage for new-workstation setup and secret handling.

## 2. Launch Scripts

- [x] 2.1 Add root start/stop `.cmd` launchers that delegate to PowerShell with execution policy bypass.
- [x] 2.2 Implement bootstrap PowerShell script with `.env` creation, prerequisite diagnostics, Ollama/model bootstrap, Docker Compose startup, health checks, and WebUI launch.
- [x] 2.3 Implement stop PowerShell script that shuts down Compose services without deleting volumes.
- [x] 2.4 Add dry-run and help paths so script contracts can be verified without starting services or downloading models.

## 3. Documentation

- [x] 3.1 Update README with the two-click new-workstation flow using the GitHub repository URL.
- [x] 3.2 Add or update deployment/restart documentation for first start, regular start, stop, update, model selection, and Gmail/Telegram secrets.

## 4. Verification

- [x] 4.1 Run deployment-script contract tests.
- [x] 4.2 Run PowerShell parse/syntax checks for new scripts.
- [x] 4.3 Run relevant backend/frontend automated checks.
- [x] 4.4 Validate OpenSpec change with strict validation.
