# plugin-validate: `claude plugin validate .` accepts the manifests of this repository (1 assertion).
#
# The command is offline and does not call the model. It is SKIP when the claude CLI is not installed.
# The CLI is the real one (found with the PATH of the runner, not the scrubbed PATH of the scenarios) and
# runs with a throw-away configuration folder.

import os
import shutil
import subprocess

from common import ROOT, Skip

ID = "plugin-validate"
NUMBERS = (1,)
PRESCRIBES = [
    ("claude plugin validate", ".claude-plugin/plugin.json"),
    ("claude plugin validate", ".claude-plugin/marketplace.json"),
]


def run(ctx):
    claude = shutil.which("claude")
    if not claude:
        raise Skip("claude CLI not found")
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(ctx.home / ".claude"), HOME=str(ctx.home), USERPROFILE=str(ctx.home))
    res = subprocess.run([claude, "plugin", "validate", "."], cwd=str(ROOT), env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=120)
    ctx.check(1, res.returncode == 0, "exit=%d %s" % (res.returncode, (res.stdout + res.stderr).strip()[-300:]))
