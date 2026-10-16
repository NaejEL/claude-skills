# Fichiers d'un run sous .claude/runs/ du depot cible :
#   <skill>-<horodatage>.jsonl           journal de cycle
#   <skill>-<horodatage>.state.json      etat des compteurs entre deux appels
#   ship-pr-<horodatage>.registry.jsonl  registre des findings (ship-pr)
# Tout le dossier est exclu de git (D3).

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
        raise ValueError("chemin de run inattendu : %s" % run)
    return str(Path(run).parent / name[: -len(".jsonl")])


def state_path(run: Path) -> Path:
    return Path(_base(run) + ".state.json")


def registry_path(run: Path) -> Path:
    return Path(_base(run) + ".registry.jsonl")


def load_state(run: Path) -> Dict[str, Any]:
    path = state_path(run)
    if not path.exists():
        raise FileNotFoundError("run inconnu (etat absent) : %s" % run)
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(run: Path, state: Dict[str, Any]) -> None:
    path = state_path(run)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(str(tmp), str(path))


def mark_begin(state: Dict[str, Any], slot: str, clock=time.time) -> None:
    """Horodatage pris par le noyau avant un appel, si le bloc d'usage manque."""
    state.setdefault("begun", {})[slot] = clock()


def duration_ms(state: Dict[str, Any], slot: str, given: Optional[int], clock=time.time) -> int:
    if given is not None:
        if given < 0:
            raise ValueError("--duration-ms doit etre >= 0")
        state.get("begun", {}).pop(slot, None)
        return int(given)
    begun = state.get("begun", {}).pop(slot, None)
    if begun is None:
        raise ValueError("duree inconnue pour %s : passer --duration-ms ou appeler 'begin' avant l'agent" % slot)
    return max(0, int(round((clock() - begun) * 1000)))


def display(path: Path) -> str:
    """Chemin relatif au dossier courant si possible, en separateurs '/'."""
    try:
        return Path(os.path.relpath(str(path))).as_posix()
    except ValueError:
        return Path(path).as_posix()
