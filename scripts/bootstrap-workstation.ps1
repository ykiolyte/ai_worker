param(
    [string]$ModelName = "",
    [int]$HealthTimeoutSeconds = 180,
    [int]$DockerTimeoutSeconds = 120,
    [switch]$NoOpen,
    [switch]$SkipModelPull,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host "Starts the Product Sourcing MVP local stack."
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  START_PROJECT.cmd"
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/bootstrap-workstation.ps1 [-ModelName mistral-nemo:12b] [-NoOpen] [-DryRun]"
    Write-Host ""
    Write-Host "What it does:"
    Write-Host "  1. Creates .env from .env.example when missing."
    Write-Host "  2. Keeps existing .env secrets intact."
    Write-Host "  3. Installs/starts portable Ollama and pulls the configured model."
    Write-Host "  4. Runs docker compose up --build -d."
    Write-Host "  5. Waits for Backend and WebUI readiness, then opens WebUI."
}

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message"
}

function Read-DotEnv([string]$Path) {
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $map
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }

        $key, $value = $trimmed.Split("=", 2)
        $map[$key.Trim()] = $value.Trim()
    }

    return $map
}

function Set-DotEnvValue([string[]]$Lines, [string]$Key, [string]$Value) {
    $updated = $false
    $result = foreach ($line in $Lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))=") {
            $updated = $true
            "$Key=$Value"
        }
        else {
            $line
        }
    }

    if (-not $updated) {
        $result += "$Key=$Value"
    }

    return $result
}

function Ensure-EnvFile([string]$Root, [switch]$DryRun) {
    $envFile = Join-Path $Root ".env"
    $example = Join-Path $Root ".env.example"

    if (Test-Path -LiteralPath $envFile) {
        Write-Host "Keeping existing .env; Gmail, Telegram, SMTP, IMAP, and model API secrets are preserved."
        return @{ Path = $envFile; Created = $false }
    }

    if (-not (Test-Path -LiteralPath $example)) {
        throw ".env.example was not found at $example"
    }

    if ($DryRun) {
        Write-Host "[dry-run] Would create .env from .env.example."
    }
    else {
        Copy-Item -LiteralPath $example -Destination $envFile
        Write-Host "Created .env from .env.example."
    }

    return @{ Path = $envFile; Created = $true }
}

function Resolve-DeploymentModel([hashtable]$EnvMap, [string]$OverrideModelName) {
    if (-not [string]::IsNullOrWhiteSpace($OverrideModelName)) {
        return $OverrideModelName
    }

    $provider = $EnvMap["MODEL_PROVIDER"]
    $configured = $EnvMap["MODEL_NAME"]
    if ($provider -eq "ollama" -and -not [string]::IsNullOrWhiteSpace($configured) -and $configured -ne "browser-extraction-v0") {
        return $configured
    }

    return "mistral-nemo:12b"
}

function Configure-LocalOllamaEnv([string]$EnvPath, [hashtable]$EnvMap, [string]$ResolvedModelName, [bool]$CreatedEnv, [switch]$DryRun) {
    $provider = $EnvMap["MODEL_PROVIDER"]
    $currentModel = $EnvMap["MODEL_NAME"]
    $usesDemoDefaults = (
        $CreatedEnv -or
        [string]::IsNullOrWhiteSpace($provider) -or
        $provider -eq "local_demo" -or
        [string]::IsNullOrWhiteSpace($currentModel) -or
        $currentModel -eq "browser-extraction-v0" -or
        -not [string]::IsNullOrWhiteSpace($ModelName)
    )

    if (-not $usesDemoDefaults) {
        Write-Host "Keeping existing MODEL_PROVIDER=$provider and MODEL_NAME=$currentModel."
        return
    }

    if ($DryRun) {
        Write-Host "[dry-run] Would configure .env for local Ollama model $ResolvedModelName."
        return
    }

    $lines = Get-Content -LiteralPath $EnvPath
    $lines = Set-DotEnvValue $lines "MODEL_PROVIDER" "ollama"
    $lines = Set-DotEnvValue $lines "MODEL_NAME" $ResolvedModelName
    $lines = Set-DotEnvValue $lines "OLLAMA_BASE_URL" "http://localhost:11434"
    $lines = Set-DotEnvValue $lines "DOCKER_OLLAMA_BASE_URL" "http://host.docker.internal:11434"
    Set-Content -LiteralPath $EnvPath -Value $lines -Encoding UTF8
    Write-Host "Configured .env for local Ollama model $ResolvedModelName. Existing connector secrets were not changed."
}

function Wait-Docker([int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            docker info *> $null
            return
        }
        catch {
            Start-Sleep -Seconds 3
        }
    } while ((Get-Date) -lt $deadline)

    throw "Docker Desktop is not ready. Install Docker Desktop and make sure it is running, then launch START_PROJECT.cmd again."
}

