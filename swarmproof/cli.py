"""CLI SwarmProof v0.2 : `swarmproof fix` et `swarmproof verify`.

Principe produit : le swarm propose, l'oracle externe décide, le pack prouve.
Le statut auto-déclaré du moteur NEXUS n'est jamais utilisé comme verdict.

v0.2 : retry infra borné (--max-retries), plafond global d'appels (--max-calls),
correctifs multi-fichiers atomiques, verdict INCONCLUSIVE explicite, sortie --json,
codes retour 0=PASS / 1=FAIL|INCONCLUSIVE / 2=usage ou erreur de configuration.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from swarmproof import __version__
from swarmproof import candidates as candidates_mod
from swarmproof import engine as engine_mod
from swarmproof.drivers import CLIDriver, driver_versions
from swarmproof.oracle import discover_test_paths, prepare_eval_tree, run_oracle
from swarmproof.pack import verify_pack, write_pack
from swarmproof.prepack import run_prepack
from swarmproof.retry import CallBudget
from swarmproof.trace import TraceWriter
from swarmproof.util import (
    changed_files,
    copy_tree,
    iso_now,
    platform_summary,
    sha256_text,
    unified_diff_dirs,
)
from swarmproof.verdict import VERDICT_DRY_RUN, VERDICT_PASS, compute_verdict

DEFAULT_ROLES = "claude,codex"
DEFAULT_TIMEOUT = 240.0
DEFAULT_ORACLE_TIMEOUT = 180.0
DEFAULT_MAX_RETRIES = 1
DEFAULT_MAX_CALLS = 6

EXIT_PASS = 0
EXIT_NOT_PASS = 1
EXIT_USAGE = 2


class SwarmProofError(RuntimeError):
    """Erreur d'usage ou de configuration (code de sortie 2)."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarmproof",
        description="Le swarm propose, l'oracle externe décide, l'Evidence Pack le prouve.",
    )
    parser.add_argument("--version", action="version", version=f"swarmproof {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fix = subparsers.add_parser("fix", help="faire proposer un correctif par le swarm et le vérifier par un oracle")
    fix.add_argument("repo", help="dépôt à corriger (copié, jamais modifié)")
    fix.add_argument("--oracle", required=True, help='commande de vérification, ex: "python -m unittest discover -s tests -v"')
    fix.add_argument("--out", required=True, help="répertoire du pack de preuves (doit être vide/absent)")
    fix.add_argument("--roles", default=DEFAULT_ROLES, help="fournisseurs dans l'ordre lead,support (claude,codex)")
    fix.add_argument("--mode", default="lead_support", choices=["lead_support", "specialist"])
    fix.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="timeout par appel modèle (s)")
    fix.add_argument("--oracle-timeout", type=float, default=DEFAULT_ORACLE_TIMEOUT, help="timeout oracle (s)")
    fix.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="retries par appel logique (défaut 1)")
    fix.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS, help="plafond global d'appels CLI (retries inclus)")
    fix.add_argument("--target", action="append", default=None, help="fichier cible (répétable ; auto-détecté sinon)")
    fix.add_argument("--dry-run", action="store_true", help="aucun appel modèle ni oracle : simule et produit un pack")
    fix.add_argument("--no-prepack", action="store_true", help="désactiver le pré-pack statique AgentProof")
    fix.add_argument("--json", action="store_true", help="imprimer un résumé machine-lisible sur stdout")
    fix.add_argument("--force", action="store_true", help="écraser un pack existant")
    fix.add_argument("--nexus-src", default=None, help="chemin du dépôt swarm-os (sinon NEXUS_SRC ou workspace)")
    fix.add_argument("--keep-temp", action="store_true", help="conserver le répertoire de travail temporaire")

    verify = subparsers.add_parser("verify", help="vérifier un pack (manifeste + rejeu oracle hors ligne)")
    verify.add_argument("pack", help="répertoire du pack")
    verify.add_argument("--skip-oracle", action="store_true", help="(défaut) ne pas exécuter de commande du pack")
    verify.add_argument("--allow-oracle-cmd", action="store_true", help="autoriser EXPLICITEMENT le rejeu de la commande oracle du pack (commande simple uniquement)")
    verify.add_argument("--oracle-timeout", type=float, default=DEFAULT_ORACLE_TIMEOUT)
    verify.add_argument("--json", action="store_true", help="imprimer le résultat machine-lisible")
    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class Printer:
    """Sortie humaine, redirigée sur stderr si --json (stdout reste du JSON pur)."""

    def __init__(self, json_mode: bool) -> None:
        self.json_mode = json_mode

    def info(self, message: str) -> None:
        print(message, file=sys.stderr if self.json_mode else sys.stdout)


