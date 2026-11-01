# Replayed installation of /software-factory on the toy-py project (the preparation of most scenarios).
#
# The sequence is the one of skills/software-factory/SKILL.md: copy of the core, scout (simulated agent),
# profiles gate, detection, one upgrade plan applied all or nothing, stamp, hooks. The scout is the only
# agent: its frozen output is read from agents/install-fresh/scout.json.

import json

from common import Prep

TEST_COMMAND = "%s -m unittest discover -s tests -t ."


def setup_project(ctx):
    """toy-py under its real names, committed: the state before the installation."""
    ctx.copy_fixture(ctx.fixtures / "toy-py", ctx.work, renames={"claude-md.txt": "CLAUDE.md"})
    (ctx.work / "specs").mkdir(exist_ok=True)
    ctx.init_git()
    return ctx.tree()


def install(ctx, observe=None):
    """Runs the installation; returns the observations the install-fresh scenario asserts on."""
    before = setup_project(ctx)
    obs = {"before": before, "steps": {}}

    copied = ctx.json(ctx.k("sf", "copy-core", "--root", "."), "sf copy-core")
    obs["copy_core"] = copied

    ctx.write_transit("scout-signals.json", (ctx.fixtures / "agents" / "install-fresh" / "scout.json")
                      .read_bytes().decode("utf-8"))
    ctx.json(ctx.k("scout", "signals", "--root", "."), "scout signals")
    verdict = ctx.json(ctx.k("scout", "verdict", "--root", ".", "--signals", ".harness/runs/scout-signals.json"),
                       "scout verdict")
    obs["verdict"] = verdict
    if verdict.get("proposal") != ["software"] or not verdict.get("clear"):
        raise Prep("scout proposal is not a clear [software]: %s" % json.dumps(verdict.get("proposal")))
    run = verdict["run"]
    obs["scout_run"] = run

    decision = ctx.json(ctx.k("gate", "decide", "--root", ".", "--run", run, "--id", "software-factory.profiles",
                              "--autonomy", "auto"), "gate decide")
    answer = ctx.json(ctx.k("gate", "answer", "--root", ".", "--run", run, "--id", "software-factory.profiles",
                            "--default"), "gate answer")
    obs["gate"] = (decision, answer)

    stack = ctx.json(ctx.k("stack", "detect", "--root", "."), "stack detect")
    obs["stack"] = stack

    command = TEST_COMMAND % ctx.interp
    ctx.write_transit("sf-params.json", json.dumps({"test_command": command}))
    plan = ctx.json(ctx.k("upgrade", "plan", "--root", ".", "--skill", "software-factory", "--profiles", "software",
                          "--by", "scout", "--params-file", ".harness/runs/sf-params.json",
                          "--interpreter", ctx.interp), "upgrade plan")
    if plan.get("action") != "plan":
        raise Prep("upgrade plan did not produce a plan: %s" % plan.get("action"))
    obs["plan"] = plan
    applied = ctx.json(ctx.k("upgrade", "apply", "--root", ".", "--plan", plan["plan"]), "upgrade apply")
    obs["applied"] = applied

    obs["autonomy"] = ctx.json(ctx.k("stamp", "autonomy", "--root", "."), "stamp autonomy")
    obs["hooks"] = ctx.json(ctx.k("hooks", "install", "--root", ".", "--py", ctx.interp), "hooks install")
    obs["params_command"] = command
    return obs


def commit_all(ctx, message="install", root=None):
    ctx.git("add", "-A", cwd=root or ctx.work)
    ctx.git("commit", "-q", "-m", message, cwd=root or ctx.work)
