# Files of a run under .claude/runs/ of the target repository:
#   <skill>-<timestamp>.jsonl            cycle journal
#   <skill>-<timestamp>.state.json       counter state between two calls
#   ship-pr-<timestamp>.registry.jsonl   findings registry (ship-pr)
# The whole directory is excluded from git (D3).

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from . import journal

RUNS_DIR = Path(".claude") / "runs"


def create(root: Path, skill: str, state: Dict[str, Any], now: Optional[datetime] = None) -> Path:
    runs = Path(root) / RUNS_DIR
    runs.mkdir(parents=True, exist_ok=True)
    moment = now or datetime.now()
    path = runs / journal.journal_name(skill, moment)
    while path.exists():
        moment += timedelta(seconds=1)
        path = runs / journal.journal_name(skill, moment)
    path.touch()
    state = dict(state)
    state["skill"] = skill
    state["root"] = str(Path(root).resolve())
    state.setdefault("begun", {})
    save_state(path, state)
    return path


def _base(run: Path) -> str:
    name = Path(run).name
    if not name.endswith(".jsonl"):
        raise ValueError("unexpected run path: %s" % run)
    return str(Path(run).parent / name[: -len(".jsonl")])


def state_path(run: Path) -> Path:
    return Path(_base(run) + ".state.json")


def registry_path(run: Path) -> Path:
    return Path(_base(run) + ".registry.jsonl")


def load_state(run: Path) -> Dict[str, Any]:
    path = state_path(run)
    if not path.exists():
        raise FileNotFoundError("unknown run (state missing): %s" % run)
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(run: Path, state: Dict[str, Any]) -> None:
    path = state_path(run)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(str(tmp), str(path))


def mark_begin(state: Dict[str, Any], slot: str, clock=time.time) -> None:
    """Timestamp taken by the core before a call, if the usage block is missing."""
    state.setdefault("begun", {})[slot] = clock()


def duration_ms(state: Dict[str, Any], slot: str, given: Optional[int], clock=time.time) -> int:
    if given is not None:
        if given < 0:
            raise ValueError("--duration-ms must be >= 0")
        state.get("begun", {}).pop(slot, None)
        return int(given)
    begun = state.get("begun", {}).pop(slot, None)
    if begun is None:
        raise ValueError("unknown duration for %s: pass --duration-ms or call 'begin' before the agent" % slot)
    return max(0, int(round((clock() - begun) * 1000)))


def display(path: Path) -> str:
    """Path relative to the current directory if possible, with '/' separators."""
    try:
        return Path(os.path.relpath(str(path))).as_posix()
    except ValueError:
        return Path(path).as_posix()