def parse_roles(raw: str, mode: str) -> dict[str, str]:
    parts = [part.strip().lower() for part in raw.split(",") if part.strip()]
    if not parts:
        raise SwarmProofError("--roles vide")
    for provider in parts:
        if provider not in ("claude", "codex"):
            raise SwarmProofError(f"fournisseur inconnu dans --roles: {provider} (attendu: claude,codex)")
    if mode == "lead_support" and len(parts) < 2:
        raise SwarmProofError("--mode lead_support exige deux fournisseurs (lead,support)")
    return {"lead": parts[0], "support": parts[1] if len(parts) > 1 else parts[0]}


def repo_commit(repo: Path) -> str | None:
    try:
        process = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10
        )
        if process.returncode == 0:
            return process.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _outputs_for_pack(outputs: list[dict]) -> list[dict]:
    stripped: list[dict] = []
    for output in outputs:
        content = output.get("content") or ""
        stripped.append(
            {
                "index": output.get("index"),
                "agent_id": output.get("agent_id"),
                "role": output.get("role"),
                "status": output.get("status"),
                "content_chars": len(content),
                "content_sha256": sha256_text(content) if content else None,
                "content_preview": content[:600],
                "error": output.get("error"),
                "time_seconds": output.get("time_seconds"),
            }
        )
    return stripped


def _prepare_pack_dir(pack_dir: Path, force: bool) -> None:
    if pack_dir.exists():
        if any(pack_dir.iterdir()):
            if not force:
                raise SwarmProofError(f"le répertoire de sortie existe et n'est pas vide: {pack_dir} (utiliser --force)")
            shutil.rmtree(pack_dir)
    pack_dir.mkdir(parents=True, exist_ok=True)


def validate_targets(targets: list[str], repo: Path, test_paths: list[str]) -> list[str]:
    """Valide les --target : relatifs, dans le dépôt, existants, jamais des tests."""
    validated: list[str] = []
    for raw in targets:
        candidate = str(raw).strip().replace("\\", "/")
        if not candidate:
            raise SwarmProofError("cible vide dans --target")
        if candidate.startswith(("/", "~")) or (len(candidate) > 1 and candidate[1] == ":"):
            raise SwarmProofError(f"--target doit être relatif au dépôt: {raw}")
        if ".." in candidate.split("/"):
            raise SwarmProofError(f"--target ne doit pas contenir '..': {raw}")
        target_path = repo / candidate
        if not target_path.is_file():
            raise SwarmProofError(f"--target introuvable dans le dépôt: {raw}")
        resolved = target_path.resolve()
        if not str(resolved).startswith(str(repo.resolve()) + "/"):
            raise SwarmProofError(f"--target hors du dépôt: {raw}")
        if any(candidate == test or candidate.startswith(test.rstrip("/") + "/") for test in test_paths):
            raise SwarmProofError(f"--target ne peut pas être un fichier de test: {raw}")
        if "__pycache__" in candidate or candidate.endswith(".pyc"):
            raise SwarmProofError(f"--target invalide (cache): {raw}")
        validated.append(candidate)
    return validated


