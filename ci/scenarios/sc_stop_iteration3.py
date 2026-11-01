# stop-iteration3: a Verifier that never approves stops the cycle cleanly at the 3rd iteration (5 assertions).

import json

import agents
import install
from common import lines_of

ID = "stop-iteration3"
PRESCRIBES = [
    ("factory-run start", "skills/software-factory/SKILL.md"),
    ("factory-run record", "skills/software-factory/SKILL.md"),
    ("begin", "skills/_core/profiles/software/orchestrator.md"),
]


def start(ctx, spec):
    ctx.write_transit("factory-run-arguments.txt", spec + "\n")
    out = ctx.json(ctx.h("factory-run", "start", "--arguments-file", ".harness/runs/factory-run-arguments.txt"),
                   "factory-run start")
    if out.get("mode") != "build":
        raise RuntimeError("factory-run start did not route %s to build: %s" % (spec, out.get("mode")))
    return out["run"], out["models"]


def record(ctx, run, agent, **extra):
    args = ["factory-run", "record", "--run", run, "--agent", agent, "--model", "inherit", "--duration-ms", "1"]
    for key, value in extra.items():
        args += ["--" + key.replace("_", "-")] + ([] if value is True else [value])
    return ctx.h(*args)


def run(ctx):
    install.install(ctx)
    install.commit_all(ctx)
    spec = "specs/SPEC-stop.md"
    ctx.write(spec, (ctx.fixtures / "agents" / "stop-iteration3" / "SPEC-stop.md").read_bytes().decode("utf-8"))
    run_path, _ = start(ctx, spec)

    results = []
    for i in (1, 2, 3):
        ctx.json(record(ctx, run_path, "factory-builder"), "builder %d" % i)
        out = agents.frozen_output(ctx, "stop-iteration3", "verifier-%d.md" % i)
        results.append(record(ctx, run_path, "factory-verifier", output=out))
    last = results[-1]
    try:
        action = json.loads(last.stdout)
    except ValueError:
        action = {}
    verdicts = [l["verdict"] for l in ctx.journal(run_path) if l.get("agent") == "factory-verifier"]
    ctx.check(1, [r.returncode for r in results] == [0, 0, 1] and action.get("action") == "fail"
              and action.get("iteration") == 3 and verdicts == ["CHANGES_REQUESTED"] * 3,
              "exit codes=%s action=%s iteration=%s verdicts=%s" % ([r.returncode for r in results],
                                                                    action.get("action"), action.get("iteration"),
                                                                    verdicts))

    fourth = record(ctx, run_path, "factory-builder")
    ctx.check(2, fourth.returncode != 0, "exit=%d stderr=%s" % (fourth.returncode, fourth.stderr.strip()[:120]))

    stops = sorted((ctx.work / ".harness" / "runs").glob("STOP-*.md"))
    text = stops[0].read_bytes().decode("utf-8") if stops else ""
    wanted = [l.strip() for l in lines_of((ctx.fixtures / "expected" / "stop-iteration3" / "stop-lines.txt")
                                          .read_bytes().decode("utf-8")) if l.strip()]
    have = [l.strip() for l in lines_of(text)]
    missing = [w for w in wanted if w not in have]
    ctx.check(3, len(stops) == 1 and not missing, "stop files=%d missing=%s" % (len(stops), missing))

    parsed = ctx.json(ctx.h("spec", "check", spec), "spec check")
    ships = list((ctx.work / ".harness" / "runs").glob("ship-pr-*"))
    ctx.check(4, not ships and parsed.get("status") == "APPROUVEE",
              "ship-pr journals=%d spec status=%s" % (len(ships), parsed.get("status")))

    # Counter-test: two refusals, a dead Verifier, then approval -> success at iteration 3, the dead agent is free.
    spec_b = "specs/SPEC-stop-b.md"
    ctx.write(spec_b, (ctx.fixtures / "agents" / "stop-iteration3" / "SPEC-stop.md").read_bytes().decode("utf-8"))
    run_b, _ = start(ctx, spec_b)
    for i in (1, 2):
        ctx.json(record(ctx, run_b, "factory-builder"), "builder b%d" % i)
        ctx.json(record(ctx, run_b, "factory-verifier",
                        output=agents.frozen_output(ctx, "stop-iteration3", "verifier-b%d.md" % i)), "verifier b%d" % i)
    ctx.json(record(ctx, run_b, "factory-builder"), "builder b3")
    dead = ctx.json(record(ctx, run_b, "factory-verifier", dead=True), "dead verifier")
    ctx.json(ctx.h("begin", "--run", run_b, "--slot", "factory-verifier"), "begin")
    done = ctx.json(record(ctx, run_b, "factory-verifier",
                           output=agents.frozen_output(ctx, "stop-iteration3", "verifier-b3.md")), "verifier b3")
    lines = [l for l in ctx.journal(run_b) if "agent" in l]
    verifiers = [l for l in lines if l["agent"] == "factory-verifier"]
    ctx.check(5, dead.get("action") == "relaunch" and done.get("action") == "success" and done.get("iteration") == 3
              and verifiers[2]["verdict"] == "DEAD" and verifiers[2]["iteration"] == verifiers[3]["iteration"] == 3,
              "dead=%s done=%s/%s" % (dead.get("action"), done.get("action"), done.get("iteration")))
