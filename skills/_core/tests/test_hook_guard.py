# Permanent destructive-command guard: HG-01 to HG-05 (and the hook pre-bash around it).

import json
import unittest

import helpers
import phase4
from hcore import guard, runs, scope

TABLE = helpers.FIXTURES / "bash-guard" / "commands.json"


def rows():
    return json.loads(TABLE.read_text(encoding="utf-8"))


@unittest.skipUnless(TABLE.is_file(), helpers.SKIP_FIXTURES)
class TableTest(helpers.TempDirCase):
    def test_hg02_hg03_every_command_of_the_table(self):
        """HG-02, HG-03, CA-28: at least 60 commands; deny gives the category, allow gives nothing."""
        table = rows()
        self.assertGreaterEqual(len(table), 60)
        check = scope.deletable_factory(self.tmp, None)
        wrong = []
        for row in table:
            hit = guard.analyze(row["command"], powershell=row["tool"] == "PowerShell", deletable=check)
            if row["expect"] == "deny":
                if hit is None or hit.name != row["category"]:
                    wrong.append((row["command"], row["category"], hit and hit.name))
            elif hit is not None:
                wrong.append((row["command"], "allow", hit.name))
        self.assertEqual(wrong, [])

    def test_hg02_the_scratch_folder_is_deletable_and_nothing_else_is_new(self):
        """HG-02: everything under <root>/.harness/tmp/ may be deleted; other temp folders and outside paths stay blocked."""
        check = scope.deletable_factory(self.tmp, None)
        for command in ("rm -rf .harness/tmp/x", "rm .harness/tmp/a.py", "rm -r .harness/tmp", "rm -rf ./.harness/tmp/a/b"):
            self.assertIsNone(guard.analyze(command, deletable=check), command)
        for command in ("rm C:/tmp/a.py", "rm /tmp/a.py", "rm -rf ..", "rm ../other/.harness/tmp/a",
                        "rm -rf .harness/tmp/../..", "rm sub/.harness/tmp/a", "rm .harness/tmpx/a", "rm -rf .harness"):
            hit = guard.analyze(command, deletable=check)
            self.assertIsNotNone(hit, command)
            self.assertEqual(hit.name, "file-delete", command)

    def test_hg02_globs_pass_only_under_the_scratch_folder(self):
        """HG-02: a glob whose literal prefix is inside <root>/.harness/tmp/ is deletable; any other glob stays blocked."""
        check = scope.deletable_factory(self.tmp, None)
        for command in ("rm -rf .harness/tmp/*", "rm .harness/tmp/*.py", "rm -f ./.harness/tmp/sub/a?.txt",
                        "rm %s/.harness/tmp/*" % self.tmp.as_posix()):
            self.assertIsNone(guard.analyze(command, deletable=check), command)
        self.assertIsNone(guard.analyze("Remove-Item .harness/tmp/* -Recurse -Force", powershell=True, deletable=check))
        for command in ("rm -rf *", "rm src/*.py", "rm .harness/*", "rm .harness/tmp*", "rm .harness/tmp/../*",
                        "rm .harness/tmp/.*", "rm .harness/tmp/..*", "rm .harness/tmp/[.][.]", "rm .harness/tmp/$X/*",
                        "rm .harness/tmp/{a,b}*", "rm dist/*", "rm *.harness/tmp/x", "rm .harness/tmp/x/../../*"):
            hit = guard.analyze(command, deletable=check)
            self.assertIsNotNone(hit, command)
            self.assertEqual(hit.name, "file-delete", command)

    def test_hg03_a_heredoc_body_is_data_only_for_a_quoted_plain_delimiter_and_a_reader(self):
        """HG-03: strict whitelist; the body is data only for `cat`/`tee`/`py`/`python`/`git commit -F -` with 'WORD'."""
        check = scope.deletable_factory(self.tmp, None)
        body = "git push --force origin main\nrm -rf /\n"
        for opener, word in (("cat <<'EOF'", "EOF"), ('cat <<"EOF"', "EOF"), ("cat <<-'EOF'", "EOF"),
                             ("cat > out.txt <<'EOF'", "EOF"), ("tee out.txt <<'EOF'", "EOF"),
                             ("py -3 - <<'PY'", "PY"), ("python3 - <<'PY'", "PY"), ("python <<'PY'", "PY"),
                             ("FOO=1 py - <<'PY'", "PY"), ("git commit -F - <<'EOF'", "EOF"),
                             ("git commit --file=- <<'EOF'", "EOF"), ("git commit -F- <<'EOF'", "EOF"),
                             ("cd x && cat <<'EOF'", "EOF")):
            self.assertIsNone(guard.analyze("%s\n%s%s\n" % (opener, body, word), deletable=check), opener)
        self.assertIsNone(guard.analyze("cat <<-'EOF'\n\t%s\tEOF\n" % body.replace("\n", "\n\t"), deletable=check))
        self.assertIsNone(guard.analyze("cat <<'EOF'\r\n%sEOF\r\n" % body.replace("\n", "\r\n"), deletable=check))
        for opener in ("bash <<'EOF'", "sh <<EOF", "cat <<'EOF' | sh", "cat <<EOF | bash", "sudo bash <<EOF",
                       "cat <<EOF", "cat <<-EOF", 'cat <<"EOF" | tee x', "cat <<\\EOF", "cat <<'EOF' <<'TWO'",
                       "git commit -m x <<'EOF'", "echo hi # <<'EOF'", "echo hi # <<EOF", "#<<EOF", "echo # note <<EOF",
                       "sudo -u root bash <<EOF", "cat <<EOF | sudo -u root sh", "timeout 5 bash <<EOF", "bash<<EOF",
                       "cat <<EOF | (sh)", "cat <<EOF | { sh; }", "cat <<EOF | ssh host sh", "bash -s -- -abc <<EOF",
                       "source /dev/stdin <<EOF", ". /dev/stdin <<EOF", "source /dev/stdin <<'EOF'",
                       "cat <<'EOF' > >(sh)", "cat <<'EOF' >(sh)", "tee >(bash) <<'EOF'", "cat <(true) <<'EOF'"):
            self.assertIsNotNone(guard.analyze("%s\n%sEOF\n" % (opener, body), deletable=check), opener)
        # an escaped or odd delimiter: the real terminator is found, what follows it is analysed
        self.assertIsNotNone(guard.analyze("cat <<E\\OF\nx\nEOF\nrm -rf src\n", deletable=check))
        self.assertIsNotNone(guard.analyze("cat <<E\\OF\n'\nEOF\nrm -rf src\n", deletable=check))
        # the opening line and what follows the terminator are still analysed
        self.assertIsNotNone(guard.analyze("cat <<'EOF' > x; git push -f\nhello\nEOF\n", deletable=check))
        self.assertIsNotNone(guard.analyze("cat <<'EOF'\nhello\nEOF\ngit push -f\n", deletable=check))
        self.assertIsNotNone(guard.analyze("cat <<EOF; rm -rf src\nhello\nEOF\n", deletable=check))
        self.assertIsNone(guard.analyze("echo $((1<<2))\ngit status\n", deletable=check))
        self.assertIsNotNone(guard.analyze("echo $((1<<2))\ngit push -f\n", deletable=check))

    def test_hg03_an_unquoted_heredoc_body_is_analysed(self):
        """HG-03: `$( )` and backticks run in an unquoted heredoc body; the body is analysed as commands."""
        check = scope.deletable_factory(self.tmp, None)
        for opener in ("cat <<EOF", "cat <<-EOF"):
            self.assertIsNotNone(guard.analyze("%s\nhi $(git push -f)\nEOF\n" % opener, deletable=check), opener)
            self.assertIsNotNone(guard.analyze("%s\nhi `git push -f` there\nEOF\n" % opener, deletable=check), opener)
        self.assertIsNotNone(guard.analyze("cat <<EOF\n$(rm -rf /)\nEOF\n", deletable=check))
        for opener in ("cat <<'EOF'", 'cat <<"EOF"'):
            self.assertIsNone(guard.analyze("%s\nhi $(git push -f) `rm -rf /`\nEOF\n" % opener, deletable=check), opener)
        self.assertIsNotNone(guard.analyze("cat <<EOF\ndon't $(rm -rf /)\nEOF\n", deletable=check))
        self.assertIsNotNone(guard.analyze("bash <<EOF\nrm -rf /\nEOF\n", deletable=check))

    def test_hg03_here_strings_fed_to_a_shell_or_source_are_commands(self):
        """HG-03: `bash <<< 'cmd'` and `source <<< 'cmd'` run the string; `cat <<< 'cmd'` does not."""
        check = scope.deletable_factory(self.tmp, None)
        for command in ("bash <<< 'rm -rf x'", "sh <<<'git push -f'", 'bash -s <<< "rm -rf x"', "source <<< 'rm -rf x'"):
            self.assertIsNotNone(guard.analyze(command, deletable=check), command)
        for command in ("cat <<< 'rm -rf x'", "bash <<< 'echo hi'", "read x <<< 'git push -f'"):
            self.assertIsNone(guard.analyze(command, deletable=check), command)

    def test_hg03_the_real_hook_follows_the_whitelist(self):
        """HG-03: through `hook.py pre-bash`, bypasses exit 2 and plain data heredocs exit 0."""
        blocked = ("echo hi # <<EOF\nrm -rf src\nEOF\n", "cat <<E\\OF\nx\nEOF\nrm -rf src\n",
                   "sudo -u root bash <<EOF\nrm -rf src\nEOF\n", "bash<<EOF\nrm -rf src\nEOF\n",
                   "bash <<< 'rm -rf src'", "cat <<EOF\n$(rm -rf /)\nEOF\n", "cat <<'EOF' | sh\nrm -rf src\nEOF\n",
                   "rm -rf .harness/tmp/../src")
        for command in blocked:
            res = phase4.hook("pre-bash", {"tool_name": "Bash", "tool_input": {"command": command}, "session_id": "s1"}, self.tmp)
            self.assertEqual(res.returncode, 2, command)
        passed = ("cat <<'EOF'\nrm -rf /\nEOF\n", "py -3 - <<'EOF'\nprint('rm -rf x')\nEOF\n",
                  "git commit -F - <<'EOF'\nmention rm -rf\nEOF\n", "rm -rf .harness/tmp/x", "rm .harness/tmp/*.py")
        for command in passed:
            res = phase4.hook("pre-bash", {"tool_name": "Bash", "tool_input": {"command": command}, "session_id": "s1"}, self.tmp)
            self.assertEqual(res.returncode, 0, command)

    def test_hg02_the_five_categories_and_the_compound_forms_are_covered(self):
        """HG-02, HG-03: the table holds the five categories, $( ), bash -c, git -C, PowerShell and the allowed deletions."""
        table = rows()
        self.assertEqual({r["category"] for r in table if r["expect"] == "deny"}, set(guard.CATEGORIES.values()))
        text = " ".join(r["command"] for r in table)
        for needle in ("$(", "bash -c", "git -C", "`", "&&", "||", "xargs"):
            self.assertIn(needle, text)
        self.assertTrue(any(r["tool"] == "PowerShell" for r in table))
        self.assertTrue(any(r["expect"] == "allow" and r["command"].startswith("rm ") for r in table))

    def test_hg03_cmd_c_and_invoke_expression_are_analysed_like_bash_c(self):
        """HG-03: `cmd /c` and `iex` / `Invoke-Expression` carry a command that is analysed."""
        for command, ps in (('cmd /c "git push -f"', False), ("cmd /c git push --force origin main", False),
                            ('iex "git push -f"', True), ("Invoke-Expression 'git push -f'", True),
                            ("cmd.exe /C \"git reset --hard\"", False)):
            self.assertIsNotNone(guard.analyze(command, powershell=ps), command)
        for command, ps in (('cmd /c "git status"', False), ('iex "git status"', True), ("cmd /c echo hi", False)):
            self.assertIsNone(guard.analyze(command, powershell=ps), command)

    def test_hg04_the_message(self):
        """HG-04: the message names the category and the fragment and tells the user to run it themselves."""
        hit = guard.analyze("git push --force origin main")
        self.assertEqual(hit.category, 1)
        message = hit.message()
        self.assertTrue(message.startswith("Blocked by harness guard: force-push (git push --force origin main)."))
        self.assertIn("run it yourself in a terminal if intended", message)

    def test_hg03_an_unbalanced_command_cannot_be_analysed(self):
        """HG-03: Unanalyzable (the hook then lets it pass and reports, HK-04)."""
        with self.assertRaises(guard.Unanalyzable):
            guard.analyze("echo 'unterminated")

    def test_hg02_the_pipeline_is_split_on_every_separator(self):
        """HG-03: ; && || | & and newlines."""
        self.assertEqual(guard.split_commands("a; b && c || d | e & f\ng"), ["a", "b", "c", "d", "e", "f", "g"])
        self.assertEqual(guard.split_commands('echo "a; b" && ls'), ['echo "a; b"', "ls"])


