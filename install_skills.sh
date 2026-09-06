#!/usr/bin/env bash
# Installe les skills de ce depot comme skills globaux Claude Code.
# Cree un lien symbolique ~/.claude/skills/<nom> -> <repo>/skills/<nom> pour
# chaque skill. Idempotent : un lien deja correct est ignore, un dossier reel
# ou un lien divergent est signale sans etre modifie.
#
# Installe aussi les outils externes dont les skills ont besoin (voir la table
# tool_package plus bas), en detectant le gestionnaire de paquets de la
# machine. Desactivable avec --skip-tools.
#
# Compatible bash 3.2 (macOS) : pas de tableau associatif.
set -euo pipefail

skip_tools=0
for arg in "$@"; do
    case "$arg" in
        --skip-tools|--skip-ripgrep) skip_tools=1 ;;
        -h|--help)
            echo "Usage: $(basename "$0") [--skip-tools]"
            echo "  --skip-tools  ne pas installer les outils externes manquants"
            exit 0
            ;;
        *)
            echo "Argument inconnu : $arg (attendu : --skip-tools)" >&2
            exit 1
            ;;
    esac
done

# ==========================================================================
# Couche generique : gestionnaire de paquets
# ==========================================================================

# Detecte une seule fois le gestionnaire de paquets utilisable. Ecrit son nom
# sur stdout, ou rien si aucun n'est disponible.
PKG_MANAGER_CACHE=""
PKG_MANAGER_DONE=0
detect_pkg_manager() {
    if [ "$PKG_MANAGER_DONE" -eq 1 ]; then
        printf '%s' "$PKG_MANAGER_CACHE"
        return 0
    fi
    PKG_MANAGER_DONE=1

    local candidates=""
    case "$(uname -s)" in
        Darwin)               candidates="brew port" ;;
        MINGW*|MSYS*|CYGWIN*) candidates="winget scoop choco" ;;
        *)                    candidates="apt-get dnf paru yay pacman zypper apk xbps-install nix-env brew" ;;
    esac

    local candidate
    for candidate in $candidates; do
        if command -v "$candidate" >/dev/null 2>&1; then
            case "$candidate" in
                apt-get)      PKG_MANAGER_CACHE="apt" ;;
                xbps-install) PKG_MANAGER_CACHE="xbps" ;;
                nix-env)      PKG_MANAGER_CACHE="nix" ;;
                *)            PKG_MANAGER_CACHE="$candidate" ;;
            esac
            break
        fi
    done

    printf '%s' "$PKG_MANAGER_CACHE"
}

# Prefixe d'elevation, vide si root ou si sudo est absent.
sudo_prefix() {
    if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
        echo "sudo"
    fi
}

# pkg_install <gestionnaire> <identifiant-de-paquet>
pkg_install() {
    local mgr="$1" pkg="$2"
    local sudo_cmd
    sudo_cmd="$(sudo_prefix)"
    case "$mgr" in
        winget)
            winget install --id "$pkg" -e --source winget \
                --silent --accept-package-agreements --accept-source-agreements
            ;;
        scoop)  scoop install "$pkg" ;;
        choco)  choco install "$pkg" -y --no-progress ;;
        brew)   brew install "$pkg" ;;
        port)   $sudo_cmd port install "$pkg" ;;
        apt)    $sudo_cmd apt-get update -qq && $sudo_cmd apt-get install -y "$pkg" ;;
        dnf)    $sudo_cmd dnf install -y "$pkg" ;;
        paru)   paru -S --needed --noconfirm "$pkg" ;;
        yay)    yay -S --needed --noconfirm "$pkg" ;;
        pacman) $sudo_cmd pacman -S --needed --noconfirm "$pkg" ;;
        zypper) $sudo_cmd zypper --non-interactive install "$pkg" ;;
        apk)    $sudo_cmd apk add "$pkg" ;;
        xbps)   $sudo_cmd xbps-install -y "$pkg" ;;
        nix)    nix-env -iA "$pkg" ;;
        cargo)  cargo install "$pkg" ;;
        *)      return 1 ;;
    esac
}

