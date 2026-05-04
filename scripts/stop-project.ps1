param(
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host "Stops the Product Sourcing MVP local Docker Compose stack without deleting volumes."
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  STOP_PROJECT.cmd"
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/stop-project.ps1 [-DryRun]"
}

if ($Help) {
    Show-Help
    exit 0
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $Root

if ($DryRun) {
    Write-Host "[dry-run] Would run docker compose down."
    Write-Host "[dry-run] PostgreSQL and Ollama data volumes would be preserved."
    exit 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker.exe was not found. If services are running, stop them from Docker Desktop."
}

docker compose down
Write-Host "Project services stopped. PostgreSQL and Ollama data volumes were preserved."
