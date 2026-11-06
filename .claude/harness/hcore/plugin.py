# Plugin distribution of the repository (Phase 7, steps M1 and M2).
#
# - PL-01: `read_manifest` reads `.claude-plugin/plugin.json` at the root of the repository
#   (the folder two levels above the core); None when absent or unreadable.
# - PL-02: `effective_name` gives the name the Skill tool must use: `<plugin>:<skill>` when the
#   skill runs from a plugin, `<skill>` otherwise. The mode is read from the UNRESOLVED skill
#   folder (`${CLAUDE_SKILL_DIR}`): `<root>/skills/<skill>` holds a `.claude-plugin/plugin.json`
#   at `<root>` in plugin mode, while a link `~/.claude/skills/<skill>` has none.
#   Without a skill folder, CLAUDE_PLUGIN_ROOT (set by Claude Code for plugin processes) decides.
# - PL-04: `core_path` gives the core a skill must call: the plugin's own core in plugin mode, else the
#   copy `.claude/harness/harness.py` of an equipped project, else the `_core` next to the skill folder
#   (a links installation). `_core/harness.py` is never cited inside an equipped project.
# - PL-03: `version_guard` fails when something under `skills/` changed since the last commit that
#   changed `version` in plugin.json and `version` was not raised (the plugin cache is indexed by
#   version: a changed content with the same version is never redistributed).

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .proc import Runner

MANIFEST_REL = ".claude-plugin/plugin.json"
GIT_TIMEOUT = 20


def read_manifest(root: Path) -> Optional[Dict[str, Any]]:
    """PL-01."""
    try:
        data = json.loads((Path(root) / MANIFEST_REL).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("name"), str) and data["name"]:
        return data
    return None


def plugin_version(root: Path) -> Optional[str]:
    manifest = read_manifest(root)
    version = manifest.get("version") if manifest else None
    return version if isinstance(version, str) and version else None


def effective_name(skill: str, skill_dir: Optional[str] = None,
                   environ: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """PL-02: {skill, name, mode, plugin} for the Skill tool."""
    env = os.environ if environ is None else environ
    plugin_root: Optional[Path] = None
    if skill_dir:
        # Deliberately not resolved: a link must keep looking like a link.
        candidate = Path(os.path.abspath(skill_dir)).parent.parent
        if read_manifest(candidate) is not None and Path(os.path.abspath(skill_dir)).parent.name == "skills":
            plugin_root = candidate
    elif env.get("CLAUDE_PLUGIN_ROOT"):
        root = Path(env["CLAUDE_PLUGIN_ROOT"])
        if read_manifest(root) is not None:
            plugin_root = root
    if plugin_root is None:
        return {"skill": skill, "name": skill, "mode": "links", "plugin": None}
    plugin = read_manifest(plugin_root)["name"]
    return {"skill": skill, "name": "%s:%s" % (plugin, skill), "mode": "plugin", "plugin": plugin}


def core_path(root: Optional[str] = None, skill_dir: Optional[str] = None,
              environ: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """PL-04: {path, mode} with mode in plugin | project | skill; ValueError when no core is found."""
    env = os.environ if environ is None else environ
    named = effective_name("x", skill_dir, env)
    if named["mode"] == "plugin":
        base = (Path(os.path.abspath(skill_dir)).parent if skill_dir
                else Path(env["CLAUDE_PLUGIN_ROOT"]) / "skills")
        own = base / "_core" / "harness.py"
        if own.is_file():
            return {"path": own.as_posix(), "mode": "plugin"}
    if root:
        project = Path(root) / ".claude" / "harness" / "harness.py"
        if project.is_file():
            return {"path": project.as_posix(), "mode": "project"}
    if skill_dir:
        beside = Path(os.path.abspath(skill_dir)).parent / "_core" / "harness.py"
        if beside.is_file():
            return {"path": beside.as_posix(), "mode": "skill"}
    raise ValueError("no core found: no plugin core, no .claude/harness/harness.py under the root, no _core next "
                     "to the skill folder")


def _git(root: Path, run: Optional[Callable[..., Any]], *args: str) -> Optional[str]:
    runner = run or Runner(cwd=str(root), timeout=GIT_TIMEOUT)
    res = runner(["git"] + list(args))
    return res.out if res.ok else None


def _version_of(text: Optional[str]) -> Optional[str]:
    try:
        data = json.loads(text or "")
    except ValueError:
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) else None


def _baseline(root: Path, run: Optional[Callable[..., Any]]) -> Tuple[Optional[str], Optional[str]]:
    """(commit, version) of the last commit where the parsed `version` value of the manifest changed: the
    commits that touch the manifest, newest first, until one whose version differs from the next older one."""
    commits = (_git(root, run, "log", "--format=%H", "--", MANIFEST_REL) or "").split()
    versions = [_version_of(_git(root, run, "show", "%s:%s" % (c, MANIFEST_REL))) for c in commits]
    for at, commit in enumerate(commits):
        older = versions[at + 1] if at + 1 < len(commits) else None
        if versions[at] != older:
            return commit, versions[at]
    return None, None


def version_guard(root: Path, run: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """PL-03: {ok, status, version, base, files}. status: no_plugin | no_git | no_baseline | bumped | clean | stale."""
    root = Path(root)
    current = plugin_version(root)
    if current is None:
        return {"ok": True, "status": "no_plugin", "version": None, "base": None, "files": []}
    if _git(root, run, "rev-parse", "--git-dir") is None:
        return {"ok": True, "status": "no_git", "version": current, "base": None, "files": []}
    base, base_version = _baseline(root, run)
    if not base:
        # The manifest is not committed yet: the version is being introduced, nothing to compare.
        return {"ok": True, "status": "no_baseline", "version": current, "base": None, "files": []}
    if base_version != current:
        from .version import semver      # lazy: version imports this module
        if semver(current) < semver(base_version):
            return {"ok": False, "status": "decreased", "version": current, "base": base, "files": [],
                    "was": base_version}
        return {"ok": True, "status": "bumped", "version": current, "base": base, "files": []}
    changed: List[str] = (_git(root, run, "diff", "--name-only", base, "--", "skills") or "").splitlines()
    changed += (_git(root, run, "ls-files", "--others", "--exclude-standard", "--", "skills") or "").splitlines()
    files = sorted(set(changed))
    return {"ok": not files, "status": "stale" if files else "clean", "version": current, "base": base,
            "files": files}
