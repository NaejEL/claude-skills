<#
.SYNOPSIS
    Runs the harness end-to-end scenarios (thin launcher for ci/scenarios/run.py).
.DESCRIPTION
    Detects the interpreter with rule D5 (the first of python, python3, py -3 that answers within
    5 s with a version >= 3.9), forwards the options to the runner and propagates its exit code:
    0 = all PASS or justified SKIP, 1 = a FAIL (or -Live without claude), 2 = unknown option or scenario.
.PARAMETER List
    Lists the scenarios (with -Details: core subcommands and the files that prescribe them).
.PARAMETER Details
    With -List: core subcommands and the files that prescribe them (equivalent of --verbose).
.PARAMETER Scenario
    Runs only this scenario; several can be given, separated by commas.
.PARAMETER Live
    Also runs the live-* scenarios (real claude, consumes tokens).
.PARAMETER Keep
    Keeps the temporary folders and prints their path.
.PARAMETER Fixtures
    Fixtures folder (default: ci/fixtures).
.PARAMETER Report
    JSON report file (default: temporary folder).
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
    # True if the command answers within 5 s with a version >= 3.9.
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
    [Console]::Error.WriteLine('No Python >= 3.9 interpreter found (python, python3, py -3).')
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
$ErrorActionPreference = 'Continue'   # the runner's native stderr is not a launcher error
& $python[0] @prefix -B -I -S $runner @forward
exit $LASTEXITCODE
