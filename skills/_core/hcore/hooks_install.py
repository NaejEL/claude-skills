# Installation of the harness hooks in .claude/settings.json (HK-02, HK-03, HK-06).
#
# - HK-02: `PreToolUse` Edit|Write|MultiEdit|NotebookEdit -> pre-edit (10 s),
#   `PreToolUse` Bash|PowerShell -> pre-bash (10 s), `PostToolUse`
#   Edit|Write|MultiEdit -> post-edit (60 s) only when `hooks.lint` is configured
#   (HL-01). An entry belongs to the harness when its command holds
#   `.claude/harness/hooks/hook.py` (no blocks in a JSON, I1 of Phase 2). The
#   merge follows FU-01: absent -> added, identical -> `identical`, different ->
#   `customized-kept`; the hooks of the user and the JSONC comments stay.
# - HK-03: the generated command never exits 2 except for a wanted blocking:
#   a missing script is skipped (Python itself would answer 2) and any other code
#   (interpreter missing = 127, crash = 1) becomes 0.

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from . import fusion

HOOK_MARK = ".claude/harness/hooks/hook.py"
EDIT_TOOLS = "Edit|Write|MultiEdit|NotebookEdit"
SHELL_TOOLS = "Bash|PowerShell"
POST_TOOLS = "Edit|Write|MultiEdit"
SPECS = (("PreToolUse", EDIT_TOOLS, "pre-edit", 10), ("PreToolUse", SHELL_TOOLS, "pre-bash", 10),
         ("PostToolUse", POST_TOOLS, "post-edit", 60))


FALLBACKS = ("python3", "python", "py -3")     # tried at run time, after the interpreter detected at install time
LEGACY = re.compile(r'^f="\$CLAUDE_PROJECT_DIR/%s"; \[ -f "\$f" \] \|\| exit 0; .+ "\$f" (?P<name>[a-z-]+); rc=\$\?; '
                    r'\[ "\$rc" -eq 2 \] && exit 2; exit 0$' % re.escape(HOOK_MARK))


NO_PYTHON = 'echo "harness hook skipped: no working Python interpreter (python3, python, py -3)" >&2'
LEGACY_CHAIN = re.compile(r'^f="\$CLAUDE_PROJECT_DIR/%s"; \[ -f "\$f" \] \|\| exit 0; if command -v .+; else (?:echo .+; )?exit 0; fi; rc=\$\?; '
                          r'\[ "\$rc" -eq 2 \] && exit 2; exit 0$' % re.escape(HOOK_MARK))


def command_for(py: str, name: str) -> str:
    """HK-03: `$CLAUDE_PROJECT_DIR`, the detected interpreter first then python3, python and `py -3` (the
    first one that is on the PATH and really prints `7` for `-c 'import sys; sys.stdout.write(str(7))'` is used, so a Windows Store stub,
    which exits 0 without running anything, is skipped; none:
    one warning line on stderr), never an accidental exit 2."""
    chain: List[str] = []
    for candidate in (py.strip(),) + FALLBACKS:
        if candidate and candidate not in chain:
            chain.append(candidate)
    branches = []
    for candidate in chain:
        head = re.match(r'"[^"]*"|\'[^\']*\'|\S+', candidate).group(0)
        branches.append('%s command -v %s >/dev/null 2>&1 && [ "$(%s -c \'import sys; sys.stdout.write(str(7))\' 2>/dev/null)" = 7 ]; then %s "$f" %s' % (
            "if" if not branches else "elif", head, candidate, candidate, name))
    return ('f="$CLAUDE_PROJECT_DIR/%s"; [ -f "$f" ] || exit 0; %s; else %s; exit 0; fi; rc=$?; '
            '[ "$rc" -eq 2 ] && exit 2; exit 0' % (HOOK_MARK, "; ".join(branches), NO_PYTHON))


def _is_legacy(command: str, name: str) -> bool:
    """The command written before the run-time fallback: a single hard-coded interpreter."""
    found = LEGACY.match(command)
    if found:
        return found.group("name") == name
    return bool(LEGACY_CHAIN.match(command)) and command.rstrip("; ").split("; else exit 0")[0].endswith(" " + name)


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
        for at, group in enumerate(groups):
            if isinstance(group, dict) and any(_is_ours(h, name) for h in group.get("hooks", [])):
                if group == wanted:
                    outcome[name] = fusion.IDENTICAL
                    return []
                old = [h.get("command", "") for h in group.get("hooks", []) if isinstance(h, dict)]
                if len(old) == 1 and len(group["hooks"]) == 1 and _is_legacy(old[0], name) and {**group, "hooks": [
                        {**group["hooks"][0], "command": command}]} == wanted:
                    groups[at] = json.loads(json.dumps(wanted))      # only the old hard-coded interpreter differed
                    outcome[name] = fusion.MERGED
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
