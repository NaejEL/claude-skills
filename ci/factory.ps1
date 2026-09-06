# Lance un cycle headless de l'usine logicielle sur une spec deja approuvee.
# Usage : pwsh -File ci/factory.ps1 <chemin-spec> [-Yolo]
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Spec,

    [switch]$Yolo
)

$ErrorActionPreference = 'Stop'

$repoDir = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path -LiteralPath $Spec -PathType Leaf)) {
    Write-Error "Spec introuvable : $Spec"
    exit 1
}

if (-not (Select-String -LiteralPath $Spec -SimpleMatch 'Statut : APPROUVEE' -Quiet)) {
    Write-Error "Spec non approuvee : '$Spec' ne contient pas 'Statut : APPROUVEE'. Un cycle CI exige une spec validee par le Product Owner."
    exit 1
}

$logDir = Join-Path $repoDir 'factory-logs'
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$logFile = Join-Path $logDir ("factory-{0}.json" -f (Get-Date -Format yyyyMMdd-HHmmss))

$claudeArgs = @(
    '-p', "/factory-run '$Spec'",
    '--output-format', 'json',
    '--max-turns', '100'
)

if ($Yolo) {
    $claudeArgs += '--dangerously-skip-permissions'
    $mode = 'YOLO (permissions ignorees)'
}
else {
    $claudeArgs += @('--permission-mode', 'acceptEdits')
    $claudeArgs += @('--allowedTools', 'Read,Glob,Grep,Write,Edit,Bash(git *),Bash(bash *),Bash(bats *),Bash(shellcheck *),Bash(pwsh *)')
    $mode = 'acceptEdits + liste blanche'
}

Write-Host "Spec      : $Spec"
Write-Host "Mode      : $mode"
Write-Host "Journal   : $logFile"

& claude @claudeArgs | Tee-Object -FilePath $logFile
$status = $LASTEXITCODE

Write-Host "Sortie claude : exit code $status"
exit $status
