# Outils partages des tests du noyau (pas un module de test).

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CORE = Path(__file__).resolve().parent.parent
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from hcore.proc import Result  # noqa: E402

HARNESS = CORE / "harness.py"
TESTS = Path(__file__).resolve().parent
# Fixtures du depot (absentes quand le noyau est copie dans un projet).
FIXTURES = CORE.parent.parent / "tests" / "fixtures"
HAS_FIXTURES = (FIXTURES / "merge-input").is_dir()
SKIP_FIXTURES = "fixtures du depot claude-skills absentes (copie du noyau dans un projet)"


def _make_writable_and_retry(func, path, exc_info) -> None:
    """onerror de rmtree : sous Windows, git cree ses objets en lecture seule."""
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    func(path)


def remove_tree(path: Path) -> None:
    """Supprime un dossier temporaire de test ; un echec n'est jamais silencieux."""
    if os.path.exists(str(path)):
        shutil.rmtree(str(path), onerror=_make_writable_and_retry)


class TempDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="hcore-"))
        self.addCleanup(remove_tree, self.tmp)


def harness(args: List[str], cwd: Path, stdin: Optional[str] = None,
            env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    full_env["PYTHONDONTWRITEBYTECODE"] = "1"
    full_env["PYTHONIOENCODING"] = "utf-8"
    if env:
        full_env.update(env)
    return subprocess.run([sys.executable, "-B", str(HARNESS)] + args, cwd=str(cwd),
                          input=stdin, capture_output=True, text=True, encoding="utf-8",
                          env=full_env, timeout=120)


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git"] + list(args), cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    if proc.returncode != 0:
        raise AssertionError("git %s : %s" % (" ".join(args), proc.stderr))
    return proc.stdout


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "Test")
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "core.autocrlf", "false")


class FakeRunner:
    """Runner simule : table (prefixe de commande -> Result), appels consignes."""

    def __init__(self, table: Optional[List[Tuple[Tuple[str, ...], Result]]] = None):
        self.table = list(table or [])
        self.calls: List[List[str]] = []

    def on(self, prefix: Tuple[str, ...], code: int = 0, out: str = "", err: str = "") -> "FakeRunner":
        self.table.insert(0, (prefix, Result(code, out, err)))
        return self

    def __call__(self, args: List[str], input: Optional[str] = None) -> Result:
        self.calls.append(list(args))
        for prefix, result in self.table:
            if tuple(args[: len(prefix)]) == prefix:
                return result
        return Result(0, "", "")

    def called(self, *prefix: str) -> List[List[str]]:
        return [c for c in self.calls if tuple(c[: len(prefix)]) == prefix]


# Contenu piege : ce qu'un shell mal employe (heredoc sans guillemets, echo '...')
# executerait, viderait ou tronquerait. Il doit transiter a l'identique par fichier.
TRAP = ("Piège : `date` puis $(whoami), $HOME, ${PATH}, $ARGUMENTS et $1 ; "
        "l'apostrophe d'O'Brien, des \"guillemets\", un antislash \\ et !! fin\nligne 2\n")


def write_output(root: Path, name: str, text: str) -> str:
    """Ce que fait l'outil Write prescrit par les SKILL.md : le contenu, tel quel,
    dans un fichier sous .claude/runs/ ; rend le chemin a passer au noyau."""
    path = Path(root) / ".claude" / "runs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return ".claude/runs/" + name


def verifier_block(verdict: str, tests_passed: bool, issues=None) -> str:
    return "Rapport.\n\n```json\n%s\n```\n" % json.dumps(
        {"verdict": verdict, "tests_passed": tests_passed, "issues": issues or []})


def reviewer_block(findings) -> str:
    return "Analyse.\n%s" % json.dumps({"findings": findings})


def validator_block(verdict: str, reason: str = "raison") -> str:
    return json.dumps({"verdict": verdict, "reason": reason})


def finding(file: str = "src/a.py", line: int = 3, title: str = "Bug", severity: str = "major") -> dict:
    return {"file": file, "line": line, "side": "RIGHT", "severity": severity, "title": title,
            "description": "scenario", "fix": "corriger"}
