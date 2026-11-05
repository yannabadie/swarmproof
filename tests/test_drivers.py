"""Tests des drivers CLI : parsing, journal d'appels, simulation, erreurs."""

from __future__ import annotations

import unittest
from unittest import mock

from swarmproof.drivers import CLICallError, CLIDriver, FakeDriver, extract_codex_tokens


class ClaudeJsonParsingTests(unittest.TestCase):
    def setUp(self):
        self.driver = CLIDriver("claude", timeout=5)

    def test_extracts_result_and_usage(self):
        payload = (
            '{"type":"result","subtype":"success","is_error":false,"result":"hello",'
            '"total_cost_usd":0.0123,"usage":{"input_tokens":10,"output_tokens":5},'
            '"model":"claude-x"}'
        )
        text, error = self.driver._extract_text(payload, None)
        self.assertEqual(text, "hello")
        self.assertIsNone(error)
        usage = self.driver._extract_usage(payload)
        self.assertEqual(usage["tokens_in"], 10)
        self.assertEqual(usage["tokens_out"], 5)
        self.assertEqual(usage["cost_usd"], 0.0123)
        self.assertEqual(self.driver._extract_model(payload), "claude-x")

    def test_provider_refusal_is_reported(self):
        payload = '{"type":"result","is_error":true,"result":"API Error: safeguards flagged"}'
        text, error = self.driver._extract_text(payload, None)
        self.assertIn("safeguards", text)
        self.assertIsNotNone(error)
        self.assertIn("refus", error)

    def test_plain_text_fallback(self):
        text, error = self.driver._extract_text("pas du json", None)
        self.assertEqual(text, "pas du json")
        self.assertIsNone(error)


class CodexTokenCaptureTests(unittest.TestCase):
    def test_parses_tokens_used_line(self):
        self.assertEqual(extract_codex_tokens("...\ntokens used: 12,345\n"), 12345)
        self.assertEqual(extract_codex_tokens("Tokens used: 987"), 987)
        self.assertEqual(extract_codex_tokens("tokens  used:  1 234"), 1234)

    def test_parses_multiline_and_separators(self):
        self.assertEqual(extract_codex_tokens("tokens used:\n 7 890\n"), 7890)
        self.assertEqual(extract_codex_tokens("tokens used — 1.234"), 1234)
        self.assertEqual(extract_codex_tokens("total tokens: 99"), 99)
        self.assertEqual(extract_codex_tokens("tokens consumed 2 500"), 2500)

    def test_ids_in_other_numbers_do_not_confuse_parser(self):
        self.assertEqual(extract_codex_tokens("run 12345; tokens used: 456"), 456)

    def test_returns_none_when_absent(self):
        self.assertIsNone(extract_codex_tokens("aucune information de tokens"))
        self.assertIsNone(extract_codex_tokens(""))


class CodexCliIntegrationTests(unittest.TestCase):
    """R3 : capture des tokens via le vrai chemin subprocess (shim CLI, aucun appel modèle)."""

    def test_cli_codex_token_line_is_captured(self):
        import os
        import stat
        import tempfile
        from pathlib import Path as _Path
        from unittest import mock

        with tempfile.TemporaryDirectory(prefix="codex-shim-") as tmp:
            shim = _Path(tmp) / "codex"
            shim.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "argv = sys.argv\n"
                "try:\n"
                "    out = argv[argv.index('--output-last-message') + 1]\n"
                "except ValueError:\n"
                "    out = None\n"
                "if out:\n"
                "    open(out, 'w').write('NEXUS_R3_OK')\n"
                "sys.stderr.write('work...\\ntokens used: 12,345\\n')\n"
                "sys.exit(0)\n",
                encoding="utf-8",
            )
            shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
            driver = CLIDriver("codex", timeout=10)
            path_env = f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}"
            with mock.patch.dict(os.environ, {"PATH": path_env}), mock.patch(
                "swarmproof.drivers.shutil.which", return_value=str(shim)
            ):
                output = driver.invoke("prompt", role="lead")
            self.assertIn("NEXUS_R3_OK", output)
            self.assertEqual(driver.records[-1].tokens_total, 12345)
            self.assertEqual(driver.records[-1].to_dict()["tokens_total"], 12345)


class InvocationTests(unittest.TestCase):
    def test_missing_binary_records_error(self):
        driver = CLIDriver("codex", timeout=5)
        with mock.patch("swarmproof.drivers.shutil.which", return_value=None):
            with self.assertRaises(CLICallError):
                driver.invoke("prompt", role="lead")
        self.assertEqual(len(driver.records), 1)
        self.assertIn("absent du PATH", driver.records[0].error)

    def test_fake_driver_records_call(self):
        driver = FakeDriver("lead", "```python\ndef f():\n    return 1\n```")
        output = driver.invoke("prompt", role="lead")
        self.assertIn("def f", output)
        records = [record.to_dict() for record in driver.records]
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]["simulated"])
        self.assertEqual(records[0]["role"], "lead")
        self.assertEqual(len(records[0]["prompt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
