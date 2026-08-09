#Requires -Version 5.1
<#
.SYNOPSIS
    Installe les skills de ce depot comme skills globaux Claude Code.
.DESCRIPTION
    Cree une jonction ~/.claude/skills/<nom> -> <repo>/skills/<nom> pour chaque skill.
    Les jonctions ne necessitent pas de droits administrateur. Idempotent :
    un lien deja correct est ignore, un dossier reel ou un lien divergent est
    signale sans etre modifie.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoSkills = Join-Path $PSScriptRoot 'skills'
$targetRoot = Join-Path $HOME '.claude\skills'

if (-not (Test-Path $repoSkills)) {
    throw "Dossier introuvable : $repoSkills"
}

if (-not (Test-Path $targetRoot)) {
    New-Item -ItemType Directory -Path $targetRoot | Out-Null
    Write-Host "[dir] $targetRoot cree"
}

$errors = 0
Get-ChildItem -Path $repoSkills -Directory | ForEach-Object {
    $name = $_.Name
    $source = $_.FullName
    $link = Join-Path $targetRoot $name

    if (Test-Path $link) {
        $item = Get-Item $link -Force
        $currentTarget = @($item.Target)[0]
        if ($item.LinkType -and $currentTarget -and
            ($currentTarget.TrimEnd('\') -ieq $source.TrimEnd('\'))) {
            Write-Host "[ok]  $name deja lie -> $source"
        }
        else {
            Write-Warning "[skip] $link existe deja (dossier reel ou lien vers '$currentTarget') - non modifie"
            $script:errors++
        }
        return
    }

    New-Item -ItemType Junction -Path $link -Target $source | Out-Null
    Write-Host "[new] $name -> $source"
}

if ($errors -gt 0) {
    Write-Warning "$errors element(s) non lie(s) : resoudre manuellement les conflits ci-dessus."
    exit 1
}
Write-Host "Installation terminee. Les skills sont disponibles dans toute nouvelle session Claude Code."
