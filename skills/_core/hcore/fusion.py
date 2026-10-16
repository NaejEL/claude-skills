# Fusions de fichiers de software-factory, jamais d'ecrasement.
#
# - SF-01 : .claude/settings.json, regles permissions.deny en Read(...) de la
#   stack detectee plus les regles generiques ; tableaux fusionnes sans doublon,
#   toute cle existante preservee.
# - SF-02 : .vscode/tasks.json (version 2.0.0), input factorySpec et trois
#   taches Factory ajoutes une seule fois ; taches et inputs existants preserves.
# - SF-03 : .gitignore complete sans dupliquer une ligne (factory-logs/,
#   .claude/runs/).
# - SF-04 : etat de chaque fichier : cree / fusionne / identique /
#   personnalise-conserve. Un fichier inchange n'est pas reecrit (seconde
#   application identique octet pour octet).
# - Lecture tolerante : BOM UTF-8 et JSONC (commentaires, virgules finales)
#   acceptes, comme les ecrivent VS Code et les outils Windows. Un JSON strict
#   est re-serialise ; un JSONC est complete par insertion de texte, ses
#   commentaires conserves (voir jsonc.py). BOM et fin de ligne CRLF conserves.
# - Tout ou rien : les trois fusions sont calculees avant toute ecriture ; un
#   fichier illisible fait echouer l'ensemble sans rien modifier.
# - D1 : copie de _core dans le projet sous .claude/harness/, jamais melangee
#   avec un noyau existant different (rien n'est copie dans ce cas).

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from . import jsonc

CREATED = "créé"
MERGED = "fusionné"
IDENTICAL = "identique"
KEPT = "personnalisé-conservé"

STACK_DENY = {
    "node": ["Read(./node_modules/**)", "Read(./dist/**)"],
    "dotnet": ["Read(./**/bin/**)", "Read(./**/obj/**)"],
    "python": ["Read(./.venv/**)", "Read(./**/__pycache__/**)", "Read(./.pytest_cache/**)"],
    "cpp": ["Read(./build/**)"],
    "rust": ["Read(./target/**)"],
}
GENERIC_DENY = ["Read(./factory-logs/**)", "Read(./.git/objects/**)"]
GITIGNORE_LINES = ["factory-logs/", ".claude/runs/"]

FACTORY_INPUT = {
    "id": "factorySpec",
    "type": "promptString",
    "description": "Chemin de la spec approuvée (specs/SPEC-*.md)",
}
FACTORY_TASKS = [
    {
        "label": "Factory: CI run",
        "type": "shell",
        "command": "./ci/factory.sh ${input:factorySpec}",
        "windows": {"command": "pwsh -File ci/factory.ps1 ${input:factorySpec}"},
        "problemMatcher": [],
    },
    {
        "label": "Factory: CI run (YOLO)",
        "type": "shell",
        "command": "./ci/factory.sh ${input:factorySpec} --yolo",
        "windows": {"command": "pwsh -File ci/factory.ps1 ${input:factorySpec} -Yolo"},
        "problemMatcher": [],
    },
    {
        "label": "Factory: nouvelle spec (session)",
        "type": "shell",
        "command": "echo 'Ouvrir Claude Code et taper : /factory-run \"<votre besoin>\"'",
        "problemMatcher": [],
    },
]


class FusionError(ValueError):
    """Fichier existant illisible : on ne le reecrit pas."""


def deny_rules(stacks: Iterable[str]) -> List[str]:
    """SF-01 : regles de la stack detectee uniquement, puis les generiques."""
    rules: List[str] = []
    for stack in stacks:
        if stack not in STACK_DENY:
            raise FusionError("stack inconnue : %r (connues : %s)" % (stack, ", ".join(STACK_DENY)))
        rules.extend(r for r in STACK_DENY[stack] if r not in rules)
    rules.extend(r for r in GENERIC_DENY if r not in rules)
    return rules


def merge_settings(existing: Optional[Dict[str, Any]], stacks: Iterable[str]) -> Dict[str, Any]:
    data = json.loads(json.dumps(existing)) if existing is not None else {}
    if not isinstance(data, dict):
        raise FusionError("settings.json n'est pas un objet JSON")
    perms = data.setdefault("permissions", {})
    if not isinstance(perms, dict):
        raise FusionError("permissions n'est pas un objet")
    deny = perms.setdefault("deny", [])
    if not isinstance(deny, list):
        raise FusionError("permissions.deny n'est pas un tableau")
    for rule in deny_rules(stacks):
        if rule not in deny:
            deny.append(rule)
    return data


