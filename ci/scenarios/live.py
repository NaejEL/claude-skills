# live-install, live-factory, live-hook: the real claude CLI in headless mode (only with --live).
#
# They cost tokens and are never run by default. Assertions are structural (D10): the LLM is not required to
# succeed, it is required to end in an explicit state. The skills are exposed to the throw-away project by
# links under <project>/.claude/skills/ (recipe R1): no installer, nothing written in ~/.claude by the scenario.
# ship-pr itself is not run live: it needs a real GitHub repository (recipe R13).

import json
import os
import shutil
import subprocess

import agents
import install
from common import ROOT, Skip
from gitflow import Flow

IDS = ("live-install", "live-factory", "live-hook")
LIVE = True
PRESCRIBES = {
    "live-install": [("sf copy-core", "skills/_core/profiles/software/install.md"), ("upgrade plan", "skills/software-factory/SKILL.md")],
    "live-factory": [("factory-run start", "skills/software-factory/SKILL.md")],
    "live-hook": [("activate", "skills/_core/profiles/software/bodies/orchestrator.md")],
}
MAX_TURNS = {"live-install": 60, "live-factory": 80, "live-hook": 10}
ALLOWED = "Read,Glob,Grep,Write,Edit,Task,Skill,Bash(git *),Bash(py *),Bash(python *),Bash(python3 *)"


def link_skills(ctx):
    """Exposes skills/* under <work>/.claude/skills/ (junctions on Windows, symlinks elsewhere), git-excluded."""
    target = ctx.work / ".claude" / "skills"
    target.mkdir(parents=True, exist_ok=True)
    names = sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())
    for name in names:
        link = target / name
        if link.exists():
            continue
        if os.name == "nt":
            res = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(ROOT / "skills" / name)],
                                 capture_output=True, text=True)
            if res.returncode != 0:
                raise Skip("cannot create a junction for the skills: %s" % res.stdout.strip()[:120])
        else:
            os.symlink(str(ROOT / "skills" / name), str(link))
    exclude = ctx.work / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with open(str(exclude), "ab") as fh:
        fh.write(("".join(".claude/skills/%s\n" % n for n in names)).encode("utf-8"))


def claude(ctx, prompt):
    """`claude -p` in the project, with a bound on the turns and a whitelist; never the all-permissions flag."""
    argv = [shutil.which("claude") or "claude", "-p", prompt, "--output-format", "json", "--max-turns", str(MAX_TURNS[ctx.sid]),
            "--permission-prompts", "none", "--permission-mode", "acceptEdits", "--allowedTools", ALLOWED]
    env = dict(os.environ, MSYS_NO_PATHCONV="1", PYTHONDONTWRITEBYTECODE="1")
    ctx.live_calls += 1
    return subprocess.run(argv, cwd=str(ctx.work), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=1800)


def run(ctx):
    {"live-install": live_install, "live-factory": live_factory, "live-hook": live_hook}[ctx.sid](ctx)


def live_install(ctx):
    ctx.copy_fixture(ctx.fixtures / "toy-py", ctx.work, renames={"claude-md.txt": "CLAUDE.md"})
    (ctx.work / "specs").mkdir(exist_ok=True)
    ctx.init_git()
    link_skills(ctx)
    claude(ctx, "/software-factory --profile software --autonomy auto")
    wanted = [l.strip() for l in (ctx.fixtures / "expected" / "install-fresh" / "files.txt")
              .read_bytes().decode("utf-8").splitlines() if l.strip()]
    missing = [w for w in wanted if not (ctx.work / w).is_file()]
    ctx.check(1, not missing, "missing files: %s" % missing)
    stamp = ctx.k("stamp", "validate", ".claude/harness.json")
    ctx.check(2, stamp.returncode == 0, "stamp validate exit=%d %s" % (stamp.returncode, stamp.stderr.strip()[:120]))
    journals = sorted((ctx.work / ".harness" / "runs").glob("*.jsonl"))
    bad = [j.name for j in journals if ctx.k("journal", "validate", str(j)).returncode != 0]
    ctx.check(3, bool(journals) and not bad, "journals=%d invalid=%s" % (len(journals), bad))
    ctx.git("add", "-A")
    ctx.run(["git", "commit", "-q", "-m", "first live installation"], fake_gh=False)   # nothing to commit is a FAIL above
    claude(ctx, "/software-factory --upgrade")
    status = ctx.git("status", "--porcelain")
    ctx.check(4, status.strip() == "", "git status after a second run: %r" % status.strip()[:200])


def live_factory(ctx):
    install.install(ctx)
    install.commit_all(ctx)
    link_skills(ctx)
    spec = "specs/SPEC-mean.md"
    text = (ctx.fixtures / "agents" / "factory-auto" / "SPEC-mean.md").read_bytes().decode("utf-8")
    ctx.write(spec, text.replace("Statut : PROPOSEE", "Statut : APPROUVEE", 1))
    claude(ctx, "/factory-run %s" % spec)
    journals = sorted((ctx.work / ".harness" / "runs").glob("factory-run-*.jsonl"))
    lines = []
    for journal in journals:
        lines += [json.loads(l) for l in journal.read_bytes().decode("utf-8").splitlines() if l.strip()]
    verifiers = [l for l in lines if l.get("agent") == "factory-verifier"]
    success = bool(verifiers) and verifiers[-1].get("verdict") == "APPROVED"
    stops = list((ctx.work / ".harness" / "runs").glob("STOP-*.md"))
    tests_green = agents.run_tests(ctx).returncode == 0
    # An explicit issue is required (Q9): success with green tests, or a STOP file. Never success with red tests,
    # never an end without either.
    ctx.check(1, (success and tests_green) or bool(stops),
              "success=%s tests green=%s stop files=%d" % (success, tests_green, len(stops)))
    ctx.check(2, not (success and not tests_green), "approved by the Verifier while the real tests are red")


def live_hook(ctx):
    install.install(ctx)
    install.commit_all(ctx)
    link_skills(ctx)
    flow = Flow(ctx, ctx.work, "live-hook")
    flow.remote_and_branch()
    start = ctx.json(flow.k("ship-pr", "start", "--target", "main"), "ship-pr start")
    # The literal placeholder gives the project marker, which applies to any session (HK-05).
    ctx.json(ctx.h("activate", "--run", start["run"], "--skill", "ship-pr", "--session", "${CLAUDE_SESSION_ID}",
                   "--phase", "review"), "activate")
    victim = ctx.work / "pyproject.toml"
    before = victim.read_bytes()
    claude(ctx, "Use the Edit tool to append the line '# touched' to pyproject.toml, then stop.")
    ctx.check(1, victim.read_bytes() == before, "pyproject.toml (outside the PR diff) was modified")
