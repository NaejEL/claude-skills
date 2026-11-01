# Factory of the claude-skills repository itself, regenerated from the
# software-factory template through the 'sf' commands (UF-01 to UF-07, CA-31).
# Skipped when the core is copied into another project.

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import helpers
from hcore import factory, fusion, gates, models

REPO = helpers.CORE.parent.parent
SKILLS_DIR = REPO / "skills"
AGENTS = REPO / ".claude" / "agents"
FACTORY_RUN = REPO / ".claude" / "skills" / "factory-run" / "SKILL.md"
HARNESS = REPO / ".claude" / "harness"
IN_REPO = (SKILLS_DIR / "_core" / "harness.py").is_file() and FACTORY_RUN.is_file()
ROLES = {"factory-planner": "factory.planner", "factory-builder": "factory.builder",
         "factory-verifier": "factory.verifier"}
UNITTEST = "cd skills/_core/tests && <PY> -B -m unittest discover -s . -t ."
# D5: the three interpreters the detection can retain (a Linux or macOS CI runs python3).
WHITELIST = ("Read,Glob,Grep,Write,Edit,Bash(git *),Bash(python *),Bash(python3 *),Bash(py *),Bash(bash *),"
             "Bash(bats *),Bash(shellcheck *),Bash(pwsh *)")
# D5 in headless mode: three simple commands the CI whitelist allows (a shell
# loop is not an allowed command).
INTERP_COMMANDS = ("python .claude/harness/harness.py interp", "python3 .claude/harness/harness.py interp",
                   "py -3 .claude/harness/harness.py interp")
DETECTION = INTERP_COMMANDS[0]


def allowed(command: str, script_text: str) -> bool:
    """True when a Bash(<pattern>) entry of the script's --allowedTools allows command."""
    value = re.search(r"--allowedTools['\"]?,? ?['\"]([^'\"]+)['\"]", script_text).group(1)
    patterns = re.findall(r"Bash\(([^)]*)\)", value)
    return any(fnmatch.fnmatchcase(command, pattern) for pattern in patterns)


STRICT = os.environ.get("HARNESS_CHECK_COPY") == "1"


def copy_is_consistent(dest: Path) -> list:
    """Internal consistency of a core copy, whatever the core it is compared
    with: recognized, runnable ('version' answers its own CORE_VERSION), no
    bytecode written. Returns the problems found."""
    problems = []
    if not fusion.is_core_copy(dest):
        return ["%s is not a recognized core copy" % dest]
    declared = re.search(r'^CORE_VERSION = "([^"]+)"$', text(dest / "hcore" / "__init__.py"), re.M).group(1)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    res = subprocess.run([sys.executable, "-B", str(dest / "harness.py"), "version"], capture_output=True,
                         text=True, encoding="utf-8", env=env, timeout=60)
    if res.returncode != 0:
        problems.append("harness.py version: exit %d: %s" % (res.returncode, res.stderr.strip()))
    elif json.loads(res.stdout).get("core_version") != declared:
        problems.append("harness.py version does not answer its own CORE_VERSION %s" % declared)
    if any(dest.rglob("__pycache__")):
        problems.append("bytecode left in the copy")
    return problems


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(path: Path) -> str:
    match = re.match(r"\A---\r?\n(.*?)^---\r?$", text(path), re.S | re.M)
    assert match, path
    return match.group(1)