def _flatten_calls(outcomes: list[dict]) -> list[dict]:
    calls: list[dict] = []
    for outcome in outcomes:
        for record in outcome.get("records") or []:
            record = dict(record)
            record.setdefault("role", outcome.get("role"))
            record.setdefault("provider", outcome.get("provider"))
            calls.append(record)
    calls.sort(key=lambda call: {"lead": 0, "support": 1}.get(call.get("role"), 2))
    return calls


def _summary(payload: dict, written: dict) -> dict:
    return {
        "tool": "swarmproof",
        "version": __version__,
        "repo": payload["repo"]["source_path"],
        "mode": payload["mode"],
        "roles": payload["roles"],
        "dry_run": payload["dry_run"],
        "verdict": payload["verdict"],
        "verdict_basis": payload["verdict_basis"],
        "verdict_reason": payload.get("verdict_reason"),
        "engine": {
            "declared_status": payload["engine"]["declared_status"],
            "selected_mode": payload["engine"]["selected_mode"],
            "engine_ok": payload["engine"]["engine_ok"],
            "errors": payload["engine"]["errors"],
        },
        "calls": {
            "used": payload["call_budget"]["used"],
            "max": payload["call_budget"]["max_calls"],
            "retries": payload["retries"],
        },
        "candidates": {
            "sets_found": payload["candidate_sets_found"],
            "rejected": len(payload["rejected_candidates"]),
            "attempts": len(payload["attempts"]),
        },
        "oracle": {
            "command": payload["oracle"]["command"],
            "passed": payload["oracle"]["verdict_passed"],
            "tests_run": payload["oracle"]["tests_run"],
        },
        "pack": {
            "dir": written["pack_dir"],
            "files": written["files"],
            "manifest_sha256": written["manifest_sha256"],
        },
        "exit_code": payload["exit_code"],
    }


def print_summary(summary: dict) -> None:
    print("")
    print("SwarmProof — fix")
    print(f"  dépôt          : {summary['repo']}")
    print(f"  mode / rôles   : {summary['mode']} / lead={summary['roles']['lead']}, support={summary['roles']['support']}")
    if summary["dry_run"]:
        print("  exécution      : DRY-RUN (simulation, aucun appel modèle)")
    else:
        engine = summary["engine"]
        print(
            f"  moteur NEXUS   : déclaré={engine['declared_status']} · mode={engine['selected_mode']} "
            f"· engine_ok={engine['engine_ok']}"
        )
        calls = summary["calls"]
        print(f"  appels CLI     : {calls['used']}/{calls['max']} (retries: {calls['retries']})")
        if engine["errors"]:
            print(f"  erreurs agent  : {len(engine['errors'])} (exposées dans le pack, non masquées)")
        if summary["candidates"]["rejected"]:
            print(f"  rejets         : {summary['candidates']['rejected']} proposition(s) rejetée(s) (voir pack)")
    print(f"  candidats      : {summary['candidates']['sets_found']} ensemble(s) · tentatives oracle : {summary['candidates']['attempts']}")
    print(f"  verdict        : {summary['verdict']}  ({summary['verdict_reason']})")
    print(f"  pack           : {summary['pack']['dir']}")
    print(f"  fichiers       : {summary['pack']['files']} · manifeste SHA-256 : {summary['pack']['manifest_sha256']}")
    print("")


