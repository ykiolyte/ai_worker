## Context

The local MVP already has Docker Compose, `.env.example`, and several PowerShell helpers for Ollama and local services. The current setup still expects the operator to know the correct sequence: copy `.env`, start or install Ollama, pull the configured model, run Docker Compose, wait for services, and open the WebUI. The requested deployment target is a Windows workstation where a user can clone or download the repository and start the project with minimal manual work.

The launch flow must preserve the production-like local contour: backend API, WebUI, PostgreSQL, Redis, Agent Worker, Browser MCP, search service, Mailpit/test email path, and a real `ModelProvider` backed by local Ollama when configured. Secrets for Gmail, Telegram, or paid model providers remain local-only in `.env`.

## Goals / Non-Goals

**Goals:**

- Provide a root-level "double click" start command for Windows.
- Prepare a runnable local `.env` from `.env.example` without overwriting existing secrets.
- Ensure local Ollama can run and the requested model is present before starting services.
- Start the Docker Compose stack and wait for backend and WebUI readiness.
- Open the WebUI after successful startup and print service URLs.
- Provide a matching stop command for clean shutdown.
- Document clone/download, first run, regular run, stop, update, and secret configuration.

**Non-Goals:**

- Do not silently install Docker Desktop, Git, or other privileged system software.
- Do not store Gmail, Telegram, or model API secrets in the repository.
- Do not add autonomous purchasing, payment, CRM, or supplier negotiation behavior.
- Do not replace the existing Docker Compose architecture.
- Do not require cloud deployment or external hosting for the MVP.

## Decisions

1. Use root `.cmd` launchers that delegate to PowerShell scripts.

   Rationale: `.cmd` files are the simplest Windows double-click entry point and avoid execution-policy friction for the first click. PowerShell remains the implementation language because the project already uses it for local scripts.

   Alternative considered: only documenting PowerShell commands. That keeps fewer files but does not satisfy the "few clicks" requirement.

2. Prefer host-local portable Ollama for the model runtime.

   Rationale: `docker-compose.yml` already points backend and worker at `host.docker.internal:11434` by default, and existing scripts can install/start a portable Ollama under `.tools`. This avoids losing models inside Docker volumes and makes model reuse predictable across rebuilds.

   Alternative considered: pull the model inside the compose `ollama` container. This is useful as a fallback but slower and less aligned with the current default Compose settings.

3. Keep Docker Desktop as a prerequisite with clear diagnostics.

   Rationale: Docker Desktop installation is privileged and machine-specific. The script can detect Docker availability, start Docker Desktop if it is installed, wait for `docker info`, and report a direct instruction if Docker is missing or not running.

   Alternative considered: unattended Docker Desktop installation. That is brittle, slow, and inappropriate for a repository bootstrap script.

4. Add a dry-run mode for contract tests.

   Rationale: Automated tests should verify the script contract without downloading multi-gigabyte models or starting services. The same script can expose `-DryRun` to list planned actions, while real operation remains unchanged.

   Alternative considered: pure documentation tests. They would not catch script regressions.

## Risks / Trade-offs

- [Risk] First model download can take a long time and require significant disk space. -> Mitigation: print the selected model and make it configurable via `.env` or `-ModelName`.
- [Risk] Docker Desktop may be absent or stopped. -> Mitigation: detect it early, attempt to start the installed app, then print a concise prerequisite message if unavailable.
- [Risk] Existing `.env` may contain real secrets. -> Mitigation: never overwrite `.env` unless the user passes an explicit reset option; only create it from `.env.example` when missing.
- [Risk] A workstation may have ports already in use. -> Mitigation: surface `docker compose up` output and document stop/retry flow.
- [Risk] Antivirus or corporate policy may block portable binaries. -> Mitigation: allow use of system `ollama` when available and keep all tooling paths configurable.
