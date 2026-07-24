[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'Wake for Codex requires PowerShell 7.'
}

$runner = Join-Path $PSScriptRoot 'run-wake-launcher.ps1'
$snapshot = @(Get-CimInstance Win32_Process)
$roots = @(
    $snapshot |
        Where-Object {
            $_.Name -eq 'pwsh.exe' -and
            $_.CommandLine -like "*$runner*"
        }
)

if ($roots.Count -eq 0) {
    Write-Output 'launcher=not_running'
    exit 0
}

$targets = [System.Collections.Generic.HashSet[int]]::new()
$frontier = @($roots.ProcessId)
while ($frontier.Count -gt 0) {
    $next = @()
    foreach ($processId in $frontier) {
        $null = $targets.Add([int]$processId)
        $children = @(
            $snapshot |
                Where-Object { $_.ParentProcessId -eq $processId }
        )
        foreach ($child in $children) {
            if (-not $targets.Contains([int]$child.ProcessId)) {
                $next += [int]$child.ProcessId
            }
        }
    }
    $frontier = $next
}

$orderedTargets = @($targets) | Sort-Object -Descending
foreach ($processId in $orderedTargets) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}
Write-Output "launcher=stopped processes=$($orderedTargets.Count)"
