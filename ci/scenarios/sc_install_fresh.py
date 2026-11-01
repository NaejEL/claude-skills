# install-fresh: installation of /software-factory on toy-py, replayed (9 assertions).

import json
from collections import OrderedDict
from pathlib import Path

import install
from common import CORE

ID = "install-fresh"
PRESCRIBES = [
    ("sf copy-core", "skills/_core/profiles/software/install.md"),
    ("scout verdict", "skills/software-factory/SKILL.md"),
    ("gate decide", "skills/software-factory/SKILL.md"),
    ("stack detect", "skills/software-factory/SKILL.md"),
    ("upgrade plan", "skills/software-factory/SKILL.md"),
    ("upgrade apply", "skills/software-factory/SKILL.md"),
    ("stamp autonomy", "skills/software-factory/SKILL.md"),
    ("hooks install", "skills/software-factory/SKILL.md"),
]


def ordered(text):
    return json.dumps(json.loads(text, object_pairs_hook=OrderedDict), indent=1)


def run(ctx):
    exp = ctx.fixtures / "expected" / "install-fresh"
    obs = install.install(ctx)
    work = ctx.work

    created = sorted(p for p in ctx.tree() if p not in obs["before"] and not p.startswith(".claude/harness/"))
    expected = sorted(l.strip() for l in (exp / "files.txt").read_text(encoding="utf-8").splitlines() if l.strip())
    ctx.check(1, created == expected, "created=%s expected=%s" % (created, expected))

    kinds = [f["kind"] for f in obs["applied"]["files"]]
    ctx.check(2, obs["applied"]["applied"] == len(kinds) and all(k in ("create", "merge", "stamp") for k in kinds)
              and "create" in kinds and not obs["applied"].get("legacy"), "kinds=%s" % kinds)

    same = _same_tree(CORE, work / ".claude" / "harness")
    version = ctx.json(ctx.k("version"), "version")["core_version"]
    installed = ctx.json(ctx.h("version"), "installed version")["core_version"]
    ctx.check(3, same == [] and installed == version, "differences=%s core=%s installed=%s" % (same[:5], version, installed))

    got = {
        "settings": ordered(ctx.read(".claude/settings.json").replace(ctx.interp, "{PY}")),
        "tasks": ordered(ctx.read(".vscode/tasks.json")),
    }
    want = {
        "settings": ordered((exp / "settings.json").read_bytes().decode("utf-8")),
        "tasks": ordered((exp / "tasks.json").read_bytes().decode("utf-8")),
    }
    gitignore = ctx.read(".gitignore").replace("\r\n", "\n")
    want_ignore = (exp / "gitignore.txt").read_bytes().decode("utf-8").replace("\r\n", "\n")
    ctx.check(4, got == want and gitignore == want_ignore,
              "settings=%s tasks=%s gitignore=%s" % (got["settings"] == want["settings"],
                                                      got["tasks"] == want["tasks"], gitignore == want_ignore))

    stamp = json.loads(ctx.read(".claude/harness.json"))
    skill = stamp.get("skills", {}).get("software-factory", {})
    profiles = [(p.get("name"), p.get("by")) for p in stamp.get("profiles", [])]
    ctx.check(5, stamp.get("autonomy") == "auto" and profiles == [("software", "scout")]
              and skill.get("core_version") == version and bool(skill.get("repo_commit")),
              "autonomy=%s profiles=%s core=%s" % (stamp.get("autonomy"), profiles, skill.get("core_version")))

    settings = json.loads(ctx.read(".claude/settings.json"))
    hooks = settings.get("hooks", {}).get("PreToolUse", [])
    commands = [h.get("command", "") for entry in hooks for h in entry.get("hooks", [])]
    matchers = sorted(entry.get("matcher") for entry in hooks)
    ctx.check(6, len(commands) == 2 and all(".claude/harness/hooks/hook.py" in c for c in commands)
              and any("pre-edit" in c for c in commands) and any("pre-bash" in c for c in commands),
              "matchers=%s" % matchers)

    headers = {}                                  # the version header is the first comment line of the file
    for rel in (".claude/agents/factory-planner.md", ".claude/agents/factory-builder.md",
                ".claude/agents/factory-verifier.md", ".claude/skills/factory-run/SKILL.md",
                "ci/factory.sh", "ci/factory.ps1"):
        headers[rel] = next((l for l in ctx.read(rel).splitlines()[:4] if l.startswith("# harness:")), "")
    ctx.check(7, all(h.startswith("# harness: claude-skills ") and "core %s" % version in h for h in headers.values()),
              "headers=%s" % headers)

    install.commit_all(ctx)
    ctx.write_transit("sf-params.json", json.dumps({"test_command": obs["params_command"]}))
    second = ctx.json(ctx.k("upgrade", "plan", "--root", ".", "--skill", "software-factory", "--profiles", "software",
                            "--by", "scout", "--params-file", ".harness/runs/sf-params.json",
                            "--interpreter", ctx.interp), "second upgrade plan")
    check_core = ctx.k("sf", "copy-core", "--root", ".", "--check")
    hooks2 = ctx.json(ctx.k("hooks", "install", "--root", ".", "--py", ctx.interp), "second hooks install")
    status = ctx.git("status", "--porcelain")
    ctx.check(8, second.get("changes") == [] and check_core.returncode == 0
              and all(v not in ("créé", "fusionné") for v in hooks2.get("entries", {}).values())
              and status.strip() == "",
              "changes=%s core_check=%s hooks=%s status=%r" % (len(second.get("changes", [])), check_core.returncode,
                                                               hooks2, status.strip()))

    journal = obs["scout_run"]
    valid = ctx.k("journal", "validate", journal)
    lines = ctx.journal(journal)
    ctx.check(9, valid.returncode == 0 and any(l.get("agent") == "harness-scout" for l in lines),
              "validate=%d agents=%s" % (valid.returncode, [l.get("agent") for l in lines if "agent" in l]))


def _same_tree(a, b):
    """Differences between two trees (like `diff -r -x __pycache__`)."""
    def files(root):
        return {p.relative_to(root).as_posix(): p for p in Path(root).rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    left, right = files(a), files(b)
    right.pop("MANIFEST.json", None)              # written by copy-core itself, not part of the core
    out = ["only in core: " + n for n in sorted(set(left) - set(right))]
    out += ["only in copy: " + n for n in sorted(set(right) - set(left))]
    out += ["differs: " + n for n in sorted(set(left) & set(right))
            if left[n].read_bytes().replace(b"\r\n", b"\n") != right[n].read_bytes().replace(b"\r\n", b"\n")]
    return out
