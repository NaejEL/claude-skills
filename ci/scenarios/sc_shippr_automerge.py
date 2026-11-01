# shippr-automerge: ship-pr without finding merges by itself under `auto`, and refuses when it must (7 assertions).
#
# gh is the simulated one (skills/_core/tests/fake_gh.py) over a local bare repository: checks, branch
# protection and the merge itself are driven by its state file (SM-03).

import shutil

import gitflow
import install
from gitflow import Flow, open_pr, review_round

ID = "shippr-automerge"
PRESCRIBES = [
    ("start --target", "skills/ship-pr/SKILL.md"),
    ("sync", "skills/ship-pr/SKILL.md"),
    ("reviewer", "skills/ship-pr/SKILL.md"),
    ("end-round", "skills/ship-pr/SKILL.md"),
    ("gate decide", "skills/ship-pr/SKILL.md"),
    ("merge --run <run> --auto", "skills/ship-pr/SKILL.md"),
]


def merge_gate(ctx, flow, run):
    """The gate ship-pr.merge under `auto`: decided by the five conditions, never asked."""
    decision = ctx.json(flow.k("gate", "decide", "--run", run, "--id", "ship-pr.merge"), "gate decide")
    answer = ctx.json(flow.k("gate", "answer", "--run", run, "--id", "ship-pr.merge", "--default"), "gate answer")
    return decision, answer


def merge_calls(flow):
    return [c for c in flow.state()["calls"] if c[:2] == ["pr", "merge"]]


def run(ctx):
    install.install(ctx)
    install.commit_all(ctx)
    template = ctx.tmp / "installed"
    shutil.copytree(str(ctx.work), str(template))

    # --- the nominal case
    flow = Flow(ctx, ctx.work, "nominal")
    head = flow.remote_and_branch()
    run_path, start = open_pr(ctx, flow)
    reviews = review_round(ctx, flow, run_path, start["themes"])
    ended = ctx.json(flow.k("ship-pr", "end-round", "--run", run_path), "end-round")
    lines = ctx.journal(run_path)
    validators = [l for l in lines if "validator" in str(l.get("agent", "")) or "validator" in str(l.get("slot", ""))]
    ctx.check(1, all(r.get("action") == "none" for r in reviews.values()) and ended.get("exit") == "exhaustion"
              and ended.get("round") == 1 and not validators,
              "actions=%s end-round=%s validators=%d" % ([r.get("action") for r in reviews.values()],
                                                         {k: ended.get(k) for k in ("exit", "round")}, len(validators)))

    decision, answer = merge_gate(ctx, flow, run_path)
    summary = ctx.json(flow.k("ship-pr", "merge", "--run", run_path, "--check", "--conditions"), "merge --check")
    result = ctx.json(flow.k("ship-pr", "merge", "--run", run_path, "--auto"), "merge --auto")
    conditions = result.get("conditions", {})
    calls = merge_calls(flow)
    flags = [a for c in flow.state()["calls"] for a in c]
    ctx.check(2, sorted(conditions) == ["C1", "C2", "C3", "C4", "C5"] and all(c["ok"] for c in conditions.values())
              and all(c["ok"] for c in summary.get("conditions", {}).values()) and result.get("merged") is True
              and len(calls) == 1 and "--merge" in calls[0] and "--delete-branch" in calls[0]
              and "--squash" not in flags and "--rebase" not in flags,
              "conditions=%s merge calls=%s" % ({k: v["ok"] for k, v in conditions.items()}, calls))

    main_sha = ctx.git("--git-dir", str(flow.bare), "rev-parse", "main").strip()
    branches = flow.git("branch", "--list", "feature").strip()
    current = flow.git("rev-parse", "--abbrev-ref", "HEAD").strip()
    ctx.check(3, main_sha == head and branches == "" and current == "main",
              "bare main=%s feature head=%s local feature=%r current=%s" % (main_sha[:8], head[:8], branches, current))

    gates = [l for l in ctx.journal(run_path) if l.get("event") == "gate" and l.get("id") == "ship-pr.merge"]
    ctx.check(4, decision.get("decision") == "default" and answer.get("source") == "default"
              and gates and all(g.get("decision") != "ask" for g in gates)
              and any(g.get("phase") == "answer" and g.get("source") == "default" for g in gates),
              "gate decision=%s source=%s" % (decision.get("decision"), answer.get("source")))

    # --- counter-tests, each on its own copy of the installed project
    def variant(name, checks=None, protected=False, dead=()):
        dest = gitflow.clone_project(ctx, template, name)
        ctx.work = dest
        f = Flow(ctx, dest, name, checks=checks, protected=protected)
        f.remote_and_branch()
        run_v, start_v = open_pr(ctx, f)
        review_round(ctx, f, run_v, start_v["themes"], dead=dead)
        ended_v = ctx.json(f.k("ship-pr", "end-round", "--run", run_v), "end-round (%s)" % name)
        res = ctx.json(f.k("ship-pr", "merge", "--run", run_v, "--auto"), "merge --auto (%s)" % name)
        return f, run_v, res, ended_v

    red = [{"name": "build", "bucket": "fail"}]
    f5, run5, res5, _ = variant("red-ci", checks=red)
    events5 = [l for l in ctx.journal(run5, root=f5.root) if l.get("event") == "merge_decision"]
    comments5 = [c.get("body") or "" for c in f5.state()["comments"]]
    ctx.check(5, res5.get("merged") is False and not merge_calls(f5) and events5 and events5[-1]["conditions"]["C3"] is False
              and any("Automatic merge not performed" in c and "C3" in c for c in comments5),
              "merged=%s merge calls=%d comments=%s" % (res5.get("merged"), len(merge_calls(f5)), len(comments5)))

    f6, run6, res6, _ = variant("protected", protected=True)
    events6 = [l for l in ctx.journal(run6, root=f6.root) if l.get("event") == "merge_decision"]
    comments6 = [c.get("body") or "" for c in f6.state()["comments"]]
    ctx.check(6, res6.get("merged") is False and not merge_calls(f6) and events6 and events6[-1]["conditions"]["C4"] is False
              and any("Automatic merge not performed" in c and "C4" in c for c in comments6),
              "merged=%s merge calls=%d" % (res6.get("merged"), len(merge_calls(f6))))

    # SP-05: a theme dead twice is not a reviewed theme, even under `auto`.
    dest = gitflow.clone_project(ctx, template, "dead-theme")
    ctx.work = dest
    f7 = Flow(ctx, dest, "dead-theme")
    f7.remote_and_branch()
    run7, start7 = open_pr(ctx, f7)
    start_theme = start7["themes"][0]
    out7 = review_round(ctx, f7, run7, start7["themes"], dead=(start_theme,))
    ended7 = ctx.json(f7.k("ship-pr", "end-round", "--run", run7), "end-round (dead theme)")
    res7 = ctx.json(f7.k("ship-pr", "merge", "--run", run7, "--auto"), "merge --auto (dead theme)")
    ctx.check(7, out7[start_theme][0].get("action") == "relaunch" and out7[start_theme][1].get("action") == "uncovered"
              and res7.get("merged") is False and bool(res7.get("refusal")) and not merge_calls(f7)
              and ended7.get("exit") is None,
              "reviewer=%s/%s refusal=%s merged=%s" % (out7[start_theme][0].get("action"),
                                                        out7[start_theme][1].get("action"), res7.get("refusal"),
                                                        res7.get("merged")))
