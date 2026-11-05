"""Test E2E de la mécanique CLI en dry-run : fix → pack → verify (aucun appel modèle)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
FIXTURE = PKG / "examples" / "fixture"
ORACLE = "python -m unittest discover -s tests -v"


def _run(*args: str, cwd: Path = PKG) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "swarmproof", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=180,
    )


class DryRunCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-cli-test-"))
        self.pack = self.tmp / "pack"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_fix_then_verify(self):
        fixed = _run(
            "fix",
            str(FIXTURE),
            "--oracle",
            ORACLE,
            "--out",
            str(self.pack),
            "--dry-run",
        )
        self.assertEqual(fixed.returncode, 0, fixed.stderr + fixed.stdout)
        self.assertTrue((self.pack / "manifest.sha256").is_file())
        self.assertTrue((self.pack / "run.json").is_file())
        self.assertTrue((self.pack / "source" / "src" / "dateutils.py").is_file())
        self.assertIn("DRY-RUN", (self.pack / "report.md").read_text(encoding="utf-8"))

        verified = _run("verify", str(self.pack))
        self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)
        self.assertIn("PACK COHÉRENT", verified.stdout)
        self.assertNotIn("RESULTAT            : PACK VALIDE", verified.stdout)
        self.assertEqual(verified.returncode, 0)

    def test_verify_detects_tampered_pack(self):
        fixed = _run("fix", str(FIXTURE), "--oracle", ORACLE, "--out", str(self.pack), "--dry-run")
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        report = self.pack / "report.md"
        report.write_text(report.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")
        verified = _run("verify", str(self.pack))
        self.assertEqual(verified.returncode, 1)
        self.assertIn("ALTÉRÉ/INVALIDE", verified.stdout)

    def test_version(self):
        result = _run("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("swarmproof", result.stdout)

    def test_refuses_non_empty_out_without_force(self):
        self.pack.mkdir(parents=True)
        (self.pack / "existing.txt").write_text("x", encoding="utf-8")
        result = _run("fix", str(FIXTURE), "--oracle", ORACLE, "--out", str(self.pack), "--dry-run")
        self.assertEqual(result.returncode, 2)
        self.assertIn("n'est pas vide", result.stderr)

    def test_missing_repo_is_usage_error(self):
        result = _run("fix", str(self.tmp / "nope"), "--oracle", ORACLE, "--out", str(self.pack), "--dry-run")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
