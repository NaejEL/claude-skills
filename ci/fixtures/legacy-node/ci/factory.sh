#!/usr/bin/env bash
# Lance un cycle headless de l'usine logicielle sur une spec deja approuvee.
# Usage : ci/factory.sh <chemin-spec> [--yolo]
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

spec=""
yolo=0
for arg in "$@"; do
    case "$arg" in
        --yolo)
            yolo=1
            ;;
        -h | --help)
            echo "Usage : ci/factory.sh <chemin-spec> [--yolo]"
            exit 0
            ;;
        -*)
            echo "Option inconnue : $arg" >&2
            echo "Usage : ci/factory.sh <chemin-spec> [--yolo]" >&2
            exit 2
            ;;
        *)
            if [ -n "$spec" ]; then
                echo "Un seul chemin de spec est attendu (recu en trop : $arg)" >&2
                exit 2
            fi
            spec="$arg"
            ;;
    esac
done

if [ -z "$spec" ]; then
    echo "Chemin de la spec approuvee manquant." >&2
    echo "Usage : ci/factory.sh <chemin-spec> [--yolo]" >&2
    exit 2
fi

if [ ! -f "$spec" ]; then
    echo "Spec introuvable : $spec" >&2
    exit 1
fi

if ! grep -q "Statut : APPROUVEE" "$spec"; then
    echo "Spec non approuvee : '$spec' ne contient pas 'Statut : APPROUVEE'." >&2
    echo "Un cycle CI exige une spec validee par le Product Owner." >&2
    exit 1
fi

log_dir="$repo_dir/factory-logs"
mkdir -p "$log_dir"
log_file="$log_dir/factory-$(date +%Y%m%d-%H%M%S).json"

cmd=(claude -p "/factory-run '$spec'" --output-format json --max-turns 100)

if [ "$yolo" -eq 1 ]; then
    cmd+=(--dangerously-skip-permissions)
else
    cmd+=(--permission-mode acceptEdits)
    cmd+=(--allowedTools "Read,Glob,Grep,Write,Edit,Bash(git *),Bash(bash *),Bash(bats *),Bash(shellcheck *),Bash(pwsh *)")
fi

echo "Spec      : $spec"
echo "Mode      : $([ "$yolo" -eq 1 ] && echo 'YOLO (permissions ignorees)' || echo 'acceptEdits + liste blanche')"
echo "Journal   : $log_file"

set +e
"${cmd[@]}" | tee "$log_file"
status="${PIPESTATUS[0]}"
set -e

echo "Sortie claude : exit code $status"
exit "$status"
