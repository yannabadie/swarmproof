"""Tests v0.2 : parsing et application atomique des correctifs multi-fichiers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swarmproof.candidates import (
    CandidateFile,
    CandidateSet,
    apply_candidate_set,
    parse_candidate_sets,
)
from swarmproof.util import write_text

STORE_V1 = "class Store:\n    def put(self, key, value):\n        self._data = {key: value}\n"
CACHE_V1 = "class Cache:\n    def get(self, key):\n        return None\n"
API_V1 = "def bootstrap():\n    return None\n"
TARGETS = ["src/store.py", "src/cache.py", "src/api.py"]


def _tagged(path: str, content: str) -> str:
    return f"--- FILE: {path} ---\n```python\n{content}```\n"


def _answer(name: str = "lead") -> str:
    return f"{name} propose un correctif multi-fichiers :\n\n" + _tagged("src/store.py", STORE_V1) + "\n" + _tagged("src/cache.py", CACHE_V1)


class ParseCandidateSetsTests(unittest.TestCase):
    def test_parses_two_tagged_files(self):
        sets, rejections = parse_candidate_sets(_answer(), TARGETS)
        self.assertEqual(rejections, [])
        self.assertEqual(len(sets), 1)
        self.assertEqual(sets[0].n_files, 2)
        self.assertEqual([item.path for item in sets[0].files], ["src/store.py", "src/cache.py"])

    def test_rejects_unknown_target_file(self):
        text = _tagged("src/store.py", STORE_V1) + _tagged("scripts/outside.py", API_V1)
        sets, rejections = parse_candidate_sets(text, TARGETS)
        self.assertEqual(sets, [])
        self.assertTrue(any("hors cible" in rejection.reason for rejection in rejections))

    def test_rejects_path_traversal(self):
        text = _tagged("src/store.py", STORE_V1) + _tagged("../../etc/passwd.py", API_V1)
        sets, rejections = parse_candidate_sets(text, TARGETS)
        self.assertEqual(sets, [])
        self.assertTrue(any("hors arborescence" in rejection.reason or "hors cible" in rejection.reason for rejection in rejections))

    def test_rejects_duplicate_file_marker(self):
        text = _tagged("src/store.py", STORE_V1) + _tagged("src/store.py", STORE_V1)
        sets, rejections = parse_candidate_sets(text, TARGETS)
        self.assertEqual(sets, [])
        self.assertTrue(any("double" in rejection.reason for rejection in rejections))

    def test_rejects_partial_or_syntax_invalid_block(self):
        broken = "class Cache:\n    def get(self, key):\n        if key:\n"
        text = _tagged("src/store.py", STORE_V1) + _tagged("src/cache.py", broken)
        sets, rejections = parse_candidate_sets(text, TARGETS)
        self.assertEqual(sets, [])
        self.assertTrue(any("incomplet" in rejection.reason for rejection in rejections))

    def test_rejects_placeholder_truncation(self):
        partial = "class Cache:\n    def get(self, key):\n        # ...\n        pass\n"
        text = _tagged("src/cache.py", partial)
        sets, rejections = parse_candidate_sets(text, TARGETS)
        self.assertEqual(sets, [])
        self.assertTrue(any("partiel" in rejection.reason for rejection in rejections))

    def test_rejects_unlabeled_block_when_multiple_targets(self):
        text = "```python\n" + STORE_V1 + "```\n"
        sets, rejections = parse_candidate_sets(text, TARGETS)
        self.assertEqual(sets, [])
        self.assertTrue(any("ambigu" in rejection.reason for rejection in rejections))

    def test_single_target_fallback(self):
        text = "```python\n" + STORE_V1 + "```\n"
        sets, rejections = parse_candidate_sets(text, ["src/store.py"])
        self.assertEqual(rejections, [])
        self.assertEqual(len(sets), 1)
        self.assertEqual(sets[0].files[0].path, "src/store.py")


class AtomicApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-multi-test-"))
        write_text(self.tmp / "src" / "store.py", "x = 1\n")
        write_text(self.tmp / "src" / "cache.py", "y = 2\n")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_applies_all_files(self):
        candidate = CandidateSet(
            files=[
                CandidateFile("src/store.py", "x = 10\n"),
                CandidateFile("src/cache.py", "y = 20\n"),
            ]
        )
        written = apply_candidate_set(self.tmp, candidate)
        self.assertEqual(sorted(written), ["src/cache.py", "src/store.py"])
        self.assertEqual((self.tmp / "src" / "store.py").read_text(), "x = 10\n")

    def test_refuses_missing_file_without_partial_write(self):
        candidate = CandidateSet(
            files=[
                CandidateFile("src/store.py", "x = 10\n"),
                CandidateFile("src/does_not_exist.py", "z = 3\n"),
            ]
        )
        with self.assertRaises(ValueError):
            apply_candidate_set(self.tmp, candidate)
        self.assertEqual((self.tmp / "src" / "store.py").read_text(), "x = 1\n")  # rollback / rien écrit

    def test_refuses_path_traversal(self):
        candidate = CandidateSet(files=[CandidateFile("../../evil.py", "x = 1\n")])
        with self.assertRaises(ValueError):
            apply_candidate_set(self.tmp, candidate)


if __name__ == "__main__":
    unittest.main()
