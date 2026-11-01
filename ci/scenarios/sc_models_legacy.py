# models-legacy: the lab-models.json of ai-lab is migrated once, never altered (4 assertions).

import json

ID = "models-legacy"
PRESCRIBES = [
    ("models resolve", "skills/_core/profiles/research/install.md"),
]


def run(ctx):
    legacy_src = (ctx.fixtures / "legacy-node" / "claude" / "lab-models.json").read_bytes()
    ctx.work.mkdir(parents=True, exist_ok=True)
    (ctx.work / ".claude").mkdir()
    legacy, models = ctx.work / ".claude" / "lab-models.json", ctx.work / ".claude" / "models.json"
    legacy.write_bytes(legacy_src)

    first = ctx.json(ctx.k("models", "resolve", "--root", "."), "models resolve")
    wanted = {"lab." + role: model for role, model in json.loads(legacy_src.decode("utf-8")).items()}
    written = json.loads(models.read_bytes().decode("utf-8")) if models.exists() else None
    ctx.check(1, first.get("migrated") is True and written == wanted and legacy.read_bytes() == legacy_src,
              "migrated=%s models.json=%s legacy_intact=%s" % (first.get("migrated"), written == wanted,
                                                               legacy.read_bytes() == legacy_src))

    snapshot = models.read_bytes()
    second = ctx.json(ctx.k("models", "resolve", "--root", "."), "second models resolve")
    ctx.check(2, models.read_bytes() == snapshot and second.get("migrated") is False,
              "migrated=%s unchanged=%s" % (second.get("migrated"), models.read_bytes() == snapshot))

    both = ctx.json(ctx.k("models", "resolve", "--root", "."), "models resolve with both files")
    warnings = " ".join(both.get("warnings", []))
    ctx.check(3, "lab-models.json ignored" in warnings and models.read_bytes() == snapshot
              and legacy.read_bytes() == legacy_src, "warnings=%s" % both.get("warnings"))

    # X8: an unknown value is an explicit error, nothing is guessed.
    bad = json.loads(legacy_src.decode("utf-8"))
    bad["neuro"] = "not-a-model"
    models.unlink()
    legacy.write_bytes((json.dumps(bad, indent=2) + "\n").encode("utf-8"))
    res = ctx.k("models", "resolve", "--root", ".")
    ctx.check(4, res.returncode == 2 and "unknown model" in res.stderr and not models.exists(),
              "exit=%d stderr=%s models.json=%s" % (res.returncode, res.stderr.strip()[:120], models.exists()))
