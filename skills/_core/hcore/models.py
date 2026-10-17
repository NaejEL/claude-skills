# Reading of .claude/models.json and of --models "role=model;..." (D6:
# standalone module, not wired in this increment).
#
# Missing file -> every role is "inherit". --models applies to the current
# cycle only, without rewriting the file. Any unknown value or role is
# refused with an explicit message rather than silently ignored.

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

ALIASES = ("inherit", "opus", "fable", "sonnet", "haiku")
FULL_ID = re.compile(r"^claude-[a-z0-9][a-z0-9.\-\[\]]*$")


class ModelsError(ValueError):
    """Invalid model assignment."""


def check_model(value: str) -> str:
    if value in ALIASES or FULL_ID.match(value):
        return value
    raise ModelsError("unknown model: %r (expected: %s or a claude-* identifier)" % (value, ", ".join(ALIASES)))


def _check_role(role: str, roles: Optional[Iterable[str]]) -> str:
    if roles is not None and role not in set(roles):
        raise ModelsError("unknown role: %r" % (role,))
    return role


def load(path: Path, roles: Optional[Iterable[str]] = None) -> Dict[str, str]:
    path = Path(path)
    result: Dict[str, str] = {r: "inherit" for r in (roles or [])}
    if not path.exists():
        return result
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ModelsError("%s is not valid JSON: %s" % (path, exc))
    if not isinstance(data, dict):
        raise ModelsError("%s must contain a role -> model object" % path)
    for role, model in data.items():
        if not isinstance(model, str):
            raise ModelsError("non-text model for role %r" % role)
        result[_check_role(role, roles)] = check_model(model)
    return result


def parse_override(value: str, roles: Optional[Iterable[str]] = None) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for pair in value.split(";"):
        if not pair.strip():
            continue
        if "=" not in pair:
            raise ModelsError("--models pair without '=': %r" % pair)
        role, model = (p.strip() for p in pair.split("=", 1))
        result[_check_role(role, roles)] = check_model(model)
    if not result:
        raise ModelsError("--models is empty")
    return result


def split_arguments(arguments: str) -> Tuple[str, Optional[str]]:
    """Removes --models "..." from $ARGUMENTS; returns (rest, value or None)."""
    tokens = shlex.split(arguments or "", posix=True)
    rest, value, i = [], None, 0
    while i < len(tokens):
        if tokens[i] == "--models":
            if i + 1 >= len(tokens):
                raise ModelsError("--models expects a value")
            value, i = tokens[i + 1], i + 2
            continue
        rest.append(tokens[i])
        i += 1
    return " ".join(rest), value


def resolve(path: Path, override: Optional[str], roles: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Effective assignment: file, then --models for this cycle."""
    result = load(path, roles)
    if override:
        result.update(parse_override(override, roles))
    return result
