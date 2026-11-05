"""Test du pré-pack statique optionnel AgentProof (ignoré si le paquet est absent)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from swarmproof.prepack import find_agentproof, run_prepack
from swarmproof.util import copy_tree

PKG = Path(__file__).resolve().parents[1]
FIXTURE = PKG / "examples" / "fixture"
AGENTPROOF_DIR, _ = find_agentproof()


@unittest.skipUnless(AGENTPROOF_DIR is not None, "paquet agentproof absent")
class PrepackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-prepack-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_prepack_produces_agentproof_pack(self):
        repo = copy_tree(FIXTURE, self.tmp / "repo")
        summary = run_prepack(repo, self.tmp / "out")
        self.assertEqual(summary["status"], "ok", summary)
        self.assertEqual(summary["tool"], "agentproof")
        pack_dir = Path(summary["pack_dir"])
        self.assertTrue(pack_dir.is_dir())
        self.assertTrue((pack_dir / "manifest.sha256").is_file())
        self.assertEqual(len(summary["manifest_sha256"]), 64)
        self.assertIsNotNone(summary["score"])

    def test_prepack_is_never_blocking_when_agentproof_broken(self):
        # Un run_prepack sur un dépôt inexistant doit retourner un statut d'échec, pas lever.
        summary = run_prepack(self.tmp / "missing-repo", self.tmp / "out2")
        self.assertIn(summary["status"], {"error", "not_run"})


if __name__ == "__main__":
    unittest.main()
