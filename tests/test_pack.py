"""Tests de l'Evidence Pack : manifeste, vérification, falsification."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swarmproof.pack import verify_pack, write_pack
from swarmproof.util import copy_tree, sha256_file, write_text


def _minimal_ctx(root: Path) -> dict:
    pristine = root / "pristine"
    tree = root / "tree"
    write_text(pristine / "src" / "code.py", "def value():\n    return 1\n")
    copy_tree(pristine, tree)
    write_text(tree / "src" / "code.py", "def value():\n    return 2\n")
    return {
        "tool_version": "0.1.0",
        "generated_at": "2026-11-05T00:00:00+00:00",
        "command": "swarmproof fix (test)",
        "dry_run": True,
        "environment": {"python": "3.11"},
        "repo": {"name": "unit", "source_path": str(pristine), "commit": None},
        "mode": "lead_support",
        "roles": {"lead": "claude", "support": "codex"},
        "engine": {
            "version": {"version": "12.4.0"},
            "declared_status": "SwarmPhase.COMPLETED",
            "selected_mode": "lead_support",
            "engine_ok": True,
            "errors": [],
            "outputs": [],
            "analysis": {"complexity": "SIMPLE", "domains": []},
        },
        "calls": [],
        "candidates": [],
        "attempts": [],
        "oracle": {
            "command": "python -m unittest",
            "timeout_seconds": 30,
            "verdict_passed": True,
            "simulated": True,
            "tests_run": 1,
            "failed_tests": [],
            "restored_test_paths": [],
        },
        "verdict": "DRY_RUN",
        "changed_files": ["src/code.py"],
        "diff": "--- a/src/code.py\n+++ b/src/code.py\n",
        "mapping": {"targets": ["src/code.py"]},
        "prepack": None,
        "pristine": pristine,
        "tree": tree,
        "trace_events": [{"event": "run_start"}],
        "limits": ["test"],
    }


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-pack-test-"))
        self.pack = self.tmp / "pack"
        self.written = write_pack(self.pack, _minimal_ctx(self.tmp))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_required_files(self):
        for name in (
            "report.md",
            "run.json",
            "trace.jsonl",
            "oracle.jsonl",
            "diff.patch",
            "mapping.json",
            "manifest.sha256",
            "README.txt",
        ):
            self.assertTrue((self.pack / name).is_file(), name)
        self.assertTrue((self.pack / "source").is_dir())
        self.assertTrue((self.pack / "tree").is_dir())

    def test_manifest_format_is_shasum_compatible(self):
        lines = (self.pack / "manifest.sha256").read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines)
        for line in lines:
            digest, separator, rel = line.partition("  ")
            self.assertEqual(separator, "  ")
            self.assertEqual(len(digest), 64)
            self.assertTrue((self.pack / rel).is_file(), rel)

    def test_verify_ok(self):
        result = verify_pack(self.pack, replay=False)
        self.assertTrue(result["manifest_ok"], result["errors"])
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["recorded_verdict"], "DRY_RUN")

    def test_verify_detects_tampered_file(self):
        target = self.pack / "report.md"
        target.write_text(target.read_text(encoding="utf-8") + "\nfalsification\n", encoding="utf-8")
        result = verify_pack(self.pack, replay=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("hash invalide" in error for error in result["errors"]))

    def test_verify_detects_missing_file(self):
        (self.pack / "oracle.jsonl").unlink()
        result = verify_pack(self.pack, replay=False)
        self.assertFalse(result["ok"])

    def test_verify_detects_unlisted_file(self):
        write_text(self.pack / "injected.txt", "fichier non prévu")
        result = verify_pack(self.pack, replay=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("non listé" in error for error in result["errors"]))

    def test_sha256_file_matches_manifest_entry(self):
        digest = sha256_file(self.pack / "run.json")
        self.assertIn(digest, (self.pack / "manifest.sha256").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
