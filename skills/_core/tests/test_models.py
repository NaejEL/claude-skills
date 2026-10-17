# Module hcore.models: reading of models.json and --models (D6, not wired).

import json
import unittest

import helpers
from hcore import models
from hcore.models import ModelsError

ROLES = ["builder", "verifier"]


class ModelsTest(helpers.TempDirCase):
    def test_absent_file_means_inherit(self):
        self.assertEqual(models.load(self.tmp / "models.json", ROLES), {"builder": "inherit", "verifier": "inherit"})

    def test_file_then_override_for_this_cycle(self):
        path = self.tmp / "models.json"
        path.write_text(json.dumps({"builder": "sonnet"}), encoding="utf-8")
        result = models.resolve(path, "verifier=opus", ROLES)
        self.assertEqual(result, {"builder": "sonnet", "verifier": "opus"})
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"builder": "sonnet"})

    def test_unknown_values_and_roles_refused(self):
        with self.assertRaises(ModelsError):
            models.parse_override("builder=gpt", ROLES)
        with self.assertRaises(ModelsError):
            models.parse_override("boss=opus", ROLES)
        with self.assertRaises(ModelsError):
            models.parse_override("builder", ROLES)
        path = self.tmp / "models.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(ModelsError):
            models.load(path, ROLES)

    def test_full_id_accepted(self):
        self.assertEqual(models.check_model("claude-opus-5-5"), "claude-opus-5-5")

    def test_split_arguments(self):
        rest, value = models.split_arguments('"my question" --models "math=fable;builder=sonnet"')
        self.assertEqual(rest, "my question")
        self.assertEqual(value, "math=fable;builder=sonnet")
        self.assertEqual(models.split_arguments("x"), ("x", None))


if __name__ == "__main__":
    unittest.main()
