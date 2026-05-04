param(
    [string]$ModelName = "mistral-nemo:12b"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$LocalOllama = Join-Path $Root ".tools\ollama\ollama.exe"

if (Test-Path $LocalOllama) {
    & (Join-Path $PSScriptRoot "start-ollama-local.ps1") | Out-Host
    $env:OLLAMA_MODELS = Join-Path $Root ".ollama\models"
    & $LocalOllama pull $ModelName
    & $LocalOllama list
    exit 0
}

$SystemOllama = Get-Command ollama -ErrorAction SilentlyContinue
if ($SystemOllama) {
    & ollama pull $ModelName
    & ollama list
    exit 0
}

try {
    docker info | Out-Null
    docker compose up -d ollama
    docker compose exec ollama ollama pull $ModelName
    docker compose exec ollama ollama list
} catch {
    Write-Error "No runnable Ollama found. Run scripts/install-ollama-portable.ps1 first, or start Docker Desktop with the Docker service available."
}
