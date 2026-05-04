param(
    [string]$Python = "python",
    [string]$HostName = "127.0.0.1"
)

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Frontend = Join-Path $Root "frontend"
$SupplierSite = Join-Path $Root "e2e\supplier-site"
$EnvFile = Join-Path $Root ".env"

if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Root ".env.example") $EnvFile
}

foreach ($line in Get-Content $EnvFile) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
        continue
    }
    $key, $value = $trimmed.Split("=", 2)
    [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
}

$LocalCache = Join-Path $Root ".npm-cache"
$LocalBrowsers = Join-Path $Root ".ms-playwright"
$LocalTemp = Join-Path $Root ".tmp"
New-Item -ItemType Directory -Force -Path $LocalCache, $LocalBrowsers, $LocalTemp | Out-Null
[Environment]::SetEnvironmentVariable("npm_config_cache", $LocalCache, "Process")
[Environment]::SetEnvironmentVariable("PLAYWRIGHT_BROWSERS_PATH", $LocalBrowsers, "Process")
[Environment]::SetEnvironmentVariable("TEMP", $LocalTemp, "Process")
[Environment]::SetEnvironmentVariable("TMP", $LocalTemp, "Process")

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Push-Location $Frontend
    npm.cmd install
    Pop-Location
}

if ($env:MODEL_PROVIDER -eq "ollama") {
    & (Join-Path $PSScriptRoot "start-ollama-local.ps1") | Out-Host
}

if (($env:BROWSER_PROVIDER -like "playwright*") -and $env:BROWSER_MCP_URL) {
    & (Join-Path $PSScriptRoot "start-browser-mcp-local.ps1") | Out-Host
}

$backend = "Set-Location -LiteralPath '$Root'; & '$Python' -m uvicorn backend.app.main:app --host $HostName --port 8000"
$supplier = "Set-Location -LiteralPath '$Root'; & '$Python' -m http.server 8088 -d '$SupplierSite'"
$frontend = "Set-Location -LiteralPath '$Frontend'; `$env:VITE_API_BASE_URL='http://localhost:8000/api'; & npm.cmd run dev -- --host $HostName --port 5173"

Start-Process -FilePath powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backend) -WindowStyle Hidden
Start-Process -FilePath powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $supplier) -WindowStyle Hidden
Start-Process -FilePath powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $frontend) -WindowStyle Hidden

Start-Sleep -Seconds 4

Write-Host "Backend:       http://localhost:8000/health"
Write-Host "WebUI:         http://localhost:5173/"
Write-Host "Supplier site: http://localhost:8088/"
