# Lance un cycle headless du laboratoire IA sur un protocole deja pre-enregistre.
# Usage : pwsh -File ci/lab.ps1 <chemin-protocole> [-Yolo]
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Protocol,

    [switch]$Yolo
)

$ErrorActionPreference = 'Stop'

$repoDir = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path -LiteralPath $Protocol -PathType Leaf)) {
    Write-Error "Protocole introuvable : $Protocol"
    exit 1
}

if (-not (Select-String -LiteralPath $Protocol -SimpleMatch 'Statut : PRE-ENREGISTRE' -Quiet)) {
    Write-Error "Protocole non pre-enregistre : '$Protocol' ne contient pas 'Statut : PRE-ENREGISTRE'. Un cycle CI exige un protocole approuve par le PI."
    exit 1
}

$logDir = Join-Path $repoDir 'lab-logs'
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$logFile = Join-Path $logDir ("lab-{0}.json" -f (Get-Date -Format yyyyMMdd-HHmmss))

$claudeArgs = @(
    '-p', "/lab-run '$Protocol'",
    '--output-format', 'json',
    '--max-turns', '150'
)

if ($Yolo) {
    $claudeArgs += '--dangerously-skip-permissions'
    $mode = 'YOLO (permissions ignorees)'
}
else {
    $claudeArgs += @('--permission-mode', 'acceptEdits')
    $claudeArgs += @('--allowedTools', '@ALLOWED@')
    $mode = 'acceptEdits + liste blanche'
}

Write-Host "Protocole : $Protocol"
Write-Host "Mode      : $mode"
Write-Host "Journal   : $logFile"

$env:CLAUDE_CODE_DISABLE_BACKGROUND_TASKS = '1'
$env:CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS = '0'
& claude @claudeArgs | Tee-Object -FilePath $logFile
$status = $LASTEXITCODE

Write-Host "Sortie claude : exit code $status"
exit $status
