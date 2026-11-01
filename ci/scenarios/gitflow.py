# A git repository with a local bare remote (FX-04) and a feature branch, driven with the simulated gh.
#
# ghflow.py only accepts a remote whose URL contains github.com, so the bare repository lives under
# <tmp>/<tag>/github.com/acme/toy.git. It is created at run time, never versioned.

import json
import shutil

import agents
from common import Prep


class Flow:
    def __init__(self, ctx, root, tag, checks=None, protected=False):
        self.ctx = ctx
        self.root = root
        self.tag = tag
        self.bare = ctx.tmp / tag / "github.com" / "acme" / "toy.git"
        self.state_file = ctx.tmp / tag / "gh-state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {"prs": [], "comments": [], "replies": [], "resolved": [], "merged": False, "calls": [],
                 "emulate_delete_branch": True, "protected": protected}
        if checks is not None:
            state["checks"] = checks
        self.state_file.write_bytes(json.dumps(state).encode("utf-8"))

    def k(self, *args, **kw):
        kw["cwd"] = self.root
        kw["extra_env"] = dict(kw.get("extra_env") or {}, HCORE_FAKE_GH_STATE=str(self.state_file))
        return self.ctx.k(*args, **kw)

    def state(self):
        return json.loads(self.state_file.read_bytes().decode("utf-8"))

    def git(self, *args):
        return self.ctx.git(*args, cwd=self.root)

    def remote_and_branch(self, patch_scenario="shippr-automerge", patch="feature.patch"):
        self.bare.mkdir(parents=True, exist_ok=True)
        self.ctx.git("init", "-q", "--bare", "-b", "main", cwd=self.bare)
        self.git("remote", "add", "origin", self.bare.as_posix())
        self.git("push", "-q", "-u", "origin", "main")
        self.git("checkout", "-q", "-b", "feature")
        agents.apply_patch(self.ctx, patch_scenario, patch)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: count()")
        return self.git("rev-parse", "HEAD").strip()


def clone_project(ctx, source, name):
    """A copy of an installed project (history included), for the scenarios that need several PRs."""
    dest = ctx.tmp / name / "work"
    shutil.copytree(str(source), str(dest))
    return dest


def review_round(ctx, flow, run, themes, dead=()):
    """The reviewers of round 1: zero finding, except the themes listed in `dead` (dead twice)."""
    out = {}
    for theme in themes:
        if theme in dead:
            first = ctx.json(flow.k("ship-pr", "reviewer", "--run", run, "--theme", theme, "--dead"), "reviewer dead 1")
            second = ctx.json(flow.k("ship-pr", "reviewer", "--run", run, "--theme", theme, "--dead"), "reviewer dead 2")
            out[theme] = (first, second)
            continue
        path = agents.frozen_output(ctx, "shippr-automerge", "reviewer.json", "reviewer-%s.json" % theme.split()[0])
        out[theme] = ctx.json(flow.k("ship-pr", "reviewer", "--run", run, "--theme", theme, "--duration-ms", "1",
                                     "--output", path), "reviewer " + theme)
    return out


def open_pr(ctx, flow):
    """start -> sync -> pr (title and body written by Write) -> diff; returns (run, start json)."""
    start = ctx.json(flow.k("ship-pr", "start", "--target", "main"), "ship-pr start")
    run = start["run"]
    ctx.json(flow.k("ship-pr", "sync", "--run", run), "ship-pr sync")
    ctx.json(flow.k("ship-pr", "pr", "--run", run), "ship-pr pr (material)")
    title = agents.frozen_output(ctx, "shippr-automerge", "pr-title.txt")
    body = agents.frozen_output(ctx, "shippr-automerge", "pr-body.md")
    pr = ctx.json(flow.k("ship-pr", "pr", "--run", run, "--title-file", title, "--body-file", body), "ship-pr pr")
    if not pr.get("created"):
        raise Prep("ship-pr pr did not create the PR: %s" % json.dumps(pr)[:200])
    diff = flow.k("ship-pr", "diff", "--run", run)
    if diff.returncode != 0 or "count" not in diff.stdout:
        raise Prep("ship-pr diff: exit %d: %s" % (diff.returncode, diff.stderr.strip()[:200]))
    return run, start
