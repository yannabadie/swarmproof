"""Tests d'intégration du VRAI moteur NEXUS avec drivers simulés (zéro appel API).

Prouve deux choses héritées de l'audit :
1. le moteur NEXUS original s'exécute vraiment via `invoke_agent` dans le produit ;
2. le produit NE croit PAS son statut : un agent en échec est exposé (`engine_ok=false`)
   même quand le moteur rapporte `COMPLETED`.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swarmproof import candidates as candidates_mod
from swarmproof import engine as engine_mod
from swarmproof.drivers import FakeDriver
from swarmproof.oracle import discover_test_paths, prepare_eval_tree, run_oracle
from swarmproof.trace import TraceWriter
from swarmproof.util import copy_tree

PKG = Path(__file__).resolve().parents[1]
FIXTURE = PKG / "examples" / "fixture"
MULTI_FIXTURE = PKG / "examples" / "fixture-multi"
ORACLE = "python -m unittest discover -s tests -v"

BUGGY = (FIXTURE / "src" / "dateutils.py").read_text(encoding="utf-8")
FIXED = BUGGY.replace(
    "from datetime import date, datetime, timedelta",
    "from datetime import date, datetime, timedelta, timezone",
).replace(
    "    # BUG: the timezone offset is silently dropped instead of being converted.\n    return datetime.fromisoformat(text).replace(tzinfo=None)",
    "    parsed = datetime.fromisoformat(text)\n    return parsed.astimezone(timezone.utc).replace(tzinfo=None)",
)


def _nexus_available() -> bool:
    return engine_mod.find_nexus_src() is not None


class _RaisingDriver:
    """Driver qui simule un refus fournisseur (comme le safeguard observé en E2E)."""

    provider = "failing"

    def __init__(self) -> None:
        self.records: list = []

    def invoke(self, prompt: str, role: str) -> str:
        raise RuntimeError("refus fournisseur simulé (safeguard)")


class EngineFactsTests(unittest.TestCase):
    def test_engine_status_is_not_trusted(self):
        outputs = [
            {"agent_id": "lead_agent", "role": "lead", "status": "error", "error": "refus"},
            {"agent_id": "support_agent", "role": "support", "status": "success", "error": None},
        ]
        facts = engine_mod.summarize_engine(outputs, "SwarmPhase.COMPLETED")
        self.assertFalse(facts["engine_ok"])
        self.assertTrue(facts["declared_completed"])
        self.assertEqual(len(facts["errors"]), 1)

    def test_clean_run_is_ok(self):
        outputs = [
            {"agent_id": "lead_agent", "role": "lead", "status": "success", "error": None},
        ]
        facts = engine_mod.summarize_engine(outputs, "SwarmPhase.COMPLETED")
        self.assertTrue(facts["engine_ok"])
        self.assertEqual(facts["errors"], [])


@unittest.skipUnless(_nexus_available(), "dépôt swarm-os absent : test d'intégration moteur ignoré")
class RealEngineWithFakeDriversTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-engine-test-"))
        cls.pristine = copy_tree(FIXTURE, cls.tmp / "pristine")
        cls.targets = candidates_mod.detect_targets(cls.pristine)
        cls.test_paths = discover_test_paths(cls.pristine)
        cls.nexus_copy = engine_mod.ensure_nexus_copy(engine_mod.find_nexus_src())

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _build(self, drivers):
        trace = TraceWriter()
        return engine_mod.build_engine(
            self.nexus_copy, drivers, {"lead": "claude", "support": "codex"}, "lead_support", trace
        )

    def test_engine_runs_and_candidate_is_oracle_green(self):
        drivers = {
            "claude": FakeDriver("lead", "```python\n" + FIXED + "\n```"),
            "codex": FakeDriver("support", "Revue : le correctif du lead est cohérent."),
        }
        handle = self._build(drivers)
        task = engine_mod.build_task_text(self.pristine, self.targets, self.test_paths)
        result = engine_mod.run_mode(handle, task)
        facts = engine_mod.summarize_engine(result["outputs"], result["declared_status"])

        self.assertTrue(facts["engine_ok"])
        self.assertTrue(result["declared_status"].endswith("COMPLETED"))
        self.assertEqual(len(result["outputs"]), 2)
        self.assertTrue(all(output["status"] == "success" for output in result["outputs"]))
        self.assertEqual(len(drivers["claude"].records), 1)
        self.assertEqual(len(drivers["codex"].records), 1)

        blocks = candidates_mod.extract_code_blocks(result["outputs"][0]["content"])
        self.assertEqual(len(blocks), 1)
        target = candidates_mod.choose_target(
            blocks[0], {self.targets[0]: (self.pristine / self.targets[0]).read_text()}, preferred=self.targets
        )
        self.assertEqual(target, self.targets[0])
        tree = copy_tree(self.pristine, self.tmp / "candidate")
        candidates_mod.apply_candidate(tree, target, blocks[0])
        eval_tree, restored = prepare_eval_tree(self.pristine, tree, self.tmp / "judge", "engine")
        judged = run_oracle(eval_tree, ORACLE, 60)
        self.assertTrue(judged["passed"])
        self.assertIn("tests", restored)

    def test_agent_failure_is_exposed_even_if_engine_says_completed(self):
        drivers = {"claude": _RaisingDriver(), "codex": FakeDriver("support", "aucun correctif exploitable")}
        handle = self._build(drivers)
        task = engine_mod.build_task_text(self.pristine, self.targets, self.test_paths)
        result = engine_mod.run_mode(handle, task)
        facts = engine_mod.summarize_engine(result["outputs"], result["declared_status"])
        # Le moteur prétend avoir terminé, mais le produit expose l'échec.
        self.assertTrue(result["declared_status"].endswith("COMPLETED"))
        self.assertFalse(facts["engine_ok"])
        self.assertEqual(len(facts["errors"]), 1)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(_nexus_available(), "dépôt swarm-os absent : test d'intégration moteur ignoré")
class RealEngineMultiFileFakeDriversTests(unittest.TestCase):
    """Valide de bout en bout le flux multi-fichiers avec le vrai moteur (0 appel API)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="swarmproof-multi-engine-"))
        cls.pristine = copy_tree(MULTI_FIXTURE, cls.tmp / "pristine")
        cls.targets = candidates_mod.detect_targets(cls.pristine)
        cls.test_paths = discover_test_paths(cls.pristine)
        cls.nexus_copy = engine_mod.ensure_nexus_copy(engine_mod.find_nexus_src())
        store = (cls.pristine / "src" / "store.py").read_text(encoding="utf-8")
        cache = (cls.pristine / "src" / "cache.py").read_text(encoding="utf-8")
        fixed_store = store.replace(
            '        # BUG: le compteur de version n\'est jamais incrémenté -> les caches ne voient\n'
            "        # jamais de changement et servent des valeurs périmées.\n",
            "        self.version += 1\n",
        )
        fixed_cache = cache.replace(
            "            if key == prefix:",
            "            if key.startswith(prefix):",
        )
        assert fixed_store != store and fixed_cache != cache, "fixture fixes non appliqués"
        cls.answer = (
            f"--- FILE: src/store.py ---\n```python\n{fixed_store}```\n\n"
            f"--- FILE: src/cache.py ---\n```python\n{fixed_cache}```\n"
        )

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_engine_then_multifile_oracle_pass(self):
        drivers = {
            "claude": FakeDriver("lead", self.answer),
            "codex": FakeDriver("support", "Revue : les deux correctifs sont cohérents."),
        }
        trace = TraceWriter()
        handle = engine_mod.build_engine(
            self.nexus_copy, drivers, {"lead": "claude", "support": "codex"}, "lead_support", trace
        )
        task = engine_mod.build_task_text(self.pristine, self.targets, self.test_paths)
        self.assertIn("--- FILE:", task)  # consigne multi-fichiers envoyée aux agents
        result = engine_mod.run_mode(handle, task)
        facts = engine_mod.summarize_engine(result["outputs"], result["declared_status"])
        self.assertTrue(facts["engine_ok"])
        sets, rejections = candidates_mod.parse_candidate_sets(result["outputs"][0]["content"], self.targets)
        self.assertEqual(rejections, [])
        self.assertEqual(sets[0].n_files, 2)
        tree = copy_tree(self.pristine, self.tmp / "tree")
        written = candidates_mod.apply_candidate_set(tree, sets[0])
        self.assertEqual(sorted(written), ["src/cache.py", "src/store.py"])
        eval_tree, restored = prepare_eval_tree(self.pristine, tree, self.tmp / "judge", "multi")
        judged = run_oracle(eval_tree, ORACLE, 60)
        self.assertTrue(judged["passed"])
        self.assertEqual(judged["tests_run"], 4)
        self.assertIn("tests", restored)
