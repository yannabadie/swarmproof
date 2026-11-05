"""Tests de sécurité v0.2 — régressions red team (oracle contourné, verify RCE, secrets).

Ces tests couvrent les 3 vulnérabilités critiques trouvées sur la v0.1 :
1. oracle contournable par `os._exit(0)` (exit 0 sans tests) ;
2. `verify` qui exécute une commande arbitraire d'un pack non fiable / chemins `../` ;
3. fuite de secrets et de chemins absolus dans le pack.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from swarmproof.oracle import run_oracle
from swarmproof.pack import build_manifest, verify_pack, write_pack
from swarmproof.util import copy_tree, iter_all_files, write_text

PKG = Path(__file__).resolve().parents[1]
FIXTURE = PKG / "examples" / "fixture"


def _minimal_ctx(root: Path, *, dry_run: bool = False, command: str = "python -m unittest discover -s tests -v") -> dict:
    pristine = root / "pristine"
    tree = root / "tree"
    write_text(pristine / "src" / "code.py", "def value():\n    return 1\n")
    copy_tree(pristine, tree)
    write_text(tree / "src" / "code.py", "def value():\n    return 2\n")
    return {
        "tool_version": "0.2.0",
        "generated_at": "2026-11-05T00:00:00+00:00",
        "command": "swarmproof fix (test)",
        "dry_run": dry_run,
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
        "retries": 0,
        "call_budget": {"max_calls": 6, "used": 2, "remaining": 4, "exhausted_events": 0},
        "candidates": [],
        "candidate_sets_found": 0,
        "rejected_candidates": [],
        "attempts": [],
        "oracle": {
            "command": command,
            "timeout_seconds": 30,
            "verdict_passed": True,
            "execution_verified": True,
            "tests_run": 1,
            "failed_tests": [],
            "restored_test_paths": [],
        },
        "verdict": "PASS",
        "verdict_basis": "oracle",
        "verdict_reason": "test",
        "verdict_explain": [],
        "changed_files": ["src/code.py"],
        "diff": "--- a/src/code.py\n+++ b/src/code.py\n",
        "mapping": {"targets": ["src/code.py"]},
        "prepack": None,
        "pristine": pristine,
        "tree": tree,
        "trace_events": [{"event": "run_start"}],
        "exit_code": 0,
        "limits": ["test"],
    }


class OracleBypassTests(unittest.TestCase):
    """FIX 1 : exit 0 nu ne doit jamais être un PASS."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-bypass-"))
        self.repo = self.tmp / "repo"
        write_text(self.repo / "tests" / "__init__.py", "")
        write_text(
            self.repo / "tests" / "test_hijack.py",
            "import os\n\nos._exit(0)  # contournement : sort avant d'exécuter les tests\n",
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_os_exit_zero_is_not_pass(self):
        result = run_oracle(self.repo, "python -m unittest discover -s tests -v", 30)
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["passed"], "exit 0 sans tests ne doit jamais être PASS")
        self.assertFalse(result["execution_verified"])
        self.assertIn("preuve d'exécution", result["evidence_reason"])

    def test_normal_run_is_verified(self):
        write_text(self.repo / "tests" / "test_hijack.py", "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        result = run_oracle(self.repo, "python -m unittest discover -s tests -v", 30)
        self.assertTrue(result["passed"])
        self.assertTrue(result["execution_verified"])
        self.assertEqual(result["tests_run"], 1)


class VerifySecurityTests(unittest.TestCase):
    """FIX 2 : verify n'exécute aucun script par défaut ; refuse traversées et fichiers cachés."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-verifysec-"))
        self.pack = self.tmp / "pack"
        write_pack(self.pack, _minimal_ctx(self.tmp, command="python -m unittest discover -s tests -v"))
        self.marker = self.tmp / "RCE_MARKER"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _resign(self) -> None:
        (self.pack / "manifest.sha256").write_text(build_manifest(self.pack), encoding="utf-8")

    def _install_malicious_command(self, command: str) -> None:
        run_path = self.pack / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["oracle"]["command"] = command
        run_path.write_text(json.dumps(run, indent=2), encoding="utf-8")
        self._resign()

    def test_verify_does_not_execute_pack_command_by_default(self):
        self._install_malicious_command(f"touch {self.marker} && true")
        result = verify_pack(self.pack)
        self.assertFalse(self.marker.exists(), "verify a exécuté une commande de pack non fiable !")
        self.assertIsNone(result["replay"])
        self.assertIn("non exécuté", " ".join(result["warnings"]))
        self.assertFalse(result["origin_proven"])

    def test_allow_oracle_cmd_refuses_shell_metacharacters(self):
        self._install_malicious_command(f"touch {self.marker} && true")
        result = verify_pack(self.pack, replay=True, allow_oracle_cmd=True)
        self.assertFalse(self.marker.exists(), "commande shell composée exécutée malgré le refus")
        self.assertTrue(any("métacaractères" in error for error in result["errors"]))

    def test_manifest_path_traversal_rejected(self):
        manifest = self.pack / "manifest.sha256"
        lines = manifest.read_text(encoding="utf-8").splitlines()
        lines.append("0" * 64 + "  ../outside.py")
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_pack(self.pack)
        self.assertFalse(result["manifest_ok"])
        self.assertTrue(any("traversée" in error for error in result["errors"]))

    def test_unlisted_hidden_file_rejected(self):
        write_text(self.pack / ".hidden_backdoor", "x")
        result = verify_pack(self.pack, replay=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("non listé" in error for error in result["errors"]))

    def test_invalid_run_json_is_handled(self):
        (self.pack / "run.json").write_text("{invalid json", encoding="utf-8")
        self._resign()
        result = verify_pack(self.pack)
        self.assertFalse(result["ok"])
        self.assertTrue(any("JSON invalide" in error for error in result["errors"]))

    def test_resigned_pack_is_integrity_only_not_origin_proof(self):
        (self.pack / "report.md").write_text("réécrit", encoding="utf-8")
        self._resign()
        result = verify_pack(self.pack)
        self.assertTrue(result["ok"], result["errors"])
        self.assertFalse(result["origin_proven"])
        self.assertEqual(result["integrity_scope"], "coherence_interne_auto_attestee")


class SecretAndPathHygieneTests(unittest.TestCase):
    """FIX 3 : secrets exclus/redactés, chemins absolus neutralisés dans le pack."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-secrets-"))
        self.repo = self.tmp / "repo"
        write_text(self.repo / "src" / "code.py", "TOKEN = 'sk-ant-abcdefghijklmnopqrstuvwxyz0123'\n")
        write_text(self.repo / ".env", "ANTHROPIC_API_KEY=sk-ant-secretsecretsecretsecret\n")
        write_text(self.repo / "deploy" / "server.pem", "-----BEGIN PRIVATE KEY-----\nxxx\n-----END PRIVATE KEY-----\n")
        ctx = _minimal_ctx(self.tmp)
        ctx["repo"]["source_path"] = str(self.repo)
        ctx["pristine"] = copy_tree(self.repo, self.tmp / "pack-pristine")
        ctx["tree"] = copy_tree(self.repo, self.tmp / "pack-tree")
        self.pack = self.tmp / "pack"
        write_pack(self.pack, ctx)
        self.manifest = (self.pack / "manifest.sha256").read_text(encoding="utf-8")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_secret_named_files_are_excluded(self):
        copied = {str(path.relative_to(self.pack)).replace("\\", "/") for path in iter_all_files(self.pack)}
        self.assertFalse(any(name.endswith(".env") for name in copied), copied)
        self.assertFalse(any(name.endswith(".pem") for name in copied), copied)

    def test_inline_secret_is_redacted_and_not_in_manifest_ok(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8", errors="replace") for path in iter_all_files(self.pack)
        )
        self.assertNotIn("sk-ant-abcdefghijklmnopqrstuvwxyz0123", combined)
        self.assertIn("[REDACTED_SECRET]", combined)

    def test_absolute_paths_are_sanitized_in_metadata(self):
        report = (self.pack / "report.md").read_text(encoding="utf-8")
        run = (self.pack / "run.json").read_text(encoding="utf-8")
        self.assertNotIn(str(Path.home()), report + run)
        self.assertNotIn(str(self.repo), report + run)


class TargetValidationCliTests(unittest.TestCase):
    """FIX bonus : --target borné au dépôt, jamais un test, jamais de traversée."""

    def _run(self, *extra: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            return subprocess.run(
                [
                    sys.executable, "-m", "swarmproof", "fix", str(FIXTURE),
                    "--oracle", "python -m unittest", "--out", str(Path(tmp) / "pack"),
                    "--dry-run", "--json", *extra,
                ],
                cwd=str(PKG), capture_output=True, text=True, timeout=120,
            )

    def test_traversal_target_rejected(self):
        result = self._run("--target", "../evil.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("..", result.stdout + result.stderr)

    def test_absolute_target_rejected(self):
        result = self._run("--target", "/etc/passwd.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("relatif", result.stdout + result.stderr)

    def test_test_file_as_target_rejected(self):
        result = self._run("--target", "tests/test_dateutils.py")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
