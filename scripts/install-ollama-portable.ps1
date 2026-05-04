param(
    [string]$Version = "0.20.2"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ToolsDir = Join-Path $Root ".tools"
$DownloadDir = Join-Path $ToolsDir "downloads"
$OllamaDir = Join-Path $ToolsDir "ollama"
$Archive = Join-Path $DownloadDir "ollama-windows-amd64.zip"
$Exe = Join-Path $OllamaDir "ollama.exe"
$Url = "https://github.com/ollama/ollama/releases/download/v$Version/ollama-windows-amd64.zip"

New-Item -ItemType Directory -Force -Path $DownloadDir, $OllamaDir | Out-Null

if (-not (Test-Path $Exe)) {
    curl.exe -L -C - -o $Archive $Url
    tar.exe -xf $Archive -C $OllamaDir
}

& $Exe --version
