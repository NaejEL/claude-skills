# Installation of the hooks in .claude/settings.json: HK-01, HK-02, HK-03, HK-06.
#
# HK-06 (software-factory installs the hooks and --upgrade regenerates them) is a property of the prose; the
# command it calls, `hooks install`, is tested here.

import json
import os
import subprocess
import sys
import unittest

import helpers
import phase4
from hcore import fusion, hooks_install

HOOKS = helpers.FIXTURES / "hooks"


def find_bash():
    for exe in ("C:/Program Files/Git/bin/bash.exe", "C:/Program Files (x86)/Git/bin/bash.exe", "bash"):
        try:
            if subprocess.run([exe, "-c", "exit 0"], capture_output=True, timeout=30).returncode == 0:
                return exe
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


class InstallTest(helpers.TempDirCase):
    def settings(self, text=None):
        path = self.tmp / ".claude" / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if text is not None:
            path.write_bytes(text.encode("utf-8"))
        return path

    @unittest.skipUnless(HOOKS.is_dir(), helpers.SKIP_FIXTURES)
    def test_hk02_merge_equals_the_expected_file_and_keeps_user_hooks_and_comments(self):
        """HK-02, CA-26: result == settings-expected.json, user hook and JSONC comments kept; second pass byte for byte."""
        path = self.settings((HOOKS / "settings-input.json").read_text(encoding="utf-8"))
        result = hooks_install.apply(self.tmp, "py -3", with_post=True)
        self.assertEqual(result[".claude/settings.json"], fusion.MERGED)
        text = path.read_text(encoding="utf-8")
        expected = (HOOKS / "settings-expected.json").read_text(encoding="utf-8")
        self.assertEqual(json.loads(text.replace("// permissions of the team", "")
                                    .replace("// generated", "")), json.loads(expected.replace("// permissions of the team", "")
                                                                               .replace("// generated", "")))
        self.assertEqual(list(json.loads(expected.replace("// permissions of the team", "").replace("// generated", ""))["hooks"]),
                         ["PreToolUse", "PostToolUse"])
        self.assertIn("// permissions of the team", text)
        self.assertIn("echo user-hook", text)
        again = hooks_install.apply(self.tmp, "py -3", with_post=True)
        self.assertEqual(again[".claude/settings.json"], fusion.IDENTICAL)
        self.assertEqual(path.read_text(encoding="utf-8"), text)

    def test_hk02_post_edit_only_when_a_linter_is_configured(self):
        """HK-02, HL-01: the PostToolUse entry exists only with `hooks.lint` in harness.json."""
        hooks_install.apply(self.tmp, "python")
        self.assertNotIn("PostToolUse", json.loads(self.settings().read_text(encoding="utf-8"))["hooks"])
        phase4.stamp(self.tmp, hooks={"lint": [{"glob": "**/*.py", "argv": ["ruff", "check", "{file}"], "timeout_s": 20}]})
        result = hooks_install.apply(self.tmp, "python")
        self.assertEqual(result["entries"]["post-edit"], fusion.CREATED)
        self.assertIn("PostToolUse", json.loads(self.settings().read_text(encoding="utf-8"))["hooks"])

    def test_hk02_a_harness_entry_edited_by_the_user_is_kept(self):
        """HK-02, CA-26: a different entry of the harness is `personnalisé-conservé`, never rewritten."""
        hooks_install.apply(self.tmp, "python")
        path = self.settings()
        data = json.loads(path.read_text(encoding="utf-8"))
        data["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] = 99
        path.write_text(json.dumps(data), encoding="utf-8")
        before = path.read_bytes()
        result = hooks_install.apply(self.tmp, "python")
        self.assertEqual(result["entries"]["pre-edit"], fusion.KEPT)
        self.assertEqual(path.read_bytes(), before)

    def test_hk02_the_interpreter_change_regenerates_nothing_by_itself(self):
        """HK-06: a new interpreter is a different entry: kept as customized, reported (the upgrade decides)."""
        hooks_install.apply(self.tmp, "python")
        result = hooks_install.apply(self.tmp, "py -3")
        self.assertEqual(result["entries"]["pre-bash"], fusion.KEPT)

    def test_hk02_cli_with_a_lint_file(self):
        """HK-02, HL-01: `hooks install --lint-file` writes hooks.lint (consumed file) then merges the three entries."""
        src = helpers.write_output(self.tmp, "lint.json", json.dumps([{"glob": "**/*.py", "argv": ["ruff", "check", "{file}"],
                                                                      "timeout_s": 20}]))
        res = helpers.harness(["hooks", "install", "--root", str(self.tmp), "--py", "py -3", "--lint-file", src], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)["entries"]["post-edit"], fusion.CREATED)
        self.assertFalse((self.tmp / src).exists())
        stamp = json.loads((self.tmp / ".claude" / "harness.json").read_text(encoding="utf-8"))
        self.assertEqual(stamp["hooks"]["lint"][0]["argv"], ["ruff", "check", "{file}"])
        bad = helpers.write_output(self.tmp, "lint.json", json.dumps([{"glob": "*.py", "argv": ["ruff"]}]))
        self.assertEqual(helpers.harness(["hooks", "install", "--root", str(self.tmp), "--py", "py", "--lint-file", bad],
                                         self.tmp).returncode, 2)

    def test_hk01_the_hook_script_is_part_of_the_core_copy(self):
        """HK-01: hooks/hook.py is copied under .claude/harness/hooks/ by copy-core."""
        res = helpers.harness(["sf", "copy-core", "--root", str(self.tmp)], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((self.tmp / ".claude" / "harness" / "hooks" / "hook.py").is_file())


@unittest.skipUnless(find_bash(), "no working bash")
class CommandTest(helpers.TempDirCase):
    def run_command(self, name, payload, project, py):
        command = hooks_install.command_for(py, name)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
        return subprocess.run([find_bash(), "-c", command], input=json.dumps(payload), capture_output=True, text=True,
                              env=env, timeout=60)

    def test_hk03_never_exit_2_by_accident(self):
        """HK-03, CA-27: no script in the project, or an interpreter that does not exist -> exit code other than 2."""
        payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}, "session_id": "s"}
        empty = self.tmp / "empty"
        empty.mkdir()
        for name in hooks_install_names():
            res = self.run_command(name, payload, empty, "python")
            self.assertNotEqual(res.returncode, 2, name)
            res = self.run_command(name, payload, empty, "definitely-not-an-interpreter")
            self.assertNotEqual(res.returncode, 2, name)

    def test_hk03_a_wanted_blocking_still_exits_2(self):
        """HK-03: the exit code 2 of the hook is kept for a blocked command."""
        project = self.tmp / "p"
        (project / ".claude" / "harness").mkdir(parents=True)
        for item in ("hooks", "hcore"):
            src = helpers.CORE / item
            dest = project / ".claude" / "harness" / item
            import shutil
            shutil.copytree(str(src), str(dest), ignore=shutil.ignore_patterns("__pycache__"))
        payload = {"tool_name": "Bash", "tool_input": {"command": "git push --force"}, "session_id": "s"}
        res = self.run_command("pre-bash", payload, project, '"%s"' % sys.executable.replace("\\", "/"))
        self.assertEqual(res.returncode, 2, res.stderr)


def hooks_install_names():
    return [name for _event, _matcher, name, _timeout in hooks_install.SPECS]


if __name__ == "__main__":
    unittest.main()
