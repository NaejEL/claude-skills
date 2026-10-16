# Rejeux scriptes (D4) : la sequence d'appels au noyau prescrite par chaque
# SKILL.md, jouee par la CLI dans un dossier temporaire.
#
# - CA15 : factory-run (FR-01 a FR-04) : Builder, Verifier CHANGES_REQUESTED,
#   Builder, Verifier mort, Verifier APPROVED.
# - CA16 : ship-pr (SP-01 a SP-19) avec un gh simule et un depot git jetable :
#   themes, validateur, sortie par epuisement, REJECTED resoumis en ronde 2.

import json
import os
import re
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

import helpers
from hcore import journal

APPROVED_SPEC = "# SPEC\n\nStatut : APPROUVEE\n\nCorps.\n"


def check_ok(test, res):
    test.assertEqual(res.returncode, 0, "stdout=%s\nstderr=%s" % (res.stdout, res.stderr))
    return json.loads(res.stdout) if res.stdout.strip().startswith("{") else res.stdout


class FactoryRunReplayTest(helpers.TempDirCase):
    def test_ca15_factory_run_sequence(self):
        """FR-01 FR-02 FR-03 FR-04 : rejeu complet et journal conforme."""
        project = self.tmp / "toy"
        if helpers.HAS_FIXTURES:
            shutil.copytree(str(helpers.FIXTURES / "toy-project"), str(project))
            spec = "specs/SPEC-somme.md"
        else:
            (project / "specs").mkdir(parents=True)
            (project / "specs" / "SPEC-x.md").write_text(APPROVED_SPEC, encoding="utf-8")
            spec = "specs/SPEC-x.md"
        h = lambda *a, **kw: helpers.harness(list(a), project, **kw)  # noqa: E731

        # $ARGUMENTS est ecrit dans un fichier par l'outil Write, jamais passe au shell.
        args_file = project / ".claude" / "runs" / "factory-run-arguments.txt"
        args_file.parent.mkdir(parents=True)
        args_file.write_text(spec + "\n", encoding="utf-8")
        start = check_ok(self, h("factory-run", "start", "--arguments-file", str(args_file)))
        self.assertEqual(start["mode"], "build")
        run = start["run"]
        common = ["factory-run", "record", "--run", run, "--model", "inherit"]

        d = check_ok(self, h(*common, "--agent", "factory-builder", "--duration-ms", "1500", "--tokens", "900"))
        self.assertEqual(d["action"], "verify")
        # La sortie du Verifier est ecrite par l'outil Write sous .claude/runs/, jamais via le shell.
        cr = helpers.verifier_block("CHANGES_REQUESTED", False,
                                    [{"file": "src/sum.js", "severity": "major", "description": helpers.TRAP}])
        out = helpers.write_output(project, "verifier-1.md", cr)
        d = check_ok(self, h(*common, "--agent", "factory-verifier", "--duration-ms", "800", "--output", out))
        self.assertEqual((d["action"], d["iteration"]), ("fix", 2))
        self.assertEqual(d["issues"][0]["description"], helpers.TRAP)
        d = check_ok(self, h(*common, "--agent", "factory-builder", "--duration-ms", "1200"))
        self.assertEqual(d["action"], "verify")
        d = check_ok(self, h(*common, "--agent", "factory-verifier", "--duration-ms", "50", "--dead"))
        self.assertEqual(d["action"], "relaunch")
        check_ok(self, h("begin", "--run", run, "--slot", "factory-verifier"))
        out = helpers.write_output(project, "verifier-2.md", helpers.verifier_block("APPROVED", True))
        d = check_ok(self, h(*common, "--agent", "factory-verifier", "--output", out))
        self.assertEqual(d["action"], "success")

        path = project / run
        self.assertRegex(path.name, journal.NAME_RE)
        self.assertEqual(path.parent, project / ".claude" / "runs")
        check_ok(self, h("journal", "validate", run))
        lines = journal.read(path)
        agents = [x["agent"] for x in lines]
        self.assertEqual(agents, ["factory-builder", "factory-verifier", "factory-builder",
                                  "factory-verifier", "factory-verifier"])
        self.assertTrue(all(x["iteration"] <= 3 for x in lines))
        dead, alive = lines[3], lines[4]
        self.assertEqual(dead["verdict"], "DEAD")
        self.assertEqual(dead["iteration"], alive["iteration"])
        self.assertEqual(alive["verdict"], "APPROVED")
        self.assertEqual(lines[0]["tokens"], 900)
        self.assertIsNone(lines[2]["tokens"])
        self.assertEqual(lines[1]["findings"]["produced"], 1)
        res = h(*common, "--agent", "factory-builder", "--duration-ms", "1")
        self.assertNotEqual(res.returncode, 0)

    def test_fr01_free_text_need_never_goes_through_shell(self):
        """FR-01 : un besoin contenant guillemets, $ et backtick est lu depuis
        un fichier ; il mene a la phase Plan sans erreur."""
        need = 'Exporter "tout" en CSV : `date` et $(whoami) ; puis ${HOME}\nligne 2'
        args_file = self.tmp / "arguments.txt"
        args_file.write_text(need, encoding="utf-8")
        start = check_ok(self, helpers.harness(["factory-run", "start", "--arguments-file", str(args_file)],
                                               self.tmp))
        self.assertEqual((start["mode"], start["spec"]), ("plan", None))
        bare = check_ok(self, helpers.harness(["factory-run", "start"], self.tmp))
        self.assertEqual(bare["mode"], "plan")


