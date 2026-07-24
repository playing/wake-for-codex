[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'Wake for Codex requires PowerShell 7.'
}

$runner = Join-Path $PSScriptRoot 'run-wake-launcher.ps1'
$configFile = Join-Path $PSScriptRoot 'config.json'
$runtimeDirectory = Join-Path $env:LOCALAPPDATA 'WakeForCodex'
$logFile = Join-Path $runtimeDirectory 'wake-launcher.jsonl'
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

$existing = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq 'pwsh.exe' -and
            $_.CommandLine -like "*$runner*"
        }
)
if ($existing.Count -gt 0) {
    exit 0
}

$processArguments = @(
    '-NoProfile',
    '-NonInteractive',
    '-File',
    "`"$runner`"",
    '-LogFile',
    "`"$logFile`""
)
if (Test-Path -LiteralPath $configFile -PathType Leaf) {
    $processArguments += @('-Config', "`"$configFile`"")
}

$null = Start-Process `
    -FilePath $pwsh `
    -ArgumentList $processArguments `
    -WindowStyle Hidden `
    -PassThru