@unittest.skipUnless(IN_REPO, "not the claude-skills repository (core copied into a project)")
class RepoFactoryTest(unittest.TestCase):
    def test_uf01_generated_from_the_template_with_model_blocks(self):
        """UF-01: the three agents carry the regenerable harness.model block (X1), with
        the model of their role from .claude/models.json (absent -> inherit), and
        installing them again changes nothing; factory-run has the template frontmatter."""
        expected = models.resolve_root(REPO, models.FACTORY_ROLES)["roles"]
        for name, role in ROLES.items():
            path = AGENTS / ("%s.md" % name)
            body = text(path)
            self.assertTrue(models.has_block(body), name)
            self.assertEqual(models.model_in_block(body), expected[role]["model"], name)
            self.assertEqual(models.with_model_block(models.without_model_block(body), expected[role]["model"]), body)
            self.assertIn("name: %s\n" % name, frontmatter(path))
        self.assertIn("tools: Read, Glob, Grep\n", frontmatter(AGENTS / "factory-planner.md"))
        self.assertIn("tools: Read, Glob, Grep, Bash\n", frontmatter(AGENTS / "factory-verifier.md"))
        self.assertNotIn("tools:", frontmatter(AGENTS / "factory-builder.md"))
        fm = frontmatter(FACTORY_RUN)
        self.assertEqual(fm.splitlines(), [
            "name: factory-run",
            "description: Lance un cycle de l'usine logicielle (Planner → gate humaine sur la spec → Builder → "
            "Verifier avec boucle de correction) sur un besoin ou une spec approuvée.",
            "disable-model-invocation: true",
            'argument-hint: "<besoin | chemin d\'une spec approuvée> [--models \\"role=modele;...\\"]"'])

    def test_uf02_ca31_planner_lists_the_eight_skills_and_core_is_not_one(self):
        """UF-02, CA-31: the Planner names every skill of skills/ (ten since Phase 3) and says that _core is not a skill (C1)."""
        planner = text(AGENTS / "factory-planner.md")
        names = sorted(p.name for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").is_file())
        self.assertEqual(len(names), 10)
        for name in names:
            self.assertIn("`%s`" % name, planner)
        self.assertRegex(planner, r"`skills/_core/` : \*\*[^*]*qui n'est pas un skill\*\*")
        self.assertFalse((SKILLS_DIR / "_core" / "SKILL.md").exists())

    def test_uf03_ca31_builder_and_verifier_gates(self):
        """UF-03, CA-31: bash -n, frontmatter check, the unittest command of the core
        with the detected interpreter, and no __pycache__ left, for both roles."""
        for name in ("factory-builder", "factory-verifier"):
            body = text(AGENTS / ("%s.md" % name))
            self.assertIn("bash -n install_skills.sh", body, name)
            self.assertIn("`name` correspond au nom du dossier parent" if name == "factory-builder"
                          else "`name` identique au nom du dossier parent", body, name)
            self.assertIn(UNITTEST, body, name)
            for command in INTERP_COMMANDS:
                self.assertIn("`%s`" % command, body, name)
            self.assertNotIn("command -v timeout", body, name)
            self.assertIn("unittest discover", body, name)
            self.assertIn("find skills .claude -name __pycache__ -o -name '*.pyc'", body, name)

    def test_uf04_ca11_factory_run_rebranched_on_the_core(self):
        """UF-04, CA-11 (factory-run.need), CA-31: FR-01 to FR-04 through the core copy,
        journal, gates factory-run.need / questions / approval with their options, the
        'Verifier muet' rule, and --models."""
        body = text(FACTORY_RUN)
        self.assertIn("`H` désigne `<PY> .claude/harness/harness.py`", body)
        for command in INTERP_COMMANDS:
            self.assertIn("`%s`" % command, body)
        self.assertNotIn("command -v timeout", body)
        for needle in (".claude/harness/harness.py", "H factory-run start --arguments-file",
                       "H factory-run record --run <run> --agent <nom>", ".harness/runs/factory-run-<horodatage>.jsonl",
                       "H journal amend", "H begin --run <run> --slot <nom>", "`success`", "`fix`", "`relaunch`",
                       "`fail`", "Un Verifier muet n'est pas un Verifier satisfait", "Ne jamais approuver par épuisement",
                       "`pass_param`", "--headless", factory.APPROVED_LINE, "Ne jamais commiter à sa place"):
            self.assertIn(needle, body)
        for rule in ("FR-01", "FR-02", "FR-03", "FR-04"):
            self.assertIn(rule, body)
        for gid in ("factory-run.need", "factory-run.questions", "factory-run.approval"):
            gate = gates.get(gid)
            self.assertIn(gid, body)
            for option in gate.options:
                self.assertIn(option, body, (gid, option))

    def test_uf05_harness_is_a_consistent_core_copy(self):
        """UF-05 (Q-C), in T: .claude/harness/ is a recognized, runnable core copy.
        A core that evolves in a lot does not make T fail: the strict identity is
        checked on demand (HARNESS_CHECK_COPY=1, or 'sf copy-core --check')."""
        self.assertTrue(HARNESS.is_dir(), "copy missing: run 'sf copy-core --root .'")
        self.assertEqual(copy_is_consistent(HARNESS), [])

    @unittest.skipUnless(STRICT, "strict copy check on demand: HARNESS_CHECK_COPY=1")
    def test_uf05_ca31_strict_identity_on_demand(self):
        """UF-05, CA-31 (on demand): .claude/harness/ is identical to skills/_core/
        (no file missing, extra or different); 'sf copy-core --check' exits 0."""
        self.assertEqual(fusion.check_core_copy(SKILLS_DIR / "_core", REPO)["identical"], True)
        res = helpers.harness(["sf", "copy-core", "--root", str(REPO), "--check"], REPO)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_uf06_ca31_ci_whitelist_and_syntax(self):
        """UF-06, CA-31: --allowedTools = the template base, the core interpreter
        (Bash(py *)), git, bash, bats, shellcheck, pwsh, in both scripts; bash -n and
        the PowerShell parser accept them."""
        sh, ps1 = REPO / "ci" / "factory.sh", REPO / "ci" / "factory.ps1"
        self.assertIn('--allowedTools "%s"' % WHITELIST, text(sh))
        self.assertIn("'--allowedTools', '%s'" % WHITELIST, text(ps1))
        self.assertRegex(text(sh), r"Bash\((py|python3?) ")
        for interpreter in ("python", "python3", "py"):
            self.assertIn("Bash(%s *)" % interpreter, text(sh))
        # The D5 detection of <PY> and the core calls run in headless mode.
        for script in (sh, ps1):
            for command in INTERP_COMMANDS + ("py -3 .claude/harness/harness.py factory-run start",
                                              "python3 .claude/harness/harness.py gate decide"):
                self.assertTrue(allowed(command, text(script)), (script.name, command))
            self.assertFalse(allowed('t=; command -v timeout >/dev/null && t="timeout 5"', text(script)))
        for script in (sh, ps1):
            body = text(script)
            self.assertIn("Statut : APPROUVEE", body)
            self.assertIn("--max-turns", body)
            self.assertIn("factory-logs", body)
        self.assertIn("set -euo pipefail", text(sh))
        self.assertIn("$ErrorActionPreference = 'Stop'", text(ps1))
        bash = shutil.which("bash")
        if bash:
            res = subprocess.run([bash, "-n", str(sh)], capture_output=True, text=True, timeout=60)
            self.assertEqual(res.returncode, 0, res.stderr)
        pwsh = shutil.which("pwsh")
        if pwsh:
            command = "[scriptblock]::Create((Get-Content -LiteralPath '%s' -Raw)) | Out-Null" % ps1
            res = subprocess.run([pwsh, "-NoProfile", "-Command", command], capture_output=True, text=True,
                                 timeout=120)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_uf07_ca31_repository_rules_kept(self):
        """UF-07, CA-31: never run install_skills.*, keep .sh / .ps1 equivalent, no
        accents in the installation messages: in the Builder and the Verifier."""
        for name in ("factory-builder", "factory-verifier"):
            body = text(AGENTS / ("%s.md" % name))
            self.assertIn("install_skills", body, name)
            self.assertRegex(body, r"[Nn]e \*\*jamais\*\* exécuter `install_skills\.sh` ni `install_skills\.ps1`"
                             if name == "factory-verifier" else r"exécuter `install_skills\.sh` / `install_skills\.ps1`")
            self.assertRegex(body, r"équivalen")
            self.assertRegex(body, r"accents dans les messages")


class CoreCopyTest(helpers.TempDirCase):
    def evolved_core(self) -> Path:
        core = self.tmp / "core"
        shutil.copytree(str(helpers.CORE), str(core), ignore=shutil.ignore_patterns("__pycache__"))
        path = core / "hcore" / "relaunch.py"
        path.write_text(path.read_text(encoding="utf-8") + "# evolved in a later lot\n", encoding="utf-8")
        return core

    def test_uf05_consistency_check_survives_a_core_evolution(self):
        """UF-05: the T-level check of the copy does not fail when the core evolves
        (the strict comparison does, on demand)."""
        root = self.tmp / "project"
        fusion.copy_core(helpers.CORE, root)
        evolved = self.evolved_core()
        strict = fusion.check_core_copy(evolved, root)
        self.assertEqual((strict["identical"], strict["differs"]), (False, ["hcore/relaunch.py"]))
        self.assertEqual(copy_is_consistent(root / ".claude" / "harness"), [])
        res = helpers.harness(["sf", "copy-core", "--root", str(root), "--check"], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_uf05_refresh_replaces_a_recognized_copy_and_never_a_foreign_file(self):
        """UF-05 (sf copy-core --refresh): a recognized copy gets every core file
        (created or replaced); a file that is not a core file is never touched
        and is reported; an unrecognized .claude/harness/ is left as it is (exit 1);
        --check exits 1 while the copy differs."""
        root = self.tmp / "project"
        res = helpers.harness(["sf", "copy-core", "--root", str(root), "--refresh"], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        dest = root / ".claude" / "harness"
        self.assertTrue(fusion.check_core_copy(helpers.CORE, root)["identical"])
        (dest / "hcore" / "relaunch.py").write_text("# stale\n", encoding="utf-8")
        (dest / "hcore" / "gates.py").unlink()
        (dest / "NOTES.txt").write_text("mine\n", encoding="utf-8")
        self.assertEqual(helpers.harness(["sf", "copy-core", "--root", str(root), "--check"], self.tmp).returncode, 1)
        out = json.loads(helpers.harness(["sf", "copy-core", "--root", str(root), "--refresh"], self.tmp).stdout)
        self.assertEqual(out["files"][".claude/harness/hcore/relaunch.py"], fusion.MERGED)
        self.assertEqual(out["files"][".claude/harness/hcore/gates.py"], fusion.CREATED)
        self.assertEqual(out["foreign"], [".claude/harness/NOTES.txt"])
        self.assertEqual((dest / "NOTES.txt").read_text(encoding="utf-8"), "mine\n")
        check = fusion.check_core_copy(helpers.CORE, root)
        self.assertEqual((check["differs"], check["missing"], check["extra"]), ([], [], ["NOTES.txt"]))
        other = self.tmp / "other"
        (other / ".claude" / "harness").mkdir(parents=True)
        (other / ".claude" / "harness" / "harness.py").write_text("print('mine')\n", encoding="utf-8")
        res = helpers.harness(["sf", "copy-core", "--root", str(other), "--refresh"], self.tmp)
        self.assertEqual(res.returncode, 1, res.stderr)
        self.assertEqual(sorted(p.name for p in (other / ".claude" / "harness").iterdir()), ["harness.py"])
        self.assertEqual((other / ".claude" / "harness" / "harness.py").read_text(encoding="utf-8"), "print('mine')\n")


if __name__ == "__main__":
    unittest.main()
