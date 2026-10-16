# Execution des commandes externes (gh, git) derriere une interface injectable,
# pour que les tests puissent simuler gh et git.
#
# Point d'injection de test : HCORE_GH / HCORE_GIT (tableau JSON remplacant
# l'executable) ne sont honores que si HCORE_TEST_MODE=1 est aussi pose. Hors
# de ce mode, ils sont ignores (avertissement sur stderr) ; dans ce mode, la
# CLI le signale dans chaque sortie JSON (cle "hcore_test_mode").

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

TEST_MODE_VAR = "HCORE_TEST_MODE"
TOOLS = ("gh", "git")


@dataclass
class Result:
    code: int
    out: str
    err: str

    @property
    def ok(self) -> bool:
        return self.code == 0


def test_mode() -> bool:
    return os.environ.get(TEST_MODE_VAR) == "1"


def overrides(warn: bool = True) -> Dict[str, List[str]]:
    """Remplacements actifs de gh/git (vide hors du mode test)."""
    active: Dict[str, List[str]] = {}
    for name in TOOLS:
        raw = os.environ.get("HCORE_" + name.upper())
        if not raw:
            continue
        if not test_mode():
            if warn:
                sys.stderr.write("AVERTISSEMENT : HCORE_%s ignore (%s=1 absent)\n" % (name.upper(), TEST_MODE_VAR))
            continue
        try:
            value = json.loads(raw)
        except ValueError:
            continue
        if isinstance(value, list) and value and all(isinstance(x, str) for x in value):
            active[name] = value
    return active


class Runner:
    """Lance une commande dans un dossier donne et rend un Result."""

    def __init__(self, cwd: Optional[str] = None, timeout: Optional[float] = None):
        self.cwd = cwd
        self.timeout = timeout
        self.overrides = overrides()

    def __call__(self, args: List[str], input: Optional[str] = None) -> Result:
        if args and args[0] in self.overrides:
            args = self.overrides[args[0]] + list(args[1:])
        try:
            proc = subprocess.run(
                args,
                cwd=self.cwd,
                input=input,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:
            return Result(127, "", str(exc))
        except subprocess.TimeoutExpired:
            return Result(124, "", "delai depasse : " + " ".join(args))
        return Result(proc.returncode, proc.stdout or "", proc.stderr or "")
