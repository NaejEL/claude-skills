# models-absent: no .claude/models.json means "inherit" everywhere (5 assertions).

import agents
import install

ID = "models-absent"
PRESCRIBES = [
    ("models resolve", "skills/_core/profiles/research/install.md"),
    ("factory-run start", "skills/software-factory/SKILL.md"),
    ("factory-run record", "skills/software-factory/SKILL.md"),
    ("doctor", "skills/harness-doctor/SKILL.md"),
]


def run(ctx):
    install.install(ctx)
    install.commit_all(ctx)
    models_file = ctx.work / ".claude" / "models.json"

    resolved = ctx.json(ctx.k("models", "resolve", "--root", "."), "models resolve")["roles"]
    odd = {r: v for r, v in resolved.items()
           if (r == "harness.scout" and v != {"model": "haiku", "pass_param": True})
           or (r != "harness.scout" and v != {"model": "inherit", "pass_param": False})}
    ctx.check(1, bool(resolved) and not odd and "harness.scout" in resolved, "unexpected=%s" % odd)

    # A replayed cycle on an approved spec: every agent line of the journal says "inherit".
    spec = "specs/SPEC-models.md"
    ctx.write(spec, (ctx.fixtures / "agents" / "models-absent" / "SPEC-models.md").read_bytes().decode("utf-8"))
    ctx.write_transit("factory-run-arguments.txt", spec + "\n")
    start = ctx.json(ctx.h("factory-run", "start", "--arguments-file", ".harness/runs/factory-run-arguments.txt"),
                     "factory-run start")
    run_path = start["run"]
    models = start["models"]
    for agent, role in (("factory-builder", "factory.builder"), ("factory-verifier", "factory.verifier")):
        args = ["factory-run", "record", "--run", run_path, "--agent", agent, "--model", models[role]["model"],
                "--duration-ms", "1"]
        if agent == "factory-verifier":
            args += ["--output", agents.verifier_output(ctx, "verifier-1.md")[0]]
        step = ctx.json(ctx.h(*args), "record " + agent)
    lines = [l for l in ctx.journal(run_path) if "agent" in l]
    ctx.check(2, step.get("action") == "success" and len(lines) == 2 and all(l["model"] == "inherit" for l in lines),
              "models=%s" % [l.get("model") for l in lines])
    ctx.check(3, not models_file.exists(), "models.json exists=%s" % models_file.exists())

    doctor = ctx.json(ctx.k("doctor", "--root", ".", "--no-journal"), "doctor")
    status = doctor.get("models", {})
    ctx.check(4, status.get("models_json") is False and status.get("status") == "warn", "models=%s" % status)

    one = ctx.json(ctx.k("models", "resolve", "--root", ".", "--models", "factory.verifier=haiku"),
                   "models resolve --models")["roles"]
    passed = sorted(r for r, v in one.items() if v["pass_param"] and r != "harness.scout")
    ctx.check(5, passed == ["factory.verifier"] and one["factory.verifier"]["model"] == "haiku"
              and not models_file.exists(), "pass_param=%s file=%s" % (passed, models_file.exists()))
