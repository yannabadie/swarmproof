"""Pré-pack statique optionnel via AgentProof (audit déterministe, sans LLM).

Intégration **optionnelle et non bloquante** : si `agentproof` est importable (paquet voisin
`product/agentproof`), un audit statique du dépôt est joint au pack SwarmProof. Sinon, le
pré-pack est marqué « non exécuté » avec la raison — jamais d'échec du run principal.
"""

from __future__ import annotations

import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from swarmproof.util import sha256_file

_WORKSPACE = Path(__file__).resolve().parents[3]


def find_agentproof() -> tuple[Path | None, str | None]:
    """Retourne (répertoire du paquet agentproof, raison si absent)."""
    candidates: list[Path] = []
    env_value = os.environ.get("SWARMPROOF_AGENTPROOF")
    if env_value:
        candidates.append(Path(env_value).expanduser())
    candidates.append(_WORKSPACE / "product" / "agentproof")
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if (resolved / "agentproof" / "__init__.py").is_file():
            return resolved, None
    return None, "paquet `agentproof` introuvable (integration optionnelle désactivée)"


def run_prepack(repo: Path, out_root: Path) -> dict:
    """Exécute l'audit AgentProof et écrit son pack sous `out_root` (résumé retourné)."""
    package_dir, reason = find_agentproof()
    if package_dir is None:
        return {"status": "not_run", "reason": reason}
    try:
        if str(package_dir) not in sys.path:
            sys.path.insert(0, str(package_dir))
        agentproof = importlib.import_module("agentproof")
        evidence = importlib.import_module("agentproof.evidence")
        generated_at = datetime.now(timezone.utc)
        audit = agentproof.run_audit(repo, name=repo.name)
        pack_dir = evidence.write_pack(
            audit,
            out_root,
            generated_at,
            command=f"agentproof audit {repo}",
        )
        scores = audit.scores
        return {
            "status": "ok",
            "tool": "agentproof",
            "version": getattr(agentproof, "__version__", "unknown"),
            "pack_dir": str(pack_dir),
            "manifest_sha256": sha256_file(pack_dir / "manifest.sha256"),
            "score": scores.global_score,
            "grade": scores.grade,
            "grade_label": scores.grade_label,
            "severity_counts": scores.severity_counts,
            "files_total": audit.files_total,
            "repo_commit": audit.repo_commit,
            "generated_at": generated_at.isoformat(timespec="seconds"),
        }
    except Exception as exc:  # défensif : le pré-pack ne doit jamais casser le run
        return {"status": "error", "reason": f"{type(exc).__name__}: {exc}"[:300]}