class ContextDeletionTest(helpers.TempDirCase):
    """HG-02 (5): a deletion passes when every target is generated."""

    def setUp(self):
        super().setUp()
        self.work, _ = phase4.project(self.tmp, {"SPEC-a.md": phase4.spec_text(
            "APPROUVEE", header=["Périmètre fichiers : src/**"])})
        (self.work / "src").mkdir()
        (self.work / "src" / "a.py").write_text("x", encoding="utf-8")
        (self.work / "docs").mkdir()
        (self.work / "docs" / "a.md").write_text("x", encoding="utf-8")
        helpers.git(self.work, "add", "-A")
        helpers.git(self.work, "commit", "-q", "-m", "files")
        (self.work / "old-untracked.txt").write_text("before the cycle", encoding="utf-8")
        self.run = runs.create(self.work, "factory-run", {"status": "running", "spec": "specs/SPEC-a.md",
                                                          "untracked_at_start": scope.untracked_snapshot(self.work)})
        (self.work / "gen.txt").write_text("created in the cycle", encoding="utf-8")
        self.ctx = {"skill": "factory-run", "run": self.run.relative_to(self.work).as_posix(), "spec": "specs/SPEC-a.md", "phase": "build"}

    def deny(self, command):
        return guard.analyze(command, deletable=scope.deletable_factory(self.work, self.ctx))

    def test_hg02_a_file_created_during_the_cycle_may_be_deleted(self):
        """HG-02 (5): untracked and absent from the snapshot of `start` -> allowed."""
        self.assertIsNone(self.deny("rm gen.txt"))

    def test_hg02_a_file_that_existed_before_or_is_tracked_may_not(self):
        """HG-02 (5): the snapshot protects the user's untracked files, git protects the tracked ones."""
        self.assertEqual(self.deny("rm old-untracked.txt").category, 5)
        self.assertEqual(self.deny("rm README.md").category, 5)

    def test_hg02_the_perimeter_of_the_active_spec_allows_the_deletion(self):
        """HG-02 (5): a tracked file inside `Périmètre fichiers` may be deleted, one outside may not."""
        self.assertIsNone(self.deny("rm src/a.py"))
        self.assertEqual(self.deny("rm docs/a.md").category, 5)
        self.assertEqual(self.deny("rm src/a.py docs/a.md").category, 5)          # EVERY target must be generated

    def test_hg02_an_unresolvable_target_is_blocked(self):
        """HG-02 (5): a variable or a glob is never resolved."""
        self.assertEqual(self.deny("rm $TARGET").category, 5)
        self.assertEqual(self.deny("rm src/*.py").category, 5)


