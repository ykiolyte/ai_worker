param(
    [string]$EnvPath = ".env"
)

function Read-SecretPlain([string]$Prompt) {
    $secure = Read-Host $Prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Set-EnvValue([string[]]$Lines, [string]$Key, [string]$Value) {
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
    $result
}

$resolved = Resolve-Path -LiteralPath $EnvPath -ErrorAction SilentlyContinue
if (-not $resolved) {
    Copy-Item ".env.example" $EnvPath
    $resolved = Resolve-Path -LiteralPath $EnvPath
}

$lines = Get-Content -LiteralPath $resolved

$telegramToken = Read-SecretPlain "TELEGRAM_BOT_TOKEN"
$telegramChatId = Read-Host "TELEGRAM_CHAT_ID"
$modelProvider = Read-Host "MODEL_PROVIDER"
$modelName = Read-Host "MODEL_NAME"
$modelApiBaseUrl = Read-Host "MODEL_API_BASE_URL"
$modelApiKey = Read-SecretPlain "MODEL_API_KEY"

$lines = Set-EnvValue $lines "TELEGRAM_CONNECTOR_PROVIDER" "telegram_bot"
$lines = Set-EnvValue $lines "TELEGRAM_BOT_TOKEN" $telegramToken
$lines = Set-EnvValue $lines "TELEGRAM_CHAT_ID" $telegramChatId
$lines = Set-EnvValue $lines "MODEL_PROVIDER" $modelProvider
$lines = Set-EnvValue $lines "MODEL_NAME" $modelName
$lines = Set-EnvValue $lines "MODEL_API_BASE_URL" $modelApiBaseUrl
$lines = Set-EnvValue $lines "MODEL_API_KEY" $modelApiKey

Set-Content -LiteralPath $resolved -Value $lines -Encoding UTF8
Write-Host "Updated $resolved"
