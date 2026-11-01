# Simulated agents (SM-01): frozen outputs, except the Verifier which runs the project's real tests.

import json

from common import Prep

RESULT = "@RESULT@"


def test_command(ctx):
    stamp = json.loads(ctx.read(".claude/harness.json"))
    return stamp["skills"]["software-factory"]["params"]["test_command"]


def run_tests(ctx):
    """The real test command of the project (the one the installation stored): its result is the truth."""
    return ctx.run(test_command(ctx).split(), fake_gh=False)


def verifier_output(ctx, name, issues=None):
    """The Verifier's report, written where the SKILL.md prescribes: frozen text + the real test verdict."""
    res = run_tests(ctx)
    passed = res.returncode == 0
    block = {"verdict": "APPROVED" if passed else "CHANGES_REQUESTED", "tests_passed": passed,
             "issues": [] if passed else (issues or [{"file": "tests", "severity": "major",
                                                       "description": (res.stderr or res.stdout).strip()[-200:]}])}
    template = (ctx.fixtures / "agents" / "common" / "verifier.md").read_bytes().decode("utf-8")
    return ctx.write_transit(name, template.replace(RESULT, json.dumps(block))), passed


def frozen_output(ctx, scenario, name, dest=None):
    """A frozen agent output (FX-05), written as the Write tool would."""
    text = (ctx.fixtures / "agents" / scenario / name).read_bytes().decode("utf-8")
    return ctx.write_transit(dest or name, text)


def apply_patch(ctx, scenario, name):
    """The simulated Builder: a frozen fix applied with `git apply`."""
    text = (ctx.fixtures / "agents" / scenario / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
    rel = ctx.write_transit(name, text)
    res = ctx.run(["git", "apply", "--whitespace=nowarn", rel], fake_gh=False)
    if res.returncode != 0:
        raise Prep("simulated Builder: git apply %s failed: %s" % (name, res.stderr.strip()[:300]))
