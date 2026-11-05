"""Tests R1 : libellé et code retour de `verify` (cohérent vs valide vs altéré)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swarmproof.pack import build_manifest, verify_pack, write_pack
from swarmproof.util import copy_tree, write_text


def _replayable_ctx(root: Path) -> dict:
    """Pack non-dry-run dont le rejeu oracle est réellement exécutable."""
    pristine = root / "pristine"
    write_text(pristine / "src" / "value.py", "VALUE = 1\n")
    write_text(pristine / "tests" / "__init__.py", "")
    write_text(pristine / "tests" / "test_value.py", "import unittest\nfrom src.value import VALUE\n\nclass T(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(VALUE, 2)\n")
    tree = copy_tree(pristine, root / "tree")
    write_text(tree / "src" / "value.py", "VALUE = 2\n")
    return {
        "tool_version": "0.2.1",
        "generated_at": "2026-11-05T00:00:00+00:00",
        "command": "swarmproof fix (test)",
        "dry_run": False,
        "environment": {"python": "3.11"},
        "repo": {"name": "unit", "source_path": str(pristine), "commit": None},
        "mode": "lead_support",
        "roles": {"lead": "claude", "support": "codex"},
        "engine": {"version": {"version": "12.4.0"}, "declared_status": "SwarmPhase.COMPLETED",
                   "selected_mode": "lead_support", "engine_ok": True, "errors": [], "outputs": [],
                   "analysis": {"complexity": "SIMPLE", "domains": []}},
        "calls": [], "retries": 0,
        "call_budget": {"max_calls": 6, "used": 2, "remaining": 4, "exhausted_events": 0},
        "candidates": [], "candidate_sets_found": 1, "rejected_candidates": [],
        "attempts": [],
        "oracle": {"command": "python -m unittest discover -s tests -v", "timeout_seconds": 60,
                   "verdict_passed": True, "execution_verified": True,
                   "evidence_reason": "preuve d'exécution: unittest, 1 test(s)",
                   "test_parser": "unittest", "tests_run": 1, "failed_tests": [],
                   "restored_test_paths": ["tests"]},
        "verdict": "PASS", "verdict_basis": "oracle", "verdict_reason": "oracle PASS", "verdict_explain": [],
        "changed_files": ["src/value.py"], "diff": "", "mapping": {"targets": ["src/value.py"]},
        "prepack": None, "pristine": pristine, "tree": tree, "trace_events": [{"event": "run_start"}],
        "exit_code": 0, "limits": ["test"],
    }


class VerifyLabelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-label-test-"))
        self.pack = self.tmp / "pack"
        write_pack(self.pack, _replayable_ctx(self.tmp))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_verify_is_coherent_not_valid(self):
        result = verify_pack(self.pack)
        self.assertEqual(result["label"], "PACK COHERENT")
        self.assertFalse(result["verdict_replayed"])
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("NON rejoué", result["label_detail"])

    def test_replay_success_is_valid(self):
        result = verify_pack(self.pack, replay=True, allow_oracle_cmd=True)
        self.assertTrue(result["replay"]["executed"])
        self.assertTrue(result["replay"]["match"])
        self.assertEqual(result["label"], "PACK VALIDE")
        self.assertEqual(result["exit_code"], 0)

    def test_tampered_pack_is_invalid_exit_1(self):
        (self.pack / "report.md").write_text("falsifié", encoding="utf-8")
        result = verify_pack(self.pack)
        self.assertEqual(result["label"], "PACK ALTERE/INVALIDE")
        self.assertEqual(result["exit_code"], 1)

    def test_resigned_tampered_pack_is_only_coherent(self):
        (self.pack / "report.md").write_text("forgé", encoding="utf-8")
        (self.pack / "manifest.sha256").write_text(build_manifest(self.pack), encoding="utf-8")
        result = verify_pack(self.pack)
        self.assertEqual(result["label"], "PACK COHERENT")
        self.assertFalse(result["origin_proven"])

    def test_json_output_carries_label(self):
        result = verify_pack(self.pack)
        payload = json.loads(json.dumps(result))
        self.assertIn("label", payload)
        self.assertEqual(payload["label"], "PACK COHERENT")


class ReadmeConsistencyTests(unittest.TestCase):
    """R3 : le README ne doit plus annoncer 73 tests et doit porter la limite d'origine."""

    def setUp(self):
        self.readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")

    def test_readme_announces_87_tests(self):
        self.assertIn("97 tests", self.readme)
        self.assertNotIn("73 tests", self.readme)

    def test_readme_header_states_no_origin_proof(self):
        head = self.readme[:2500]
        self.assertIn("preuve technique de cohérence interne", head)
        self.assertIn("pas d'origine", head)
        self.assertIn("non opposable", head)


if __name__ == "__main__":
    unittest.main()
