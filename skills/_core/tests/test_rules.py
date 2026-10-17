# Traceability of the rules and size of the rewired SKILL.md files.
#
# - CA-03: every rule of the lots delivered so far is named by its literal
#   identifier (for example GT-02) in the docstring of at least one test.
# - CA-05 / Q-G: line count and maximal line width of the touched SKILL.md
#   files (width bound: the one of BASE1 031df12, in characters).

import ast
import re
import unittest
from pathlib import Path

import helpers

TESTS = Path(__file__).resolve().parent
SKILLS = helpers.CORE.parent
SPEC = helpers.CORE.parent.parent / "specs" / "SPEC-phase1-rebranchement.md"

# Prefixes of the lots L1 to L3, L5 and L6.
PREFIXES = ("GT", "LK", "JR", "MD", "FD", "RG", "ST", "TS", "FU", "BK")
COUNTS = {"GT": 8, "LK": 2, "JR": 3, "MD": 9, "FD": 11, "RG": 7, "ST": 5, "TS": 5, "FU": 6, "BK": 2}
# Rules of a later lot, not delivered yet: BK-02 (equivalence of the rgkb.py
# hook blocks with blocks.py) belongs to lot L8 (code-index).
DEFERRED = {"BK-02": "L8"}

# (max lines, max width at BASE1 031df12)
SKILL_BOUNDS = {"ship-pr": (118, 1016), "software-factory": (96, 1060)}


def test_docstrings():
    texts = []
    for path in sorted(TESTS.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name.startswith(("test", "Test")) \
                    or isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                if doc:
                    texts.append(doc)
    return "\n".join(texts)


class RuleTraceTest(unittest.TestCase):
    def rules(self):
        expected = {"%s-%02d" % (p, n) for p, count in COUNTS.items() for n in range(1, count + 1)}
        if SPEC.is_file():
            found = set(re.findall(r"\b(?:%s)-[0-9]{2}\b" % "|".join(PREFIXES), SPEC.read_text(encoding="utf-8")))
            self.assertEqual(found, expected, "rule set of the spec changed")
        return sorted(expected - set(DEFERRED))

    def test_ca03_every_delivered_rule_named_in_a_test_docstring(self):
        """CA-03: GT-, LK-, JR-, MD-, FD-, RG-, ST-, TS-, FU- and BK- rules each appear,
        literally, in the docstring of at least one test (MD-03 and MD-09 are noted
        as replaced by X8 and X1; BK-02 belongs to lot L8)."""
        docs = test_docstrings()
        missing = [rule for rule in self.rules() if not re.search(r"\b%s\b" % re.escape(rule), docs)]
        self.assertEqual(missing, [])
        self.assertIn("MD-09 is replaced by X1", docs)


@unittest.skipUnless((SKILLS / "ship-pr" / "SKILL.md").is_file(), "SKILL.md files absent")
class SkillSizeTest(unittest.TestCase):
    def test_ca05_qg_line_count_and_width_of_touched_skills(self):
        """CA-05, Q-G: software-factory <= 96 lines, ship-pr <= 118 lines, and no
        line wider than the widest line of the same file at BASE1."""
        for name, (max_lines, max_width) in SKILL_BOUNDS.items():
            lines = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8").splitlines()
            self.assertLessEqual(len(lines), max_lines, name)
            widest = max(range(len(lines)), key=lambda i: len(lines[i]))
            self.assertLessEqual(len(lines[widest]), max_width, "%s:%d" % (name, widest + 1))


if __name__ == "__main__":
    unittest.main()
