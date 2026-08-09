#!/usr/bin/env bash
# Installe les skills de ce depot comme skills globaux Claude Code.
# Cree un lien symbolique ~/.claude/skills/<nom> -> <repo>/skills/<nom> pour
# chaque skill. Idempotent : un lien deja correct est ignore, un dossier reel
# ou un lien divergent est signale sans etre modifie.
set -euo pipefail

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

if [ "$errors" -gt 0 ]; then
    echo "$errors element(s) non lie(s) : resoudre manuellement les conflits ci-dessus." >&2
    exit 1
fi
echo "Installation terminee. Les skills sont disponibles dans toute nouvelle session Claude Code."
