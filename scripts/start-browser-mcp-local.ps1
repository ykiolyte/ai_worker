param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8931,
    [string]$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogDir = Join-Path $Root ".logs"
$NpmCache = Join-Path $Root ".npm-cache"
$PlaywrightBrowsers = Join-Path $Root ".ms-playwright"
$TempDir = Join-Path $Root ".tmp"

New-Item -ItemType Directory -Force -Path $LogDir, $NpmCache, $PlaywrightBrowsers, $TempDir | Out-Null

try {
    Invoke-RestMethod -Uri "http://${HostName}:$Port/mcp" -TimeoutSec 3 | Out-Null
    Write-Host "Browser MCP already listening on http://${HostName}:$Port/mcp"
    exit 0
} catch {
    # The MCP endpoint may reject GET while still being alive, so also check TCP.
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "Browser MCP port $Port is already in use."
        exit 0
    }
}

if (-not (Test-Path $ChromePath)) {
    $ChromePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
}
if (-not (Test-Path $ChromePath)) {
    throw "Chrome or Edge executable was not found"
}

$command = @"
Set-Location -LiteralPath '$Root'
`$env:npm_config_cache='$NpmCache'
`$env:PLAYWRIGHT_BROWSERS_PATH='$PlaywrightBrowsers'
`$env:TEMP='$TempDir'
`$env:TMP='$TempDir'
npx.cmd --yes @playwright/mcp@latest --headless --isolated --executable-path '$ChromePath' --host $HostName --port $Port --allowed-hosts '*'
"@

Start-Process `
    -FilePath powershell.exe `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "browser-mcp.out.log") `
    -RedirectStandardError (Join-Path $LogDir "browser-mcp.err.log")

Start-Sleep -Seconds 8
Write-Host "Browser MCP: http://${HostName}:$Port/mcp"
