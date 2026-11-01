# hook-diff: the PreToolUse hook of ship-pr keeps edits inside the PR diff (6 assertions).
#
# The hook is run the way Claude Code runs it: the command line read from the project's .claude/settings.json,
# through bash, with the hook JSON on stdin and CLAUDE_PROJECT_DIR set. It is not called through python directly.

import json

import install
from common import Skip, find_bash
from gitflow import Flow

ID = "hook-diff"
PRESCRIBES = [
    ("start --target", "skills/ship-pr/SKILL.md"),
    ("activate", "skills/_core/profiles/software/bodies/orchestrator.md"),
    ("deactivate", "skills/_core/profiles/software/bodies/orchestrator.md"),
    ("hooks install", "skills/software-factory/SKILL.md"),
]
SESSION = "hook-diff-session"


def pre_edit_command(ctx):
    settings = json.loads(ctx.read(".claude/settings.json"))
    for entry in settings["hooks"]["PreToolUse"]:
        if "Edit" in entry["matcher"]:
            return entry["hooks"][0]["command"]
    raise AssertionError("no PreToolUse hook for Edit in settings.json")


def fire(ctx, bash, command, tool, path, raw=None, extra_env=None):
    """The hook, as Claude Code runs it."""
    payload = raw if raw is not None else json.dumps({"tool_name": tool, "tool_input": {"file_path": path},
                                                      "session_id": SESSION})
    env = dict(extra_env or {}, CLAUDE_PROJECT_DIR=ctx.work.as_posix())
    return ctx.run([bash, "-c", command], stdin=payload, extra_env=env, fake_gh=False)


def run_status(ctx, run_path):
    """Why a marker would be ignored: the hook only applies to a run whose state says `running` (HK-05)."""
    state = json.loads(ctx.read(run_path[: -len(".jsonl")] + ".state.json"))
    return "state of %s: status=%r" % (run_path, state.get("status"))


def run(ctx):
    bash = find_bash()
    if not bash:
        raise Skip("no working bash found: the hook command lines of settings.json are shell lines")
    install.install(ctx)
    install.commit_all(ctx)
    command = pre_edit_command(ctx)
    flow = Flow(ctx, ctx.work, "hook")
    flow.remote_and_branch()                      # the PR diff is: toy/core.py
    start = ctx.json(flow.k("ship-pr", "start", "--target", "main"), "ship-pr start")
    run_path = start["run"]
    stops = lambda: sorted((ctx.work / ".harness" / "runs").glob("STOP-*.md"))  # noqa: E731

    cases = (("Edit", "pyproject.toml"), ("Write", "docs/new-file.md"), ("Edit", "toy/core.py"))

    # 4. Without activation nothing is blocked (hand edits stay free).
    free = [fire(ctx, bash, command, tool, path).returncode for tool, path in cases]
    ctx.check(4, free == [0, 0, 0], "exit codes without activation=%s" % free)

    # 0. The hook only applies to a run whose state says `running` (HK-05): `ship-pr start` must leave it so.
    ctx.check(0, json.loads(ctx.read(run_path[: -len(".jsonl")] + ".state.json")).get("status") == "running",
              run_status(ctx, run_path) + " after ship-pr start (the hooks ignore a run that is not running)")

    ctx.json(ctx.h("activate", "--run", run_path, "--skill", "ship-pr", "--session", SESSION, "--phase", "review"),
             "activate")

    # 3. A file of the diff passes.
    inside = fire(ctx, bash, command, "Edit", "toy/core.py")
    # 5. An internal error never blocks: a warning on stderr, exit 0.
    garbage = fire(ctx, bash, command, "Edit", "x", raw="this is not json")
    no_git = fire(ctx, bash, command, "Edit", "pyproject.toml",
                  extra_env={"HCORE_TEST_MODE": "1", "HCORE_GIT": json.dumps(["no-such-git-executable"])})
    ctx.check(3, inside.returncode == 0, "exit=%d stderr=%s" % (inside.returncode, inside.stderr.strip()[:120]))
    # HK-04: exit 0, a systemMessage on stdout and a line in hook-errors.jsonl (the warning is not on stderr).
    errors = ctx.work / ".harness" / "runs" / "hook-errors.jsonl"
    count = len(errors.read_text(encoding="utf-8").splitlines()) if errors.is_file() else 0
    ctx.check(5, garbage.returncode == 0 and "systemMessage" in garbage.stdout and no_git.returncode == 0
              and "systemMessage" in no_git.stdout and count >= 2,
              "invalid json: exit=%d stdout=%r; git missing: exit=%d stdout=%r; hook-errors lines=%d" % (
                  garbage.returncode, garbage.stdout.strip()[:60], no_git.returncode, no_git.stdout.strip()[:60], count))

    # 1. First drift: an Edit outside the diff is refused, the message names the file and the limited scope.
    first = fire(ctx, bash, command, "Edit", "pyproject.toml")
    ctx.check(1, first.returncode == 2 and "pyproject.toml" in first.stderr and "scope limited to the PR diff" in first.stderr
              and not stops(), "exit=%d stderr=%s stop files=%d; %s" % (
                  first.returncode, first.stderr.strip()[:160], len(stops()), run_status(ctx, run_path)))

    # 2 and 6. A Write of a new file outside the diff is refused too; this second drift of the cycle stops it.
    second = fire(ctx, bash, command, "Write", "docs/new-file.md")
    ctx.check(2, second.returncode == 2 and "docs/new-file.md" in second.stderr, "exit=%d stderr=%s" % (
        second.returncode, second.stderr.strip()[:160]))
    stop_text = stops()[0].read_bytes().decode("utf-8") if stops() else ""
    events = [l for l in ctx.journal(run_path) if l.get("event") == "drift"]
    ctx.check(6, len(stops()) == 1 and "— drift" in stop_text and "## Command" in stop_text
              and '"continue": false' in second.stdout and [e.get("count") for e in events] == [1, 2],
              "stop files=%d drift events=%s stdout=%r" % (len(stops()), [e.get("count") for e in events],
                                                           second.stdout.strip()[:80]))
