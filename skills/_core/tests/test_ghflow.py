# Module hcore.ghflow : sequences gh/git de ship-pr avec gh et git simules
# (SP-11 a SP-19), messages d'arret (CA7), exclusion git du journal (D3, CA11).

import contextlib
import io
import json
import os
import sys
import unittest
from unittest import mock

import helpers
from hcore import ghflow, journal, registry, runs, shippr
from hcore.ghflow import Stop
from hcore.proc import Runner


def green_preflight():
    return (helpers.FakeRunner()
            .on(("git", "remote", "get-url", "origin"), out="https://github.com/acme/toy.git\n")
            .on(("git", "rev-parse", "--abbrev-ref", "HEAD"), out="feature\n"))


class PreflightTest(unittest.TestCase):
    def test_sp11_gh_not_authenticated(self):
        """SP-11."""
        run = green_preflight().on(("gh", "auth", "status"), code=1)
        with self.assertRaises(Stop) as ctx:
            ghflow.preflight_checks(run, "main")
        self.assertIn("gh non authentifié", str(ctx.exception))
        self.assertFalse(run.called("git"))

    def test_sp11_no_github_remote(self):
        """SP-11."""
        run = green_preflight().on(("git", "remote", "get-url", "origin"), out="https://gitlab.com/x/y.git\n")
        with self.assertRaises(Stop) as ctx:
            ghflow.preflight_checks(run, "main")
        self.assertIn("pas de remote GitHub", str(ctx.exception))

    def test_sp11_already_on_target(self):
        """SP-11."""
        run = green_preflight().on(("git", "rev-parse", "--abbrev-ref", "HEAD"), out="main\n")
        with self.assertRaises(Stop) as ctx:
            ghflow.preflight_checks(run, "main")
        self.assertIn("vous êtes déjà sur main", str(ctx.exception))

    def test_sp11_target_missing_on_origin(self):
        """SP-11."""
        run = green_preflight().on(("git", "rev-parse", "--verify", "origin/main"), code=128)
        with self.assertRaises(Stop) as ctx:
            ghflow.preflight_checks(run, "main")
        self.assertIn("la branche cible main n'existe pas sur origin", str(ctx.exception))

    def test_sp11_green_and_dirty_reported(self):
        """SP-11."""
        run = green_preflight()
        self.assertEqual(ghflow.preflight_checks(run, "main"), {"branch": "feature"})
        self.assertEqual(run.called("git", "fetch"), [["git", "fetch", "origin", "main"]])
        run.on(("git", "status", "--porcelain"), out=" M a.py\n").on(("gh", "repo", "view"), out="acme/toy\n")
        info = ghflow.worktree_and_repo(run)
        self.assertEqual(info, {"dirty": True, "dirty_files": [" M a.py"], "owner_repo": "acme/toy"})


class UpstreamTest(unittest.TestCase):
    def test_sp12_push_when_no_upstream(self):
        """SP-12."""
        run = helpers.FakeRunner().on(("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name"), code=128)
        self.assertTrue(ghflow.sync_upstream(run)["pushed"])
        self.assertEqual(run.called("git", "push"), [["git", "push", "-u", "origin", "HEAD"]])

    def test_sp12_push_only_when_ahead(self):
        """SP-12."""
        run = helpers.FakeRunner().on(("git", "rev-list"), out="0\n")
        self.assertFalse(ghflow.sync_upstream(run)["pushed"])
        self.assertFalse(run.called("git", "push"))
        run = helpers.FakeRunner().on(("git", "rev-list"), out="2\n")
        self.assertTrue(ghflow.sync_upstream(run)["pushed"])