function Start-DockerDesktopIfInstalled {
    $candidates = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Docker\Docker Desktop.exe")
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

    if ($candidates.Count -gt 0) {
        Write-Host "Starting Docker Desktop..."
        Start-Process -FilePath $candidates[0] -WindowStyle Hidden
    }
}

function Ensure-Docker([int]$TimeoutSeconds, [switch]$DryRun) {
    if ($DryRun) {
        Write-Host "[dry-run] Would check Docker Desktop and Docker Engine readiness."
        return
    }

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop is required but docker.exe was not found. Install Docker Desktop, start it once, then launch START_PROJECT.cmd again."
    }

    try {
        docker info *> $null
    }
    catch {
        Start-DockerDesktopIfInstalled
        Wait-Docker $TimeoutSeconds
    }
}

function Ensure-OllamaModel([string]$Root, [string]$ResolvedModelName, [switch]$SkipModelPull, [switch]$DryRun) {
    $install = Join-Path $Root "scripts\install-ollama-portable.ps1"
    $start = Join-Path $Root "scripts\start-ollama-local.ps1"
    $pull = Join-Path $Root "scripts\pull-local-model.ps1"

    if ($DryRun) {
        Write-Host "[dry-run] Would run install-ollama-portable.ps1."
        Write-Host "[dry-run] Would run start-ollama-local.ps1."
        if ($SkipModelPull) {
            Write-Host "[dry-run] Would skip model pull for $ResolvedModelName."
        }
        else {
            Write-Host "[dry-run] Would run pull-local-model.ps1 -ModelName $ResolvedModelName."
        }
        return
    }

    & $install | Out-Host
    & $start | Out-Host

    if ($SkipModelPull) {
        Write-Host "Skipping model pull by request. Model expected: $ResolvedModelName"
        return
    }

    & $pull -ModelName $ResolvedModelName | Out-Host
}

function Start-Compose([switch]$DryRun) {
    if ($DryRun) {
        Write-Host "[dry-run] Would run docker compose up --build -d."
        return
    }

    docker compose up --build -d
}

function Wait-HttpReady([string]$Url, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        }
        catch {
            Start-Sleep -Seconds 3
        }
    } while ((Get-Date) -lt $deadline)

    throw "Health check timed out for $Url. Check logs with: docker compose logs --tail=100 backend worker webui"
}

if ($Help) {
    Show-Help
    exit 0
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $Root

Write-Step "Preparing local environment"
$envInfo = Ensure-EnvFile -Root $Root -DryRun:$DryRun
$envSource = if (Test-Path -LiteralPath $envInfo.Path) { $envInfo.Path } else { Join-Path $Root ".env.example" }
$envMap = Read-DotEnv $envSource
$resolvedModel = Resolve-DeploymentModel -EnvMap $envMap -OverrideModelName $ModelName
Configure-LocalOllamaEnv -EnvPath $envInfo.Path -EnvMap $envMap -ResolvedModelName $resolvedModel -CreatedEnv $envInfo.Created -DryRun:$DryRun

Write-Step "Checking Docker Desktop"
Ensure-Docker -TimeoutSeconds $DockerTimeoutSeconds -DryRun:$DryRun

Write-Step "Preparing local AI model: $resolvedModel"
Ensure-OllamaModel -Root $Root -ResolvedModelName $resolvedModel -SkipModelPull:$SkipModelPull -DryRun:$DryRun

Write-Step "Starting Docker Compose services"
Start-Compose -DryRun:$DryRun

Write-Step "Waiting for services"
if ($DryRun) {
    Write-Host "[dry-run] Would wait for http://127.0.0.1:8000/health."
    Write-Host "[dry-run] Would wait for http://127.0.0.1:5173."
}
else {
    Wait-HttpReady -Url "http://127.0.0.1:8000/health" -TimeoutSeconds $HealthTimeoutSeconds
    Wait-HttpReady -Url "http://127.0.0.1:5173" -TimeoutSeconds $HealthTimeoutSeconds
}

Write-Step "Ready"
Write-Host "WebUI:          http://127.0.0.1:5173"
Write-Host "Backend health: http://127.0.0.1:8000/health"
Write-Host "Mailpit:        http://127.0.0.1:8025"
Write-Host "Supplier site:  http://127.0.0.1:8088"
Write-Host "SearXNG:        http://127.0.0.1:8888"
Write-Host "Ollama:         http://127.0.0.1:11434"
Write-Host "Model:          $resolvedModel"

if ($DryRun) {
    Write-Host "[dry-run] Startup simulation complete."
    exit 0
}

if (-not $NoOpen) {
    Start-Process "http://127.0.0.1:5173"
}
