[CmdletBinding()]
param(
    [switch] $Check,
    [switch] $DryRun,
    [switch] $Once,
    [string] $Config,
    [string] $Device,
    [string] $Hotkey,
    [string] $LogFile
)

$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'Wake for Codex requires PowerShell 7.'
}

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$python = Join-Path $PSScriptRoot '.venv-kws\Scripts\python.exe'
$defaultConfig = Join-Path $PSScriptRoot 'config.json'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "KWS Python runtime not found: $python"
}
if (
    [string]::IsNullOrWhiteSpace($Config) -and
    (Test-Path -LiteralPath $defaultConfig -PathType Leaf)
) {
    $Config = $defaultConfig
}

$launcherArguments = @('-m', 'launcher.wake_launcher')
if ($Check) {
    $launcherArguments += '--check'
}
if ($DryRun) {
    $launcherArguments += '--dry-run'
}
if ($Once) {
    $launcherArguments += '--once'
}
if (-not [string]::IsNullOrWhiteSpace($Config)) {
    $launcherArguments += @('--config', $Config)
}
if (-not [string]::IsNullOrWhiteSpace($Device)) {
    $launcherArguments += @('--device', $Device)
}
if (-not [string]::IsNullOrWhiteSpace($Hotkey)) {
    $launcherArguments += @('--hotkey', $Hotkey)
}
if (-not [string]::IsNullOrWhiteSpace($LogFile)) {
    $launcherArguments += @('--log-file', $LogFile)
}

Push-Location $PSScriptRoot
try {
    & $python @launcherArguments
    $launcherExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $launcherExitCode
