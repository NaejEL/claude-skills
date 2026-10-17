# software-factory file merges, never an overwrite.
#
# - SF-01: .claude/settings.json, permissions.deny rules as Read(...) for the
#   detected stack plus the generic rules; arrays merged without duplicates,
#   every existing key preserved.
# - SF-02: .vscode/tasks.json (version 2.0.0), factorySpec input and three
#   Factory tasks added only once; existing tasks and inputs preserved.
# - SF-03: .gitignore completed without duplicating a line (factory-logs/,
#   .claude/runs/).
# - SF-04: state of each file: created / merged / identical /
#   customized-kept (the state values below are the French labels shared by
#   all the skills and are kept as is). An unchanged file is not rewritten
#   (second application byte-for-byte identical).
# - Tolerant reading: UTF-8 BOM and JSONC (comments, trailing commas)
#   accepted, as VS Code and Windows tools write them. A strict JSON file is
#   re-serialized; a JSONC file is completed by inserting text, its comments
#   kept (see jsonc.py). BOM and CRLF line endings kept.
# - All or nothing: the three merges are computed before any write; an
#   unreadable file makes the whole operation fail without modifying anything.
# - D1: copy of _core into the project under .claude/harness/, never mixed
#   with a different existing core (nothing is copied in that case).

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
    "description": "Path of the approved spec (specs/SPEC-*.md)",
}
# The task labels are the SF-02 deduplication keys of existing projects: kept as is.
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
        "command": "echo 'Open Claude Code and type: /factory-run \"<your need>\"'",
        "problemMatcher": [],
    },
]


class FusionError(ValueError):
    """Unreadable existing file: it is not rewritten."""


def deny_rules(stacks: Iterable[str]) -> List[str]:
    """SF-01: rules of the detected stack only, then the generic ones."""
    rules: List[str] = []
    for stack in stacks:
        if stack not in STACK_DENY:
            raise FusionError("unknown stack: %r (known: %s)" % (stack, ", ".join(STACK_DENY)))
        rules.extend(r for r in STACK_DENY[stack] if r not in rules)
    rules.extend(r for r in GENERIC_DENY if r not in rules)
    return rules


def merge_settings(existing: Optional[Dict[str, Any]], stacks: Iterable[str]) -> Dict[str, Any]:
    data = json.loads(json.dumps(existing)) if existing is not None else {}
    if not isinstance(data, dict):
        raise FusionError("settings.json is not a JSON object")
    perms = data.setdefault("permissions", {})
    if not isinstance(perms, dict):
        raise FusionError("permissions is not an object")
    deny = perms.setdefault("deny", [])
    if not isinstance(deny, list):
        raise FusionError("permissions.deny is not an array")
    for rule in deny_rules(stacks):
        if rule not in deny:
            deny.append(rule)
    return data


def merge_tasks(existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """SF-02."""
    data = json.loads(json.dumps(existing)) if existing is not None else {}
    if not isinstance(data, dict):
        raise FusionError("tasks.json is not a JSON object")
    data.setdefault("version", "2.0.0")
    inputs = data.setdefault("inputs", [])
    tasks = data.setdefault("tasks", [])
    if not isinstance(inputs, list) or not isinstance(tasks, list):
        raise FusionError("inputs and tasks must be arrays")
    if not any(isinstance(i, dict) and i.get("id") == FACTORY_INPUT["id"] for i in inputs):
        inputs.append(dict(FACTORY_INPUT))
    labels = {t.get("label") for t in tasks if isinstance(t, dict)}
    for task in FACTORY_TASKS:
        if task["label"] not in labels:
            tasks.append(json.loads(json.dumps(task)))
    return data


def merge_gitignore(text: Optional[str], lines: Iterable[str] = GITIGNORE_LINES) -> str:
    """SF-03: lines added with the file's line ending (CRLF kept)."""
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
    """Raw text (line endings and BOM intact), or None if absent."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8", newline="") as fh:
        try:
            return fh.read()
        except UnicodeDecodeError as exc:
            raise FusionError("%s is not UTF-8 encoded (expected encoding: UTF-8, BOM accepted; "
                              "invalid byte at position %d), file left untouched" % (path, exc.start))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".hcore-tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(str(tmp), str(path))


def _plan_json(path: Path, merged_of: Callable[[Any], Any]) -> Tuple[str, Optional[str]]:
    """State and new text of a JSON/JSONC file, without writing anything."""
    raw = _read_text(path)
    if raw is None:
        return CREATED, dump_json(merged_of(None))
    try:
        doc = jsonc.loads(raw)
    except ValueError as exc:
        raise FusionError("%s is not valid JSON, merge refused: %s" % (path, exc))
    merged = merged_of(doc.value)
    if json.dumps(merged) == json.dumps(doc.value):
        return IDENTICAL, None
    if doc.loose:
        try:
            return MERGED, doc.patched(merged)
        except ValueError as exc:
            raise FusionError("%s: JSONC merge impossible, file left untouched: %s" % (path, exc))
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
    """SF-01 to SF-04: computes the three merges, then writes (all or nothing)."""
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
    """SF-04: a generated file never overwrites a different existing file."""
    dest = Path(dest)
    state = file_state(dest, content)
    if state == CREATED:
        _write(dest, content)
    return state


def file_state(dest: Path, content: str) -> str:
    """State that installing `content` at `dest` would have, without writing anything."""
    if not dest.exists():
        return CREATED
    current = _read_text(dest) or ""
    if current.replace("\r\n", "\n") == content.replace("\r\n", "\n"):
        return IDENTICAL
    return KEPT


def copy_core(core_dir: Path, root: Path) -> Dict[str, Any]:
    """D1: copies _core as is under <root>/.claude/harness/, without bytecode.

    Never a mixed core: if a file already present differs from the source
    (customized core or another version), it stays customized-kept (KEPT)
    and NOTHING is copied, not even the missing files; `copied` is False and
    `blocked_by` lists the files at fault, to be reported to the user."""
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
