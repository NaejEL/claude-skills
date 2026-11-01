# Installation of the harness hooks in .claude/settings.json (HK-02, HK-03, HK-06).
#
# - HK-02: `PreToolUse` Edit|Write|MultiEdit|NotebookEdit -> pre-edit (10 s),
#   `PreToolUse` Bash|PowerShell -> pre-bash (10 s), `PostToolUse`
#   Edit|Write|MultiEdit -> post-edit (60 s) only when `hooks.lint` is configured
#   (HL-01). An entry belongs to the harness when its command holds
#   `.claude/harness/hooks/hook.py` (no blocks in a JSON, I1 of Phase 2). The
#   merge follows FU-01: absent -> added, identical -> `identique`, different ->
#   `personnalisé-conservé`; the hooks of the user and the JSONC comments stay.
# - HK-03: the generated command never exits 2 except for a wanted blocking:
#   a missing script is skipped (Python itself would answer 2) and any other code
#   (interpreter missing = 127, crash = 1) becomes 0.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from . import fusion

HOOK_MARK = ".claude/harness/hooks/hook.py"
EDIT_TOOLS = "Edit|Write|MultiEdit|NotebookEdit"
SHELL_TOOLS = "Bash|PowerShell"
POST_TOOLS = "Edit|Write|MultiEdit"
SPECS = (("PreToolUse", EDIT_TOOLS, "pre-edit", 10), ("PreToolUse", SHELL_TOOLS, "pre-bash", 10),
         ("PostToolUse", POST_TOOLS, "post-edit", 60))


def command_for(py: str, name: str) -> str:
    """HK-03: `$CLAUDE_PROJECT_DIR`, the detected interpreter, never an accidental exit 2."""
    return ('f="$CLAUDE_PROJECT_DIR/%s"; [ -f "$f" ] || exit 0; %s "$f" %s; rc=$?; '
            '[ "$rc" -eq 2 ] && exit 2; exit 0' % (HOOK_MARK, py, name))


def lint_configured(root: Path) -> bool:
    """HL-01: `hooks.lint` of harness.json holds at least one entry."""
    try:
        data = json.loads((Path(root) / ".claude" / "harness.json").read_text(encoding="utf-8-sig"))
        return bool(data["hooks"]["lint"])
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _is_ours(hook: Any, name: str) -> bool:
    cmd = hook.get("command", "") if isinstance(hook, dict) else ""
    return HOOK_MARK in cmd and (" %s;" % name in cmd or cmd.rstrip().endswith(" " + name))


def _op(event: str, matcher: str, name: str, command: str, timeout: int, outcome: Dict[str, str]):
    wanted = {"matcher": matcher, "hooks": [{"type": "command", "command": command, "timeout": timeout}]}

    def run(data: Dict[str, Any]) -> List[str]:
        hooks = data.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            raise fusion.FusionError("hooks is not an object")
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise fusion.FusionError("hooks.%s is not an array" % event)
        for group in groups:
            if isinstance(group, dict) and any(_is_ours(h, name) for h in group.get("hooks", [])):
                if group == wanted:
                    outcome[name] = fusion.IDENTICAL
                    return []
                outcome[name] = fusion.KEPT
                return ["hooks.%s[%s]" % (event, name)]
        groups.append(json.loads(json.dumps(wanted)))
        outcome[name] = fusion.CREATED
        return []
    return run


def plan(root: Path, py: str, with_post: bool = None):
    """The FU-01 plan of .claude/settings.json and the per-entry outcome."""
    root = Path(root)
    with_post = lint_configured(root) if with_post is None else with_post
    outcome: Dict[str, str] = {}
    ops = [_op(event, matcher, name, command_for(py, name), timeout, outcome)
           for event, matcher, name, timeout in SPECS if name != "post-edit" or with_post]
    return fusion.plan_json(root / ".claude" / "settings.json", ops), outcome


def apply(root: Path, py: str, with_post: bool = None) -> Dict[str, Any]:
    """HK-02: merges the hooks and writes the file only when something changed."""
    root = Path(root)
    result, outcome = plan(root, py, with_post)
    if result.text is not None:
        fusion._write(root / ".claude" / "settings.json", result.text)
    return {".claude/settings.json": result.state, "entries": outcome, "kept": list(result.kept)}
