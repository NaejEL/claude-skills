# Module hcore.shippr : boucle de revue de ship-pr (SP-05 a SP-10).

import json
import unittest

import helpers
from hcore import registry, shippr

THEMES = ["logique", "regressions", "coherence"]


class LoopCase(helpers.TempDirCase):
    def setUp(self):
        super().setUp()
        self.reg = registry.Registry(self.tmp / "ship-pr-20261016-120000.registry.jsonl")
        self.state = shippr.new_state("main", 3, THEMES)

    def review(self, theme, findings=None, dead=False, raw=None):
        out = raw if raw is not None else helpers.reviewer_block(findings or [])
        return shippr.record_reviewer(self.state, self.reg, theme, None if dead else out, dead)

    def validate(self, fid, verdict=None, dead=False):
        out = None if dead else helpers.validator_block(verdict)
        return shippr.record_validator(self.state, self.reg, fid, out, dead)

    def registry_lines(self):
        return [json.loads(x) for x in self.reg.path.read_text(encoding="utf-8").splitlines()]


class ThemeDeathTest(LoopCase):
    def test_sp05_dead_theme_relaunched_once_then_uncovered(self):
        """SP-05."""
        self.assertEqual(self.review("logique", dead=True)[0]["action"], "relaunch")
        decision, log = self.review("logique", raw="sortie tronquee")
        self.assertEqual(decision["action"], "uncovered")
        self.assertEqual(log["verdict"], "DEAD")
        self.review("regressions")
        self.review("coherence")
        result = shippr.end_round(self.state, "sha1")
        self.assertNotEqual(result["exit"], "exhaustion")
        # Pas de sortie anticipee sur le silence d'un theme mort : ronde suivante.
        self.assertIsNone(result["exit"])
        self.assertEqual(result["next_round"], 2)
        self.assertEqual(result["uncovered"], [{"round": 1, "theme": "logique"}])
        self.assertIsNotNone(shippr.merge_refusal(self.state))
        for theme in THEMES:
            self.review(theme)
        self.assertEqual(shippr.end_round(self.state, "sha2")["exit"], "exhaustion")
        self.assertIn("logique (ronde 1)", shippr.merge_refusal(self.state))

    def test_sp05_uncovered_silence_never_exits_until_cap(self):
        """SP-05 : rondes sans CONFIRMED mais theme non couvert -> la boucle
        continue jusqu'au plafond ; le merge reste refuse."""
        for number in (1, 2, 3):
            self.review("logique", dead=True)
            self.review("logique", dead=True)
            self.review("regressions")
            self.review("coherence")
            result = shippr.end_round(self.state, "sha%d" % number)
            self.assertEqual(result["exit"], None if number < 3 else "cap")
        self.assertEqual(len(self.state["uncovered"]), 3)
        self.assertIn("non couvert", shippr.merge_refusal(self.state))

    def test_sp05_silent_theme_blocks_early_exit(self):
        """SP-05."""
        self.review("logique")
        self.review("regressions")
        with self.assertRaises(shippr.LoopError):
            shippr.end_round(self.state, "sha1")

    def test_sp05_dead_theme_with_confirmed_continues_but_merge_refused(self):
        """SP-05."""
        self.review("logique", dead=True)
        self.review("logique", dead=True)
        fid = self.review("regressions", [helpers.finding()])[0]["to_validate"][0]["id"]
        self.review("coherence")
        self.validate(fid, "CONFIRMED")
        shippr.set_outcome(self.state, self.reg, fid, True, commit="abc")
        self.assertEqual(shippr.end_round(self.state, "sha1")["next_round"], 2)
        for theme in THEMES:
            self.review(theme)
        self.assertEqual(shippr.end_round(self.state, "sha2")["exit"], "exhaustion")
        self.assertIsNotNone(shippr.merge_refusal(self.state))


class ValidatorDeathTest(LoopCase):
    def test_sp06_dead_validator_leaves_finding_unvalidated(self):
        """SP-06."""
        fid = self.review("logique", [helpers.finding()])[0]["to_validate"][0]["id"]
        self.assertEqual(self.validate(fid, dead=True)[0]["action"], "relaunch")
        decision, log = self.validate(fid, dead=True)
        self.assertEqual(decision["action"], "unvalidated")
        self.assertEqual(self.registry_lines()[-1]["verdict"], "UNVALIDATED")
        self.assertEqual(shippr.confirmed_of_round(self.state), [])
        with self.assertRaises(shippr.LoopError):
            shippr.set_outcome(self.state, self.reg, fid, True, commit="abc")


class InterruptedRelaunchTest(LoopCase):
    def test_sp07_validator_replayed_after_lost_state_single_registry_line(self):
        """SP-07 : verdict inscrit au registre, etat non sauvegarde (interruption),
        puis meme appel rejoue sur l'etat precedent : une seule ligne au registre."""
        fid = self.review("logique", [helpers.finding()])[0]["to_validate"][0]["id"]
        saved = json.loads(json.dumps(self.state))
        self.validate(fid, "REJECTED")
        self.state = saved
        self.reg = registry.Registry(self.reg.path)
        self.assertEqual(self.validate(fid, "REJECTED")[0]["action"], "drop")
        self.assertEqual(len(self.registry_lines()), 1)


