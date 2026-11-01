<#
.SYNOPSIS
    Lance les scenarios de bout en bout du harnais (lanceur mince de ci/scenarios/run.py).
.DESCRIPTION
    Detecte l'interpreteur par la regle D5 (premier de python, python3, py -3 qui repond en moins
    de 5 s avec une version >= 3.9), transmet les options au runner et propage son code de sortie :
    0 = tout PASS ou SKIP motive, 1 = un FAIL (ou -Live sans claude), 2 = option ou scenario inconnu.
.PARAMETER List
    Liste les scenarios (avec -Details : sous-commandes du noyau et fichiers qui les prescrivent).
.PARAMETER Details
    Avec -List : sous-commandes du noyau et fichiers qui les prescrivent (equivalent de --verbose).
.PARAMETER Scenario
    Ne lance que ce scenario ; plusieurs separes par des virgules.
.PARAMETER Live
    Lance aussi les scenarios live-* (vrai claude, consomme des tokens).
.PARAMETER Keep
    Garde les dossiers temporaires et affiche leur chemin.
.PARAMETER Fixtures
    Dossier des fixtures (defaut : ci/fixtures).
.PARAMETER Report
    Fichier du rapport JSON (defaut : dossier temporaire).
#>
param(
    [switch]$List,
    [switch]$Details,
    [string[]]$Scenario,
    [switch]$Live,
    [switch]$Keep,
    [string]$Fixtures,
    [string]$Report,
    [Alias('h')]
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = 'Stop'

function Test-Interpreter {
    # Vrai si la commande repond en moins de 5 s avec une version >= 3.9.
    param([string[]]$Command)
    $found = Get-Command $Command[0] -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $found) { return $false }
    $extra = @()
    if ($Command.Count -gt 1) { $extra = $Command[1..($Command.Count - 1)] }
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $found.Source
    $info.Arguments = (($extra + @('-c', '"import sys; print(sys.version_info >= (3, 9))"')) -join ' ')
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    try {
        $proc = [System.Diagnostics.Process]::Start($info)
    }
    catch {
        return $false
    }
    if (-not $proc.WaitForExit(5000)) {
        try { $proc.Kill() } catch { }
        return $false
    }
    return ($proc.StandardOutput.ReadToEnd() -match 'True')
}

$python = $null
foreach ($candidate in @(@('python'), @('python3'), @('py', '-3'))) {
    if (Test-Interpreter -Command $candidate) { $python = $candidate; break }
}
if (-not $python) {
    [Console]::Error.WriteLine('Aucun interpreteur Python >= 3.9 trouve (python, python3, py -3).')
    exit 1
}

$runner = Join-Path $PSScriptRoot 'scenarios' | Join-Path -ChildPath 'run.py'
$forward = @()
if ($Help) { $forward += '-h' }
if ($List) { $forward += '--list' }
if ($Details) { $forward += '--verbose' }
foreach ($item in @($Scenario)) {
    foreach ($id in ($item -split '[,\s]+')) {
        if ($id) { $forward += '--scenario'; $forward += $id }
    }
}
if ($Live) { $forward += '--live' }
if ($Keep) { $forward += '--keep' }
if ($Fixtures) { $forward += '--fixtures'; $forward += $Fixtures }
if ($Report) { $forward += '--report'; $forward += $Report }
if ($Rest) { $forward += $Rest }

$prefix = @()
if ($python.Count -gt 1) { $prefix = $python[1..($python.Count - 1)] }
$env:HTS_LAUNCHER = 'pwsh'
$ErrorActionPreference = 'Continue'   # le stderr natif du runner n'est pas une erreur du lanceur
& $python[0] @prefix -B -I -S $runner @forward
exit $LASTEXITCODE
