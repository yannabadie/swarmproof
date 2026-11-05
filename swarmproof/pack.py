"""Evidence Pack SwarmProof : écriture, manifeste SHA-256 et vérification autonome.

Le pack est **autosuffisant** : il contient `source/` (copie vierge du dépôt) et `tree/`
(état évalué). `swarmproof verify <pack>` peut donc rejouer l'oracle hors ligne et comparer
le verdict rejoué au verdict enregistré — sans refaire d'appel modèle.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

from swarmproof.oracle import (
    discover_test_paths,
    parse_unittest_output,
    restore_paths,
    run_oracle,
)
from swarmproof.util import (
    SECRET_NAME_PATTERNS,
    changed_files,
    contains_secret,
    copy_tree,
    is_text,
    iter_all_files,
    iter_files,
    redact_secrets,
    relative_files,
    run_command,
    sanitize_paths,
    sha256_file,
    unified_diff_dirs,
    write_json,
    write_text,
)

MANIFEST_NAME = "manifest.sha256"
REQUIRED_FILES = (
    "report.md",
    "run.json",
    "trace.jsonl",
    "oracle.jsonl",
    "diff.patch",
    "mapping.json",
    f"{MANIFEST_NAME}",
    "README.txt",
)
PACK_SCHEMA = "swarmproof/1"
README_TEXT = """SwarmProof — Evidence Pack
==========================

Ce pack est la preuve d'un run de remédiation vérifiée :
  * le swarm (moteur NEXUS) a PROPOSÉ des correctifs ;
  * un oracle externe (tests) a DÉCIDÉ ;
  * ce pack documente ce qui s'est passé, avec quels modèles, quels appels,
    quels hashes, quel diff et quel verdict.

Contenu
-------
  report.md        Résumé lisible : verdict, appels, oracle, limites.
  run.json         Données structurées du run (statuts, durées, tokens, coûts).
  trace.jsonl      Une ligne par événement/appel (prompt sha256, durée, statut).
  oracle.jsonl     Une ligne par tentative de correctif jugée par l'oracle.
  diff.patch       Diff unifié entre le dépôt source et l'arbre évalué.
  mapping.json     Fichiers cibles, chemins de tests restaurés, mapping agents.
  source/          Copie vierge du dépôt au moment du run (tests non modifiés).
  tree/            État évalué (correctif appliqué + tests restaurés).
  manifest.sha256  SHA-256 de chaque fichier du pack (vérifiable hors ligne).
  README.txt       Ce fichier.

Vérification
------------
  cd <ce_pack> && shasum -a 256 -c manifest.sha256
  python -m swarmproof verify <ce_pack>

Le second rejoue l'oracle sur tree/ (tests restaurés depuis source/) et compare
le verdict rejoué au verdict enregistré. Aucun appel modèle n'est effectué.

Sécurité / authenticité
-----------------------
  * Ce pack est une COHÉRENCE INTERNE AUTO-ATTESTÉE : le manifeste prouve que les
    fichiers n'ont pas changé depuis l'écriture du pack, PAS qu'il vient de nous.
    Aucune signature cryptographique n'est incluse. Pour l'origine, exigez un canal
    de livraison authentifié (ou ajoutez une signature hors pack).
  * `swarmproof verify` n'exécute AUCUNE commande par défaut : le rejeu de l'oracle
    exige `--allow-oracle-cmd`, et les commandes avec métacaractères shell sont refusées.
  * Les fichiers de secrets connus (.env, *.pem, *.key, id_rsa*, etc.) sont EXCLUS et
    les motifs ressemblant à des clés sont redactés ; les chemins locaux absolus sont
    remplacés par des jetons neutres dans les métadonnées.

Rappels
-------
  * Le verdict vient de l'oracle, jamais du statut auto-déclaré du moteur.
  * `engine_error`/`engine_ok=false` dans run.json signale qu'un agent a échoué
    même si le moteur prétendait avoir terminé.
  * Ce pack ne prouve pas la qualité générale du code : il prouve que, sur ce
    dépôt, à cette date, avec cet oracle, le correctif évalué passe les tests.
  * PREUVE TECHNIQUE, PAS CERTIFICATION. La supériorité du hybrid swarm sur un
    agent seul n'est pas prouvée par ce pack (n=1, un run).
