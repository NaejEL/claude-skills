# Lecture de .claude/models.json et de --models "role=modele;..." (D6 : module
# seul, non branche dans cet increment).
#
# Fichier absent -> chaque role en "inherit". --models s'applique pour le cycle
# seulement, sans reecrire le fichier. Toute valeur ou tout role inconnu est
# refuse avec un message explicite plutot que silencieusement ignore.

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

ALIASES = ("inherit", "opus", "fable", "sonnet", "haiku")
FULL_ID = re.compile(r"^claude-[a-z0-9][a-z0-9.\-\[\]]*$")


class ModelsError(ValueError):
    """Affectation de modeles invalide."""


def check_model(value: str) -> str:
    if value in ALIASES or FULL_ID.match(value):
        return value
    raise ModelsError("modele inconnu : %r (attendu : %s ou un identifiant claude-*)" % (value, ", ".join(ALIASES)))


def _check_role(role: str, roles: Optional[Iterable[str]]) -> str:
    if roles is not None and role not in set(roles):
        raise ModelsError("role inconnu : %r" % (role,))
    return role


def load(path: Path, roles: Optional[Iterable[str]] = None) -> Dict[str, str]:
    path = Path(path)
    result: Dict[str, str] = {r: "inherit" for r in (roles or [])}
    if not path.exists():
        return result
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ModelsError("%s n'est pas du JSON valide : %s" % (path, exc))
    if not isinstance(data, dict):
        raise ModelsError("%s doit contenir un objet role -> modele" % path)
    for role, model in data.items():
        if not isinstance(model, str):
            raise ModelsError("modele non textuel pour le role %r" % role)
        result[_check_role(role, roles)] = check_model(model)
    return result


def parse_override(value: str, roles: Optional[Iterable[str]] = None) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for pair in value.split(";"):
        if not pair.strip():
            continue
        if "=" not in pair:
            raise ModelsError("paire --models sans '=' : %r" % pair)
        role, model = (p.strip() for p in pair.split("=", 1))
        result[_check_role(role, roles)] = check_model(model)
    if not result:
        raise ModelsError("--models est vide")
    return result


def split_arguments(arguments: str) -> Tuple[str, Optional[str]]:
    """Retire --models "..." de $ARGUMENTS ; rend (reste, valeur ou None)."""
    tokens = shlex.split(arguments or "", posix=True)
    rest, value, i = [], None, 0
    while i < len(tokens):
        if tokens[i] == "--models":
            if i + 1 >= len(tokens):
                raise ModelsError("--models attend une valeur")
            value, i = tokens[i + 1], i + 2
            continue
        rest.append(tokens[i])
        i += 1
    return " ".join(rest), value


def resolve(path: Path, override: Optional[str], roles: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Affectation effective : fichier, puis --models pour ce cycle."""
    result = load(path, roles)
    if override:
        result.update(parse_override(override, roles))
    return result
