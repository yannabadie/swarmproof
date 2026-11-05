"""Tests de l'oracle : red/green, restauration des tests, parsing unittest."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swarmproof.oracle import (
    discover_test_paths,
    parse_unittest_output,
    prepare_eval_tree,
    restore_paths,
    run_oracle,
)
from swarmproof.util import copy_tree, write_text

PKG = Path(__file__).resolve().parents[1]
FIXTURE = PKG / "examples" / "fixture"

BUGGY = (FIXTURE / "src" / "dateutils.py").read_text(encoding="utf-8")
FIXED = BUGGY.replace(
    "from datetime import date, datetime, timedelta",
    "from datetime import date, datetime, timedelta, timezone",
).replace(
    "    # BUG: the timezone offset is silently dropped instead of being converted.\n    return datetime.fromisoformat(text).replace(tzinfo=None)",
    "    parsed = datetime.fromisoformat(text)\n    return parsed.astimezone(timezone.utc).replace(tzinfo=None)",
)
ORACLE = "python -m unittest discover -s tests -v"


class OracleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-oracle-test-"))
        self.pristine = copy_tree(FIXTURE, self.tmp / "pristine")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_fixture_is_red_before_fix(self):
        tree = copy_tree(self.pristine, self.tmp / "buggy")
        eval_tree, restored = prepare_eval_tree(self.pristine, tree, self.tmp / "judge", "buggy")
        result = run_oracle(eval_tree, ORACLE, 60)
        self.assertFalse(result["passed"])
        self.assertEqual(result["tests_run"], 5)
        self.assertIn("tests", restored)

    def test_fixed_candidate_is_green(self):
        tree = copy_tree(self.pristine, self.tmp / "fixed")
        (tree / "src" / "dateutils.py").write_text(FIXED + "\n", encoding="utf-8")
        eval_tree, _ = prepare_eval_tree(self.pristine, tree, self.tmp / "judge", "fixed")
        result = run_oracle(eval_tree, ORACLE, 60)
        self.assertTrue(result["passed"])
        self.assertEqual(result["exit_code"], 0)

    def test_tests_restored_before_judging(self):
        """Un candidat qui casse les tests ne gagne pas en les modifiant."""
        tree = copy_tree(self.pristine, self.tmp / "cheat")
        write_text(tree / "src" / "dateutils.py", "def parse_rfc3339(value):\n    return None\n")
        write_text(tree / "tests" / "test_dateutils.py", "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n")
        eval_tree, restored = prepare_eval_tree(self.pristine, tree, self.tmp / "judge", "cheat")
        self.assertIn("tests", restored)
        self.assertIn("test_positive_offset_is_converted_to_utc", (eval_tree / "tests" / "test_dateutils.py").read_text())
        result = run_oracle(eval_tree, ORACLE, 60)
        self.assertFalse(result["passed"])

    def test_parse_unittest_output(self):
        stdout = "Ran 5 tests in 0.001s\n"
        stderr = "FAIL: test_positive_offset_is_converted_to_utc (test_dateutils.ParseRfc3339Tests.test_positive_offset_is_converted_to_utc)\n" \
                 "ERROR: test_other (test_dateutils.X.test_other)\n"
        parsed = parse_unittest_output(stdout, stderr)
        self.assertEqual(parsed["tests_run"], 5)
        self.assertEqual(len(parsed["failed_tests"]), 2)


class TestRestoreTests(unittest.TestCase):
    def test_discover_test_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_text(repo / "tests" / "test_a.py", "def test_a():\n    pass\n")
            write_text(repo / "src" / "code.py", "x = 1\n")
            self.assertEqual(discover_test_paths(repo), ["tests"])

    def test_restore_paths_copies_pristine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pristine = copy_tree(FIXTURE, root / "pristine")
            tree = copy_tree(FIXTURE, root / "tree")
            (tree / "tests" / "test_dateutils.py").write_text("# saboté\n", encoding="utf-8")
            restored = restore_paths(pristine, tree, ["tests"])
            self.assertEqual(restored, ["tests"])
            self.assertNotIn("# saboté", (tree / "tests" / "test_dateutils.py").read_text(encoding="utf-8"))
            self.assertIn("class ParseRfc3339Tests", (tree / "tests" / "test_dateutils.py").read_text())


if __name__ == "__main__":
    unittest.main()
