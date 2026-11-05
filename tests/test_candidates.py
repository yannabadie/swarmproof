"""Tests d'extraction des correctifs candidats et du mapping vers les fichiers cibles."""

from __future__ import annotations

import unittest

from swarmproof.candidates import choose_target, extract_code_blocks, target_score

SOURCE = '''"""Calculs."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a + b
'''


class ExtractCodeBlocksTests(unittest.TestCase):
    def test_extracts_fenced_python_block(self):
        text = "Voici le correctif :\n\n```python\ndef subtract(a, b):\n    return a - b\n```\n"
        blocks = extract_code_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertIn("return a - b", blocks[0])

    def test_ignores_test_files_and_short_blocks(self):
        text = "```python\nimport unittest\nclass TestX(unittest.TestCase):\n    pass\n```\n```python\nx=1\n```"
        self.assertEqual(extract_code_blocks(text), [])

    def test_falls_back_to_plain_text(self):
        blocks = extract_code_blocks("def subtract(a, b):\n    return a - b\n")
        self.assertEqual(len(blocks), 1)

    def test_empty_answer(self):
        self.assertEqual(extract_code_blocks(""), [])
        self.assertEqual(extract_code_blocks("aucun code ici"), [])

    def test_deduplicates(self):
        block = "```python\ndef subtract(a, b):\n    return a - b\n```"
        self.assertEqual(len(extract_code_blocks(block + "\n" + block)), 1)


class TargetMappingTests(unittest.TestCase):
    def test_single_target_auto_selected(self):
        candidate = "def subtract(a, b):\n    return a - b\n"
        self.assertEqual(choose_target(candidate, {"mod.py": SOURCE}), "mod.py")

    def test_best_symbol_overlap_wins(self):
        candidate = "def subtract(a, b):\n    return a - b\n"
        targets = {"other.py": "def render():\n    return 'x'\n", "mod.py": SOURCE}
        self.assertEqual(choose_target(candidate, targets), "mod.py")

    def test_no_overlap_returns_none(self):
        candidate = "def totally_unrelated_zzz():\n    return 1\n"
        targets = {"a.py": "def alpha():\n    return 1\n", "b.py": "def beta():\n    return 2\n"}
        self.assertIsNone(choose_target(candidate, targets))

    def test_target_score(self):
        self.assertGreater(target_score("def subtract(a, b):\n    return a - b\n", SOURCE), 0)


if __name__ == "__main__":
    unittest.main()
