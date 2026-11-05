"""Drivers CLI hétérogènes (`claude -p`, `codex exec`) avec timeout et journal d'appels.

Chaque appel est tracé avec l'empreinte SHA-256 du prompt (jamais le prompt complet :
pas de fuite de contenu dans le pack). Le temps, le code retour et, si le CLI les expose,
les tokens et le coût notionnel sont conservés.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swarmproof.util import sha256_text

PROVIDERS = ("claude", "codex")


class CLICallError(RuntimeError):
    """Erreur d'appel modèle (timeout, code retour non nul, refus fournisseur)."""


@dataclass
class CallRecord:
    role: str
    provider: str
    model: str | None
    prompt_sha256: str
    prompt_chars: int
    output: str = ""
    output_sha256: str = ""
    exit_code: int | None = None
    duration_seconds: float = 0.0
    tokens_in: int | None = None
    tokens_out: int | None = None
    tokens_total: int | None = None
    cost_usd: float | None = None
    timed_out: bool = False
    error: str | None = None
    simulated: bool = False

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "provider": self.provider,
            "model": self.model,
            "prompt_sha256": self.prompt_sha256,
            "prompt_chars": self.prompt_chars,
            "output_sha256": self.output_sha256,
            "output_chars": len(self.output),
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 2),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tokens_total": self.tokens_total,
            "cost_usd": self.cost_usd,
            "timed_out": self.timed_out,
            "error": self.error,
            "simulated": self.simulated,
        }