"""


# ---------------------------------------------------------------------------
# Manifeste
# ---------------------------------------------------------------------------
def build_manifest(pack_dir: Path) -> str:
    """Manifeste compatible `shasum -a 256 -c` : `<sha256>  <chemin relatif>`."""
    lines: list[str] = []
    for path in sorted(iter_files(pack_dir)):
        rel = str(path.relative_to(pack_dir)).replace("\\", "/")
        if rel == MANIFEST_NAME:
            continue
        lines.append(f"{sha256_file(path)}  {rel}")
    return "\n".join(lines) + "\n"


def manifest_entries(pack_dir: Path) -> dict[str, str]:
    manifest = pack_dir / MANIFEST_NAME
    if not manifest.is_file():
        return {}
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        if digest and rel:
            entries[rel.strip()] = digest.strip()
    return entries


# ---------------------------------------------------------------------------
# Écriture du pack
# ---------------------------------------------------------------------------
def write_pack(pack_dir: Path, ctx: dict) -> dict:
    """Écrit tous les artefacts puis le manifeste (dernier, pour se couvrir lui-même)."""
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    pack_dir.mkdir(parents=True)

    # 1. Fichiers de preuve
    write_text(pack_dir / "report.md", render_report(ctx))
    write_json(pack_dir / "run.json", build_run_document(ctx))
    _write_jsonl(pack_dir / "trace.jsonl", ctx.get("trace_events", []))
    _write_jsonl(pack_dir / "oracle.jsonl", ctx.get("attempts", []))
    write_text(pack_dir / "diff.patch", ctx.get("diff", ""))
    write_json(pack_dir / "mapping.json", ctx.get("mapping", {}))
    write_text(pack_dir / "README.txt", README_TEXT)

    # 2. Arborescences autosuffisantes pour le rejeu hors ligne (secrets nettoyés)
    redacted = _copy_sanitized(ctx["pristine"], pack_dir / "source")
    redacted += _copy_sanitized(ctx["tree"], pack_dir / "tree")

    # 3. Pré-pack optionnel (AgentProof), copié tel quel (sous-pack avec son manifeste)
    prepack_dir = ctx.get("prepack_pack_dir")
    if prepack_dir and Path(prepack_dir).is_dir():
        shutil.copytree(Path(prepack_dir), pack_dir / "prepack")

    # 4. Redaction des chemins locaux absolus et des secrets dans les métadonnées
    repo_root = ctx.get("repo", {}).get("source_path")
    _sanitize_metadata(pack_dir, ctx, repo_root)
    # 5. Manifeste en dernier
    write_text(pack_dir / MANIFEST_NAME, build_manifest(pack_dir))

    files = relative_files(pack_dir)
    return {
        "pack_dir": str(pack_dir),
        "manifest_sha256": sha256_file(pack_dir / MANIFEST_NAME),
        "files": len(files),
        "total_bytes": sum((pack_dir / rel).stat().st_size for rel in files),
        "sanitized_secret_files": sorted(set(redacted)),
    }


_METADATA_SUFFIXES = (".md", ".json", ".txt", ".jsonl", ".patch", ".mmd")
_COPY_EXCLUDED_DIRS = (".git", "source", "tree")


def _copy_sanitized(source: Path, destination: Path) -> list[str]:
    """Copie avec exclusion des fichiers de secrets ; redacte les motifs de clés inline."""
    copy_tree(source, destination)
    redacted_files: list[str] = []
    for path in iter_files(destination):
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        redacted = redact_secrets(text)
        if redacted != text:
            path.write_text(redacted, encoding="utf-8", newline="\n")
            redacted_files.append(str(path.relative_to(destination)).replace("\\", "/"))
    return redacted_files


def _sanitize_metadata(pack_dir: Path, ctx: dict, repo_root: str | None) -> None:
    """Remplace les chemins locaux absolus dans les métadonnées lisibles du pack."""
    roots = [Path(repo_root)] if repo_root else []
    for path in iter_all_files(pack_dir):
        rel = str(path.relative_to(pack_dir)).replace("\\", "/")
        if rel == MANIFEST_NAME or rel.startswith("source/") or rel.startswith("tree/"):
            continue
        if not rel.endswith(_METADATA_SUFFIXES) or rel.startswith("prepack/"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        sanitized = redact_secrets(sanitize_paths(text, roots))
        if sanitized != text:
            path.write_text(sanitized, encoding="utf-8", newline="\n")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            import json

            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_run_document(ctx: dict) -> dict:
    engine = ctx.get("engine", {})
    oracle = ctx.get("oracle", {})
    return {
        "schema": PACK_SCHEMA,
        "tool": {"name": "swarmproof", "version": ctx.get("tool_version")},
        "generated_at": ctx.get("generated_at"),
        "command": ctx.get("command"),
        "dry_run": ctx.get("dry_run", False),
        "environment": ctx.get("environment", {}),
        "repo": ctx.get("repo", {}),
        "mode": ctx.get("mode"),
        "roles": ctx.get("roles"),
        "nexus": {
            "source_path": engine.get("source_path"),
            "engine_version": engine.get("version"),
            "selected_mode": engine.get("selected_mode"),
            "declared_status": engine.get("declared_status"),
            "engine_ok": engine.get("engine_ok"),
            "build_seconds": engine.get("build_seconds"),
            "registry_ids": engine.get("registry_ids"),
            "agent_mapping": engine.get("agent_mapping"),
            "task_analysis": engine.get("analysis"),
            "errors": engine.get("errors", []),
            "outputs": engine.get("outputs", []),
        },
        "model_calls": ctx.get("calls", []),
        "candidates": ctx.get("candidates", []),
        "oracle": {
            "command": oracle.get("command"),
            "timeout_seconds": oracle.get("timeout_seconds"),
            "verdict_passed": bool(oracle.get("verdict_passed")),
            "execution_verified": bool(oracle.get("execution_verified", False)),
            "evidence_reason": oracle.get("evidence_reason"),
            "test_parser": oracle.get("test_parser"),
            "simulated": bool(oracle.get("simulated", False)),
            "tests_run": oracle.get("tests_run"),
            "failed_tests": oracle.get("failed_tests", []),
            "restored_test_paths": oracle.get("restored_test_paths", []),
            "attempts": len(ctx.get("attempts", [])),
        },
        "verdict": ctx.get("verdict"),
        "verdict_basis": ctx.get("verdict_basis"),
        "verdict_reason": ctx.get("verdict_reason"),
        "verdict_explain": ctx.get("verdict_explain", []),
        "verdict_source": "oracle" if not ctx.get("dry_run") else "simulated",
        "retries": ctx.get("retries", 0),
        "call_budget": ctx.get("call_budget"),
        "candidate_sets_found": ctx.get("candidate_sets_found", len(ctx.get("candidates", []))),
        "rejected_candidates": ctx.get("rejected_candidates", []),
        "exit_code": ctx.get("exit_code"),
        "changed_files": ctx.get("changed_files", []),
        "prepack": ctx.get("prepack"),
        "security": {
            "origin_proven": False,
            "integrity_scope": "coherence_interne_auto_attestee",
            "replay_requires_explicit_flag": "--allow-oracle-cmd",
            "sanitized_paths": True,
            "excluded_secret_files": True,
        },
        "limits": ctx.get("limits", []),
    }


# ---------------------------------------------------------------------------
# Rapport lisible
# ---------------------------------------------------------------------------
def render_report(ctx: dict) -> str:
    engine = ctx.get("engine", {})
    oracle = ctx.get("oracle", {})
    verdict = ctx.get("verdict", "UNKNOWN")
    dry_run = ctx.get("dry_run", False)
    repo = ctx.get("repo", {})
    lines: list[str] = []
    lines.append("# SwarmProof — Evidence Pack")
    lines.append("")
    lines.append(f"- **Généré** : {ctx.get('generated_at')}")
    lines.append(f"- **Outil** : swarmproof {ctx.get('tool_version')}")
    lines.append(f"- **Dépôt** : `{repo.get('name')}` ({repo.get('source_path')})")
    lines.append(f"- **Mode** : {ctx.get('mode')} — rôles : lead=`{ctx.get('roles', {}).get('lead')}`, support=`{ctx.get('roles', {}).get('support')}`")
    lines.append(f"- **Dry-run** : {'oui (simulation)' if dry_run else 'non'}")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    if dry_run:
        lines.append("**VERDICT SIMULÉ — DRY-RUN : aucune conclusion réelle.** Cette exécution teste la mécanique du produit (drivers, oracle, pack) sans modèle ni oracle réels.")
    else:
        lines.append(f"**VERDICT (oracle externe) : {verdict}**")
        lines.append("")
        lines.append(f"- Oracle : `{oracle.get('command')}` (timeout {oracle.get('timeout_seconds')}s)")
        lines.append(f"- Tests exécutés : {oracle.get('tests_run')} · échecs : {len(oracle.get('failed_tests') or [])}")
        lines.append(f"- Tests restaurés avant jugement : {', '.join(oracle.get('restored_test_paths') or []) or '(aucun)'}")
        if oracle.get("evidence_reason"):
            lines.append(f"- Preuve d'exécution : {oracle.get('evidence_reason')}")
        lines.append(f"- Tentatives de correctif jugées : {len(ctx.get('attempts', []))}")
        if ctx.get("verdict_reason"):
            lines.append(f"- Justification du verdict : {ctx.get('verdict_reason')}")
        if ctx.get("verdict") == "INCONCLUSIVE":
            lines.append("")
            lines.append("**INCONCLUSIVE** : aucun verdict exploitable n'a pu être établi (erreur infra, "
                         "budget épuisé ou timeout oracle). Ce pack n'est PAS un succès ; il documente un échec "
                         "de procédure, pas une validation.")
    lines.append("")
    lines.append("## Moteur NEXUS (statut auto-déclaré — NON utilisé comme preuve)")
    lines.append("")
    if dry_run:
        lines.append("Simulé.")
    else:
        version = engine.get("version") or {}
        if isinstance(version, dict):
            version_text = f"{version.get('version', '?')} ({version.get('codename', '?')})"
        else:
            version_text = str(version)
        lines.append(f"- Statut déclaré : `{engine.get('declared_status')}` · mode sélectionné : `{engine.get('selected_mode')}` · version : {version_text}")
        lines.append(f"- `engine_ok` : **{engine.get('engine_ok')}** · erreurs d'agent : {len(engine.get('errors') or [])}")
        calls_info = ctx.get("call_budget") or {}
        lines.append(
            f"- appels CLI : {calls_info.get('used', '?')}/{calls_info.get('max_calls', '?')} "
            f"· retries : {ctx.get('retries', 0)}"
        )
        for error in engine.get("errors") or []:
            lines.append(f"  - `{error.get('role')}` / {error.get('agent_id')} : {str(error.get('error'))[:180]}")
        lines.append("")
        lines.append("> Rappel : un moteur peut rapporter `COMPLETED` alors qu'un agent a échoué. Seul l'oracle tranche.")
    lines.append("")
    lines.append("## Étapes (rôle / fournisseur / modèle / durée / tokens / coût)")
    lines.append("")
    calls = ctx.get("calls", [])
    if calls:
        lines.append("| # | rôle | fournisseur | modèle | tentative | durée (s) | tokens in/out (total) | coût USD | statut |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for index, call in enumerate(calls, start=1):
            status = "error" if call.get("error") else "ok"
            if call.get("tokens_in") is not None:
                tokens = f"{call.get('tokens_in')}/{call.get('tokens_out')}"
            elif call.get("tokens_total") is not None:
                tokens = f"n/a (total {call.get('tokens_total')})"
            else:
                tokens = "n/a"
            cost = call.get("cost_usd") if call.get("cost_usd") is not None else "n/a"
            lines.append(
                f"| {index} | {call.get('role')} | {call.get('provider')} | {call.get('model') or 'n/a'} | "
                f"{call.get('attempt', 1)} | {call.get('duration_seconds')} | {tokens} | {cost} | {status} |"
            )
        for call in calls:
            if call.get("error"):
                lines.append("")
                lines.append(f"- Erreur appel #{call.get('role')} : {str(call.get('error'))[:300]}")
    else:
        lines.append("Aucun appel modèle réel.")
    lines.append("")
    lines.append("## Correctifs proposés et jugements de l'oracle")
    lines.append("")
    candidates = ctx.get("candidates", [])
    if candidates:
        lines.append("| # | rôle | agent | fichier cible | sha256 (court) |")
        lines.append("|---|---|---|---|---|")
        for candidate in candidates:
            lines.append(
                f"| {candidate.get('index')} | {candidate.get('role')} | {candidate.get('agent_id')} | "
                f"{candidate.get('target')} | {str(candidate.get('sha256'))[:16]} |"
            )
    else:
        lines.append("Aucun correctif exploitable extrait des réponses agents.")
    lines.append("")
    attempts = ctx.get("attempts", [])
    if attempts:
        lines.append("| tentative | provenance | cible | exit | PASS/FAIL | tests | échecs |")
        lines.append("|---|---|---|---|---|---|---|")
        for attempt in attempts:
            lines.append(
                f"| {attempt.get('attempt')} | {attempt.get('role', '?')}/{attempt.get('agent_id', '?')} | "
                f"{attempt.get('target')} | {attempt.get('exit_code')} | "
                f"{'PASS' if attempt.get('passed') else 'FAIL'} | {attempt.get('tests_run')} | "
                f"{len(attempt.get('failed_tests') or [])} |"
            )
    rejected = ctx.get("rejected_candidates") or []
    if rejected:
        lines.append("")
        lines.append("## Propositions rejetées (blocs partiels/ambigus/hors cible)")
        lines.append("")
        lines.append("| rôle | agent | raison | détail |")
        lines.append("|---|---|---|---|")
        for rejection in rejected:
            lines.append(
                f"| {rejection.get('role')} | {rejection.get('agent_id')} | {rejection.get('reason')} | "
                f"{str(rejection.get('detail'))[:160]} |"
            )
    lines.append("")
    lines.append("## Changements")
    lines.append("")
    changed = ctx.get("changed_files", [])
    lines.append(f"Fichiers modifiés vs dépôt source : {', '.join(f'`{name}`' for name in changed) or '(aucun)'}.")
    lines.append("")
    prepack = ctx.get("prepack") or {}
    if prepack:
        lines.append("## Pré-pack statique AgentProof (optionnel)")
        lines.append("")
        if prepack.get("status") == "ok":
            lines.append(
                f"- AgentProof {prepack.get('version')} : score {prepack.get('score')}/100 "
                f"({prepack.get('grade')} — {prepack.get('grade_label')}), {prepack.get('files_total')} fichiers."
            )
            lines.append(f"- Sous-pack : `prepack/` · manifeste : `{prepack.get('manifest_sha256')}`")
        else:
            lines.append(f"- Statut : `{prepack.get('status')}` — {prepack.get('reason', '')}")
        lines.append("")
    lines.append("## Ce que ce pack prouve / ne prouve pas")
    lines.append("")
    if dry_run:
        lines.append("**Dry-run** : ce pack atteste seulement que la mécanique produit (drivers simulés, oracle simulé, pack) fonctionne ; il ne prouve aucun correctif réel.")
    else:
        lines.append("**Prouve** : sur ce dépôt, à cet instant, le correctif de `tree/` fait passer l'oracle `{}` ; les tests ont été restaurés avant jugement ; chaque fichier du pack a l'empreinte SHA-256 listée.".format(oracle.get("command")))
    lines.append("")
    lines.append("**Ne prouve pas** : la qualité générale du code hors tests, la supériorité d'un swarm sur un agent seul, la reproductibilité des réponses des modèles (non déterministes), ni la sécurité du correctif pour un usage en production.")
    lines.append("")
    lines.append("**Preuve technique, pas certification.** La supériorité du hybrid swarm sur un agent seul n'est pas démontrée par ce pack (n=1, un run).")
    lines.append("")
    lines.append("**Authenticité** : manifeste = cohérence interne auto-attestée (pas de signature, pas de preuve d'origine). Aucune commande du pack n'est exécutée par `verify` sans `--allow-oracle-cmd`.")
    for limit in ctx.get("limits") or []:
        lines.append(f"- Limite : {limit}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Vérification du pack
# ---------------------------------------------------------------------------
def _validate_manifest_entries(entries: dict[str, str], pack_dir: Path) -> list[str]:
    """Refuse chemins absolus, traversées `..`, liens symboliques et cibles hors pack."""
    errors: list[str] = []
    root = pack_dir.resolve()
    for rel in entries:
        candidate = rel.strip()
        if not candidate:
            errors.append("entrée de manifeste vide")
            continue
        normalized = candidate.replace("\\", "/")
        if normalized.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", normalized):
            errors.append(f"chemin absolu interdit dans le manifeste: {rel}")
            continue
        if ".." in normalized.split("/"):
            errors.append(f"traversée de répertoire interdite dans le manifeste: {rel}")
            continue
        target = (pack_dir / normalized).resolve()
        if not str(target).startswith(str(root) + "/") and target != root:
            errors.append(f"chemin hors pack: {rel}")
            continue
        if (pack_dir / normalized).is_symlink():
            errors.append(f"lien symbolique interdit dans le pack: {rel}")
            continue
        if not target.is_file():
            errors.append(f"fichier manquant: {rel}")
        name = Path(normalized).name
        if any(Path(name).match(pattern) for pattern in SECRET_NAME_PATTERNS):
            errors.append(f"fichier de secret interdit dans le pack: {rel}")
    return errors


def verify_pack(
    pack_dir: Path,
    replay: bool = False,
    oracle_timeout: float = 180.0,
    *,
    allow_oracle_cmd: bool = False,
) -> dict:
    """Vérifie un pack SANS exécuter de commande par défaut (sécurité).

    Par défaut : manifeste SHA-256 + cohérence interne uniquement. Le rejeu de l'oracle
    (commande non fiable venue du pack) exige `allow_oracle_cmd=True` explicitement, et
    n'accepte qu'une commande simple sans métacaractères shell.
    """
    result: dict = {
        "pack_dir": str(pack_dir),
        "ok": False,
        "manifest_ok": False,
        "errors": [],
        "warnings": [],
        "recorded_verdict": None,
        "dry_run": None,
        "checks": {},
        "replay": None,
        "origin_proven": False,
        "integrity_scope": "coherence_interne_auto_attestee",
        "notes": [
            "Le manifeste prouve une cohérence interne (auto-attestée), pas l'origine du pack.",
            "Aucune commande du pack n'est exécutée sans --allow-oracle-cmd.",
        ],
    }
    pack_dir = Path(pack_dir)
    if not pack_dir.is_dir():
        result["errors"].append(f"pack introuvable: {pack_dir}")
        return result

    missing = [name for name in REQUIRED_FILES if not (pack_dir / name).is_file()]
    result["checks"]["required_files"] = not missing
    if missing:
        result["errors"].append(f"fichiers requis manquants: {', '.join(missing)}")

    entries = manifest_entries(pack_dir)
    result["checks"]["manifest_present"] = bool(entries)
    if not entries:
        result["errors"].append("manifest.sha256 absent ou illisible")

    path_errors = _validate_manifest_entries(entries, pack_dir)
    result["errors"].extend(path_errors)

    hash_errors: list[str] = []
    for rel, expected in entries.items():
        target = pack_dir / rel
        if target.is_file() and not target.is_symlink() and sha256_file(target) != expected:
            hash_errors.append(f"hash invalide: {rel}")
    listed = set(entries)
    actual = {
        str(path.relative_to(pack_dir)).replace("\\", "/")
        for path in iter_all_files(pack_dir)
        if path.name != MANIFEST_NAME
    }
    for rel in sorted(actual - listed):
        hash_errors.append(f"fichier non listé dans le manifeste: {rel}")
    result["checks"]["manifest_hashes"] = not hash_errors and not path_errors
    result["errors"].extend(hash_errors)
    result["manifest_ok"] = not missing and not hash_errors and not path_errors

    run_path = pack_dir / "run.json"
    run: dict = {}
    if run_path.is_file():
        try:
            run = json.loads(run_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            result["errors"].append(f"run.json illisible (JSON invalide): {exc}")
            run = {}
    result["recorded_verdict"] = run.get("verdict")
    result["dry_run"] = bool(run.get("dry_run"))
    result["checks"]["recorded_verdict"] = result["recorded_verdict"]
    oracle_info = run.get("oracle") or {}
    recorded_passed = bool(oracle_info.get("verdict_passed"))
    command = oracle_info.get("command")
    recorded_verified = bool(oracle_info.get("execution_verified", recorded_passed))

    if replay or allow_oracle_cmd:
        if not allow_oracle_cmd:
            result["warnings"].append(
                "rejeu non exécuté (sécurité) : passer --allow-oracle-cmd pour rejouer l'oracle"
            )
        elif result["dry_run"]:
            result["warnings"].append("pack dry-run : rejeu oracle inutile (simulation)")
        elif not command:
            result["errors"].append("rejeu demandé mais run.json ne contient aucune commande oracle")
        elif not recorded_verified:
            result["warnings"].append(
                "le run enregistré n'a pas de preuve d'exécution de tests : rejeu exécuté pour inspection seule"
            )
            _replay_oracle(result, pack_dir, command, oracle_timeout, recorded_passed, check_verdict=False)
        else:
            _replay_oracle(result, pack_dir, command, oracle_timeout, recorded_passed, check_verdict=True)
    else:
        result["warnings"].append(
            "rejeu oracle non exécuté par défaut (sécurité) — utiliser --allow-oracle-cmd"
        )

    result["ok"] = result["manifest_ok"] and not result["errors"]
    replay_info = result.get("replay") or {}
    replay_ok = bool(
        replay_info.get("executed")
        and replay_info.get("match")
        and replay_info.get("execution_verified")
        and not replay_info.get("refused")
    )
    result["verdict_replayed"] = replay_ok
    if not result["manifest_ok"] or (result["errors"] and not replay_ok):
        result["label"] = "PACK ALTERE/INVALIDE"
        result["label_detail"] = "intégrité ou rejeu invalide"
        result["exit_code"] = 1
    elif replay_ok:
        result["label"] = "PACK VALIDE"
        result["label_detail"] = "rejeu oracle réussi et cohérent avec le verdict enregistré"
        result["exit_code"] = 0
    elif result["dry_run"]:
        result["label"] = "PACK COHERENT"
        result["label_detail"] = "intégrité OK, pack dry-run : verdict simulé, non rejoué (origine non prouvée)"
        result["exit_code"] = 0
    else:
        result["label"] = "PACK COHERENT"
        result["label_detail"] = "intégrité OK, verdict NON rejoué (origine non prouvée)"
        result["exit_code"] = 0
    return result


def _replay_oracle(
    result: dict,
    pack_dir: Path,
    command: str,
    oracle_timeout: float,
    recorded_passed: bool,
    *,
    check_verdict: bool,
) -> None:
    source = pack_dir / "source"
    tree = pack_dir / "tree"
    if not (source.is_dir() and tree.is_dir()):
        result["errors"].append("rejeu impossible : source/ ou tree/ absent")
        return
    with tempfile.TemporaryDirectory(prefix="swarmproof-verify-") as tmp:
        eval_tree = copy_tree(tree, Path(tmp) / "judge")
        restored = restore_paths(source, eval_tree, discover_test_paths(source))
        replayed = run_oracle(eval_tree, command, oracle_timeout, safe_command=True)
        replay_verified = bool(replayed.get("execution_verified"))
        replay_passed = bool(replayed.get("passed"))
        result["replay"] = {
            "executed": True,
            "safe_mode": True,
            "refused": bool(replayed.get("refused")),
            "passed": replay_passed,
            "execution_verified": replay_verified,
            "recorded_passed": recorded_passed,
            "match": replay_passed == recorded_passed,
            "exit_code": replayed.get("exit_code"),
            "tests_run": replayed.get("tests_run"),
            "restored_test_paths": restored,
            "duration_seconds": replayed.get("duration_seconds"),
            "command": command,
        }
        if replayed.get("refused"):
            result["errors"].append("rejeu refusé : commande non simple (métacaractères shell interdits)")
            return
        if not replay_verified:
            result["warnings"].append("rejeu sans preuve d'exécution de tests : résultat non concluant")
        if check_verdict and replay_passed != recorded_passed:
            result["errors"].append(
                f"verdict rejoué ({'PASS' if replay_passed else 'FAIL'}) != verdict enregistré "
                f"({'PASS' if recorded_passed else 'FAIL'})"
            )
        if check_verdict and result.get("recorded_verdict") == "PASS" and not replay_passed:
            result["errors"].append("le pack annonce PASS mais l'oracle rejoué échoue")