# ==========================================================================
# Table des outils requis par les skills.
# Ajouter un outil demain = une entree ici + une ligne dans la section
# « Outils externes » plus bas. Le nom du paquet ne coincide pas toujours avec
# le nom de la commande, ni d'un gestionnaire a l'autre.
# ==========================================================================

# tool_package <outil> <gestionnaire> -> identifiant de paquet sur stdout
tool_package() {
    case "$1:$2" in
        ripgrep:winget) echo "BurntSushi.ripgrep.MSVC" ;;
        ripgrep:nix)    echo "nixpkgs.ripgrep" ;;
        ripgrep:*)      echo "ripgrep" ;;
        *)              return 1 ;;
    esac
}

# ensure_tool <commande> <outil> <a-quoi-il-sert>
ensure_tool() {
    local cmd="$1" tool="$2" purpose="$3"

    if command -v "$cmd" >/dev/null 2>&1; then
        echo "[$cmd] deja present : $(command -v "$cmd")"
        return 0
    fi

    echo "[$cmd] absent ($purpose) - installation automatique."

    local mgr pkg
    mgr="$(detect_pkg_manager)"
    if [ -z "$mgr" ]; then
        echo "[$cmd] aucun gestionnaire de paquets detecte."
    elif pkg="$(tool_package "$tool" "$mgr")"; then
        echo "[$cmd] via $mgr ($pkg)..."
        pkg_install "$mgr" "$pkg" || true
        hash -r 2>/dev/null || true
    else
        echo "[$cmd] aucun paquet connu pour $mgr."
    fi

    # Dernier recours : compilation depuis les sources.
    if ! command -v "$cmd" >/dev/null 2>&1 && command -v cargo >/dev/null 2>&1 \
        && pkg="$(tool_package "$tool" cargo)"; then
        echo "[$cmd] repli sur cargo (compilation, plusieurs minutes)..."
        pkg_install cargo "$pkg" || true
        hash -r 2>/dev/null || true
    fi

    if command -v "$cmd" >/dev/null 2>&1; then
        echo "[$cmd] installe : $(command -v "$cmd")"
        return 0
    fi

    echo "[$cmd] installation automatique impossible." >&2
    return 1
}

# ==========================================================================
# Liaison des skills
# ==========================================================================

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skills_src="$repo_dir/skills"
target_root="$HOME/.claude/skills"

if [ ! -d "$skills_src" ]; then
    echo "Dossier introuvable : $skills_src" >&2
    exit 1
fi

mkdir -p "$target_root"

errors=0
for dir in "$skills_src"/*/; do
    [ -d "$dir" ] || continue
    src="${dir%/}"
    name="$(basename "$src")"
    link="$target_root/$name"

    if [ -L "$link" ]; then
        current="$(readlink "$link")"
        if [ "$current" = "$src" ]; then
            echo "[ok]  $name deja lie -> $src"
        else
            echo "[skip] $link pointe vers '$current' (attendu '$src') - non modifie" >&2
            errors=$((errors + 1))
        fi
    elif [ -e "$link" ]; then
        echo "[skip] $link existe deja (dossier reel) - non modifie" >&2
        errors=$((errors + 1))
    else
        ln -s "$src" "$link"
        echo "[new] $name -> $src"
    fi
done

# ==========================================================================
# Outils externes
# ==========================================================================

tools_missing=0
if [ "$skip_tools" -eq 1 ]; then
    echo "[outils] installation ignoree (--skip-tools)."
else
    ensure_tool rg ripgrep "serveur de connaissance du skill code-index" || tools_missing=1
fi

if [ "$tools_missing" -eq 1 ]; then
    cat >&2 <<'MSG'
[outils] un outil externe manque. Les skills sont installes et fonctionnent ;
         seuls ceux qui en dependent resteront inoperants. Deux issues :
           - installer l'outil avec le gestionnaire de paquets de la machine ;
           - pour ripgrep uniquement, declarer un chemin dans le fichier non
             versionne .knowledge/config.local.json du depot cible :
             {"rg_path": "/chemin/vers/rg"}
MSG
fi

if [ "$errors" -gt 0 ]; then
    echo "$errors element(s) non lie(s) : resoudre manuellement les conflits ci-dessus." >&2
    exit 1
fi
echo "Installation terminee. Les skills sont disponibles dans toute nouvelle session Claude Code."
