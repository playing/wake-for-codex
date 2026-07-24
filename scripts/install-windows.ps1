[CmdletBinding()]
param(
    [string] $Python = 'python',
    [switch] $DownloadModel,
    [switch] $InstallHook
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

$repoRoot = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $repoRoot '.venv-kws'
$venvPython = Join-Path $venv 'Scripts\python.exe'
$requirements = Join-Path $repoRoot 'launcher\requirements.txt'

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to create the Python virtual environment.'
    }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to upgrade pip.'
}
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to install Python dependencies.'
}

if ($DownloadModel) {
    Write-Warning (
        'The sherpa-onnx model artifact has no explicit model-specific license. ' +
        'This script downloads it from the upstream release and does not redistribute it.'
    )
    $modelName = 'sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20'
    $modelRoot = Join-Path $env:LOCALAPPDATA 'WakeForCodex\models'
    $modelDirectory = Join-Path $modelRoot $modelName
    $legacyModelDirectories = @(
        (Join-Path $env:LOCALAPPDATA "CodexWakeLauncher\models\$modelName"),
        (Join-Path $env:LOCALAPPDATA "CodexVoiceHelper\models\$modelName")
    )
    $modelUrl = (
        'https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/' +
        "$modelName.tar.bz2"
    )
    $expectedHash = '68447f4fbc67e70eee3a93961f36e81e98f47aef73ce7e7ca00885c6cd3616a6'

    $existingLegacyModel = @(
        $legacyModelDirectories |
            Where-Object { Test-Path -LiteralPath $_ -PathType Container }
    ) | Select-Object -First 1
    if ($null -ne $existingLegacyModel) {
        Write-Output "Using existing model: $existingLegacyModel"
    } elseif (-not (Test-Path -LiteralPath $modelDirectory -PathType Container)) {
        $null = New-Item -ItemType Directory -Path $modelRoot -Force
        $archive = Join-Path ([System.IO.Path]::GetTempPath()) "$modelName.tar.bz2"
        try {
            Invoke-WebRequest -Uri $modelUrl -OutFile $archive
            $actualHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
            if ($actualHash.ToLowerInvariant() -ne $expectedHash) {
                throw "Model checksum mismatch: $actualHash"
            }
            & tar -xjf $archive -C $modelRoot
            if ($LASTEXITCODE -ne 0) {
                throw 'Failed to extract the model archive.'
            }
        } finally {
            if (Test-Path -LiteralPath $archive -PathType Leaf) {
                Remove-Item -LiteralPath $archive -Force
            }
        }
    }
}

if ($InstallHook) {
    & $venvPython (Join-Path $PSScriptRoot 'codex_hook.py') `
        --repo-root $repoRoot
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to install the optional Codex hook.'
    }
    Write-Warning 'Review and trust the new hook once in Codex with /hooks.'
}

Push-Location $repoRoot
try {
    & $venvPython -m launcher.doctor
    $doctorExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $doctorExitCode