class ShipPrReplayTest(helpers.TempDirCase):
    def setUp(self):
        super().setUp()
        bare = self.tmp / "github.com" / "acme" / "toy.git"
        bare.mkdir(parents=True)
        helpers.git(bare, "init", "-q", "--bare", "-b", "main")
        self.work = self.tmp / "work"
        helpers.init_repo(self.work)
        (self.work / "src").mkdir()
        (self.work / "src" / "sum.js").write_text("function sum(v) {\n    return 0;\n}\n", encoding="utf-8")
        helpers.git(self.work, "add", "-A")
        helpers.git(self.work, "commit", "-q", "-m", "init")
        helpers.git(self.work, "remote", "add", "origin", bare.as_posix())
        helpers.git(self.work, "push", "-q", "-u", "origin", "main")
        helpers.git(self.work, "checkout", "-q", "-b", "feature")
        (self.work / "src" / "sum.js").write_text(
            "function sum(v) {\n    return v.reduce((a, b) => a + b);\n}\n", encoding="utf-8")
        helpers.git(self.work, "commit", "-q", "-am", "sum")
        self.env = {"HCORE_GH": json.dumps([sys.executable, "-B", str(helpers.TESTS / "fake_gh.py")]),
                    "HCORE_FAKE_GH_STATE": str(self.tmp / "gh-state.json"), "HCORE_TEST_MODE": "1"}

    def h(self, *args, stdin=None):
        return helpers.harness(list(args), self.work, stdin=stdin, env=self.env)

    def gh_state(self):
        return json.loads((self.tmp / "gh-state.json").read_text(encoding="utf-8"))

    def test_ca16_ship_pr_sequence(self):
        """SP-01 a SP-19 : rejeu complet, journal, registre, merge."""
        bad = self.h("ship-pr", "start", "--target", "main", "--rounds", "0")
        self.assertEqual(bad.returncode, 2)
        self.assertIn("--rounds", bad.stderr)
        on_target = helpers.harness(["ship-pr", "start", "--target", "feature"], self.work, env=self.env)
        self.assertEqual(on_target.returncode, 1)
        self.assertIn("vous êtes déjà sur feature", on_target.stderr)

        start = check_ok(self, self.h("ship-pr", "start", "--target", "main", "--themes", "logique;regressions;coherence"))
        run, themes = start["run"], start["themes"]
        self.assertEqual((start["rounds"], start["dirty"], start["owner_repo"]), (3, False, "acme/toy"))
        self.assertTrue(start["exclude_added"])
        self.assertTrue(check_ok(self, self.h("ship-pr", "sync", "--run", run))["pushed"])
        material = check_ok(self, self.h("ship-pr", "pr", "--run", run))
        self.assertIsNone(material["number"])
        self.assertIn("sum", material["log"])
        # Corps de PR et sorties d'agents : ecrits par l'outil Write sous .claude/runs/.
        body = helpers.write_output(self.work, "pr-body.md", helpers.TRAP)
        pr = check_ok(self, self.h("ship-pr", "pr", "--run", run, "--title", "Somme", "--body-file", body))
        self.assertEqual((pr["number"], pr["created"], pr["conflicting"]), (7, True, False))
        self.assertEqual(self.gh_state()["prs"][-1]["body"], helpers.TRAP)
        self.assertIn("reduce", check_ok(self, self.h("ship-pr", "diff", "--run", run)))

        def review(theme, findings, *extra):
            out = helpers.write_output(self.work, "reviewer.md", helpers.reviewer_block(findings))
            return check_ok(self, self.h("ship-pr", "reviewer", "--run", run, "--theme", theme, "--model", "haiku",
                                         "--duration-ms", "900", "--tokens", "1200", "--output", out, *extra))

        def validate(fid, verdict):
            out = helpers.write_output(self.work, "validator.md", helpers.validator_block(verdict))
            return check_ok(self, self.h("ship-pr", "validator", "--run", run, "--finding", fid, "--model", "haiku",
                                         "--duration-ms", "300", "--output", out))

        real = helpers.finding(file="src/sum.js", line=2, title="reduce sans valeur initiale")
        real["description"] = helpers.TRAP
        fake = helpers.finding(file="src/sum.js", line=1, title="Nom de parametre trop court", severity="minor")
        # Ronde 1
        r1 = review("logique", [real])["to_validate"][0]
        self.assertEqual(r1["description"], helpers.TRAP)
        f1 = r1["id"]
        dead = check_ok(self, self.h("ship-pr", "reviewer", "--run", run, "--theme", "regressions",
                                     "--model", "haiku", "--duration-ms", "10", "--dead"))
        self.assertEqual(dead["action"], "relaunch")
        f2 = review("regressions", [fake])["to_validate"][0]["id"]
        self.assertEqual(review("coherence", [])["action"], "none")
        self.assertEqual(validate(f1, "CONFIRMED")["action"], "post")
        # Defaut de journalisation (ni duree ni 'begin', tokens invalides, modele vide) :
        # signale, journalise une valeur de repli, jamais bloquant ; le verdict est pris en compte.
        out = helpers.write_output(self.work, "validator.md", helpers.validator_block("REJECTED"))
        dropped = check_ok(self, self.h("ship-pr", "validator", "--run", run, "--finding", f2, "--model", " ",
                                        "--tokens", "beaucoup", "--output", out))
        self.assertEqual(dropped["action"], "drop")
        self.assertEqual(len(dropped["journal_warnings"]), 3)
        self.assertIn("overrides", dropped["hcore_test_mode"])
        posted = check_ok(self, self.h("ship-pr", "comment", "--run", run, "--finding", f1))
        self.assertEqual(posted["mode"], "inline")
        (self.work / "src" / "sum.js").write_text(
            "function sum(v) {\n    return v.reduce((a, b) => a + b, 0);\n}\n", encoding="utf-8")
        # Le correctif touche aussi un fichier jamais signale : la ronde 2 doit le relire.
        (self.work / "src" / "sum.test.js").write_text("assert(sum([]) === 0);\n", encoding="utf-8")
        commit = check_ok(self, self.h("ship-pr", "commit", "--run", run, "--summary", "valeur initiale",
                                       "--fixed", f1))
        self.assertEqual(helpers.git(self.work, "log", "-1", "--format=%s").strip(),
                         "fix(review): corrections round 1 — valeur initiale")
        threads = check_ok(self, self.h("ship-pr", "threads", "--run", run))
        self.assertEqual(threads["resolved"], [f1])
        self.assertIn("Corrigé dans %s." % commit["commit"], self.gh_state()["replies"][0]["body"])
        end1 = check_ok(self, self.h("ship-pr", "end-round", "--run", run))
        self.assertEqual(end1["next_round"], 2)
        self.assertEqual((end1["counts"]["raw"], end1["counts"]["confirmed"], end1["counts"]["rejected"]), (2, 1, 1))
        # Ronde 2 (SP-15) : le commit de correctif est relu, fichiers non signales compris.
        diff2 = check_ok(self, self.h("ship-pr", "diff", "--run", run))
        self.assertIn("src/sum.test.js", diff2)
        self.assertIn("a + b, 0);", diff2)
        # Le finding REJECTED est resoumis
        again = review("logique", [fake])
        self.assertEqual(again["to_validate"], [])
        self.assertEqual(again["duplicates"][0]["previous"], "REJECTED")
        review("regressions", [])
        review("coherence", [])
        end2 = check_ok(self, self.h("ship-pr", "end-round", "--run", run))
        self.assertEqual(end2["exit"], "exhaustion")
        summary = check_ok(self, self.h("ship-pr", "merge", "--run", run, "--check"))
        self.assertEqual(len(summary["rounds"]), 2)
        merged = check_ok(self, self.h("ship-pr", "merge", "--run", run))
        self.assertTrue(merged["merged"])
        self.assertTrue(self.gh_state()["merged"])
        self.assertEqual(helpers.git(self.work, "rev-parse", "--abbrev-ref", "HEAD").strip(), "main")

        path = self.work / run
        self.assertRegex(path.name, journal.NAME_RE)
        check_ok(self, self.h("journal", "validate", run))
        lines = journal.read(path)
        self.assertTrue(all(x["iteration"] <= 3 for x in lines))
        reviewer_themes = {x["theme"] for x in lines if x["agent"] == "reviewer"}
        self.assertEqual(reviewer_themes, set(themes))
        validators = [x for x in lines if x["agent"] == "validator"]
        self.assertEqual([x["iteration"] for x in validators], [1, 1])
        self.assertEqual((validators[1]["duration_ms"], validators[1]["tokens"]), (None, None))
        self.assertEqual(validators[1]["model"], journal.FALLBACK_TEXT)
        reg_path = path.with_name(path.name[: -len(".jsonl")] + ".registry.jsonl")
        reg = [json.loads(x) for x in reg_path.read_text(encoding="utf-8").splitlines()]
        rejected = [x for x in reg if x["verdict"] == "REJECTED"]
        self.assertEqual(len(rejected), 1)
        self.assertFalse([x for x in reg if x.get("round") == 2])
        self.assertEqual(helpers.git(self.work, "status", "--porcelain", "--untracked-files=all"), "")