class HookTest(helpers.TempDirCase):
    def payload(self, command, tool="Bash", session="s1"):
        return {"tool_name": tool, "tool_input": {"command": command}, "session_id": session}

    def test_hg01_the_guard_is_permanent_with_or_without_a_marker(self):
        """HG-01, CA-29: `git push --force` -> exit 2 with no marker, and with an active marker; benign commands pass."""
        res = phase4.hook("pre-bash", self.payload("git push --force"), self.tmp)
        self.assertEqual(res.returncode, 2, res.stderr)
        self.assertIn("Blocked by harness guard: force-push", res.stderr)
        self.assertEqual(phase4.hook("pre-bash", self.payload("git status"), self.tmp).returncode, 0)
        self.assertEqual(phase4.hook("pre-bash", self.payload("git push --force", "PowerShell"), self.tmp).returncode, 2)

    def test_hg01_the_guard_ignores_the_policy(self):
        """HG-01: the autonomy stamp changes nothing."""
        phase4.stamp(self.tmp, autonomy="auto")
        self.assertEqual(phase4.hook("pre-bash", self.payload("git branch -D x"), self.tmp).returncode, 2)

    def test_hg05_with_an_active_cycle_the_block_is_also_a_stop(self):
        """HG-05, CA-29: a blocked command writes a STOP of kind destructive and stops the run (SX-06)."""
        run = runs.create(self.tmp, "factory-run", {"status": "running"})
        scope.activate(self.tmp, "factory-run", run.relative_to(self.tmp).as_posix(), "s1")
        res = phase4.hook("pre-bash", self.payload("git reset --hard"), self.tmp)
        self.assertEqual(res.returncode, 2)
        stop = sorted((self.tmp / ".harness" / "runs").glob("STOP-*.md"))
        self.assertEqual(len(stop), 1)
        self.assertIn("— destructive", stop[0].read_text(encoding="utf-8"))
        self.assertEqual(runs.load_state(run)["stopped"]["kind"], "destructive")
        helpers_res = helpers.harness(["factory-run", "record", "--run", str(run), "--agent", "factory-builder"], self.tmp)
        self.assertEqual(helpers_res.returncode, 1)

    def test_hg05_without_a_cycle_it_only_blocks(self):
        """HG-05: no active context -> no STOP file."""
        phase4.hook("pre-bash", self.payload("git push -f"), self.tmp)
        self.assertEqual(list((self.tmp / ".harness" / "runs").glob("STOP-*.md")) if (self.tmp / ".harness").exists() else [], [])

    def test_hg03_a_command_that_cannot_be_analysed_passes_and_is_reported(self):
        """HG-03, HK-04: an unbalanced quote -> exit 0 and a systemMessage."""
        res = phase4.hook("pre-bash", self.payload("echo 'oops"), self.tmp)
        self.assertEqual(res.returncode, 0)
        self.assertIn("systemMessage", res.stdout)


if __name__ == "__main__":
    unittest.main()
