#!/usr/bin/env bash
# Lance un cycle headless du laboratoire IA sur un protocole deja pre-enregistre.
# Usage : ci/lab.sh <chemin-protocole> [--yolo]
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

protocol=""
yolo=0
for arg in "$@"; do
    case "$arg" in
        --yolo)
            yolo=1
            ;;
        -h | --help)
            echo "Usage : ci/lab.sh <chemin-protocole> [--yolo]"
            exit 0
            ;;
        -*)
            echo "Option inconnue : $arg" >&2
            echo "Usage : ci/lab.sh <chemin-protocole> [--yolo]" >&2
            exit 2
            ;;
        *)
            if [ -n "$protocol" ]; then
                echo "Un seul chemin de protocole est attendu (recu en trop : $arg)" >&2
                exit 2
            fi
            protocol="$arg"
            ;;
    esac
done

if [ -z "$protocol" ]; then
    echo "Chemin du protocole pre-enregistre manquant." >&2
    echo "Usage : ci/lab.sh <chemin-protocole> [--yolo]" >&2
    exit 2
fi

if [ ! -f "$protocol" ]; then
    echo "Protocole introuvable : $protocol" >&2
    exit 1
fi

if ! grep -q "Statut : PRE-ENREGISTRE" "$protocol"; then
    echo "Protocole non pre-enregistre : '$protocol' ne contient pas 'Statut : PRE-ENREGISTRE'." >&2
    echo "Un cycle CI exige un protocole approuve par le PI." >&2
    exit 1
fi

log_dir="$repo_dir/lab-logs"
mkdir -p "$log_dir"
log_file="$log_dir/lab-$(date +%Y%m%d-%H%M%S).json"

export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
cmd=(claude -p "/lab-run '$protocol'" --output-format json --max-turns 150)

if [ "$yolo" -eq 1 ]; then
    cmd+=(--dangerously-skip-permissions)
else
    cmd+=(--permission-mode acceptEdits)
    cmd+=(--allowedTools "@ALLOWED@")
fi

echo "Protocole : $protocol"
echo "Mode      : $([ "$yolo" -eq 1 ] && echo 'YOLO (permissions ignorees)' || echo 'acceptEdits + liste blanche')"
echo "Journal   : $log_file"

set +e
"${cmd[@]}" | tee "$log_file"
status="${PIPESTATUS[0]}"
set -e

echo "Sortie claude : exit code $status"
exit "$status"