SKILLS_DIR = helpers.CORE.parent
SKILL_FILES = [SKILLS_DIR / "software-factory" / "SKILL.md", SKILLS_DIR / "ship-pr" / "SKILL.md"]
STDIN_OPTION = re.compile(r"--(?:output|source|body-file|content)\s+-(?![\w-])")


class UntrustedContentTest(helpers.TempDirCase):
    @unittest.skipUnless(all(p.is_file() for p in SKILL_FILES), "SKILL.md absents (copie du noyau dans un projet)")
    def test_skills_never_pipe_untrusted_content_through_stdin(self):
        """SF-04 FR-01 SP-13 : aucun contenu non fiable (agent, skill, script CI, sortie
        d'agent, corps de PR) n'est passe au noyau par stdin depuis une commande shell."""
        for path in SKILL_FILES:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(STDIN_OPTION.findall(text), [], path)
            self.assertIn("Write", text, path)
            self.assertIn(".claude/runs/", text, path)

    def test_sf04_generated_file_transits_by_file_unchanged(self):
        """SF-04 : un agent ou script contenant $ARGUMENTS, $1, $(date), backticks et
        apostrophes est installe octet pour octet depuis le fichier ecrit par Write."""
        src = helpers.write_output(self.tmp, "factory-builder.md", helpers.TRAP)
        res = helpers.harness(["sf", "install", "--dest", ".claude/agents/factory-builder.md", "--source", src],
                              self.tmp)
        self.assertEqual(json.loads(res.stdout)[".claude/agents/factory-builder.md"], "créé", res.stderr)
        self.assertEqual((self.tmp / ".claude" / "agents" / "factory-builder.md").read_bytes(),
                         helpers.TRAP.encode("utf-8"))


class TempCleanupTest(unittest.TestCase):
    def test_read_only_git_objects_are_removed(self):
        """Les depots jetables (objets git en lecture seule) ne survivent pas au test."""
        tmp = Path(tempfile.mkdtemp(prefix="hcore-"))
        try:
            helpers.init_repo(tmp / "repo")
            (tmp / "repo" / "f.txt").write_text("x\n", encoding="utf-8")
            helpers.git(tmp / "repo", "add", "-A")
            helpers.git(tmp / "repo", "commit", "-q", "-m", "x")
            locked = tmp / "verrou.txt"
            locked.write_text("ro", encoding="utf-8")
            os.chmod(str(locked), stat.S_IREAD)
            helpers.remove_tree(tmp)
            self.assertFalse(tmp.exists())
        finally:
            if tmp.exists():
                shutil.rmtree(str(tmp), ignore_errors=True)
