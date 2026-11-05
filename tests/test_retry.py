"""Tests v0.2 : budget d'appels, retry infra borné, échecs définitifs explicites."""

from __future__ import annotations

import unittest

from swarmproof.drivers import CLICallError
from swarmproof.retry import CallBudget, invoke_with_retries, is_retryable_error
from swarmproof.trace import TraceWriter


class _ScriptedDriver:
    """Driver factice : échoue N fois puis réussit (ou échoue toujours)."""

    provider = "fake"

    def __init__(self, failures: int, error: str = "timeout après 1s") -> None:
        self.failures = failures
        self.error = error
        self.records = []
        self.invocations = 0

    def invoke(self, prompt: str, role: str) -> str:
        self.invocations += 1
        if self.invocations <= self.failures:
            self.records.append(type("R", (), {"to_dict": lambda self: {"role": role, "provider": "fake", "error": self.error}})())
            raise CLICallError(self.error)
        self.records.append(type("R", (), {"to_dict": lambda self: {"role": role, "provider": "fake", "error": None}})())
        return "ok"


class RetryableErrorTests(unittest.TestCase):
    def test_timeout_is_retryable(self):
        self.assertTrue(is_retryable_error("timeout après 90s"))
        self.assertTrue(is_retryable_error("exit=1: safeguard"))
        self.assertTrue(is_retryable_error("Rate limit exceeded"))

    def test_no_message_is_not_retryable(self):
        self.assertFalse(is_retryable_error(None))
        self.assertFalse(is_retryable_error(""))


class CallBudgetTests(unittest.TestCase):
    def test_consume_and_exhaust(self):
        budget = CallBudget(max_calls=2)
        self.assertTrue(budget.try_consume("lead"))
        self.assertTrue(budget.try_consume("support"))
        self.assertFalse(budget.try_consume("support"))
        self.assertEqual(budget.used, 2)
        self.assertEqual(budget.exhausted_events, 1)
        self.assertEqual(budget.to_dict()["remaining"], 0)


class InvokeWithRetriesTests(unittest.TestCase):
    def _run(self, driver, retries, budget=None):
        trace = TraceWriter()
        budget = budget or CallBudget(max_calls=10)
        return invoke_with_retries(driver, "prompt", "lead", max_retries=retries, budget=budget, trace=trace), trace, budget

    def test_success_without_retry(self):
        driver = _ScriptedDriver(failures=0)
        outcome, trace, budget = self._run(driver, retries=1)
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.attempts, 1)
        self.assertEqual(outcome.retries, 0)
        self.assertEqual(budget.used, 1)
        self.assertEqual(trace.count("model_call"), 2)  # start + ok

    def test_retry_once_then_success(self):
        driver = _ScriptedDriver(failures=1)
        outcome, trace, budget = self._run(driver, retries=1)
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.attempts, 2)
        self.assertEqual(outcome.retries, 1)
        self.assertEqual(budget.used, 2)
        self.assertEqual(trace.count("call_retry"), 1)

    def test_no_retry_when_disabled(self):
        driver = _ScriptedDriver(failures=1)
        outcome, _, budget = self._run(driver, retries=0)
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.attempts, 1)
        self.assertEqual(budget.used, 1)

    def test_definitive_failure_is_explicit(self):
        driver = _ScriptedDriver(failures=5)
        outcome, _, _ = self._run(driver, retries=1)
        self.assertFalse(outcome.ok)
        self.assertIn("timeout", outcome.error or "")
        self.assertEqual(len(outcome.retry_errors), 2)

    def test_budget_exhaustion_blocks_calls(self):
        driver = _ScriptedDriver(failures=999)
        budget = CallBudget(max_calls=1)
        outcome, trace, budget = self._run(driver, retries=3, budget=budget)
        self.assertFalse(outcome.ok)
        self.assertTrue(outcome.budget_exhausted)
        self.assertEqual(budget.used, 1)
        self.assertEqual(driver.invocations, 1)
        self.assertEqual(trace.count("call_budget_exhausted"), 1)


if __name__ == "__main__":
    unittest.main()
