"""Oracle externe : la seule source de vérité du produit.

Règles :
- l'oracle ne tourne jamais dans le dépôt source, mais dans une copie jetable ;
- les fichiers de test sont RESTAURÉS depuis la copie vierge avant jugement
  (un modèle ne peut pas gagner en modifiant/neutralisant les tests) ;
- le verdict est le code retour de l'oracle, rien d'autre.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from swarmproof.util import copy_tree, iter_files, run_command, run_command_argv

TEST_DIR_NAMES = {"tests", "test", "__tests__"}
TEST_FILE_PATTERNS = ("test_*.py", "*_test.py", "test_*.js", "*_test.js")
RAN_TESTS = re.compile(r"Ran\s+(\d+)\s+tests?", re.IGNORECASE)
FAILED_TEST = re.compile(r"^(?:FAIL|ERROR):\s+(\S+)", re.MULTILINE)
UNITTEST_OK = re.compile(r"(?m)^OK\b")
UNITTEST_FAILED = re.compile(r"(?m)^FAILED\b")
PYTEST_COUNT = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped)", re.IGNORECASE)
PYTEST_SUMMARY = re.compile(r"=+\s*[^=]*\b(?:passed|failed|error|no tests ran)\b[^=]*=+", re.IGNORECASE)


def discover_test_paths(repo: Path) -> list[str]:
    """Chemins relatifs à restaurer avant tout jugement (répertoires et fichiers de test)."""
    paths: list[str] = []
    for path in sorted(repo.rglob("*")):
        if not path.is_dir() or path.name not in TEST_DIR_NAMES:
            continue
        rel = str(path.relative_to(repo)).replace("\\", "/")
        rel = rel.rstrip("/") or path.name
        if rel not in paths:
            paths.append(rel)
    if not paths:
        for pattern in TEST_FILE_PATTERNS:
            for path in sorted(repo.rglob(pattern)):
                if not path.is_file():
                    continue
                rel = str(path.relative_to(repo)).replace("\\", "/")
                if rel not in paths:
                    paths.append(rel)
    return sorted(paths)


def restore_paths(pristine: Path, tree: Path, rel_paths: list[str]) -> list[str]:
    """Réécrit les chemins de test depuis la copie vierge (tests non modifiables par le modèle)."""
    restored: list[str] = []
    for rel in rel_paths:
        source = pristine / rel
        destination = tree / rel
        if not source.exists():
            continue
        if destination.is_dir():
            shutil.rmtree(destination)
        elif destination.exists():
            destination.unlink()
        if source.is_dir():
            copy_tree(source, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        restored.append(rel)
    return restored


def parse_unittest_output(stdout: str, stderr: str) -> dict:
    combined = f"{stdout}\n{stderr}"
    match = RAN_TESTS.search(combined)
    failed = sorted(set(FAILED_TEST.findall(combined)))
    return {
        "tests_run": int(match.group(1)) if match else None,
        "failed_tests": failed,
    }


def parse_test_evidence(stdout: str, stderr: str) -> dict:
    """Prouve qu'une suite de tests a réellement été exécutée (anti-`os._exit(0)`).

    Un exit code 0 ne suffit JAMAIS : il faut un compteur de tests >= 1 et un marqueur de
    synthèse reconnu (unittest `OK`/`FAILED`, pytest `N passed`/`N failed`).
    """
    combined = f"{stdout}\n{stderr}"
    tests_run = None
    parser = None
    ran = RAN_TESTS.search(combined)
    if ran:
        parser = "unittest"
        tests_run = int(ran.group(1))
        summary_ok = bool(UNITTEST_OK.search(combined) or UNITTEST_FAILED.search(combined))
    else:
        counts = {kind.lower(): int(number) for number, kind in PYTEST_COUNT.findall(combined)}
        if counts:
            parser = "pytest"
            tests_run = sum(
                counts.get(kind, 0) for kind in ("passed", "failed", "error", "errors", "skipped")
            )
            summary_ok = bool(PYTEST_SUMMARY.search(combined)) or any(
                kind in counts for kind in ("passed", "failed", "error", "errors")
            )
        else:
            summary_ok = False
    evidence_ok = bool(parser and tests_run is not None and tests_run >= 1 and summary_ok)
    if evidence_ok:
        reason = f"preuve d'exécution: {parser}, {tests_run} test(s), marqueur de synthèse présent"
    elif parser and tests_run is not None and tests_run < 1:
        reason = "aucun test exécuté (tests_run=0) : exit 0 non concluant"
    elif parser is not None:
        reason = "synthèse de tests non reconnue : exit 0 non concluant"
    else:
        reason = "aucune preuve d'exécution de tests (sortie non parsable) : exit 0 non concluant"
    return {
        "parser": parser,
        "tests_run": tests_run,
        "summary_marker": summary_ok,
        "evidence_ok": evidence_ok,
        "reason": reason,
    }


def run_oracle(
    eval_tree: Path,
    command: str,
    timeout: float,
    pristine: Path | None = None,
    restore: list[str] | None = None,
    *,
    safe_command: bool = False,
) -> dict:
    """Exécute l'oracle dans `eval_tree` et retourne un résultat structuré.

    `passed` n'est vrai que si l'oracle sort 0 **et** qu'une exécution réelle de tests est prouvée
    (`tests_run >= 1` + marqueur de synthèse). Sinon `execution_verified=False` et le verdict devra
    être INCONCLUSIVE : jamais de PASS sur un exit 0 nu.
    """
    restored = restore_paths(pristine, eval_tree, restore or []) if pristine else []
    if safe_command:
        result = run_command_argv(command, cwd=eval_tree, timeout=timeout)
    else:
        result = run_command(command, cwd=eval_tree, timeout=timeout)
    parsed = parse_unittest_output(result["stdout"], result["stderr"])
    evidence = parse_test_evidence(result["stdout"], result["stderr"])
    execution_verified = bool(evidence["evidence_ok"] and not result.get("refused"))
    passed = (
        (not result["timed_out"])
        and result["exit_code"] == 0
        and execution_verified
    )
    return {
        "passed": passed,
        "execution_verified": execution_verified,
        "evidence_reason": evidence["reason"],
        "test_parser": evidence["parser"],
        "exit_code": result["exit_code"],
        "timed_out": result["timed_out"],
        "refused": bool(result.get("refused")),
        "duration_seconds": result["duration_seconds"],
        "command": command,
        "cwd": str(eval_tree),
        "tests_run": parsed["tests_run"] if parsed["tests_run"] is not None else evidence["tests_run"],
        "evidence_tests_run": evidence["tests_run"],
        "failed_tests": parsed["failed_tests"],
        "restored_test_paths": restored,
        "stdout_tail": result["stdout"][-2000:],
        "stderr_tail": result["stderr"][-2000:],
    }


def prepare_eval_tree(pristine: Path, candidate_tree: Path, temp_root: Path, label: str) -> tuple[Path, list[str]]:
    """Copie la candidate tree dans un dossier jetable et restaure les tests depuis la vierge."""
    eval_tree = temp_root / f"judge-{label}"
    copy_tree(candidate_tree, eval_tree)
    restored = restore_paths(pristine, eval_tree, discover_test_paths(pristine))
    return eval_tree, restored


def count_text_files(tree: Path) -> int:
    return len(iter_files(tree))


def tree_fingerprint(tree: Path) -> str:
    """Empreinte courte de l'arborescence (chemins + hashes) pour tracer un jugement."""
    import hashlib

    digest = hashlib.sha256()
    for path in iter_files(tree):
        digest.update(str(path.relative_to(tree)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


__all__ = [
    "discover_test_paths",
    "restore_paths",
    "run_oracle",
    "parse_unittest_output",
    "prepare_eval_tree",
    "tree_fingerprint",
    "count_text_files",
    "is_within",
]
_ = os  # keep os imported for platform-agnostic path handling in future patches
