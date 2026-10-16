# Module hcore.blocks : blocs delimites (D9, non utilise par software-factory).

import unittest

import helpers  # noqa: F401
from hcore import blocks
from hcore.blocks import BlockError


class BlocksTest(unittest.TestCase):
    def test_upsert_appends_then_replaces_in_place(self):
        text = "# Agent\n\nPrompt utilisateur.\n"
        once = blocks.upsert_block(text, "rgkb", "regle v1", "md")
        self.assertIn("<!-- rgkb:debut -->\nregle v1\n<!-- rgkb:fin -->", once)
        self.assertTrue(once.startswith(text))
        twice = blocks.upsert_block(once, "rgkb", "regle v2", "md")
        self.assertNotIn("regle v1", twice)
        self.assertEqual(twice.count("rgkb:debut"), 1)
        self.assertEqual(blocks.upsert_block(twice, "rgkb", "regle v2", "md"), twice)

    def test_hash_style_and_get(self):
        text = blocks.upsert_block("#!/bin/sh\n", "rgkb", "echo hi", "hash")
        self.assertIn("# >>> rgkb >>>", text)
        self.assertEqual(blocks.get_block(text, "rgkb", "hash"), "echo hi")
        self.assertIsNone(blocks.get_block("rien", "rgkb", "hash"))

    def test_remove_restores_text(self):
        text = "debut\n"
        self.assertEqual(blocks.remove_block(blocks.upsert_block(text, "b", "x", "md"), "b", "md"), text)

    def test_malformed_refused(self):
        with self.assertRaises(BlockError):
            blocks.upsert_block("<!-- b:debut -->\nsans fin\n", "b", "x", "md")
        with self.assertRaises(BlockError):
            blocks.markers("nom invalide", "md")
        with self.assertRaises(BlockError):
            blocks.markers("b", "xml")


if __name__ == "__main__":
    unittest.main()
