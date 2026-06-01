param(
    [string]$LanIp = "172.22.25.24",
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8080,
    [string]$ModelName = "qwen2.5:7b",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Logs = Join-Path $Root ".logs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null

$ports = 8000, 8080, 5173
$oldProjectProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        ($_.Name -in @("python.exe", "powershell.exe", "cmd.exe", "node.exe")) -and
        ($_.CommandLine -like "*C:\ai_reserch\ai_worker*" -or
            $_.CommandLine -like "*app.main:app*" -or
            $_.CommandLine -like "*app.worker*" -or
            $_.CommandLine -like "*vite preview*" -or
            $_.CommandLine -like "*vite --host*")
    } |
    Select-Object -ExpandProperty ProcessId -Unique

foreach ($procId in $oldProjectProcesses) {
    if ($procId -ne $PID) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

$listeners = Get-NetTCPConnection -LocalPort $ports -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $listeners) {
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

$backendLog = Join-Path $Logs "backend-dev.cmd.log"
$workerLog = Join-Path $Logs "worker-dev.cmd.log"
$frontendLog = Join-Path $Logs "frontend-dev.cmd.log"

Push-Location $Frontend
try {
    $env:VITE_API_BASE_URL = ""
    npm.cmd run build *> $frontendLog
    if ($LASTEXITCODE -ne 0) {
        Get-Content $frontendLog -Tail 120 -ErrorAction SilentlyContinue
        throw "Frontend build failed"
    }
} finally {
    Pop-Location
}

$backendCommand = @"
Set-Location -LiteralPath '$Backend'
`$env:WEBUI_BASE_URL = 'http://$LanIp`:$Port'
`$env:API_BASE_URL = 'http://$LanIp`:$Port/api'
`$env:DATABASE_URL = 'sqlite:///dev-local.db'
`$env:AUTO_PROCESS_SEARCH_TASKS = 'false'
`$env:AUTO_PROCESS_SUPPLIER_CONTACT_TASKS = 'false'
`$env:AUTO_PROCESS_CONTRACT_TASKS = 'false'
`$env:AUTO_SYNC_GMAIL_INBOUND = 'false'
`$env:MODEL_PROVIDER = 'ollama'
`$env:MODEL_NAME = '$ModelName'
`$env:OLLAMA_BASE_URL = 'http://localhost:11434'
`$env:OLLAMA_TIMEOUT_SECONDS = '180'
`$env:MADE_IN_CHINA_DISCOVERY_ENABLED = 'true'
`$env:MADE_IN_CHINA_MAX_RESULTS = '50'
`$env:ENABLE_MADE_IN_CHINA_PROVIDER = 'true'
`$env:MADE_IN_CHINA_PROVIDER_MAX_RESULTS = '50'
`$env:INTERNET_SEARCH_RESULT_LIMIT = '50'
`$env:WEB_SEARCH_RESULT_LIMIT = '50'
`$env:AI_SEARCH_CANDIDATE_LIMIT = '50'
`$env:EMAIL_CONNECTOR_PROVIDER = ''
`$env:EMAIL_INBOUND_PROVIDER = ''
`$env:TELEGRAM_CONNECTOR_PROVIDER = ''
& '$Python' -m uvicorn app.main:app --host $BindHost --port $Port *> '$backendLog'
"@

$workerCommand = @"
Set-Location -LiteralPath '$Backend'
`$env:WEBUI_BASE_URL = 'http://$LanIp`:$Port'
`$env:API_BASE_URL = 'http://$LanIp`:$Port/api'
`$env:DATABASE_URL = 'sqlite:///dev-local.db'
`$env:AUTO_PROCESS_SEARCH_TASKS = 'false'
`$env:AUTO_PROCESS_SUPPLIER_CONTACT_TASKS = 'false'
`$env:AUTO_PROCESS_CONTRACT_TASKS = 'false'
`$env:AUTO_SYNC_GMAIL_INBOUND = 'false'
`$env:MODEL_PROVIDER = 'ollama'
`$env:MODEL_NAME = '$ModelName'
`$env:OLLAMA_BASE_URL = 'http://localhost:11434'
`$env:OLLAMA_TIMEOUT_SECONDS = '180'
`$env:MADE_IN_CHINA_DISCOVERY_ENABLED = 'true'
`$env:MADE_IN_CHINA_MAX_RESULTS = '50'
`$env:ENABLE_MADE_IN_CHINA_PROVIDER = 'true'
`$env:MADE_IN_CHINA_PROVIDER_MAX_RESULTS = '50'
`$env:INTERNET_SEARCH_RESULT_LIMIT = '50'
`$env:WEB_SEARCH_RESULT_LIMIT = '50'
`$env:AI_SEARCH_CANDIDATE_LIMIT = '50'
`$env:EMAIL_CONNECTOR_PROVIDER = ''
`$env:EMAIL_INBOUND_PROVIDER = ''
`$env:TELEGRAM_CONNECTOR_PROVIDER = ''
`$env:WORKER_POLL_INTERVAL_SECONDS = '1'
`$env:WORKER_MAX_TASKS_PER_TICK = '1'
& '$Python' -m app.worker *> '$workerLog'
"@

Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand)
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $workerCommand)

Start-Sleep -Seconds 6

Write-Host "Expected URLs:"
Write-Host "  WebUI:   http://$LanIp`:$Port"
Write-Host "  Health:  http://$LanIp`:$Port/health"
Write-Host "  Bind:    $BindHost`:$Port"
Write-Host ""
Write-Host "Listening ports:"
netstat -ano | findstr ":5173 :8000 :8080"
Write-Host ""
Write-Host "Backend health:"
try {
    Invoke-WebRequest -UseBasicParsing "http://$LanIp`:$Port/health" -TimeoutSec 10 |
        Select-Object StatusCode, StatusDescription
} catch {
    Write-Host $_.Exception.Message
    Write-Host "Backend log tail:"
    Get-Content $backendLog -Tail 80 -ErrorAction SilentlyContinue
    Write-Host "Worker log tail:"
    Get-Content $workerLog -Tail 80 -ErrorAction SilentlyContinue
}
Write-Host ""
Write-Host "WebUI:"
try {
    Invoke-WebRequest -UseBasicParsing "http://$LanIp`:$Port/" -TimeoutSec 10 |
        Select-Object StatusCode, StatusDescription
} catch {
    Write-Host $_.Exception.Message
    Write-Host "Backend log tail:"
    Get-Content $backendLog -Tail 80 -ErrorAction SilentlyContinue
}
