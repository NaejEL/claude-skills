#!/usr/bin/env bash
# Lance les scenarios de bout en bout du harnais (lanceur mince de ci/scenarios/run.py).
# Detecte l'interpreteur par la regle D5 (premier de python, python3, py -3 qui repond en moins
# de 5 s avec une version >= 3.9), transmet les options au runner et propage son code de sortie.
#
# Usage : ci/test-harness.sh [--list [--verbose]] [--scenario ID]... [--live] [--keep]
#                            [--fixtures DOSSIER] [--report FICHIER] [-h]
# Codes : 0 = tout PASS ou SKIP motive, 1 = un FAIL (ou --live sans claude), 2 = option inconnue.
set -euo pipefail

# pwd -W (Git Bash) donne un chemin Windows que py.exe comprend ; ailleurs, pwd.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })"

find_python() {
    local t="" c
    command -v timeout >/dev/null 2>&1 && t="timeout 5"
    for c in python python3 "py -3"; do
        # $t et $c sont volontairement non quotes : "py -3" doit etre separe en deux mots.
        if $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep True >/dev/null; then
            echo "$c"
            return 0
        fi
    done
    return 1
}

if ! py="$(find_python)"; then
    echo "Aucun interpreteur Python >= 3.9 trouve (python, python3, py -3)." >&2
    exit 1
fi

rc=0
HTS_LAUNCHER=bash $py -B -I -S "$here/scenarios/run.py" "$@" || rc=$?
exit "$rc"
