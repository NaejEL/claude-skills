# Version of the claude-skills repository, and lag of an installation (Phase 3).
#
# - VS-01: `repo` = {commit, describe, dirty, path}, read with git from the real
#   folder of the repository (links and junctions resolved by harness.py). Without
#   git, outside a repository or after 5 s: commit null, describe "core-<version>",
#   dirty null; never an error.
# - VS-02: a project copy (.claude/harness/) reads the version that produced it
#   in MANIFEST.json (source "manifest"), never a neighbouring git repository.
# - VS-03: lag of an installed commit: up_to_date | behind (+ commits) | ahead |
#   diverged | unknown (commit absent: semver fallback on core_version).
# - VS-04: CORE_VERSION is bumped in hcore/__init__.py.

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from . import CORE_VERSION
from .proc import Runner

GIT_TIMEOUT = 5
MANIFEST = "MANIFEST.json"


def _git(path: Path, run: Optional[Callable[..., Any]], *args: str) -> Optional[str]:
    runner = run or Runner(cwd=str(path), timeout=GIT_TIMEOUT)
    res = runner(["git"] + list(args))
    if not res.ok:
        return None
    return res.out.strip()


def fallback(core_version: str = CORE_VERSION) -> Dict[str, Any]:
    return {"commit": None, "describe": "core-%s" % core_version, "dirty": None}


def repo_info(path: Path, run: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """VS-01: commit, describe and dirty flag of the repository at `path`."""
    path = Path(path)
    commit = _git(path, run, "rev-parse", "HEAD")
    describe = _git(path, run, "describe", "--tags", "--always", "--dirty") if commit else None
    if not commit or not describe:
        return dict(fallback(), path=str(path))
    return {"commit": commit, "describe": describe, "dirty": describe.endswith("-dirty"), "path": str(path)}


def read_manifest(core_dir: Path) -> Optional[Dict[str, Any]]:
    path = Path(core_dir) / MANIFEST
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("repo"), dict) else None


def report(core_dir: Path, run: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """`version` output: the git repository of a repository core, the manifest of a project copy."""
    core_dir = Path(core_dir)
    manifest = read_manifest(core_dir)
    if manifest is not None:
        repo = {k: manifest["repo"].get(k) for k in ("commit", "describe", "dirty")}
        return {"core_version": CORE_VERSION, "repo": repo, "source": "manifest"}
    return {"core_version": CORE_VERSION, "repo": repo_info(core_dir.parent.parent, run), "source": "git"}


def semver(value: Optional[str]) -> Tuple[int, ...]:
    if not value:
        return (0,)
    return tuple(int(x) for x in re.findall(r"\d+", value)[:3]) or (0,)


def lag(installed_commit: Optional[str], head: Optional[str], path: Path, installed_core: Optional[str] = None,
        core_version: str = CORE_VERSION, run: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """VS-03."""
    path = Path(path)
    known = bool(installed_commit and head and
                 _git(path, run, "cat-file", "-e", "%s^{commit}" % installed_commit) is not None)
    if not known:
        have, want = semver(installed_core), semver(core_version)
        status = "up_to_date" if have == want else "behind" if have < want else "ahead"
        return {"status": status if installed_core else "unknown", "commits": None}
    if installed_commit == head:
        return {"status": "up_to_date", "commits": 0}
    runner = run or Runner(cwd=str(path), timeout=GIT_TIMEOUT)
    if runner(["git", "merge-base", "--is-ancestor", installed_commit, head]).ok:
        count = _git(path, run, "rev-list", "--count", "%s..%s" % (installed_commit, head))
        return {"status": "behind", "commits": int(count) if count and count.isdigit() else None}
    if runner(["git", "merge-base", "--is-ancestor", head, installed_commit]).ok:
        return {"status": "ahead", "commits": None}
    return {"status": "diverged", "commits": None}
