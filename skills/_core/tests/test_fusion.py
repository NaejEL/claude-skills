# Module hcore.fusion: software-factory merges (SF-01 to SF-04, CA12),
# git exclusion of the journal by the generated .gitignore (CA11), core copy (D1).

import json
import os
import shutil
import subprocess
import sys
import unittest

import helpers
from hcore import CORE_VERSION, fusion, journal, jsonc, registry, runs


def ordered(path):
    return json.dumps(json.loads(path.read_text(encoding="utf-8")))


class DenyRulesTest(unittest.TestCase):
    def test_sf01_stack_correspondence(self):
        """SF-01."""
        self.assertEqual(fusion.deny_rules([]), ["Read(./factory-logs/**)", "Read(./.git/objects/**)"])
        self.assertEqual(fusion.deny_rules(["node"])[:2], ["Read(./node_modules/**)", "Read(./dist/**)"])
        self.assertIn("Read(./**/obj/**)", fusion.deny_rules(["dotnet"]))
        self.assertIn("Read(./.pytest_cache/**)", fusion.deny_rules(["python"]))
        self.assertIn("Read(./build/**)", fusion.deny_rules(["cpp"]))
        self.assertIn("Read(./target/**)", fusion.deny_rules(["rust"]))
        self.assertNotIn("Read(./target/**)", fusion.deny_rules(["node"]))
        with self.assertRaises(fusion.FusionError):
            fusion.deny_rules(["cobol"])


