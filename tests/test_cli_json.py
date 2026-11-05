"""Tests v0.2 : sortie --json, codes retour et ergonomie CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
FIXTURE = PKG / "examples" / "fixture"
ORACLE = "python -m unittest discover -s tests -v"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "swarmproof", *args],
        cwd=str(PKG),
        capture_output=True,
        text=True,
        timeout=180,
    )


class JsonOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-json-test-"))
        self.pack = self.tmp / "pack"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_json_is_machine_readable(self):
        result = _run("fix", str(FIXTURE), "--oracle", ORACLE, "--out", str(self.pack), "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool"], "swarmproof")
        self.assertEqual(payload["verdict"], "DRY_RUN")
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["exit_code"], 0)
        self.assertIn("pack", payload)
        self.assertTrue(Path(payload["pack"]["dir"]).is_dir())

    def test_json_usage_error_exit_2(self):
        result = _run("fix", str(self.tmp / "missing"), "--oracle", ORACLE, "--out", str(self.pack), "--json")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["exit_code"], 2)

    def test_verify_json(self):
        fixed = _run("fix", str(FIXTURE), "--oracle", ORACLE, "--out", str(self.pack), "--dry-run")
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        verified = _run("verify", str(self.pack), "--json")
        self.assertEqual(verified.returncode, 0, verified.stderr)
        payload = json.loads(verified.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["recorded_verdict"], "DRY_RUN")
        self.assertEqual(payload["label"], "PACK COHERENT")
        self.assertEqual(payload["exit_code"], 0)

    def test_verify_tampered_exit_1_json(self):
        fixed = _run("fix", str(FIXTURE), "--oracle", ORACLE, "--out", str(self.pack), "--dry-run")
        self.assertEqual(fixed.returncode, 0)
        (self.pack / "report.md").write_text("tampered", encoding="utf-8")
        verified = _run("verify", str(self.pack), "--json")
        self.assertEqual(verified.returncode, 1)
        self.assertFalse(json.loads(verified.stdout)["ok"])

    def test_help_mentions_new_options(self):
        result = _run("fix", "--help")
        self.assertEqual(result.returncode, 0)
        for option in ("--max-retries", "--max-calls", "--oracle-timeout", "--json", "--dry-run"):
            self.assertIn(option, result.stdout)


if __name__ == "__main__":
    unittest.main()