def merge_tasks(existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """SF-02."""
    data = json.loads(json.dumps(existing)) if existing is not None else {}
    if not isinstance(data, dict):
        raise FusionError("tasks.json n'est pas un objet JSON")
    data.setdefault("version", "2.0.0")
    inputs = data.setdefault("inputs", [])
    tasks = data.setdefault("tasks", [])
    if not isinstance(inputs, list) or not isinstance(tasks, list):
        raise FusionError("inputs et tasks doivent etre des tableaux")
    if not any(isinstance(i, dict) and i.get("id") == FACTORY_INPUT["id"] for i in inputs):
        inputs.append(dict(FACTORY_INPUT))
    labels = {t.get("label") for t in tasks if isinstance(t, dict)}
    for task in FACTORY_TASKS:
        if task["label"] not in labels:
            tasks.append(json.loads(json.dumps(task)))
    return data


def merge_gitignore(text: Optional[str], lines: Iterable[str] = GITIGNORE_LINES) -> str:
    """SF-03 : lignes ajoutees avec la fin de ligne du fichier (CRLF conserve)."""
    content = text or ""
    present = {line.strip() for line in content.splitlines()}
    missing = [line for line in lines if line not in present]
    if not missing:
        return content
    nl = "\r\n" if "\r\n" in content else "\n"
    if content and not content.endswith("\n"):
        content += nl
    return content + "".join(line + nl for line in missing)


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _read_text(path: Path) -> Optional[str]:
    """Texte brut (fins de ligne et BOM intacts), ou None si absent."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8", newline="") as fh:
        try:
            return fh.read()
        except UnicodeDecodeError as exc:
            raise FusionError("%s n'est pas encode en UTF-8 (encodage attendu : UTF-8, BOM accepte ; "
                              "octet invalide en position %d), fichier laisse intact" % (path, exc.start))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".hcore-tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(str(tmp), str(path))


def _plan_json(path: Path, merged_of: Callable[[Any], Any]) -> Tuple[str, Optional[str]]:
    """Etat et nouveau texte d'un fichier JSON/JSONC, sans rien ecrire."""
    raw = _read_text(path)
    if raw is None:
        return CREATED, dump_json(merged_of(None))
    try:
        doc = jsonc.loads(raw)
    except ValueError as exc:
        raise FusionError("%s n'est pas du JSON valide, fusion refusee : %s" % (path, exc))
    merged = merged_of(doc.value)
    if json.dumps(merged) == json.dumps(doc.value):
        return IDENTICAL, None
    if doc.loose:
        try:
            return MERGED, doc.patched(merged)
        except ValueError as exc:
            raise FusionError("%s : fusion JSONC impossible, fichier laisse intact : %s" % (path, exc))
    text = dump_json(merged)
    if doc.newline == "\r\n":
        text = text.replace("\n", "\r\n")
    return MERGED, (jsonc.BOM if doc.bom else "") + text


def _plan_gitignore(path: Path) -> Tuple[str, Optional[str]]:
    before = _read_text(path)
    after = merge_gitignore(before)
    if before is None:
        return CREATED, after
    if after == before:
        return IDENTICAL, None
    return MERGED, after


def apply(root: Path, stacks: Iterable[str]) -> Dict[str, str]:
    """SF-01 a SF-04 : calcule les trois fusions, puis ecrit (tout ou rien)."""
    root = Path(root)
    stacks = list(stacks)
    plans = {
        ".claude/settings.json": _plan_json(root / ".claude" / "settings.json",
                                            lambda e: merge_settings(e, stacks)),
        ".vscode/tasks.json": _plan_json(root / ".vscode" / "tasks.json", merge_tasks),
        ".gitignore": _plan_gitignore(root / ".gitignore"),
    }
    for rel, (_, text) in plans.items():
        if text is not None:
            _write(root / rel, text)
    return {rel: state for rel, (state, _) in plans.items()}


def install_file(dest: Path, content: str) -> str:
    """SF-04 : un fichier genere n'ecrase jamais un fichier existant different."""
    dest = Path(dest)
    state = file_state(dest, content)
    if state == CREATED:
        _write(dest, content)
    return state


def file_state(dest: Path, content: str) -> str:
    """Etat qu'aurait l'installation de `content` en `dest`, sans rien ecrire."""
    if not dest.exists():
        return CREATED
    current = _read_text(dest) or ""
    if current.replace("\r\n", "\n") == content.replace("\r\n", "\n"):
        return IDENTICAL
    return KEPT


def copy_core(core_dir: Path, root: Path) -> Dict[str, Any]:
    """D1 : copie _core tel quel sous <root>/.claude/harness/, sans bytecode.

    Jamais de noyau melange : si un fichier deja present differe de la source
    (noyau personnalise ou d'une autre version), il reste personnalise-conserve
    et RIEN n'est copie, pas meme les fichiers absents ; `copied` vaut False et
    `blocked_by` liste les fichiers en cause, a signaler a l'utilisateur."""
    core_dir, dest_dir = Path(core_dir), Path(root) / ".claude" / "harness"
    plan: List[Tuple[str, Path, str, str]] = []
    for src in sorted(core_dir.rglob("*")):
        rel = src.relative_to(core_dir)
        if src.is_dir() or "__pycache__" in rel.parts or src.suffix in (".pyc", ".pyo"):
            continue
        content = src.read_text(encoding="utf-8")
        shown = (Path(".claude/harness") / rel).as_posix()
        plan.append((shown, dest_dir / rel, content, file_state(dest_dir / rel, content)))
    blocked = [shown for shown, _, _, state in plan if state == KEPT]
    if blocked:
        return {"copied": False, "blocked_by": blocked,
                "not_copied": [shown for shown, _, _, state in plan if state == CREATED],
                "files": {shown: state for shown, _, _, state in plan if state != CREATED}}
    for shown, dest, content, state in plan:
        if state == CREATED:
            _write(dest, content)
    return {"copied": True, "blocked_by": [], "not_copied": [],
            "files": {shown: state for shown, _, _, state in plan}}
