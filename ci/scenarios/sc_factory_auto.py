# factory-auto: a whole factory-run cycle in `auto`, up to the Verifier (7 assertions).
#
# The sequence is the one prescribed by the generated orchestrator (the installed .claude/skills/factory-run/SKILL.md,
# rendered from profiles/software/bodies/orchestrator.md): the LLM is not replayed, the agents are frozen outputs and a real test run.

import agents
import install

ID = "factory-auto"
PRESCRIBES = [
    ("factory-run start", "skills/_core/profiles/software/bodies/orchestrator.md"),
    ("factory-run bind", "skills/_core/profiles/software/bodies/orchestrator.md"),
    ("spec settle", "skills/_core/profiles/software/bodies/orchestrator.md"),
    ("gate decide", "skills/_core/profiles/software/bodies/orchestrator.md"),
    ("spec set-status", "skills/_core/profiles/software/bodies/orchestrator.md"),
    ("activate", "skills/_core/profiles/software/bodies/orchestrator.md"),
    ("factory-run record", "skills/_core/profiles/software/bodies/orchestrator.md"),
]
SESSION = "factory-auto-session"


def approval(ctx, run):
    """Gate factory-run.approval under `auto`: the default is applied, nothing is asked."""
    decision = ctx.json(ctx.h("gate", "decide", "--run", run, "--id", "factory-run.approval"), "gate decide")
    answer = ctx.json(ctx.h("gate", "answer", "--run", run, "--id", "factory-run.approval", "--default"),
                      "gate answer")
    return decision, answer


def record(ctx, run, agent, output=None):
    args = ["factory-run", "record", "--run", run, "--agent", agent, "--model", "inherit", "--duration-ms", "1"]
    if output:
        args += ["--output", output]
    return ctx.h(*args)


