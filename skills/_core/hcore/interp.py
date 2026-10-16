# Detection de l'interpreteur Python (D5).
#
# Une seule regle, celle que les SKILL.md appliquent en Bash : candidats
# essayes dans l'ordre python -> python3 -> py -3, chacun resolu par le PATH
# (comme `command -v` : ni le dossier courant, ni le dossier de l'interpreteur
# qui execute ce module), lance avec un delai d'expiration (le stub du
# Microsoft Store ne repond pas) et une verification de version (plancher
# 3.9). Le premier candidat valide gagne.

from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, List, Optional, Sequence

CANDIDATES: List[List[str]] = [["python"], ["python3"], ["py", "-3"]]
FLOOR = (3, 9)
TIMEOUT = 5.0
PROBE = "import sys; print('%d.%d.%d' % sys.version_info[:3])"


def resolve(name: str, path: Optional[str] = None) -> Optional[str]:
    """Chemin de l'executable `name` trouve dans le PATH, ou None.

    Equivalent de `command -v` : seul le PATH est parcouru, dans l'ordre (sous
    Windows, avec les extensions de PATHEXT). Un nom contenant un separateur
    de dossier est pris tel quel."""
    if os.path.dirname(name):
        return name if os.path.isfile(name) and os.access(name, os.X_OK) else None
    dirs = (os.environ.get("PATH", "") if path is None else path).split(os.pathsep)
    exts = [""]
    if sys.platform == "win32":
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep)
        exts = [e for e in pathext if e] if not os.path.splitext(name)[1] else [""]
    for folder in dirs:
        if not folder:
            continue
        for ext in exts:
            full = os.path.join(folder, name + ext)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return full
    return None


def probe(cmd: Sequence[str], timeout: float = TIMEOUT) -> Optional[tuple]:
    """Version du candidat, ou None s'il est absent, muet ou en erreur."""
    if not cmd:
        return None
    exe = resolve(cmd[0])
    if exe is None:
        return None
    try:
        proc = subprocess.run([exe] + list(cmd[1:]) + ["-c", PROBE], capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    parts = (proc.stdout or "").strip().splitlines()
    if not parts:
        return None
    try:
        return tuple(int(x) for x in parts[-1].strip().split("."))
    except ValueError:
        return None


def detect(candidates: Optional[Sequence[Sequence[str]]] = None, timeout: float = TIMEOUT,
           floor: tuple = FLOOR) -> Optional[Dict[str, object]]:
    """Premier candidat qui repond avant le delai avec une version >= floor."""
    tried = []
    for cmd in (candidates if candidates is not None else CANDIDATES):
        version = probe(cmd, timeout)
        tried.append({"command": list(cmd), "version": version})
        if version is not None and version[:2] >= floor:
            return {"command": list(cmd), "version": ".".join(str(v) for v in version), "tried": tried}
    return None
