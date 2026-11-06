# upgrade-legacy: `--upgrade` of a project installed the old way (8 assertions).
#
# legacy-node = the sources of tests/fixtures/toy-project (referenced, not copied) + the files generated
# before the v2 core (no block, no stamp), with the out-of-block customizations listed in customizations.json.

import json
import shutil

import install
from common import REPO_FIXTURES, Prep

ID = "upgrade-legacy"
PRESCRIBES = [
    ("stamp resolve", "skills/software-factory/SKILL.md"),
    ("doctor", "skills/harness-doctor/SKILL.md"),
    ("sf copy-core", "skills/_core/profiles/software/install.md"),
    ("upgrade plan", "skills/software-factory/SKILL.md"),
    ("upgrade apply", "skills/software-factory/SKILL.md"),
    ("sf install", "skills/software-factory/SKILL.md"),
    ("factory-run start", "skills/software-factory/SKILL.md"),
]
GENERATED = (".claude/agents/factory-planner.md", ".claude/agents/factory-builder.md",
             ".claude/agents/factory-verifier.md", ".claude/skills/factory-run/SKILL.md",
             "ci/factory.sh", "ci/factory.ps1")
ALLOWED = set(GENERATED) | {".claude/settings.json", ".vscode/tasks.json", ".gitignore", ".claude/models.json",
                            ".claude/harness.json"}


def build_legacy(ctx, dest):
    """toy-project sources + the legacy files under their real names, committed."""
    fixture = ctx.fixtures / "legacy-node"
    meta = json.loads((fixture / "fixture.json").read_bytes().decode("utf-8"))
    sources = [REPO_FIXTURES / s["path"].split("tests/fixtures/", 1)[1] for s in meta["sources"]]
    for source in sources:
        if not source.is_dir():
            raise Prep("referenced fixture missing: %s" % source)
        ctx.copy_fixture(source, dest)
    ctx.copy_fixture(fixture, dest, renames=meta["renames"], skip=("fixture.json", "customizations.json"))
    # History: the files as generated, then the team's additions (the conversion tells them apart through git).
    appended = [c for c in json.loads((fixture / "customizations.json").read_bytes().decode("utf-8")) if c.get("suffix")]
    finals = {}
    for item in appended:
        text = ctx.read(item["project_path"], root=dest)
        if not text.endswith(item["suffix"]):
            raise Prep("%s does not end with the declared suffix of customizations.json" % item["project_path"])
        finals[item["project_path"]] = text
        ctx.write(item["project_path"], text[: -len(item["suffix"])], root=dest)
    ctx.init_git(dest, "legacy installation")
    for rel, text in finals.items():
        ctx.write(rel, text, root=dest)
    ctx.git("add", "-A", cwd=dest)
    ctx.git("commit", "-q", "-m", "team customizations", cwd=dest)
    return meta


