param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 11434
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Exe = Join-Path $Root ".tools\ollama\ollama.exe"
$ModelsDir = Join-Path $Root ".ollama\models"

if (-not (Test-Path $Exe)) {
    & (Join-Path $PSScriptRoot "install-ollama-portable.ps1")
}

New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

$env:OLLAMA_HOST = "${HostName}:$Port"
$env:OLLAMA_MODELS = $ModelsDir

try {
    Invoke-RestMethod -Uri "http://${HostName}:$Port/api/tags" -TimeoutSec 3 | Out-Null
} catch {
    Start-Process -FilePath $Exe -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

Invoke-RestMethod -Uri "http://${HostName}:$Port/api/tags" -TimeoutSec 10 | ConvertTo-Json -Depth 5
