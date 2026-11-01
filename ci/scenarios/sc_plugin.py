# plugin-guard: the version guard of the plugin and the effective skill name (7 assertions).
#
# The guard is exercised on a throw-away git repository (behavior), then on this repository itself
# (the real gate: skills/ must not change after the last version bump without a new version).

import json
import os

from common import ROOT

ID = "plugin-guard"
NUMBERS = (1, 2, 3, 4, 5, 6, 7)
PRESCRIBES = [
    ("plugin version-guard", "ci/test-harness.sh"),
    ("plugin version-guard", "ci/test-harness.ps1"),
    ("plugin skill-name", "skills/harness-doctor/SKILL.md"),
    ("plugin skill-name", "skills/ai-lab/SKILL.md"),
    ("audit alias-args", "skills/legacy-audit/SKILL.md"),
]


def manifest(version):
    return json.dumps({"name": "harness", "version": version}, indent=2) + "\n"


def guard(ctx, root):
    res = ctx.k("plugin", "version-guard", "--root", str(root))
    try:
        data = json.loads(res.stdout)
    except ValueError:
        data = {}
    return res.returncode, data


def run(ctx):
    repo = ctx.work
    ctx.write(".claude-plugin/plugin.json", manifest("1.0.0"))
    ctx.write("skills/demo/SKILL.md", "---\nname: demo\n---\nbody\n")
    ctx.init_git(repo)

    # 1. Nothing changed since the commit that set the version: the guard passes.
    code, data = guard(ctx, repo)
    ctx.check(1, code == 0 and data.get("status") == "clean", "exit=%d data=%s" % (code, data))

    # 2. A change under skills/ without a version bump fails and names the file.
    ctx.write("skills/demo/SKILL.md", "---\nname: demo\n---\nchanged\n")
    code, data = guard(ctx, repo)
    ctx.check(2, code == 1 and data.get("status") == "stale" and data.get("files") == ["skills/demo/SKILL.md"],
              "exit=%d data=%s" % (code, data))

    # 3. A new file under skills/ counts too.
    ctx.write("skills/other/SKILL.md", "---\nname: other\n---\n")
    code, data = guard(ctx, repo)
    ctx.check(3, code == 1 and "skills/other/SKILL.md" in data.get("files", []), "exit=%d data=%s" % (code, data))

    # 4. With a version bump the same changes pass.
    ctx.write(".claude-plugin/plugin.json", manifest("1.0.1"))
    code, data = guard(ctx, repo)
    ctx.check(4, code == 0 and data.get("status") == "bumped", "exit=%d data=%s" % (code, data))

    # 5. Once the bump is committed, the baseline moves: clean again, and a later change fails again.
    ctx.git("add", "-A", cwd=repo)
    ctx.git("commit", "-q", "-m", "bump", cwd=repo)
    code_clean, data_clean = guard(ctx, repo)
    ctx.write("skills/demo/SKILL.md", "---\nname: demo\n---\nagain\n")
    code_stale, _ = guard(ctx, repo)
    ctx.check(5, code_clean == 0 and data_clean.get("status") == "clean" and code_stale == 1,
              "after bump=%d/%s, after change=%d" % (code_clean, data_clean.get("status"), code_stale))

    # 6. The effective name, in both modes. Plugin mode: the skill folder sits under a root that holds the
    # manifest. Links mode: the folder is a link under a folder without manifest. The skill folder is
    # not resolved, so a link to a plugin-shaped repository still counts as links mode.
    plugin_dir = os.path.join(str(repo), "skills", "demo")
    links_dir = os.path.join(str(ctx.home), ".claude", "skills", "demo")
    in_plugin = ctx.json(ctx.k("plugin", "skill-name", "--skill", "ship-pr", "--skill-dir", plugin_dir), "name plugin")
    in_links = ctx.json(ctx.k("plugin", "skill-name", "--skill", "ship-pr", "--skill-dir", links_dir), "name links")
    ctx.check(6, in_plugin["name"] == "harness:ship-pr" and in_plugin["mode"] == "plugin"
              and in_links["name"] == "ship-pr" and in_links["mode"] == "links",
              "plugin=%s links=%s" % (in_plugin, in_links))

    # 7. The real gate on this repository.
    code, data = guard(ctx, ROOT)
    ctx.check(7, code == 0, "exit=%d status=%s version=%s files=%s" % (code, data.get("status"), data.get("version"),
                                                                       data.get("files")))