def run(ctx):
    meta = build_legacy(ctx, ctx.work)
    customizations = json.loads((ctx.fixtures / "legacy-node" / "customizations.json").read_bytes().decode("utf-8"))
    legacy_models = (ctx.fixtures / "legacy-node" / "claude" / "lab-models.json").read_bytes()
    before = ctx.tree()

    # 1. Before: inferred stamp, doctor reports it and proposes --upgrade without launching it (policy gate).
    resolved = ctx.json(ctx.k("stamp", "resolve", "--root", "."), "stamp resolve")
    doctor = ctx.json(ctx.k("doctor", "--root", ".", "--no-journal"), "doctor")
    proposal = doctor.get("proposal") or {}
    ctx.check(1, resolved.get("source") == "inferred" and resolved.get("profiles") == ["software"]
              and doctor.get("equipped") == "inferred" and proposal.get("launch") is False
              and "/software-factory --upgrade" in proposal.get("commands", []),
              "source=%s equipped=%s launch=%s commands=%s" % (resolved.get("source"), doctor.get("equipped"),
                                                              proposal.get("launch"), proposal.get("commands")))

    # Core copy (SKILL.md, upgrade step 3), then the plan.
    ctx.json(ctx.k("sf", "copy-core", "--root", "."), "sf copy-core")
    plan = ctx.json(ctx.k("upgrade", "plan", "--root", ".", "--skill", "software-factory",
                          "--interpreter", ctx.interp), "upgrade plan")
    if plan.get("action") != "plan":
        raise Prep("upgrade plan: %s" % plan.get("action"))
    changed = {c["file"] for c in plan["changes"]}
    diff_text = ctx.read(plan["diff"])
    ctx.check(2, changed <= ALLOWED and ".claude/harness.json" in changed and ".claude/models.json" in changed
              and all(name in diff_text for name in changed),
              "outside the allowed set=%s; diff complete=%s" % (sorted(changed - ALLOWED),
                                                                all(n in diff_text for n in changed)))

    applied = ctx.json(ctx.k("upgrade", "apply", "--root", ".", "--plan", plan["plan"]), "upgrade apply")

    # 3. Every customization is found again, byte for byte.
    lost = []
    for item in customizations:
        text = ctx.read(item["project_path"])
        if item["excerpt"] not in text:
            lost.append("%s: %s" % (item["project_path"], item["excerpt"]))
    ctx.check(3, bool(customizations) and not lost, "lost=%s" % lost)

    stamp = json.loads(ctx.read(".claude/harness.json"))
    skill = stamp.get("skills", {}).get("software-factory", {})
    ctx.check(4, skill.get("core_version") == ctx.json(ctx.k("version"), "version")["core_version"]
              and [p["name"] for p in stamp.get("profiles", [])] == ["software"],
              "stamp=%s" % json.dumps(stamp)[:200])

    models = json.loads(ctx.read(".claude/models.json")) if (ctx.work / ".claude" / "models.json").is_file() else None
    expected = {"lab." + role: model for role, model in json.loads(legacy_models.decode("utf-8")).items()}
    ctx.check(5, models == expected and (ctx.work / ".claude" / "lab-models.json").read_bytes() == legacy_models,
              "models.json=%s legacy intact=%s" % (models == expected,
                                                   (ctx.work / ".claude" / "lab-models.json").read_bytes() == legacy_models))

    # 6. A second upgrade changes nothing and says so.
    snapshot = ctx.tree()
    again = ctx.json(ctx.k("upgrade", "plan", "--root", ".", "--skill", "software-factory",
                           "--interpreter", ctx.interp), "second upgrade plan")
    ctx.check(6, again.get("changes") == [] and ctx.tree() == snapshot,
              "changes=%d action=%s" % (len(again.get("changes", [])), again.get("action")))

    # 7. The installed core routes an approved spec to the Build phase.
    ctx.write_transit("factory-run-arguments.txt", "specs/SPEC-somme.md\n")
    start = ctx.json(ctx.h("factory-run", "start", "--arguments-file", ".harness/runs/factory-run-arguments.txt"),
                     "factory-run start")
    ctx.check(7, start.get("mode") == "build" and start.get("spec") == "specs/SPEC-somme.md",
              "mode=%s spec=%s" % (start.get("mode"), start.get("spec")))

    # 8. A project that was not upgraded keeps every file when the old installer is replayed (no --upgrade).
    old = ctx.tmp / "not-upgraded"
    build_legacy(ctx, old)
    snapshot = ctx.tree(old)
    states = {}
    for rel in GENERATED:
        ctx.write("candidate.txt", "# regenerated by the new harness\n", root=old / ".harness" / "runs")
        res = ctx.k("sf", "install", "--root", ".", "--dest", rel, "--source", ".harness/runs/candidate.txt", cwd=old)
        try:
            states[rel] = json.loads(res.stdout).get("state") or res.stdout.strip()
        except ValueError:
            states[rel] = res.stdout.strip()
    kept = all("customized-kept" in str(v) for v in states.values())
    ctx.check(8, ctx.tree(old) == snapshot and kept, "unchanged=%s states=%s" % (ctx.tree(old) == snapshot, states))
