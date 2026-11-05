"""Tests v0.2 : verdicts PASS / FAIL / INCONCLUSIVE (jamais de PASS silencieux)."""

from __future__ import annotations

import unittest

from swarmproof.verdict import (
    VERDICT_DRY_RUN,
    VERDICT_FAIL,
    VERDICT_INCONCLUSIVE,
    VERDICT_PASS,
    compute_verdict,
)


class VerdictTests(unittest.TestCase):
    def test_pass_when_oracle_passes(self):
        result = compute_verdict(attempts=[{"attempt": 0, "passed": True, "timed_out": False}])
        self.assertEqual(result["verdict"], VERDICT_PASS)
        self.assertEqual(result["basis"], "oracle")

    def test_fail_when_oracle_genuinely_fails(self):
        result = compute_verdict(attempts=[{"attempt": 0, "passed": False, "timed_out": False}])
        self.assertEqual(result["verdict"], VERDICT_FAIL)

    def test_inconclusive_when_engine_errors_and_no_candidate(self):
        result = compute_verdict(
            attempts=[],
            engine_errors=[{"role": "lead", "error": "timeout après 90s"}],
            agent_calls_ok=0,
        )
        self.assertEqual(result["verdict"], VERDICT_INCONCLUSIVE)
        self.assertEqual(result["basis"], "infrastructure")
        self.assertIn("échec définitif", result["reason"])

    def test_inconclusive_when_budget_exhausted(self):
        result = compute_verdict(
            attempts=[],
            engine_errors=[{"role": "support", "error": "budget épuisé"}],
            agent_calls_ok=1,
            budget_exhausted=True,
        )
        self.assertEqual(result["verdict"], VERDICT_INCONCLUSIVE)
        self.assertIn("budget", result["reason"])

    def test_inconclusive_on_oracle_timeout(self):
        result = compute_verdict(attempts=[{"attempt": 0, "passed": False, "timed_out": True}])
        self.assertEqual(result["verdict"], VERDICT_INCONCLUSIVE)
        self.assertIn("timeout", result["reason"])

    def test_inconclusive_when_no_usable_candidate(self):
        result = compute_verdict(attempts=[], agent_calls_ok=1, candidate_sets_found=0, rejected_candidate_sets=2)
        self.assertEqual(result["verdict"], VERDICT_INCONCLUSIVE)
        self.assertIn("rejet", result["reason"])

    def test_dry_run_never_passes(self):
        result = compute_verdict(dry_run=True, attempts=[{"attempt": 0, "passed": True}])
        self.assertEqual(result["verdict"], VERDICT_DRY_RUN)
        self.assertEqual(result["basis"], "simulated")

    def test_engine_declared_status_is_not_an_input(self):
        # Aucun paramètre « statut moteur » : seul l'oracle peut produire PASS.
        result = compute_verdict(attempts=[], engine_errors=[{"role": "lead", "error": "boom"}])
        self.assertNotEqual(result["verdict"], VERDICT_PASS)


if __name__ == "__main__":
    unittest.main()