def pr_view_state(run, sha="sha-head"):
    return run.on(("gh", "pr", "view", "7"), out=json.dumps(
        {"headRefOid": sha, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"}))


class PullRequestTest(unittest.TestCase):
    def state(self):
        st = shippr.new_state("main", 3, ["a"])
        st.update(branch="feature", owner_repo="acme/toy")
        return st

    def test_sp13_existing_pr_reused(self):
        """SP-13."""
        run = pr_view_state(helpers.FakeRunner().on(("gh", "pr", "list"),
                                                    out='[{"number": 7, "url": "u", "title": "t"}]'))
        st = self.state()
        result = ghflow.find_or_create_pr(run, st)
        self.assertEqual((result["number"], result["created"], st["pr"]), (7, False, 7))
        self.assertFalse(run.called("gh", "pr", "create"))
        self.assertIn(["gh", "pr", "list", "--head", "feature", "--base", "main", "--state", "open",
                       "--json", "number,url,title"], run.calls)

    def test_sp13_missing_pr_returns_material_then_creates(self):
        """SP-13."""
        run = helpers.FakeRunner().on(("gh", "pr", "list"), out="[]").on(("git", "log"), out="abc fix\n")
        st = self.state()
        material = ghflow.find_or_create_pr(run, st)
        self.assertIsNone(material["number"])
        self.assertEqual(material["log"], "abc fix\n")
        pr_view_state(run.on(("gh", "pr", "view", "--json", "number,url"), out='{"number": 7, "url": "u"}'))
        result = ghflow.find_or_create_pr(run, st, "Titre", "Corps")
        self.assertTrue(result["created"])
        self.assertEqual(run.called("gh", "pr", "create")[0],
                         ["gh", "pr", "create", "--base", "main", "--title", "Titre", "--body", "Corps"])

    def test_sp14_conflict_detected(self):
        """SP-14."""
        run = helpers.FakeRunner().on(("gh", "pr", "view", "7"), out=json.dumps(
            {"headRefOid": "s", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}))
        self.assertTrue(ghflow.pr_state(run, 7)["conflicting"])


class RoundFlowTest(helpers.TempDirCase):
    def setUp(self):
        super().setUp()
        self.reg = registry.Registry(self.tmp / "r.registry.jsonl")
        self.st = shippr.new_state("main", 3, ["a"])
        self.st.update(branch="feature", owner_repo="acme/toy", pr=7)
        out = helpers.reviewer_block([helpers.finding(file="src/x.py", line=4, title="Off by one")])
        self.fid = shippr.record_reviewer(self.st, self.reg, "a", out, False)[0]["to_validate"][0]["id"]
        shippr.record_validator(self.st, self.reg, self.fid, helpers.validator_block("CONFIRMED"), False)

    def test_sp15_round1_pr_diff_then_incremental(self):
        """SP-15."""
        run = helpers.FakeRunner().on(("gh", "pr", "diff"), out="DIFF1")
        self.assertEqual(ghflow.collect_diff(run, self.st), "DIFF1")
        self.st["round"], self.st["prev_round_sha"] = 2, "s1"
        run = helpers.FakeRunner().on(("git", "diff", "s1..HEAD"), out="INC\n").on(("git", "diff", "origin/main...HEAD"), out="FLAG\n")
        self.assertEqual(ghflow.collect_diff(run, self.st), "INC\nFLAG\n")
        self.assertIn(["git", "diff", "origin/main...HEAD", "--", "src/x.py"], run.calls)

    def test_sp15_reference_is_head_before_fix_commit_real_git(self):
        """SP-15 : rejeu reel sur un depot jetable ; la ronde 2 relit le commit de
        correctif de la ronde 1 (reference = HEAD d'avant ce commit)."""
        repo, bare = self.tmp / "repo", self.tmp / "origin.git"
        helpers.git(self.tmp, "init", "-q", "--bare", "-b", "main", str(bare))
        helpers.init_repo(repo)
        (repo / "a.txt").write_text("base\n", encoding="utf-8")
        helpers.git(repo, "add", "-A")
        helpers.git(repo, "commit", "-q", "-m", "base")
        helpers.git(repo, "remote", "add", "origin", bare.as_posix())
        helpers.git(repo, "push", "-q", "-u", "origin", "main")
        helpers.git(repo, "checkout", "-q", "-b", "feature")
        helpers.git(repo, "push", "-q", "-u", "origin", "feature")
        reviewed = helpers.git(repo, "rev-parse", "HEAD").strip()
        (repo / "src").mkdir()
        (repo / "src" / "x.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "jamais_signale.py").write_text("y = 2\n", encoding="utf-8")
        run = Runner(cwd=str(repo))
        ghflow.commit_round(run, self.st, self.reg, "borne", [self.fid], {})
        result = shippr.end_round(self.st, helpers.git(repo, "rev-parse", "HEAD").strip())
        self.assertEqual(result["next_round"], 2)
        self.assertEqual(self.st["prev_round_sha"], reviewed)
        diff = ghflow.collect_diff(run, self.st)
        self.assertIn("jamais_signale.py", diff)
        self.assertIn("y = 2", diff)

    def test_sp16_inline_comment_uses_fresh_head(self):
        """SP-16."""
        run = pr_view_state(helpers.FakeRunner(), sha="fresh").on(("gh", "api"), out='{"id": 99}')
        result = ghflow.post_comment(run, self.st, self.fid)
        self.assertEqual((result["mode"], result["comment_id"], result["commit_id"]), ("inline", 99, "fresh"))
        call = run.called("gh", "api")[0]
        self.assertIn("commit_id=fresh", call)
        self.assertIn("line=4", call)
        self.assertIn("side=RIGHT", call)

    def test_sp16_fallback_422_then_pr_comment(self):
        """SP-16."""
        class Seq(helpers.FakeRunner):
            def __call__(inner, args, input=None):
                if args[:2] == ["gh", "api"]:
                    inner.calls.append(list(args))
                    if "subject_type=file" in args:
                        return helpers.Result(0, '{"id": 5}', "")
                    return helpers.Result(1, "", "HTTP 422: Unprocessable")
                return helpers.FakeRunner.__call__(inner, args, input)
        run = pr_view_state(Seq())
        result = ghflow.post_comment(run, self.st, self.fid)
        self.assertEqual((result["mode"], result["comment_id"]), ("file", 5))
        run = pr_view_state(helpers.FakeRunner()).on(("gh", "api"), code=1, err="HTTP 422")
        result = ghflow.post_comment(run, self.st, self.fid)
        self.assertEqual(result["mode"], "pr")
        self.assertTrue(run.called("gh", "pr", "comment"))

    def test_sp16_non_422_error_stops_without_fallback(self):
        """SP-16 : le repli n'existe que sur HTTP 422 ; toute autre erreur arrete."""
        run = pr_view_state(helpers.FakeRunner()).on(("gh", "api"), code=1, err="HTTP 502: Bad Gateway")
        with self.assertRaises(Stop) as ctx:
            ghflow.post_comment(run, self.st, self.fid)
        self.assertIn("502", str(ctx.exception))
        self.assertEqual(len(run.called("gh", "api")), 1)
        self.assertFalse(run.called("gh", "pr", "comment"))
        self.assertIsNone(self.st["candidates"][self.fid]["comment_id"])

    def test_sp16_bare_422_elsewhere_in_error_does_not_trigger_fallback(self):
        """SP-16 : seul « HTTP 422 » declenche le repli, pas un 422 dans un identifiant
        ou un corps de reponse ; le vrai message de gh (« (HTTP 422) ») le declenche."""
        err = "HTTP 500: Internal Server Error (request 4220:1422AB, line 422)"
        run = pr_view_state(helpers.FakeRunner()).on(("gh", "api"), code=1, err=err)
        with self.assertRaises(Stop):
            ghflow.post_comment(run, self.st, self.fid)
        self.assertEqual(len(run.called("gh", "api")), 1)
        run = pr_view_state(helpers.FakeRunner()).on(("gh", "api"), code=1, out='{"id": 4221, "code": 422}',
                                                      err="HTTP 403: Forbidden")
        with self.assertRaises(Stop):
            ghflow.post_comment(run, self.st, self.fid)
        run = pr_view_state(helpers.FakeRunner()).on(
            ("gh", "api"), code=1, err="gh: Validation Failed (HTTP 422)")
        self.assertEqual(ghflow.post_comment(run, self.st, self.fid)["mode"], "pr")

    def test_sp17_one_commit_per_round_never_amend_or_force(self):
        """SP-17."""
        run = helpers.FakeRunner().on(("git", "rev-parse", "HEAD"), out="c0ffee\n")
        result = ghflow.commit_round(run, self.st, self.reg, "borne corrigee", [self.fid], {})
        self.assertEqual(result["commit"], "c0ffee")
        self.assertEqual(run.called("git", "commit"),
                         [["git", "commit", "-m", "fix(review): corrections round 1 — borne corrigee"]])
        flat = [a for call in run.calls for a in call]
        for forbidden in ("--amend", "--force", "-f", "--force-with-lease"):
            self.assertNotIn(forbidden, flat)
        self.assertEqual(self.reg.current(self.st["candidates"][self.fid]["key"]), "FIXED")

    def test_sp17_duplicate_id_refused_before_any_git_call(self):
        """SP-17, SP-09 : un id consigne deux fois est refuse avant commit et push."""
        for fixed, not_fixed in (([self.fid, self.fid], {}), ([self.fid], {self.fid: "faux positif"})):
            run = helpers.FakeRunner().on(("git", "rev-parse", "HEAD"), out="c0ffee\n")
            with self.assertRaises(Stop) as ctx:
                ghflow.commit_round(run, self.st, self.reg, "fix", fixed, not_fixed)
            self.assertIn(self.fid, str(ctx.exception))
            self.assertEqual(run.calls, [])
            self.assertIsNone(self.st["candidates"][self.fid]["outcome"])

    def test_sp18_threads_replied_and_resolved(self):
        """SP-18."""
        self.st["candidates"][self.fid]["comment_id"] = 99
        ghflow.commit_round(helpers.FakeRunner().on(("git", "rev-parse"), out="c0ffee\n"),
                            self.st, self.reg, "fix", [self.fid], {})
        graph = {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [
            {"id": "T1", "isResolved": False, "comments": {"nodes": [{"databaseId": 99}]}}]}}}}}
        run = helpers.FakeRunner().on(("gh", "api", "graphql", "-f", "query=" + ghflow.THREADS_QUERY),
                                      out=json.dumps(graph))
        result = ghflow.handle_threads(run, self.st)
        self.assertEqual(result, {"resolved": [self.fid], "left_open": []})
        self.assertIn(["gh", "api", "repos/acme/toy/pulls/7/comments/99/replies", "-f", "body=Corrigé dans c0ffee."], run.calls)
        self.assertIn("t=T1", run.calls[-1])
        self.assertEqual(ghflow.handle_threads(run, self.st), {"resolved": [], "left_open": []})

    def test_sp18_not_fixed_thread_left_open(self):
        """SP-18."""
        self.st["candidates"][self.fid]["comment_id"] = 99
        ghflow.commit_round(helpers.FakeRunner(), self.st, self.reg, "", [], {self.fid: "hors perimetre"})
        graph = {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": []}}}}}
        run = helpers.FakeRunner().on(("gh", "api", "graphql"), out=json.dumps(graph))
        result = ghflow.handle_threads(run, self.st)
        self.assertEqual(result["left_open"], [self.fid])
        self.assertFalse([c for c in run.calls if any("resolveReviewThread" in a for a in c)])

    def test_sp19_merge_refused_when_theme_uncovered(self):
        """SP-19."""
        self.st["exit"] = "exhaustion"
        self.st["uncovered"] = [{"round": 1, "theme": "a"}]
        run = helpers.FakeRunner()
        with self.assertRaises(Stop) as ctx:
            ghflow.merge(run, self.st, check_only=True)
        self.assertIn("non couvert", str(ctx.exception))
        with self.assertRaises(Stop):
            ghflow.merge(run, self.st, check_only=False)
        self.assertFalse(run.called("gh", "pr", "merge"))

    def test_sp19_merge_commit_and_branch_deleted(self):
        """SP-19."""
        self.st["exit"] = "exhaustion"
        run = pr_view_state(helpers.FakeRunner())
        self.assertIn("rounds", ghflow.merge(run, self.st, check_only=True))
        self.assertFalse(run.called("gh", "pr", "merge"))
        ghflow.merge(run, self.st, check_only=False)
        self.assertEqual(run.called("gh", "pr", "merge"), [["gh", "pr", "merge", "7", "--merge", "--delete-branch"]])
        self.assertEqual(run.calls[-2:], [["git", "checkout", "main"], ["git", "pull"]])


class ExcludeTest(helpers.TempDirCase):
    def test_ca11_exclude_hides_journal_and_registry_idempotent(self):
        helpers.init_repo(self.tmp)
        run_cmd = Runner(cwd=str(self.tmp))
        self.assertTrue(ghflow.ensure_exclude(run_cmd, self.tmp))
        exclude = self.tmp / ".git" / "info" / "exclude"
        before = exclude.read_text(encoding="utf-8")
        self.assertFalse(ghflow.ensure_exclude(run_cmd, self.tmp))
        self.assertEqual(exclude.read_text(encoding="utf-8"), before)
        self.assertEqual(before.splitlines().count(".claude/runs/"), 1)
        run = runs.create(self.tmp, "ship-pr", {})
        journal.append(run, journal.make_record("reviewer", "inherit", 5, 1, "NO_FINDING"))
        registry.Registry(runs.registry_path(run)).add(helpers.finding(), "REJECTED")
        status = helpers.git(self.tmp, "status", "--porcelain", "--untracked-files=all")
        self.assertNotIn(".claude/runs", status)



class TestModeGuardTest(helpers.TempDirCase):
    """HCORE_GH / HCORE_GIT : honores seulement avec HCORE_TEST_MODE=1, et signales."""

    FAKE = json.dumps([sys.executable, "-c", "print('FAUX-GIT')"])

    def test_override_ignored_without_test_mode(self):
        env = {k: v for k, v in os.environ.items() if k != "HCORE_TEST_MODE"}
        env["HCORE_GIT"] = self.FAKE
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stderr(io.StringIO()) as err:
            res = Runner()(["git", "--version"])
        self.assertNotIn("FAUX-GIT", res.out)
        self.assertIn("git version", res.out)
        self.assertIn("HCORE_GIT ignore", err.getvalue())

    def test_override_honoured_and_signalled_in_test_mode(self):
        with mock.patch.dict(os.environ, {"HCORE_GIT": self.FAKE, "HCORE_TEST_MODE": "1"}):
            self.assertEqual(Runner()(["git", "--version"]).out.strip(), "FAUX-GIT")
        res = helpers.harness(["version"], self.tmp, env={"HCORE_GIT": self.FAKE, "HCORE_TEST_MODE": "1"})
        self.assertEqual(json.loads(res.stdout)["hcore_test_mode"]["overrides"]["git"][0], sys.executable)
        res = helpers.harness(["version"], self.tmp, env={"HCORE_GIT": self.FAKE, "HCORE_TEST_MODE": "0"})
        self.assertNotIn("hcore_test_mode", json.loads(res.stdout))


if __name__ == "__main__":
    unittest.main()