class DedupTest(LoopCase):
    def test_sp07_rejected_finding_does_not_reach_validator_again(self):
        """SP-07."""
        rejected = self.review("logique", [helpers.finding(title="Faux bug")])[0]["to_validate"][0]["id"]
        self.validate(rejected, "REJECTED")
        real = self.review("regressions", [helpers.finding(file="b.py", title="Vrai bug")])[0]["to_validate"][0]["id"]
        self.validate(real, "CONFIRMED")
        self.review("coherence")
        shippr.set_outcome(self.state, self.reg, real, True, commit="c")
        self.assertEqual(shippr.end_round(self.state, "sha1")["next_round"], 2)
        decision, log = self.review("logique", [helpers.finding(title="faux  BUG !")])
        self.assertEqual(decision["action"], "none")
        self.assertEqual(decision["to_validate"], [])
        self.assertEqual(decision["duplicates"][0]["previous"], "REJECTED")
        self.assertEqual(log["rejected"], 1)

    def test_sp07_same_finding_from_two_themes_validated_once(self):
        """SP-07."""
        first = self.review("logique", [helpers.finding()])[0]
        second = self.review("regressions", [helpers.finding()])[0]
        self.assertEqual(len(first["to_validate"]), 1)
        self.assertEqual(second["to_validate"], [])
        self.assertEqual(second["duplicates"][0]["previous"], "PENDING")


class ExitTest(LoopCase):
    def full_round(self, confirmed):
        fids = []
        for i, theme in enumerate(THEMES):
            findings = [helpers.finding(title="bug %d-%d" % (self.state["round"], i))] if confirmed else []
            fids += [f["id"] for f in self.review(theme, findings)[0]["to_validate"]]
        for fid in fids:
            self.validate(fid, "CONFIRMED")
            shippr.set_outcome(self.state, self.reg, fid, True, commit="c")
        return shippr.end_round(self.state, "sha%d" % self.state["round"])

    def test_sp08_exhaustion(self):
        """SP-08."""
        self.assertEqual(self.full_round(True)["next_round"], 2)
        self.assertEqual(self.full_round(False)["exit"], "exhaustion")

    def test_sp08_cap(self):
        """SP-08."""
        self.state["rounds"] = 2
        self.full_round(True)
        result = self.full_round(True)
        self.assertEqual(result["exit"], "cap")
        with self.assertRaises(shippr.LoopError):
            self.review("logique")

    def test_sp08_prev_round_sha_recorded(self):
        """SP-08."""
        self.full_round(True)
        self.assertEqual(self.state["prev_round_sha"], "sha1")

    def test_sp15_reference_is_head_before_fix_commit(self):
        """SP-15 : la reference de la ronde suivante est HEAD avant le correctif."""
        fid = self.review("logique", [helpers.finding()])[0]["to_validate"][0]["id"]
        self.review("regressions")
        self.review("coherence")
        self.validate(fid, "CONFIRMED")
        shippr.mark_pre_fix(self.state, "avant-fix")
        shippr.mark_pre_fix(self.state, "ignore")
        shippr.set_outcome(self.state, self.reg, fid, True, commit="fix1")
        shippr.end_round(self.state, "fix1")
        self.assertEqual(self.state["prev_round_sha"], "avant-fix")


class OutcomeTest(LoopCase):
    def test_sp09_confirmed_not_fixed_is_recorded(self):
        """SP-09."""
        fid = self.review("logique", [helpers.finding()])[0]["to_validate"][0]["id"]
        self.validate(fid, "CONFIRMED")
        self.review("regressions")
        self.review("coherence")
        with self.assertRaises(shippr.LoopError):
            shippr.end_round(self.state, "s")
        with self.assertRaises(shippr.LoopError):
            shippr.set_outcome(self.state, self.reg, fid, False, reason="")
        shippr.set_outcome(self.state, self.reg, fid, False, reason="faux positif decouvert au fix")
        last = self.registry_lines()[-1]
        self.assertEqual(last["verdict"], "NOT_FIXED")
        self.assertEqual(last["reason"], "faux positif decouvert au fix")
        self.assertEqual(shippr.summary(self.state)["left_open"][0]["id"], fid)


class CountersTest(LoopCase):
    def test_sp10_raw_confirmed_rejected_per_round(self):
        """SP-10."""
        out = self.review("logique", [helpers.finding(title="a"), helpers.finding(title="b"),
                                      helpers.finding(title="a")])[0]
        a, b = [f["id"] for f in out["to_validate"]]
        self.validate(a, "CONFIRMED")
        self.validate(b, "REJECTED")
        self.review("regressions")
        self.review("coherence")
        shippr.set_outcome(self.state, self.reg, a, True, commit="c")
        result = shippr.end_round(self.state, "s")
        self.assertEqual(result["counts"], {"round": 1, "raw": 3, "confirmed": 1, "rejected": 1,
                                            "duplicates": 1, "unvalidated": 0})
        self.assertEqual(shippr.summary(self.state)["rounds"][0]["raw"], 3)


if __name__ == "__main__":
    unittest.main()