def run(ctx):
    install.install(ctx)
    install.commit_all(ctx)
    spec = "specs/SPEC-mean.md"
    generated = ctx.read(".claude/skills/factory-run/SKILL.md")
    missing = [sub for sub, _ in PRESCRIBES if sub not in generated]
    if missing:
        raise AssertionError("the generated factory-run skill does not prescribe: %s" % ", ".join(missing))

    # 1. The need, written by Write, is routed to the Plan phase.
    ctx.write_transit("factory-run-arguments.txt", (ctx.fixtures / "agents" / "factory-auto" / "need.txt")
                      .read_bytes().decode("utf-8"))
    start = ctx.json(ctx.h("factory-run", "start", "--arguments-file", ".harness/runs/factory-run-arguments.txt"),
                     "factory-run start")
    run = start["run"]
    ctx.check(1, start.get("mode") == "plan" and start.get("autonomy") == "auto",
              "mode=%s autonomy=%s" % (start.get("mode"), start.get("autonomy")))

    # 2. Planner: no blocking question; the spec is written, settled, approved by default.
    ctx.json(record(ctx, run, "factory-planner"), "record planner")
    ctx.write(spec, (ctx.fixtures / "agents" / "factory-auto" / "SPEC-mean.md").read_bytes().decode("utf-8"))
    ctx.json(ctx.h("factory-run", "bind", "--run", run, "--spec", spec), "factory-run bind")
    settled = ctx.json(ctx.h("spec", "settle", "--run", run, "--file", spec), "spec settle")
    decision, answer = approval(ctx, run)
    ctx.json(ctx.h("spec", "set-status", spec, "APPROUVEE"), "spec set-status")
    parsed = ctx.json(ctx.h("spec", "check", spec), "spec check")
    gates = [l for l in ctx.journal(run) if l.get("event") == "gate" and l.get("id") == "factory-run.approval"]
    ctx.check(2, parsed["blocking"] == [] and parsed["status"] == "APPROUVEE" and settled.get("action") == "defaults"
              and decision.get("decision") == "default" and answer.get("source") == "default"
              and gates and all(g.get("source") in (None, "default") for g in gates)
              and any(g.get("phase") == "answer" and g.get("source") == "default" for g in gates),
              "blocking=%s status=%s gate=%s/%s" % (parsed["blocking"], parsed["status"], decision.get("decision"),
                                                    answer.get("source")))

    # 3. Builder (frozen fix), 4. Verifier (real tests).
    ctx.json(ctx.h("activate", "--run", run, "--skill", "factory-run", "--session", SESSION, "--spec", spec),
             "activate")
    ctx.json(record(ctx, run, "factory-builder"), "record builder")
    agents.apply_patch(ctx, "factory-auto", "builder.patch")
    ctx.check(3, "def mean" in ctx.read("toy/core.py") and (ctx.work / "tests" / "test_mean.py").is_file(),
              "mean present=%s" % ("def mean" in ctx.read("toy/core.py")))

    output, passed = agents.verifier_output(ctx, "verifier-1.md")
    done = ctx.json(record(ctx, run, "factory-verifier", output), "record verifier")
    ctx.json(ctx.h("deactivate", "--run", run, "--session", SESSION), "deactivate")
    ctx.check(4, passed and done.get("action") == "success" and done.get("iteration") == 1
              and done.get("tests_passed") is True,
              "tests passed=%s action=%s iteration=%s" % (passed, done.get("action"), done.get("iteration")))

    # 5. Journal and agent sequence; 6. nothing asked, nothing stopped.
    valid = ctx.h("journal", "validate", run)
    journal = ctx.journal(run)
    sequence = [l["agent"] for l in journal if "agent" in l]
    ctx.check(5, valid.returncode == 0 and sequence == ["factory-planner", "factory-builder", "factory-verifier"],
              "validate=%d agents=%s" % (valid.returncode, sequence))
    asks = [l for l in journal if l.get("event") == "gate" and l.get("decision") == "ask"]
    stops = list((ctx.work / ".harness" / "runs").glob("STOP-*.md"))
    ctx.check(6, not asks and not stops, "ask events=%d stop files=%d" % (len(asks), len(stops)))

    # 7. Counter-test: a blocking question blocks the spec, no Builder runs; once answered, the cycle resumes.
    blocked = "specs/SPEC-blocked.md"
    ctx.write_transit("factory-run-arguments.txt", "Add a largest function to a new module toy.extra\n")
    start_b = ctx.json(ctx.h("factory-run", "start", "--arguments-file", ".harness/runs/factory-run-arguments.txt"),
                       "factory-run start (blocked)")
    run_b = start_b["run"]
    ctx.json(record(ctx, run_b, "factory-planner"), "record planner (blocked)")
    ctx.write(blocked, (ctx.fixtures / "agents" / "factory-auto" / "SPEC-blocked.md").read_bytes().decode("utf-8"))
    ctx.json(ctx.h("factory-run", "bind", "--run", run_b, "--spec", blocked), "factory-run bind (blocked)")
    settle = ctx.h("spec", "settle", "--run", run_b, "--file", blocked)
    status = ctx.json(ctx.h("spec", "check", blocked), "spec check (blocked)")["status"]
    stop_files = sorted((ctx.work / ".harness" / "runs").glob("STOP-*.md"))
    builders = [l for l in ctx.journal(run_b) if l.get("agent") == "factory-builder"]
    blocked_ok = settle.returncode == 1 and status == "BLOQUEE" and len(stop_files) == 1 and not builders

    text = ctx.read(blocked)
    ctx.write(blocked, text.replace("Réponse :\n", "Réponse : empty list gives None\n"))
    ctx.write_transit("factory-run-arguments.txt", blocked + "\n")
    resumed = ctx.json(ctx.h("factory-run", "start", "--arguments-file", ".harness/runs/factory-run-arguments.txt"),
                       "factory-run start (answered)")
    run_c = resumed["run"]
    settle_c = ctx.json(ctx.h("spec", "settle", "--run", run_c, "--file", blocked), "spec settle (answered)")
    approval(ctx, run_c)
    ctx.json(ctx.h("spec", "set-status", blocked, "APPROUVEE"), "spec set-status (answered)")
    ctx.json(record(ctx, run_c, "factory-builder"), "record builder (resumed)")
    agents.apply_patch(ctx, "factory-auto", "builder-2.patch")
    output, passed = agents.verifier_output(ctx, "verifier-2.md")
    final = ctx.json(record(ctx, run_c, "factory-verifier", output), "record verifier (resumed)")
    ctx.check(7, blocked_ok and resumed.get("mode") == "approve" and settle_c.get("action") == "defaults"
              and final.get("action") == "success",
              "settle exit=%d status=%s stops=%d builders=%d resumed mode=%s final=%s"
              % (settle.returncode, status, len(stop_files), len(builders), resumed.get("mode"), final.get("action")))