class CLIDriver:
    """Adaptateur minimal : prompt → texte, via le CLI du fournisseur (non interactif)."""

    def __init__(self, provider: str, timeout: float = 240.0, cwd: Path | None = None) -> None:
        if provider not in PROVIDERS:
            raise ValueError(f"fournisseur inconnu: {provider}")
        self.provider = provider
        self.timeout = timeout
        self.cwd = cwd
        self.records: list[CallRecord] = []

    # -- commandes ----------------------------------------------------------
    def _build_command(self, prompt: str, tmpdir: str) -> tuple[list[str], Path | None]:
        if self.provider == "claude":
            return (
                [
                    "claude",
                    "-p",
                    prompt,
                    "--output-format",
                    "json",
                    "--tools",
                    "",
                    "--strict-mcp-config",
                    "--no-session-persistence",
                ],
                None,
            )
        output_file = Path(tmpdir) / "codex-last-message.txt"
        return (
            [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--color",
                "never",
                "--output-last-message",
                str(output_file),
                prompt,
            ],
            output_file,
        )

    # -- invocation ---------------------------------------------------------
    def invoke(self, prompt: str, role: str) -> str:
        record = CallRecord(
            role=role,
            provider=self.provider,
            model=None,
            prompt_sha256=sha256_text(prompt),
            prompt_chars=len(prompt),
        )
        started = time.time()
        if shutil.which(self.provider) is None:
            record.error = f"binaire `{self.provider}` absent du PATH"
            record.duration_seconds = time.time() - started
            self.records.append(record)
            raise CLICallError(record.error)

        with tempfile.TemporaryDirectory(prefix="swarmproof-cli-") as tmpdir:
            command, output_file = self._build_command(prompt, tmpdir)
            try:
                process = subprocess.run(
                    command,
                    cwd=str(self.cwd) if self.cwd else None,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            except subprocess.TimeoutExpired as exc:
                record.timed_out = True
                record.duration_seconds = time.time() - started
                record.error = f"timeout après {self.timeout:.0f}s"
                self.records.append(record)
                raise CLICallError(record.error) from exc
            except OSError as exc:
                record.error = str(exc)
                record.duration_seconds = time.time() - started
                self.records.append(record)
                raise CLICallError(record.error) from exc

            record.exit_code = process.returncode
            record.duration_seconds = time.time() - started
            raw_stdout = process.stdout or ""
            raw_stderr = process.stderr or ""
            text, meta_error = self._extract_text(raw_stdout, output_file, raw_stderr)
            record.output = text
            record.output_sha256 = sha256_text(text)
            record.model = self._extract_model(raw_stdout) or record.model
            usage = self._extract_usage(raw_stdout)
            record.tokens_in = usage.get("tokens_in")
            record.tokens_out = usage.get("tokens_out")
            record.tokens_total = usage.get("tokens_total", getattr(self, "_pending_tokens_total", None))
            self._pending_tokens_total = None
            record.cost_usd = usage.get("cost_usd")

            if meta_error:
                record.error = meta_error
            elif process.returncode != 0:
                record.error = f"exit={process.returncode}: {(raw_stderr or text)[-300:]}"

        self.records.append(record)
        if record.error:
            raise CLICallError(record.error)
        return record.output

    # -- parsing ------------------------------------------------------------
    def _extract_text(self, stdout: str, output_file: Path | None, stderr: str = "") -> tuple[str, str | None]:
        if self.provider == "codex":
            # Codex imprime souvent "tokens used: N" dans sa sortie de progression.
            used = extract_codex_tokens(stdout) or extract_codex_tokens(stderr)
            if used is not None:
                self._pending_tokens_total = used
            if output_file is not None and output_file.exists():
                text = output_file.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    return text, None
            return stdout, None

        # claude: --output-format json
        payload = self._try_json(stdout)
        if isinstance(payload, dict):
            text = payload.get("result") or payload.get("response") or ""
            if payload.get("is_error"):
                return text, f"refus/erreur fournisseur: {str(text)[:300]}"
            subtype = payload.get("subtype")
            if subtype and subtype != "success":
                return text, f"sous-type inattendu: {subtype}"
            return str(text), None
        return stdout, None

    @staticmethod
    def _try_json(text: str) -> Any:
        stripped = (text or "").strip()
        if not stripped.startswith("{"):
            return None
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None

    def _extract_model(self, stdout: str) -> str | None:
        payload = self._try_json(stdout)
        if isinstance(payload, dict):
            model = payload.get("model")
            if isinstance(model, str):
                return model
            usage = payload.get("modelUsage")
            if isinstance(usage, dict) and usage:
                return "+".join(sorted(str(key) for key in usage))[:120]
        return None

    def _extract_usage(self, stdout: str) -> dict:
        payload = self._try_json(stdout)
        if not isinstance(payload, dict):
            return {}
        usage = payload.get("usage")
        result: dict[str, Any] = {}
        if isinstance(usage, dict):
            result["tokens_in"] = usage.get("input_tokens")
            result["tokens_out"] = usage.get("output_tokens")
        cost = payload.get("total_cost_usd", payload.get("cost_usd"))
        if isinstance(cost, (int, float)):
            result["cost_usd"] = round(float(cost), 6)
        return result


class FakeDriver:
    """Driver simulé pour `--dry-run` : aucun subprocess, aucun appel modèle."""

    provider = "fake"

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content
        self.records: list[CallRecord] = []

    def invoke(self, prompt: str, role: str) -> str:
        record = CallRecord(
            role=role,
            provider=self.provider,
            model="simulated",
            prompt_sha256=sha256_text(prompt),
            prompt_chars=len(prompt),
            output=self.content,
            output_sha256=sha256_text(self.content),
            exit_code=0,
            duration_seconds=0.0,
            simulated=True,
        )
        self.records.append(record)
        return self.content


CODEX_TOKENS_PATTERNS = (
    # "tokens used: 12,345" / "tokens used 1 234" / "tokens used — 12.345"
    re.compile(r"tokens?\s*used[^\n\d]*([0-9][0-9., _]*)", re.IGNORECASE),
    # "tokens used" puis la valeur sur la ligne suivante
    re.compile(r"tokens?\s*used[^\n]*\n[ \t]*([0-9][0-9., _]*)", re.IGNORECASE),
    # variantes "total tokens: N" / "tokens consumed: N"
    re.compile(r"(?:total\s+tokens?|tokens?\s*consumed)[^\n\d]*([0-9][0-9., _]*)", re.IGNORECASE),
)


def extract_codex_tokens(text: str) -> int | None:
    """Extrait le total de tokens Codex, tolérant séparateurs/retours ligne ; None si absent."""
    if not text:
        return None
    found: int | None = None
    for pattern in CODEX_TOKENS_PATTERNS:
        for raw in pattern.findall(text):
            digits = re.sub(r"[^0-9]", "", raw)
            if digits:
                found = int(digits)
    return found


def driver_versions() -> dict[str, str | None]:
    """Versions des CLIs détectés (information de pack, jamais bloquant)."""
    from swarmproof.util import run_version

    return {"claude": run_version("claude"), "codex": run_version("codex")}
