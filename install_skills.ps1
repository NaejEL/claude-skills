#Requires -Version 5.1
<#
.SYNOPSIS
    Installe les skills de ce depot comme skills globaux Claude Code.
.DESCRIPTION
    Cree une jonction ~/.claude/skills/<nom> -> <repo>/skills/<nom> pour chaque skill.
    Les jonctions ne necessitent pas de droits administrateur. Idempotent :
    un lien deja correct est ignore, un dossier reel ou un lien divergent est
    signale sans etre modifie.

    Installe aussi les outils externes dont les skills ont besoin (voir la table
    Get-ToolPackage), en detectant le gestionnaire de paquets de la machine :
    winget, puis scoop, puis chocolatey, avec cargo en dernier recours.
.PARAMETER SkipTools
    Ne pas installer les outils externes manquants.
#>
[CmdletBinding()]
param(
    [Alias('SkipRipgrep')]
    [switch]$SkipTools
)

$ErrorActionPreference = 'Stop'

# ==========================================================================
# Couche generique : gestionnaire de paquets
# ==========================================================================

$script:PkgManager = $null
$script:PkgManagerResolved = $false

function Get-PackageManager {
    # Detecte une seule fois le gestionnaire de paquets utilisable.
    # Rend son nom, ou $null si aucun n'est disponible.
    if ($script:PkgManagerResolved) { return $script:PkgManager }
    $script:PkgManagerResolved = $true

    foreach ($candidate in 'winget', 'scoop', 'choco') {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            $script:PkgManager = $candidate
            break
        }
    }
    return $script:PkgManager
}

function Update-SessionPath {
    # winget, scoop et choco ecrivent le PATH dans le registre : la session
    # courante ne le voit pas sans ce rafraichissement.
    $parts = @(
        $env:Path,
        [Environment]::GetEnvironmentVariable('Path', 'Machine'),
        [Environment]::GetEnvironmentVariable('Path', 'User')
    ) | Where-Object { $_ }
    $env:Path = ($parts -join ';')
}

function Invoke-PackageInstall {
    param(
        [Parameter(Mandatory)][string]$Manager,
        [Parameter(Mandatory)][string]$Package
    )
    try {
        switch ($Manager) {
            'winget' {
                winget install --id $Package -e --source winget `
                    --silent --accept-package-agreements --accept-source-agreements
            }
            'scoop' { scoop install $Package }
            'choco' { choco install $Package -y --no-progress }
            'cargo' { cargo install $Package }
            default { Write-Warning "[outils] gestionnaire inconnu : $Manager"; return }
        }
    }
    catch {
        Write-Warning "[outils] $Manager a echoue : $($_.Exception.Message)"
    }
    Update-SessionPath
}

# ==========================================================================
# Table des outils requis par les skills.
# Ajouter un outil demain = une entree ici + une ligne dans la section
# « Outils externes » plus bas. L'identifiant de paquet ne coincide pas
# toujours avec le nom de la commande, ni d'un gestionnaire a l'autre.
# ==========================================================================

function Get-ToolPackage {
    param(
        [Parameter(Mandatory)][string]$Tool,
        [Parameter(Mandatory)][string]$Manager
    )
    switch ("${Tool}:${Manager}") {
        'ripgrep:winget' { return 'BurntSushi.ripgrep.MSVC' }
        'ripgrep:scoop'  { return 'ripgrep' }
        'ripgrep:choco'  { return 'ripgrep' }
        'ripgrep:cargo'  { return 'ripgrep' }
        default          { return $null }
    }
}

function Install-ToolIfMissing {
    param(
        [Parameter(Mandatory)][string]$Command,
        [Parameter(Mandatory)][string]$Tool,
        [Parameter(Mandatory)][string]$Purpose
    )

    $found = Get-Command $Command -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "[$Command] deja present : $($found.Source)"
        return $true
    }

    Write-Host "[$Command] absent ($Purpose) - installation automatique."

    $manager = Get-PackageManager
    if (-not $manager) {
        Write-Host "[$Command] aucun gestionnaire de paquets detecte."
    }
    else {
        $package = Get-ToolPackage -Tool $Tool -Manager $manager
        if ($package) {
            Write-Host "[$Command] via $manager ($package)..."
            Invoke-PackageInstall -Manager $manager -Package $package
        }
        else {
            Write-Host "[$Command] aucun paquet connu pour $manager."
        }
    }

    # Dernier recours : compilation depuis les sources.
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        $package = Get-ToolPackage -Tool $Tool -Manager 'cargo'
        if ($package -and (Get-Command cargo -ErrorAction SilentlyContinue)) {
            Write-Host "[$Command] repli sur cargo (compilation, plusieurs minutes)..."
            Invoke-PackageInstall -Manager 'cargo' -Package $package
        }
    }

    $found = Get-Command $Command -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "[$Command] installe : $($found.Source)"
        return $true
    }

    Write-Warning "[$Command] installation automatique impossible."
    return $false
}

# ==========================================================================
# Liaison des skills
# ==========================================================================

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

# ==========================================================================
# Outils externes
# ==========================================================================

$toolsMissing = $false
if ($SkipTools) {
    Write-Host '[outils] installation ignoree (-SkipTools).'
}
else {
    $ok = Install-ToolIfMissing -Command 'rg' -Tool 'ripgrep' `
        -Purpose 'serveur de connaissance du skill code-index'
    $toolsMissing = -not $ok
}

if ($toolsMissing) {
    Write-Warning @'
[outils] un outil externe manque. Les skills sont installes et fonctionnent ;
         seuls ceux qui en dependent resteront inoperants. Deux issues :
           - installer l'outil a la main, p. ex.
             winget install BurntSushi.ripgrep.MSVC
           - pour ripgrep uniquement, declarer un chemin dans le fichier non
             versionne .knowledge\config.local.json du depot cible :
             {"rg_path": "C:/chemin/vers/rg.exe"}
'@
}

if ($errors -gt 0) {
    Write-Warning "$errors element(s) non lie(s) : resoudre manuellement les conflits ci-dessus."
    exit 1
}
Write-Host "Installation terminee. Les skills sont disponibles dans toute nouvelle session Claude Code."
