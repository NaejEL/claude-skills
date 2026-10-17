# Module hcore.journal: journal schema and file name (CA9, CA10).

import json
import unittest
from datetime import datetime

import helpers
from hcore import journal, runs

GOOD = {"agent": "factory-verifier", "model": "inherit", "duration_ms": 1200, "iteration": 1,
        "verdict": "APPROVED", "findings": {"produced": 0, "validated": 0, "rejected": 0}, "tokens": None}


class NameTest(unittest.TestCase):
    def test_ca10_name_pattern(self):
        name = journal.journal_name("ship-pr", datetime(2026, 10, 16, 9, 5, 7))
        self.assertEqual(name, "ship-pr-20261016-090507.jsonl")
        self.assertRegex(name, journal.NAME_RE)

    def test_unknown_skill_refused(self):
        with self.assertRaises(ValueError):
            journal.journal_name("ai-lab", datetime.now())


class ValidateTest(helpers.TempDirCase):
    def write(self, lines):
        path = self.tmp / "factory-run-20261016-120000.jsonl"
        path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        return path

    def test_ca9_valid_journal(self):
        path = self.write([json.dumps(GOOD), json.dumps(dict(GOOD, tokens=4200))])
        self.assertEqual(journal.validate_file(path), [])

    def test_ca9_line_without_verdict_rejected(self):
        bad = dict(GOOD)
        del bad["verdict"]
        errors = journal.validate_file(self.write([json.dumps(GOOD), json.dumps(bad)]))
        self.assertTrue(any("verdict" in e for e in errors))

    def test_ca9_non_json_line_rejected(self):
        errors = journal.validate_file(self.write([json.dumps(GOOD), "not json"]))
        self.assertTrue(any("invalid JSON" in e for e in errors))

    def test_ca9_field_types(self):
        cases = [dict(GOOD, findings={"produced": -1, "validated": 0, "rejected": 0}),
                 dict(GOOD, findings={"produced": 1, "validated": 0}),
                 dict(GOOD, tokens="12"), dict(GOOD, duration_ms=1.5), dict(GOOD, iteration=True)]
        for case in cases:
            self.assertTrue(journal.validate_record(case), case)

    def test_ca9_cli_exit_codes(self):
        good = self.write([json.dumps(GOOD)])
        self.assertEqual(helpers.harness(["journal", "validate", str(good)], self.tmp).returncode, 0)
        bad = dict(GOOD)
        del bad["verdict"]
        path = self.write([json.dumps(bad)])
        self.assertNotEqual(helpers.harness(["journal", "validate", str(path)], self.tmp).returncode, 0)
        path = self.write(["{"])
        self.assertNotEqual(helpers.harness(["journal", "validate", str(path)], self.tmp).returncode, 0)

    def test_append_refuses_invalid_record(self):
        with self.assertRaises(ValueError):
            journal.append(self.tmp / "x.jsonl", {"agent": "a"})


class RunFilesTest(helpers.TempDirCase):
    def test_ca10_run_created_under_claude_runs(self):
        run = runs.create(self.tmp, "factory-run", {}, now=datetime(2026, 10, 16, 12, 0, 0))
        twin = runs.create(self.tmp, "factory-run", {}, now=datetime(2026, 10, 16, 12, 0, 0))
        self.assertEqual(run.parent, self.tmp / ".claude" / "runs")
        self.assertNotEqual(run, twin)
        for path in (run, twin):
            self.assertRegex(path.name, journal.NAME_RE)
        self.assertTrue(runs.state_path(run).exists())
        self.assertTrue(runs.registry_path(run).name.endswith(".registry.jsonl"))

    def test_sanitize_replaces_every_invalid_field_and_reports_it(self):
        """No invalid field blocks: conforming fallback value, every fallback reported."""
        bad = {"agent": "", "model": " ", "duration_ms": -1, "iteration": "two", "verdict": None,
               "findings": {"produced": -2, "validated": "x", "rejected": True}, "tokens": 1.5, "theme": "t"}
        fixed, warnings = journal.sanitize(bad)
        self.assertEqual(journal.validate_record(fixed), [])
        self.assertEqual((fixed["agent"], fixed["model"], fixed["verdict"]), (journal.FALLBACK_TEXT,) * 3)
        self.assertEqual((fixed["duration_ms"], fixed["tokens"], fixed["iteration"]), (None, None, 0))
        self.assertEqual(fixed["findings"], {"produced": 0, "validated": 0, "rejected": 0})
        self.assertEqual(fixed["theme"], "t")
        self.assertEqual(len(warnings), 9)
        self.assertEqual(journal.sanitize(GOOD), (GOOD, []))
        self.assertEqual(journal.sanitize(dict(GOOD, findings="x"))[0]["findings"],
                         {"produced": 0, "validated": 0, "rejected": 0})

    def test_cli_invalid_caller_fields_never_stop_the_skill(self):
        """Every field supplied by the caller (--model, --duration-ms, --tokens):
        an invalid value is logged as a fallback and reported, exit 0."""
        start = json.loads(helpers.harness(["factory-run", "start"], self.tmp).stdout)
        run = start["run"]
        cases = [("--model", ""), ("--model", " "), ("--duration-ms", "abc"), ("--duration-ms", "-3"),
                 ("--tokens", "lots"), ("--tokens", "-1"), ("--tokens", "1.5")]
        for option, value in cases:
            args = ["factory-run", "record", "--run", run, "--agent", "factory-planner",
                    "--model", "inherit", "--duration-ms", "10", option, value]
            res = helpers.harness(args, self.tmp)
            self.assertEqual(res.returncode, 0, "%s %r: %s" % (option, value, res.stderr))
            warnings = " ".join(json.loads(res.stdout)["journal_warnings"])
            self.assertIn(option.lstrip("-"), warnings, (option, value))
        lines = journal.read(self.tmp / run)
        self.assertEqual(len(lines), len(cases))
        self.assertEqual([x["model"] for x in lines[:2]], [journal.FALLBACK_TEXT] * 2)
        self.assertEqual([x["duration_ms"] for x in lines[2:4]], [None, None])
        self.assertEqual([x["tokens"] for x in lines[4:]], [None, None, None])
        self.assertEqual(journal.validate_file(self.tmp / run), [])

    def test_duration_from_core_timestamps(self):
        state = {}
        runs.mark_begin(state, "x", clock=lambda: 10.0)
        self.assertEqual(runs.duration_ms(state, "x", None, clock=lambda: 12.5), 2500)
        with self.assertRaises(ValueError):
            runs.duration_ms(state, "x", None)
        self.assertEqual(runs.duration_ms(state, "y", 42), 42)


if __name__ == "__main__":
    unittest.main()