# ---------------------------------------------------------------------------
# fix
# ---------------------------------------------------------------------------
def run_fix(args: argparse.Namespace) -> int:
    printer = Printer(json_mode=args.json)
    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        raise SwarmProofError(f"dépôt introuvable: {repo}")
    if args.max_retries < 0:
        raise SwarmProofError("--max-retries doit être >= 0")
    if args.max_calls < 1:
        raise SwarmProofError("--max-calls doit être >= 1")
    roles = parse_roles(args.roles, args.mode)
    pack_dir = Path(args.out).expanduser().resolve()
    _prepare_pack_dir(pack_dir, args.force)

    nexus_src = None
    if not args.dry_run:
        nexus_src = engine_mod.find_nexus_src(args.nexus_src)
        if nexus_src is None:
            raise SwarmProofError(
                "moteur NEXUS introuvable (swarm-os). Indiquer --nexus-src ou NEXUS_SRC=/chemin/vers/swarm-os."
            )

    workdir = Path(tempfile.mkdtemp(prefix="swarmproof-run-"))
    trace = TraceWriter()
    budget = CallBudget(max_calls=args.max_calls)
    generated_at = iso_now()
    dry_run = bool(args.dry_run)
    trace.event(
        "run_start",
        repo=str(repo),
        mode=args.mode,
        roles=roles,
        dry_run=dry_run,
        oracle=args.oracle,
        max_calls=args.max_calls,
        max_retries=args.max_retries,
    )
    printer.info(f"[swarmproof] run démarré — travail: {workdir}")

    try:
        pristine = copy_tree(repo, workdir / "pristine")
        test_paths = discover_test_paths(pristine)
        if args.target:
            targets = validate_targets(args.target, pristine, test_paths)
        else:
            targets = candidates_mod.detect_targets(pristine)
            targets = [target.replace("\\", "/") for target in targets if (pristine / target).is_file()]
        if not targets:
            raise SwarmProofError("aucun fichier cible détecté ; préciser --target <fichier.py>")
        trace.event("repo_prepared", targets=targets, test_paths=test_paths)

        prepack_summary: dict | None = None
        prepack_pack_dir: Path | None = None
        if not dry_run and not args.no_prepack:
            trace.event("prepack_start")
            prepack_summary = run_prepack(pristine, workdir / "prepack-out")
            if prepack_summary.get("status") == "ok":
                prepack_pack_dir = Path(prepack_summary["pack_dir"])
            trace.event("prepack_end", status=prepack_summary.get("status"), score=prepack_summary.get("score"))
            printer.info(f"[swarmproof] pré-pack AgentProof : {prepack_summary.get('status')}")

        calls: list[dict] = []
        candidate_sets: list[candidates_mod.CandidateSet] = []
        rejected: list[dict] = []
        attempts: list[dict] = []
        retries = 0
        oracle_timed_out = False
        verdict_info: dict
        verdict: str
        dry_run = bool(args.dry_run)

        if dry_run:
            outputs = [
                {
                    "index": 0,
                    "agent_id": "lead_agent",
                    "role": "lead",
                    "status": "success",
                    "content": "```python\n# SwarmProof dry-run : correctif simulé, aucun modèle réel\n```",
                    "error": None,
                    "time_seconds": 0.0,
                }
            ]
            attempts = [
                {
                    "attempt": 0,
                    "simulated": True,
                    "agent_id": "lead_agent",
                    "role": "lead",
                    "target": targets[0],
                    "files": [targets[0]],
                    "passed": True,
                    "exit_code": 0,
                    "timed_out": False,
                    "tests_run": None,
                    "failed_tests": [],
                    "restored_test_paths": test_paths,
                    "duration_seconds": 0.0,
                    "execution_verified": True,
                    "evidence_reason": "simulation dry-run",
                    "test_parser": None,
                }
            ]
            verdict = VERDICT_DRY_RUN
            verdict_info = compute_verdict(dry_run=True)
            tree = copy_tree(pristine, workdir / "tree")
            diff = ""
            changed: list[str] = []
            engine_info = {
                "source_path": None,
                "version": {"version": __version__, "codename": "dry-run"},
                "selected_mode": args.mode,
                "declared_status": "SIMULATED_DRY_RUN",
                "engine_ok": True,
                "errors": [],
                "build_seconds": 0.0,
                "registry_ids": [],
                "agent_mapping": {},
                "analysis": {"complexity": "SIMULATED", "domains": []},
                "outputs": _outputs_for_pack(outputs),
            }
            oracle_info = {
                "command": args.oracle,
                "timeout_seconds": args.oracle_timeout,
                "verdict_passed": True,
                "execution_verified": True,
                "evidence_reason": "simulation dry-run",
                "test_parser": None,
                "simulated": True,
                "tests_run": None,
                "failed_tests": [],
                "restored_test_paths": test_paths,
            }
            trace.event("dry_run_simulated", oracle_attempts=1)
        else:
            drivers = {
                provider: CLIDriver(provider, timeout=args.timeout, cwd=workdir)
                for provider in sorted(set(roles.values()))
            }
            assert nexus_src is not None
            nexus_copy = engine_mod.ensure_nexus_copy(nexus_src)
            handle = engine_mod.build_engine(
                nexus_copy, drivers, roles, args.mode, trace, max_retries=args.max_retries, budget=budget
            )
            task_text = engine_mod.build_task_text(pristine, targets, test_paths)
            trace.event("engine_task_built", task_chars=len(task_text))
            result = engine_mod.run_mode(handle, task_text)
            outputs = result["outputs"]
            facts = engine_mod.summarize_engine(outputs, result["declared_status"])
            outcomes = handle.get("outcomes") or []
            calls = _flatten_calls(outcomes)
            retries = sum(int(outcome.get("retries") or 0) for outcome in outcomes)
            trace.event(
                "engine_result",
                declared_status=result["declared_status"],
                selected_mode=result["selected_mode"],
                engine_ok=facts["engine_ok"],
                engine_errors=len(facts["errors"]),
                retries=retries,
                duration_seconds=result["duration_seconds"],
            )

            # 1) Parser les propositions multi-fichiers de chaque agent (rejet explicite des ambiguës).
            for output in outputs:
                if output["status"] == "error":
                    continue
                content = output.get("content") or ""
                sets, rejections = candidates_mod.parse_candidate_sets(
                    content,
                    targets,
                    agent_id=output["agent_id"],
                    role=output["role"],
                    raw_sha256=sha256_text(content),
                )
                for rejection in rejections:
                    record = rejection.to_dict()
                    rejected.append(record)
                    trace.event("candidate_rejected", **record)
                for candidate_set in sets:
                    candidate_sets.append(candidate_set)
                    trace.event("candidate_set_parsed", **candidate_set.to_dict())

            # 2) Juger chaque ensemble atomiquement, jamais un correctif partiel.
            final_tree: Path | None = None
            for index, candidate_set in enumerate(candidate_sets):
                candidate_tree = copy_tree(pristine, workdir / f"candidate-{index}")
                try:
                    written_files = candidates_mod.apply_candidate_set(candidate_tree, candidate_set)
                except (ValueError, OSError) as exc:
                    record = {
                        "reason": "application atomique impossible",
                        "detail": str(exc)[:300],
                        "agent_id": candidate_set.agent_id,
                        "role": candidate_set.role,
                    }
                    rejected.append(record)
                    trace.event("candidate_rejected", **record)
                    continue
                printer.info(f"[swarmproof] candidat #{index} ({candidate_set.role}, {len(written_files)} fichier(s)) → oracle…")
                eval_tree, restored = prepare_eval_tree(pristine, candidate_tree, workdir / "judge", str(index))
                judged = run_oracle(eval_tree, args.oracle, args.oracle_timeout)
                oracle_timed_out = oracle_timed_out or bool(judged["timed_out"])
                attempt = {
                    "attempt": index,
                    "simulated": False,
                    "agent_id": candidate_set.agent_id,
                    "role": candidate_set.role,
                    "target": written_files[0] if written_files else None,
                    "files": written_files,
                    "candidate_sha256": candidate_set.raw_sha256,
                    "passed": judged["passed"],
                    "exit_code": judged["exit_code"],
                    "timed_out": judged["timed_out"],
                    "tests_run": judged["tests_run"],
                    "failed_tests": judged["failed_tests"],
                    "restored_test_paths": restored,
                    "duration_seconds": judged["duration_seconds"],
                    "execution_verified": judged.get("execution_verified", False),
                    "evidence_reason": judged.get("evidence_reason"),
                    "test_parser": judged.get("test_parser"),
                }
                attempts.append(attempt)
                trace.event(
                    "oracle_attempt",
                    attempt=index,
                    files=len(written_files),
                    passed=judged["passed"],
                    exit_code=judged["exit_code"],
                    tests_run=judged["tests_run"],
                    failed=len(judged["failed_tests"]),
                    timed_out=judged["timed_out"],
                )
                final_tree = eval_tree
                if judged["passed"]:
                    break

            ok_calls = sum(1 for outcome in outcomes if outcome.get("ok"))
            verdict_info = compute_verdict(
                attempts=attempts,
                engine_errors=facts["errors"],
                agent_calls_ok=ok_calls,
                candidate_sets_found=len(candidate_sets),
                rejected_candidate_sets=len(rejected),
                budget_exhausted=budget.exhausted_events > 0 or budget.used >= budget.max_calls,
                oracle_timed_out=oracle_timed_out,
            )
            verdict = verdict_info["verdict"]
            if final_tree is None:
                final_tree = copy_tree(pristine, workdir / "tree-unmodified")
            tree = final_tree
            diff = unified_diff_dirs(pristine, tree)
            changed = changed_files(pristine, tree)
            trace.event("verdict", verdict=verdict, reason=verdict_info["reason"], basis=verdict_info["basis"])

            best_attempt = attempts[0] if attempts else {}
            if any(attempt["passed"] for attempt in attempts):
                best_attempt = next(attempt for attempt in attempts if attempt["passed"])
            elif attempts:
                best_attempt = attempts[-1]
            oracle_info = {
                "command": args.oracle,
                "timeout_seconds": args.oracle_timeout,
                "verdict_passed": bool(best_attempt.get("passed")),
                "execution_verified": bool(best_attempt.get("execution_verified", False)),
                "evidence_reason": best_attempt.get("evidence_reason"),
                "test_parser": best_attempt.get("test_parser"),
                "simulated": False,
                "tests_run": best_attempt.get("tests_run"),
                "failed_tests": best_attempt.get("failed_tests", []),
                "restored_test_paths": best_attempt.get("restored_test_paths", test_paths),
            }
            engine_info = {
                "source_path": str(nexus_src),
                "version": handle["info"]["version"],
                "selected_mode": result["selected_mode"],
                "declared_status": result["declared_status"],
                "engine_ok": facts["engine_ok"],
                "errors": facts["errors"],
                "build_seconds": handle["info"]["build_seconds"],
                "registry_ids": handle["info"]["registry_ids"],
                "agent_mapping": handle["info"]["agent_mapping"],
                "analysis": result["analysis"],
                "outputs": _outputs_for_pack(outputs),
            }

        exit_code = EXIT_PASS if (dry_run or verdict == VERDICT_PASS) else EXIT_NOT_PASS
        mapping = {
            "targets": targets,
            "test_paths_restored": test_paths,
            "agent_mapping": engine_info.get("agent_mapping") or {},
            "candidate_sets": len(candidate_sets),
            "rejected": len(rejected),
        }
        payload = {
            "tool_version": __version__,
            "generated_at": generated_at,
            "command": " ".join(sys.argv),
            "dry_run": dry_run,
            "environment": {**platform_summary(), "cli_versions": driver_versions() if not dry_run else {}},
            "repo": {"name": repo.name, "source_path": str(repo), "commit": repo_commit(repo)},
            "mode": args.mode,
            "roles": roles,
            "engine": engine_info,
            "calls": calls,
            "retries": retries,
            "call_budget": budget.to_dict(),
            "candidates": [candidate_set.to_dict() for candidate_set in candidate_sets],
            "candidate_sets_found": len(candidate_sets),
            "rejected_candidates": rejected,
            "attempts": attempts,
            "oracle": oracle_info,
            "verdict": "DRY_RUN" if dry_run else verdict,
            "verdict_basis": verdict_info["basis"],
            "verdict_reason": verdict_info["reason"],
            "verdict_explain": verdict_info["explain"],
            "changed_files": changed,
            "diff": diff,
            "mapping": mapping,
            "prepack": prepack_summary,
            "prepack_pack_dir": prepack_pack_dir,
            "pristine": pristine,
            "tree": tree,
            "trace_events": trace.events,
            "exit_code": exit_code,
            "limits": [
                "n=1 run, tâche unique : signal de faisabilité, pas de significativité.",
                "Le verdict dépend entièrement de l'oracle choisi (qualité des tests).",
                "Preuve technique, pas certification ; supériorité du swarm non prouvée.",
                "Les réponses des modèles ne sont pas reproductibles à l'identique.",
                "Le moteur NEXUS est une extraction (copie /tmp) ; swarm-os n'est pas modifié.",
            ],
        }
        written = write_pack(pack_dir, payload)
        summary = _summary(payload, written)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print_summary(summary)
        return exit_code
    finally:
        if not args.keep_temp:
            shutil.rmtree(workdir, ignore_errors=True)
        else:
            printer.info(f"[swarmproof] répertoire de travail conservé : {workdir}")


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------
def run_verify(args: argparse.Namespace) -> int:
    pack_dir = Path(args.pack).expanduser().resolve()
    allow_cmd = bool(args.allow_oracle_cmd and not args.skip_oracle)
    result = verify_pack(
        pack_dir,
        replay=allow_cmd,
        oracle_timeout=args.oracle_timeout,
        allow_oracle_cmd=allow_cmd,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("")
        print("SwarmProof — verify")
        print(f"  pack                : {result['pack_dir']}")
        print(f"  manifeste SHA-256   : {'OK' if result['manifest_ok'] else 'INVALIDE'}")
        print(f"  verdict enregistré  : {result['recorded_verdict']}")
        print(f"  portée intégrité    : {result['integrity_scope']} (origine NON prouvée)")
        if not allow_cmd:
            print("  exécution de commande : AUCUNE (sécurité) — utiliser --allow-oracle-cmd pour rejouer")
        if result["dry_run"]:
            print("  rejeu oracle        : ignoré (pack dry-run)")
        elif result["replay"]:
            replay = result["replay"]
            print(
                f"  rejeu oracle        : {'PASS' if replay['passed'] else 'FAIL'} "
                f"(enregistré : {'PASS' if replay['recorded_passed'] else 'FAIL'}, "
                f"correspondance : {'oui' if replay['match'] else 'NON'})"
            )
            print(f"  commande rejouée    : {replay['command']}")
        if result["errors"]:
            print("  erreurs :")
            for error in result["errors"]:
                print(f"    - {error}")
        for warning in result["warnings"]:
            print(f"  avertissement : {warning}")
        label = result.get("label", "PACK INVALIDE")
        if label == "PACK VALIDE":
            print(f"  RESULTAT            : PACK VALIDE — rejeu oracle réussi et cohérent (verdict : {result['recorded_verdict']})")
        elif label == "PACK COHERENT":
            print(f"  RESULTAT            : PACK COHÉRENT — intégrité OK, verdict NON rejoué (origine non prouvée)")
            print("                        → utiliser --allow-oracle-cmd pour rejouer et obtenir 'PACK VALIDE'")
        else:
            print("  RESULTAT            : PACK ALTÉRÉ/INVALIDE — voir erreurs ci-dessus")
        print("")
    return int(result.get("exit_code", EXIT_PASS if result["ok"] else EXIT_NOT_PASS))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "fix":
            return run_fix(args)
        if args.command == "verify":
            return run_verify(args)
        raise SwarmProofError(f"commande inconnue: {args.command}")
    except SwarmProofError as error:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(error), "exit_code": EXIT_USAGE}, ensure_ascii=False))
        else:
            print(f"swarmproof: erreur: {error}", file=sys.stderr)
        return EXIT_USAGE
    except KeyboardInterrupt:
        print("swarmproof: interrompu", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