@unittest.skipUnless(helpers.HAS_FIXTURES, helpers.SKIP_FIXTURES)
class FixtureMergeTest(helpers.TempDirCase):
    def prepare(self):
        src = helpers.FIXTURES / "merge-input"
        (self.tmp / ".claude").mkdir()
        (self.tmp / ".vscode").mkdir()
        shutil.copy(str(src / "settings.json"), str(self.tmp / ".claude" / "settings.json"))
        shutil.copy(str(src / "tasks.json"), str(self.tmp / ".vscode" / "tasks.json"))
        shutil.copy(str(src / "gitignore.txt"), str(self.tmp / ".gitignore"))

    def snapshot(self):
        return {p: (self.tmp / p).read_bytes() for p in (".claude/settings.json", ".vscode/tasks.json", ".gitignore")}

    def test_sf01_sf02_sf03_equal_expected_files(self):
        """SF-01 SF-02 SF-03."""
        self.prepare()
        states = fusion.apply(self.tmp, ["node"])
        expected = helpers.FIXTURES / "merge-expected"
        self.assertEqual(ordered(self.tmp / ".claude" / "settings.json"), ordered(expected / "settings.json"))
        self.assertEqual(ordered(self.tmp / ".vscode" / "tasks.json"), ordered(expected / "tasks.json"))
        self.assertEqual((self.tmp / ".gitignore").read_text(encoding="utf-8"),
                         (expected / "gitignore.txt").read_text(encoding="utf-8"))
        self.assertEqual(set(states.values()), {fusion.MERGED})

    def test_sf01_third_party_key_kept_and_deny_without_duplicate(self):
        """SF-01."""
        self.prepare()
        fusion.apply(self.tmp, ["node"])
        data = json.loads((self.tmp / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(data["model"], "sonnet")
        self.assertEqual(data["env"], {"TOY": "1"})
        self.assertEqual(data["permissions"]["allow"], ["Bash(npm test)"])
        deny = data["permissions"]["deny"]
        self.assertEqual(len(deny), len(set(deny)))
        self.assertEqual(deny.count("Read(./node_modules/**)"), 1)

    def test_sf02_existing_kept_factory_entries_once(self):
        """SF-02."""
        self.prepare()
        fusion.apply(self.tmp, ["node"])
        fusion.apply(self.tmp, ["node"])
        data = json.loads((self.tmp / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        labels = [t["label"] for t in data["tasks"]]
        self.assertIn("npm: test", labels)
        for label in ("Factory: CI run", "Factory: CI run (YOLO)", "Factory: nouvelle spec (session)"):
            self.assertEqual(labels.count(label), 1)
        ids = [i["id"] for i in data["inputs"]]
        self.assertEqual(ids.count("factorySpec"), 1)
        self.assertIn("target", ids)

    def test_sf03_gitignore_line_added_once(self):
        """SF-03."""
        self.prepare()
        fusion.apply(self.tmp, ["node"])
        fusion.apply(self.tmp, ["node"])
        lines = (self.tmp / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines.count("factory-logs/"), 1)
        self.assertEqual(lines.count(".claude/runs/"), 1)

    def test_sf04_second_application_byte_identical(self):
        """SF-04."""
        self.prepare()
        fusion.apply(self.tmp, ["node"])
        before = self.snapshot()
        states = fusion.apply(self.tmp, ["node"])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(set(states.values()), {fusion.IDENTICAL})

    def test_sf04_fresh_project_matches_reference_output(self):
        """SF-04."""
        states = fusion.apply(self.tmp, [])
        expected = helpers.FIXTURES / "merge-expected"
        self.assertEqual(ordered(self.tmp / ".claude" / "settings.json"), ordered(expected / "fresh-settings.json"))
        self.assertEqual(ordered(self.tmp / ".vscode" / "tasks.json"), ordered(expected / "fresh-tasks.json"))
        self.assertEqual((self.tmp / ".gitignore").read_text(encoding="utf-8"),
                         (expected / "fresh-gitignore.txt").read_text(encoding="utf-8"))
        self.assertEqual(set(states.values()), {fusion.CREATED})

    def test_sf01_invalid_json_not_overwritten(self):
        """SF-01."""
        (self.tmp / ".claude").mkdir()
        (self.tmp / ".claude" / "settings.json").write_text("{ broken", encoding="utf-8")
        with self.assertRaises(fusion.FusionError):
            fusion.apply(self.tmp, [])
        self.assertEqual((self.tmp / ".claude" / "settings.json").read_text(encoding="utf-8"), "{ broken")


VSCODE_DEFAULT_TASKS = (
    "{\n"
    "\t// See https://go.microsoft.com/fwlink/?LinkId=733558\n"
    "\t// for the documentation about the tasks.json format\n"
    "\t\"version\": \"2.0.0\",\n"
    "\t\"tasks\": [\n"
    "\t\t{\n"
    "\t\t\t\"label\": \"echo\", /* sample task */\n"
    "\t\t\t\"type\": \"shell\",\n"
    "\t\t\t\"command\": \"echo // not a comment\",\n"
    "\t\t},\n"
    "\t]\n"
    "}\n"
)


class TolerantReadTest(helpers.TempDirCase):
    """SF-01 / SF-02: VS Code JSONC and BOM from Windows tools, all or nothing."""

    def put(self, rel, text, newline="\n"):
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(text)
        return path

    def test_sf02_vscode_default_jsonc_merged_comments_kept(self):
        """SF-02."""
        path = self.put(".vscode/tasks.json", VSCODE_DEFAULT_TASKS)
        states = fusion.apply(self.tmp, [])
        self.assertEqual(states[".vscode/tasks.json"], fusion.MERGED)
        text = path.read_text(encoding="utf-8")
        for kept in ("// See https://go.microsoft.com", "/* sample task */", "echo // not a comment"):
            self.assertIn(kept, text)
        data = jsonc.loads(text).value
        self.assertEqual([t["label"] for t in data["tasks"]],
                         ["echo", "Factory: CI run", "Factory: CI run (YOLO)", "Factory: nouvelle spec (session)"])
        self.assertEqual([i["id"] for i in data["inputs"]], ["factorySpec"])
        self.assertIn('\n\t\t{\n\t\t\t"label": "Factory: CI run"', text)
        before = path.read_bytes()
        self.assertEqual(fusion.apply(self.tmp, [])[".vscode/tasks.json"], fusion.IDENTICAL)
        self.assertEqual(path.read_bytes(), before)

    def test_sf01_bom_and_crlf_preserved(self):
        """SF-01."""
        path = self.put(".claude/settings.json", '﻿{\r\n  "model": "sonnet"\r\n}\r\n', newline="")
        self.assertEqual(fusion.apply(self.tmp, ["rust"])[".claude/settings.json"], fusion.MERGED)
        raw = path.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        data = json.loads(raw.decode("utf-8-sig"))
        self.assertEqual(data["model"], "sonnet")
        self.assertIn("Read(./target/**)", data["permissions"]["deny"])
        self.assertEqual(fusion.apply(self.tmp, ["rust"])[".claude/settings.json"], fusion.IDENTICAL)
        self.assertEqual(path.read_bytes(), raw)

    def test_sf01_jsonc_settings_with_trailing_commas(self):
        """SF-01."""
        path = self.put(".claude/settings.json",
                        '{\n  // settings\n  "permissions": {\n    "deny": ["Read(./x/**)",],\n  },\n}\n')
        fusion.apply(self.tmp, [])
        text = path.read_text(encoding="utf-8")
        self.assertIn("// settings", text)
        deny = jsonc.loads(text).value["permissions"]["deny"]
        self.assertEqual(deny, ["Read(./x/**)", "Read(./factory-logs/**)", "Read(./.git/objects/**)"])

    def test_sf03_gitignore_crlf_kept(self):
        """SF-03."""
        path = self.put(".gitignore", "node_modules/\r\ndist/\r\n", newline="")
        fusion.apply(self.tmp, [])
        self.assertEqual(path.read_bytes(), b"node_modules/\r\ndist/\r\nfactory-logs/\r\n.claude/runs/\r\n")
        fusion.apply(self.tmp, [])
        self.assertEqual(path.read_bytes(), b"node_modules/\r\ndist/\r\nfactory-logs/\r\n.claude/runs/\r\n")

    def test_sf04_all_or_nothing_when_one_file_is_invalid(self):
        """SF-04: unreadable tasks.json -> neither settings.json nor .gitignore touched."""
        settings = self.put(".claude/settings.json", '{"model": "sonnet"}\n')
        self.put(".vscode/tasks.json", "{ broken")
        with self.assertRaises(fusion.FusionError):
            fusion.apply(self.tmp, ["node"])
        self.assertEqual(settings.read_text(encoding="utf-8"), '{"model": "sonnet"}\n')
        self.assertFalse((self.tmp / ".gitignore").exists())
        self.assertEqual(sorted(p.name for p in self.tmp.rglob("*") if p.is_file()), ["settings.json", "tasks.json"])

    def test_jsonc_parser_errors_and_strings(self):
        for bad in ("{ broken", '{"a": 1 /* ouvert', '{"a" 1}', "[1,, 2]", '{"a": 1} x'):
            with self.assertRaises(ValueError, msg=bad):
                jsonc.loads(bad)
        doc = jsonc.loads('{"u": "a/*b*/c//d", "e": "\\"x\\""}')
        self.assertEqual(doc.value, {"u": "a/*b*/c//d", "e": '"x"'})
        self.assertFalse(doc.loose)

    def test_sf04_non_utf8_file_named_and_all_or_nothing(self):
        """SF-04: an existing non-UTF-8 file (UTF-16 from a PowerShell tool) is
        refused by a message naming it with the expected encoding; nothing is written."""
        tasks = self.tmp / ".vscode" / "tasks.json"
        tasks.parent.mkdir(parents=True)
        tasks.write_bytes('{"version": "2.0.0"}\n'.encode("utf-16"))
        before = tasks.read_bytes()
        with self.assertRaises(fusion.FusionError) as ctx:
            fusion.apply(self.tmp, ["node"])
        self.assertIn("tasks.json", str(ctx.exception))
        self.assertIn("UTF-8", str(ctx.exception))
        self.assertEqual(tasks.read_bytes(), before)
        self.assertEqual([p.name for p in self.tmp.rglob("*") if p.is_file()], ["tasks.json"])
        res = helpers.harness(["sf", "apply", "--stacks", "node"], self.tmp)
        self.assertEqual(res.returncode, 2)
        self.assertIn("tasks.json", res.stderr)
        self.assertIn("UTF-8", res.stderr)
        self.assertNotIn("codec", res.stderr)
        gitignore = self.tmp / ".gitignore"
        gitignore.write_bytes("node_modules/\n".encode("utf-16"))
        tasks.unlink()
        with self.assertRaises(fusion.FusionError) as ctx:
            fusion.apply(self.tmp, [])
        self.assertIn(".gitignore", str(ctx.exception))
        agent = self.tmp / ".claude" / "agents" / "a.md"
        agent.parent.mkdir(parents=True)
        agent.write_bytes("prompt\n".encode("utf-16"))
        with self.assertRaises(fusion.FusionError) as ctx:
            fusion.install_file(agent, "prompt\n")
        self.assertIn("a.md", str(ctx.exception))

    def test_sf01_end_of_line_comment_stays_with_its_element(self):
        """SF-01: a // comment after the last item stays attached to that item;
        valid JSONC result and identical second application."""
        cases = [
            ('{\n  "permissions": {\n    "deny": [\n      "Read(./x)", // keep\n    ]\n  }\n}\n',
             '      "Read(./x)", // keep\n      "Read(./factory-logs/**)",\n'),
            ('{\n  "permissions": {\n    "deny": [\n      "Read(./x)" // keep\n    ]\n  }\n}\n',
             '      "Read(./x)", // keep\n      "Read(./factory-logs/**)",\n'),
            ('{\r\n  "permissions": {\r\n    "deny": [\r\n      "Read(./x)" /* a */, // keep\r\n    ]\r\n  }\r\n}\r\n',
             '      "Read(./x)" /* a */, // keep\r\n      "Read(./factory-logs/**)",\r\n'),
        ]
        for raw, expected in cases:
            path = self.put(".claude/settings.json", raw, newline="")
            fusion.apply(self.tmp, [])
            text = path.read_bytes().decode("utf-8")
            self.assertIn(expected, text, text)
            self.assertEqual(text.count("// keep"), 1)
            self.assertEqual(jsonc.loads(text).value["permissions"]["deny"],
                             ["Read(./x)", "Read(./factory-logs/**)", "Read(./.git/objects/**)"])
            before = path.read_bytes()
            self.assertEqual(fusion.apply(self.tmp, [])[".claude/settings.json"], fusion.IDENTICAL)
            self.assertEqual(path.read_bytes(), before)
        path = self.put(".claude/settings.json", '{\n  "model": "sonnet" // choice\n}\n')
        fusion.apply(self.tmp, [])
        text = path.read_text(encoding="utf-8")
        self.assertIn('  "model": "sonnet", // choice\n  "permissions": {', text)
        self.assertEqual(jsonc.loads(text).value["model"], "sonnet")


class InstallFileTest(helpers.TempDirCase):
    def test_sf04_states(self):
        """SF-04."""
        dest = self.tmp / ".claude" / "agents" / "factory-builder.md"
        self.assertEqual(fusion.install_file(dest, "prompt\n"), fusion.CREATED)
        self.assertEqual(fusion.install_file(dest, "prompt\n"), fusion.IDENTICAL)
        dest.write_text("customized prompt\n", encoding="utf-8")
        self.assertEqual(fusion.install_file(dest, "prompt\n"), fusion.KEPT)
        self.assertEqual(dest.read_text(encoding="utf-8"), "customized prompt\n")

    def test_d1_copy_core_with_version_and_no_bytecode(self):
        result = fusion.copy_core(helpers.CORE, self.tmp)
        states = result["files"]
        self.assertTrue(result["copied"])
        self.assertEqual(set(states.values()), {fusion.CREATED})
        harness_dir = self.tmp / ".claude" / "harness"
        self.assertTrue((harness_dir / "harness.py").is_file())
        init = (harness_dir / "hcore" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn('CORE_VERSION = "%s"' % CORE_VERSION, init)
        self.assertFalse(any("__pycache__" in k or k.endswith(".pyc") for k in states))
        self.assertEqual(set(fusion.copy_core(helpers.CORE, self.tmp)["files"].values()), {fusion.IDENTICAL})
        res = helpers.harness(["version"], self.tmp)
        self.assertEqual(res.returncode, 0)
        copied = subprocess.run([helpers.sys.executable, "-B", str(harness_dir / "harness.py"), "version"],
                                capture_output=True, text=True)
        self.assertEqual(json.loads(copied.stdout)["core_version"], CORE_VERSION)

    def test_d1_copied_core_run_without_B_leaves_no_bytecode(self):
        """D1: the versioned copy of the core, called without -B or PYTHONDONTWRITEBYTECODE
        (factory-run template), creates no __pycache__ in the repository."""
        helpers.init_repo(self.tmp)
        fusion.copy_core(helpers.CORE, self.tmp)
        helpers.git(self.tmp, "add", "-A")
        helpers.git(self.tmp, "commit", "-q", "-m", "core")
        env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
        res = subprocess.run([sys.executable, str(self.tmp / ".claude" / "harness" / "harness.py"), "version"],
                             cwd=str(self.tmp), capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(helpers.git(self.tmp, "status", "--porcelain", "--untracked-files=all"), "")
        self.assertEqual(list(self.tmp.rglob("__pycache__")), [])

    def test_d1_copy_core_never_mixes_two_versions(self):
        """SF-04 / D1: a different existing core is neither overwritten nor completed."""
        fusion.copy_core(helpers.CORE, self.tmp)
        harness_dir = self.tmp / ".claude" / "harness"
        init = harness_dir / "hcore" / "__init__.py"
        old = init.read_text(encoding="utf-8").replace(CORE_VERSION, "0.9.0")
        init.write_text(old, encoding="utf-8")
        (harness_dir / "hcore" / "shippr.py").unlink()   # file that appeared in the new version
        result = fusion.copy_core(helpers.CORE, self.tmp)
        self.assertFalse(result["copied"])
        self.assertEqual(result["blocked_by"], [".claude/harness/hcore/__init__.py"])
        self.assertEqual(result["not_copied"], [".claude/harness/hcore/shippr.py"])
        self.assertEqual(result["files"][".claude/harness/hcore/__init__.py"], fusion.KEPT)
        self.assertFalse((harness_dir / "hcore" / "shippr.py").exists())
        self.assertEqual(init.read_text(encoding="utf-8"), old)


class CliTest(helpers.TempDirCase):
    def test_sf04_cli_apply_install_copy_core(self):
        """SF-01 SF-04: the CLI called by software-factory."""
        res = helpers.harness(["sf", "apply", "--root", ".", "--stacks", "node,python"], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)[".claude/settings.json"], fusion.CREATED)
        deny = json.loads((self.tmp / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]["deny"]
        self.assertIn("Read(./.venv/**)", deny)
        args = ["sf", "install", "--root", ".", "--dest", "ci/factory.sh", "--source", "-"]
        self.assertEqual(json.loads(helpers.harness(args, self.tmp, stdin="#!/usr/bin/env bash\n").stdout)["ci/factory.sh"],
                         fusion.CREATED)
        self.assertEqual(json.loads(helpers.harness(args, self.tmp, stdin="other\n").stdout)["ci/factory.sh"],
                         fusion.KEPT)
        res = helpers.harness(["sf", "copy-core", "--root", "."], self.tmp)
        self.assertEqual(json.loads(res.stdout)["core_version"], CORE_VERSION)
        bad = helpers.harness(["sf", "apply", "--stacks", "cobol"], self.tmp)
        self.assertEqual(bad.returncode, 2)


class GitignoreExcludesRunsTest(helpers.TempDirCase):
    def test_ca11_generated_gitignore_hides_runs(self):
        helpers.init_repo(self.tmp)
        fusion.apply(self.tmp, [])
        run = runs.create(self.tmp, "factory-run", {})
        journal.append(run, journal.make_record("factory-builder", "inherit", 1, 1, "DONE"))
        registry.Registry(runs.registry_path(run)).add(helpers.finding(), "REJECTED")
        status = helpers.git(self.tmp, "status", "--porcelain", "--untracked-files=all")
        self.assertNotIn(".claude/runs", status)
        self.assertIn(".gitignore", status)


if __name__ == "__main__":
    unittest.main()
