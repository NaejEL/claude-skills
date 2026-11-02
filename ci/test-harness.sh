#!/usr/bin/env bash
# Runs the harness end-to-end scenarios (thin launcher for ci/scenarios/run.py).
# Detects the interpreter with rule D5 (the first of python, python3, py -3 that answers within
# 5 s with a version >= 3.9), forwards the options to the runner and propagates its exit code.
#
# Usage: ci/test-harness.sh [--list [--verbose]] [--scenario ID]... [--live] [--keep]
#                           [--fixtures DIR] [--report FILE] [-h]
# Codes: 0 = all PASS or justified SKIP, 1 = a FAIL (or --live without claude), 2 = unknown option.
set -euo pipefail

# pwd -W (Git Bash) gives a Windows path that py.exe understands; elsewhere, pwd.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })"

find_python() {
    local t="" c
    command -v timeout >/dev/null 2>&1 && t="timeout 5"
    for c in python python3 "py -3"; do
        # $t and $c are deliberately unquoted: "py -3" must be split into two words.
        if $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep True >/dev/null; then
            echo "$c"
            return 0
        fi
    done
    return 1
}

if ! py="$(find_python)"; then
    echo "No Python >= 3.9 interpreter found (python, python3, py -3)." >&2
    exit 1
fi

rc=0
HTS_LAUNCHER=bash $py -B -I -S "$here/scenarios/run.py" "$@" || rc=$?
exit "$rc"
